"""Exercise preview worker lifetime and interruption using real stdio pipes."""

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from src.worker_client import BackgroundPreviewWorker, LoadCancelledInWorker, WorkerTimeoutError


WORKER_SCRIPT = """
import json, os, sys, time
for line in sys.stdin:
    request = json.loads(line)
    path = request['args']['bundle_path']
    if path.startswith('lock:'):
        with open(path[5:], 'wb') as locked:
            locked.write(b'worker holds file open')
            locked.flush()
            time.sleep(60)
    if path == 'slow':
        time.sleep(60)
    if path == 'exit':
        sys.exit(1)
    result = {'id': request['id']}
    if path == 'bad':
        result['error'] = 'invalid bundle'
    else:
        result['result'] = {'pid': os.getpid()}
    print(json.dumps(result), flush=True)
"""


class BackgroundWorkerTests(unittest.TestCase):
    def setUp(self):
        def spawn(_mode):
            return subprocess.Popen(
                [sys.executable, "-u", "-c", WORKER_SCRIPT],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8",
            )
        self.patch = patch("src.worker_client._spawn_worker", side_effect=spawn)
        self.spawn = self.patch.start()
        self.worker = BackgroundPreviewWorker()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.worker.close)

    def test_warmup_reuses_process_and_bundle_error_allows_next_request(self):
        self.worker.warmup()
        first = self.worker.preview(Path("ok"))
        with self.assertRaisesRegex(RuntimeError, "invalid bundle"):
            self.worker.preview(Path("bad"))
        self.assertEqual(first, self.worker.preview(Path("ok")))
        self.assertEqual(self.spawn.call_count, 1)
        proc = self.worker._proc
        self.worker.close()
        self.assertIsNotNone(proc.poll())

    def test_cancel_kills_worker_and_next_request_restarts(self):
        first = self.worker.preview(Path("ok"))
        proc = self.worker._proc
        cancel = threading.Event()
        timer = threading.Timer(0.1, cancel.set)
        timer.start()
        try:
            with self.assertRaises(LoadCancelledInWorker):
                self.worker.preview(Path("slow"), cancel_check=cancel.is_set)
        finally:
            timer.cancel()
        self.assertIsNotNone(proc.poll())
        self.assertNotEqual(first, self.worker.preview(Path("ok")))

    def test_timeout_or_crash_is_recoverable(self):
        for path in ("slow", "exit"):
            with self.subTest(path=path):
                self.worker.preview(Path("ok"))
                proc = self.worker._proc
                with self.assertRaises(WorkerTimeoutError):
                    self.worker.preview(Path(path), timeout=0.1)
                self.assertIsNotNone(proc.poll())
                self.assertIn("pid", self.worker.preview(Path("ok")))

    @unittest.skipUnless(os.name == "nt", "Windows file-lock and venv launcher regression")
    def test_cancel_closes_actual_workers_file_before_parent_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            locked = Path(directory) / "in-progress.tmp"
            with self.assertRaises(LoadCancelledInWorker):
                self.worker.preview("lock:" + str(locked), cancel_check=locked.exists, timeout=5)
            locked.unlink()  # Fails with WinError 32 if the launched worker survives.


if __name__ == "__main__":
    unittest.main()

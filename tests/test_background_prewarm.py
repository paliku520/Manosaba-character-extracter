"""Verify batch prewarming, partial failures, cancellation, and cache cleanup."""

import base64
import io
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from run import JsApi
from src.background_assets import BackgroundPreviewCache


class BackgroundPrewarmTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.api = object.__new__(JsApi)
        self.api._temp_dir = root / "temp"
        self.api._background_preview_cache = BackgroundPreviewCache(
            max_bytes=1, directory=self.api._temp_dir / "background-previews",
        )
        self.api._background_bundles = {}
        for i in range(3):
            path = root / f"{i}.bundle"
            path.write_bytes(b"bundle")
            self.api._background_bundles[str(i)] = {"id": str(i), "bundle_path": str(path)}
        with Image.new("RGBA", (12, 6)) as image, io.BytesIO() as stream:
            image.save(stream, format="PNG")
            self.preview = {"name": "preview", "size": [12, 6], "count": 1,
                            "data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")}
        self.api._background_preview_worker = SimpleNamespace(preview=Mock(return_value=self.preview))
        self.api._background_cancel = threading.Event()
        self.api._background_lock = threading.Lock()
        self.api._work_lock = threading.Lock()
        self.api._char_busy = False
        self.api._loading_path = None
        self.events = []
        self.api._emit = lambda event, payload: self.events.append((event, payload))
        self.api._run_async = lambda task: task()

    def test_prewarm_all_reuses_disk_entries_and_does_not_change_selection_or_export_count(self):
        self.assertTrue(self.api.prewarm_backgrounds()["ok"])
        completed = self.events[-1][1]
        self.assertEqual(completed, {"operation": "prewarm", "count": 3, "total": 3, "errors": []})
        self.assertEqual(self.api._background_preview_worker.preview.call_count, 3)
        self.api._background_preview_cache.clear()  # No memory cache entries survive.
        self.assertTrue(self.api.prewarm_backgrounds()["ok"])
        self.assertEqual(self.api._background_preview_worker.preview.call_count, 3)
        self.assertEqual(self.api._background_preview_cache._bytes, 0)
        self.assertNotIn("export_count", completed)
        self.assertEqual(len(self.api._background_bundles), 3)

    def test_prewarm_reports_partial_failure_and_continues(self):
        self.api._background_preview_worker.preview.side_effect = [self.preview, ValueError("bad bundle"), self.preview]
        self.api.prewarm_backgrounds()
        self.assertEqual(self.events[-1][1]["count"], 2)
        self.assertEqual(self.events[-1][1]["errors"], [{"id": "1", "message": "bad bundle"}])
        self.assertEqual([p["current"] for e, p in self.events if e == "background_progress"], [1, 2, 3])

    def test_cancel_retains_completed_cache_and_next_prewarm_resumes(self):
        def emit(event, payload):
            self.events.append((event, payload))
            if event == "background_progress":
                self.api.cancel_backgrounds()
        self.api._emit = emit
        self.api.prewarm_backgrounds()
        self.assertTrue(self.events[-1][1]["cancelled"])
        self.assertEqual(len(list(self.api._background_preview_cache.directory.glob("*.png"))), 1)
        self.api._emit = lambda event, payload: self.events.append((event, payload))
        self.api.prewarm_backgrounds()
        self.assertEqual(self.events[-1][1]["count"], 3)
        self.assertEqual(self.api._background_preview_worker.preview.call_count, 3)

    def test_clear_cache_removes_background_previews_when_character_preview_is_retained(self):
        self.api.prewarm_backgrounds()
        character_preview = self.api._temp_dir / "preview"
        character_preview.mkdir()
        (character_preview / "test.png").write_bytes(b"keep")
        self.api.clear_cache(keep_preview=True)
        self.assertFalse(self.api._background_preview_cache.directory.exists())
        self.assertTrue((character_preview / "test.png").exists())


if __name__ == "__main__":
    unittest.main()

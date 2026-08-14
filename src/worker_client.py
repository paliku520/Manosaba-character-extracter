"""提取工作进程客户端（方案 A）

将 UnityPy 提取（extract_character_data / extract_sprites / export_sprites）放入
独立子进程执行（backend.py --worker），绕开"backend 进程内首次 UnityPy 提取偶发卡死"
的问题（独立进程已验证首次提取正常）。

父进程（backend）调用 run_extract_worker()：
  1. spawn 子进程：开发模式 [python backend.py --worker]；打包后 [backend.exe --worker]
  2. 发一行 JSON 请求 {id, kind, args}
  3. 子进程：执行提取 → 进度经 stdout {event:progress} 上报 → 完成写 {id, result}
  4. 父进程：读 stdout 转发进度；支持取消（kill）与"无进展超时 kill 后上层重试"
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional


class WorkerTimeoutError(Exception):
    """提取子进程无进展超时（视为卡死，由上层 kill 后重试）"""


class LoadCancelledInWorker(Exception):
    """用户取消（父进程 kill 子进程）"""


def _spawn_worker() -> subprocess.Popen:
    """启动提取工作子进程（同一 backend.py/exe 的 --worker 模式）"""
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--worker"]
    else:
        backend_py = str(Path(__file__).resolve().parent.parent / "backend.py")
        cmd = [sys.executable, backend_py, "--worker"]
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
        text=True,
        encoding="utf-8",
        bufsize=1,
    )


def _stderr_reader(proc: subprocess.Popen) -> None:
    """透传子进程 stderr（已格式化日志，保留原始内容）到父进程 stderr"""
    try:
        for line in proc.stderr:
            sys.stderr.write(line)
            sys.stderr.flush()
    except Exception:
        pass


def _kill(proc: subprocess.Popen) -> None:
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=3)
    except Exception:
        pass


def run_extract_worker(
    kind: str,
    args: Dict,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    no_progress_timeout: float = 45.0,
    total_timeout: float = 600.0,
):
    """在子进程中执行一次提取，返回结果。

    Args:
        kind: 提取类型（extract_character / extract_sprites / export_sprites）
        args: 传给子进程的参数 dict（bundle_path / output_dir / has_components 等）
        progress_callback: 进度回调 fn(current, total)
        cancel_check: 返回 True 时中断并抛 LoadCancelledInWorker
        no_progress_timeout: 无任何 stdout 输出的秒数 → 视为卡死抛 WorkerTimeoutError
        total_timeout: 总超时上限
    """
    proc = _spawn_worker()
    last_activity = [time.monotonic()]
    result_box: Dict = {}

    def _reader() -> None:
        try:
            for line in proc.stdout:
                last_activity[0] = time.monotonic()
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                if msg.get("event") == "progress" and progress_callback is not None:
                    pl = msg.get("payload") or {}
                    try:
                        progress_callback(int(pl.get("current", 0)), int(pl.get("total", 1)))
                    except Exception:
                        pass
                elif msg.get("id") is not None:
                    result_box["msg"] = msg
                    return
        except Exception:
            pass

    threading.Thread(target=_reader, daemon=True).start()
    threading.Thread(target=_stderr_reader, args=(proc,), daemon=True).start()

    try:
        proc.stdin.write(json.dumps({"id": 1, "kind": kind, "args": args}) + "\n")
        proc.stdin.flush()
    except Exception as e:
        _kill(proc)
        raise WorkerTimeoutError(f"failed to send worker request: {e}")

    start = time.monotonic()
    while "msg" not in result_box:
        if cancel_check is not None and cancel_check():
            _kill(proc)
            raise LoadCancelledInWorker()
        if time.monotonic() - last_activity[0] > no_progress_timeout:
            _kill(proc)
            raise WorkerTimeoutError("extract worker no progress (killed)")
        if time.monotonic() - start > total_timeout:
            _kill(proc)
            raise WorkerTimeoutError("extract worker total timeout (killed)")
        if proc.poll() is not None and "msg" not in result_box:
            # 子进程提前退出且未返回结果
            _kill(proc)
            raise WorkerTimeoutError("extract worker exited without result")
        time.sleep(0.1)

    msg = result_box["msg"]
    if msg.get("error"):
        raise RuntimeError(str(msg["error"]))
    return msg.get("result")

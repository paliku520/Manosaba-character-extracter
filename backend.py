"""Electron 后端入口：stdio JSON-RPC 服务（stdin 请求 / stdout 响应，每行一个 JSON）。

前端 window.pywebview.api.<method>(...) → Electron 主进程 → 本进程 stdin → 处理后 stdout 响应。
事件推送: {"event": <name>, "payload": {...}} 由 Electron 主进程转发给前端 window.__pywebview.events。

复用 run.py 的 JsApi（业务逻辑零复制），仅替换 pywebview 相关实现：
  - _emit           → stdout 事件行
  - _on_gui_thread  → 直接执行（对话框由 Electron 主进程接管，preload 已拦截）
  - 窗口控制方法     → 由 Electron 主进程处理（preload 白名单拦截，不经过本进程）
"""

import json
import os
import queue
import shutil
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# 数据目录重定向（Electron 打包后 backend 位于 resources/ 不可写；必须在 import run（→ settings）之前设置）
_DATA_DIR = os.environ.get("MCE_DATA_DIR")
if _DATA_DIR:
    os.environ["MCE_DATA_DIR"] = str(Path(_DATA_DIR))

import run  # noqa: E402  复用 run.py 的 JsApi 与模块级工具函数
from run import JsApi  # noqa: E402
from src.logtools import configure, log  # noqa: E402

# 业务数据目录（output/ temp/ logs/）同样重定向到数据目录
if _DATA_DIR:
    run.BASE_DIR = Path(_DATA_DIR)
    run.MEI_DIR = Path(_DATA_DIR)

# 日志目录：优先跟随 MCE_DATA_DIR（main.js 已探测为可写目录）。
# 打包安装到 Program Files 等受保护目录时，exe 所在目录（resources/backend）对普通用户不可写，
# 若日志仍写到 exe 目录会因 mkdir PermissionError 导致后端启动即崩溃（前端表现为 "backend exited"）。
# 注意 run.BASE_DIR 已在上方重定向，但那是 run 模块的业务目录；本模块日志目录需单独跟随数据目录。
_LOG_BASE = (
    Path(_DATA_DIR)
    if _DATA_DIR
    else (Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent)
)


# stdout 写入锁（emit 后台线程与主线程响应共用，防止 JSON 行撕裂）
_STDOUT_LOCK = threading.Lock()

# 事件异步输出：worker 只入队，由后台 daemon 线程写 stdout。
# 避免 stdout 管道缓冲满（Electron 主进程 console.log 到 cmd 终端渲染慢 → 不读管道）时
# 阻塞 worker 线程（表现为首次提取卡死、无日志）。
_EMIT_QUEUE: "queue.Queue[Optional[str]]" = queue.Queue()
_EMIT_THREAD: Optional[threading.Thread] = None
_EMIT_LOCK = threading.Lock()


def _emit_worker() -> None:
    """事件写线程：消费队列，持锁写 stdout（行级原子）"""
    while True:
        line = _EMIT_QUEUE.get()
        if line is None:
            return
        try:
            with _STDOUT_LOCK:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
        except Exception:
            pass


def _ensure_emit() -> None:
    global _EMIT_THREAD
    if _EMIT_THREAD is not None:
        return
    with _EMIT_LOCK:
        if _EMIT_THREAD is None:
            _EMIT_THREAD = threading.Thread(target=_emit_worker, name="emit-writer", daemon=True)
            _EMIT_THREAD.start()


def _flush_emit(timeout: float = 2.0) -> None:
    """退出前同步消费事件队列直到空"""
    import time as _t
    deadline = _t.monotonic() + timeout
    while _t.monotonic() < deadline:
        try:
            line = _EMIT_QUEUE.get(timeout=0.1)
        except queue.Empty:
            if _EMIT_QUEUE.empty():
                return
            continue
        try:
            with _STDOUT_LOCK:
                if line is not None:
                    sys.stdout.write(line + "\n")
                    sys.stdout.flush()
        except Exception:
            pass


def _emit(self, event: str, payload: dict):
    """事件推送：入队后由后台线程写一行 JSON 到 stdout（不阻塞调用线程）"""
    try:
        line = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        _ensure_emit()
        _EMIT_QUEUE.put(line)
    except Exception as e:
        log("warning", f"[backend] emit {event} failed: {e}")


def _on_gui_thread(self, fn):
    """Electron 模式下无需 WinForms GUI 线程，直接执行"""
    return fn()


# 打补丁：替换 pywebview 相关实现
JsApi._emit = _emit
JsApi._on_gui_thread = staticmethod(_on_gui_thread)


def _startup_logs():
    """与 run.py 一致的启动生命周期日志（语言加载 / 启动 / 免责声明 / banner）"""
    from src.i18n import LANGUAGE_CODES, _, set_lang as _set_lang
    from src.settings import get_lang as _get_lang

    saved = _get_lang()
    if saved and saved in LANGUAGE_CODES:
        _set_lang(saved)
        log("info", _("log.lang_from_settings", code=saved))
    else:
        det = run._detect_system_language()
        _set_lang(det)
        log("info", _("log.lang_detected", code=det))

    log("info", _("log.app_started", version=run.__version__))
    log("info", _("app.disclaimer"))

    # banner 走日志队列（与普通日志同一后台线程串行写 stderr，避免并发写导致换行粘连）
    from src.logtools import flush_logs, log_raw
    log_raw("")
    log_raw("=" * 48)
    log_raw(_("console.startup_msg_electron"))  # Electron 日志控制台：关闭不退出程序
    log_raw("=" * 48)
    log_raw("")
    flush_logs()


def _shutdown_logs():
    """与 run.py 一致的退出生命周期日志（免责声明 / 退出 / preview 清理 / GC / banner）"""
    from src.i18n import _

    try:
        log("info", _("app.disclaimer"))
        log("info", _("log.app_exited"))
        preview_dir = run.BASE_DIR / "temp" / "preview"
        if preview_dir.exists():
            shutil.rmtree(preview_dir, ignore_errors=True)
            log("info", _("log.preview_cleaned", path=str(preview_dir)))
    except Exception:
        pass

    try:
        import gc
        collected = gc.collect()
        from src.resource_monitor import process_memory_mb
        mem = round(process_memory_mb(), 1)
        log("info", _("log.gc_before_exit", mem=mem, count=collected))
    except Exception:
        log("info", _("log.gc_before_exit", mem=0, count=0))

    # banner 走日志队列（与普通日志同一后台线程串行写 stderr，避免并发写导致换行粘连）；退出前 flush 保证写出
    from src.logtools import flush_logs, log_raw
    log_raw("")
    log_raw("=" * 48)
    log_raw(_("console.exit_msg_electron"))
    log_raw("=" * 48)
    log_raw("")
    try:
        flush_logs()
    except Exception:
        pass  # 主进程可能已退出（管道关闭），忽略


def _worker_main() -> None:
    """提取工作子进程入口（backend.py --worker）：执行一次 UnityPy 提取。

    父进程（src.worker_client）spawn 本模式子进程 → 发一行 JSON 请求 →
    子进程执行提取 → 进度经 stdout {event:progress} 上报 → 完成写 {id, result}。
    日志走 stderr（logtools 配置到 stderr），避免污染 stdout JSON 协议。
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    from src.logtools import configure as _cfg
    _cfg(stream=sys.stderr, color=False)

    from src.compositor import extract_character_data, extract_sprites
    from src.export_manager import export_sprites as _export_sprites

    def _send(obj) -> None:
        try:
            sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            kind = req.get("kind")
            args = req.get("args") or {}

            def _cb(cur: int, total: int) -> None:
                _send({"event": "progress", "payload": {"current": cur, "total": total}})

            bp = str(args["bundle_path"])
            out = str(args["output_dir"])
            if kind == "extract_character":
                result = extract_character_data(Path(bp), Path(out), progress_callback=_cb)
            elif kind == "extract_sprites":
                result = extract_sprites(Path(bp), Path(out), progress_callback=_cb)
            elif kind == "export_sprites":
                result = _export_sprites(
                    Path(bp), Path(out),
                    has_components=bool(args.get("has_components", False)),
                    progress_callback=_cb,
                )
            else:
                result = {"error": f"unknown worker kind: {kind}"}
            _send({"id": rid, "result": result})
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            _send({"id": rid, "error": f"{type(e).__name__}: {e}"})
        break  # 一个子进程只服务一个请求（无状态残留，父进程按需重开）


def main():
    # Windows 下 stdout/stderr 默认 GBK，JSON 可能含 © 等字符 → 强制 UTF-8
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # 日志输出到 stderr：Electron 主进程会转发打印到启动终端；stdout 专用于 JSON 协议
    # color=True：保留 ANSI 颜色高亮（现代终端 Win10+ 默认支持 VT；start.bat 已 chcp 65001 解决代码页）
    try:
        # 日志文件写入数据目录（_LOG_BASE 已跟随 MCE_DATA_DIR，Program Files 等受保护目录下可正常创建）
        configure(log_file=_LOG_BASE / "logs" / f"{ts}.log", level="info", stream=sys.stderr, color=True)
    except Exception:
        # 兜底：日志目录创建/写入失败不阻断启动（仅输出到 stderr，退出清理同样不因日志崩溃）
        traceback.print_exc(file=sys.stderr)
        configure(level="info", stream=sys.stderr, color=True)

    # 启动生命周期日志（与 run.py 一致）
    _startup_logs()

    api = JsApi()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            method = req.get("method")
            args = req.get("args") or []
            fn = getattr(api, method, None)
            if fn is None:
                with _STDOUT_LOCK:
                    sys.stdout.write(
                        json.dumps({"id": rid, "error": f"no such method: {method}"}) + "\n"
                    )
                    sys.stdout.flush()
                continue
            result = fn(*args)
            with _STDOUT_LOCK:
                sys.stdout.write(
                    json.dumps({"id": rid, "result": result}, ensure_ascii=False, default=str)
                    + "\n"
                )
                sys.stdout.flush()
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            with _STDOUT_LOCK:
                sys.stdout.write(
                    json.dumps({"id": rid, "error": f"{type(e).__name__}: {e}"}) + "\n"
                )
                sys.stdout.flush()

    # stdin EOF（Electron 主进程窗口关闭/退出时关闭管道）→ 优雅退出清理
    _shutdown_logs()
    _flush_emit()
    from src.logtools import flush_logs
    flush_logs()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker_main()  # 提取工作子进程模式（方案 A）
    else:
        main()

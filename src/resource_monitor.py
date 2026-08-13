"""
资源占用监视模块（调试模式用）

后台线程定期采集当前进程的内存 / CPU / 窗口分辨率，通过回调推送给上层
（run.py 的 JsApi 会转发为 res_monitor 事件并在状态栏显示）。

仅使用标准库（ctypes + time + threading），无额外依赖。
"""

import os
import threading
import time
from typing import Callable, Dict, Optional, Tuple


def process_memory_mb() -> float:
    """返回当前进程内存占用（MB）。

    Windows 用 psapi 的 GetProcessMemoryInfo（标准库 ctypes 实现，无 psutil 依赖）。
    失败时返回 0.0。
    """
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        pid = kernel32.GetCurrentProcessId()
        handle = kernel32.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION | VM_READ
        if not handle:
            return 0.0
        try:
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), ctypes.sizeof(counters)):
                return counters.WorkingSetSize / (1024.0 * 1024.0)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    return 0.0


class ResourceMonitor:
    """后台线程定期采集内存 / CPU / 窗口分辨率，通过回调推送。

    Args:
        emit: 回调（接收 payload: dict），每次采集完成调用一次。
              payload 含 mem_mb / cpu，若窗口尺寸可得则含 width / height。
        window_size: 可选回调（返回 (w, h) 或 None），用于在 GUI 线程安全获取窗口尺寸。
        interval: 采集间隔（秒）。
    """

    def __init__(
        self,
        emit: Callable[[Dict], None],
        window_size: Optional[Callable[[], Optional[Tuple[int, int]]]] = None,
        interval: float = 5.0,
    ):
        self._emit = emit
        self._window_size = window_size
        self._interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动监视线程（幂等：已运行时忽略）"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止监视线程（下一次循环自然退出）"""
        self._running = False

    def _loop(self) -> None:
        cores = os.cpu_count() or 1
        prev_cpu = time.process_time()
        prev_wall = time.perf_counter()
        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break
            try:
                mem_mb = process_memory_mb()
                cur_cpu = time.process_time()
                cur_wall = time.perf_counter()
                dt = cur_wall - prev_wall
                cpu = (cur_cpu - prev_cpu) / dt * 100.0 / cores if dt > 0 else 0.0
                prev_cpu, prev_wall = cur_cpu, cur_wall

                payload: Dict = {"mem_mb": round(mem_mb, 1), "cpu": round(cpu, 1)}
                if self._window_size:
                    size = self._window_size()
                    if size:
                        payload["width"], payload["height"] = size
                self._emit(payload)
            except Exception:
                pass

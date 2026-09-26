"""
在系统文件管理器中打开目录 / 定位文件（复用并聚焦已打开的资源管理器窗口）

需求背景（点击「打开输出目录」这类按钮时）：
    1) 应聚焦弹出的资源管理器窗口 —— 发起者是 Electron 派生的 Python 子进程，没有前台
       激活权，Windows 不允许它把别的进程的窗口抢到前台，窗口往往开在主窗口背后；
    2) 不应频繁创建新的资源管理器窗口 —— 该目录已在资源管理器中打开时应复用并聚焦，
       而不是再开一个（连点按钮、窗口尚未就绪时尤其明显）。

实现（仅 Windows 做增强，纯标准库 ctypes，无额外依赖）：
    1. 先查已打开的资源管理器文件夹窗口（CabinetWClass / ExploreWClass）：
       - 本进程最近聚焦过的窗口句柄（缓存，精确匹配，仅由本模块写入）；
       - 标题等于完整路径（资源管理器开启“显示完整路径”时）或等于目录名且唯一的窗口；
       命中 → 直接前置聚焦，不新开窗口。
    2. 未命中 → os.startfile 交给系统打开，随后短时间内轮询：
       - 窗口集合里「新增」的窗口即本次打开的窗口 → 精确聚焦；
       - 若系统复用了已有窗口（没有新增）→ 回退按标题定位并聚焦。
    3. 同一目录在打开过程中重复点击 → 直接返回（由进行中的那一次负责聚焦），且刚打开过的
       目录在一个短窗口内不再重复 os.startfile，避免重复开窗。
    4. 任何一步失败都回退到「直接 os.startfile」，功能不因增强逻辑而失效。

定位文件（`reveal`）：
    用 Shell 官方 API `SHOpenFolderAndSelectItems`（打开所在目录并选中该项，已打开的窗口会被复用），
    随后同样显式聚焦（该 API 不保证抢到前台）；Shell 调用失败时回退为「打开所在目录」。

注意：开窗/聚焦在后台线程执行（backend.py 的主循环是顺序处理请求，阻塞会拖慢其它 API）；
日志经 logtools 的写线程输出，线程安全。非 Windows 平台保持原有行为。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.logtools import log

_IS_WIN = sys.platform == "win32"

# 资源管理器「文件夹窗口」的窗口类
_EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}

_FOCUS_TIMEOUT = 1.5      # 打开后等待窗口出现的上限（秒）
_POLL_INTERVAL = 0.04     # 轮询间隔（秒）
_REOPEN_TTL = 2.0         # 刚打开过的目录在该时间内重复点击只当作“聚焦”，不再开窗
_CACHE_MAX = 32           # 缓存上限（目录数），避免长期运行后无限增长

SW_RESTORE = 9
SW_SHOW = 5

_lock = threading.Lock()
_inflight: Set[str] = set()          # 正在打开/聚焦中的目录（normcase 归一化后）
_hwnd_cache: Dict[str, int] = {}     # 目录 → 最近聚焦的窗口句柄
_recent: Dict[str, float] = {}       # 目录 → 最近一次真正发起打开的时刻


# ── Win32 API 绑定 ────────────────────────────────────────────

class _Win32:
    """user32 / kernel32 函数签名（HWND 是 64 位指针，必须声明 argtypes 否则会被截断）。"""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        # Shell 定位文件用（SHOpenFolderAndSelectItems）；个别系统缺导出也不影响上面的聚焦能力
        self.shell32 = None
        self.ole32 = None
        try:
            s = ctypes.WinDLL("shell32", use_last_error=True)
            o = ctypes.WinDLL("ole32", use_last_error=True)
            s.SHParseDisplayName.argtypes = [
                wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
            ]
            s.SHParseDisplayName.restype = ctypes.c_long            # HRESULT
            s.SHOpenFolderAndSelectItems.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, wintypes.DWORD,
            ]
            s.SHOpenFolderAndSelectItems.restype = ctypes.c_long    # HRESULT
            o.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            o.CoInitializeEx.restype = ctypes.c_long
            o.CoUninitialize.argtypes = []
            o.CoTaskMemFree.argtypes = [ctypes.c_void_p]
            self.shell32, self.ole32 = s, o
        except Exception as e:
            log("debug", f"shell_open: shell32/ole32 bind failed: {e}")

        u, k = self.user32, self.kernel32
        u.EnumWindows.argtypes = [self.WNDENUMPROC, wintypes.LPARAM]
        u.EnumWindows.restype = wintypes.BOOL
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.restype = ctypes.c_int
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetWindowTextLengthW.restype = ctypes.c_int
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.restype = ctypes.c_int
        u.IsWindow.argtypes = [wintypes.HWND]
        u.IsWindow.restype = wintypes.BOOL
        u.IsIconic.argtypes = [wintypes.HWND]
        u.IsIconic.restype = wintypes.BOOL
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.ShowWindow.restype = wintypes.BOOL
        u.BringWindowToTop.argtypes = [wintypes.HWND]
        u.BringWindowToTop.restype = wintypes.BOOL
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.SetForegroundWindow.restype = wintypes.BOOL
        u.GetForegroundWindow.argtypes = []
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        u.AttachThreadInput.restype = wintypes.BOOL
        k.GetCurrentThreadId.argtypes = []
        k.GetCurrentThreadId.restype = wintypes.DWORD


_win: Optional[_Win32] = None


def _api() -> Optional[_Win32]:
    """惰性初始化 Win32 绑定（非 Windows / 初始化失败返回 None）。"""
    global _win
    if _win is None:
        if not _IS_WIN:
            return None
        try:
            _win = _Win32()
        except Exception as e:      # 增强逻辑失效不影响开窗：回退到系统默认行为
            log("debug", f"shell_open: win32 init failed: {e}")
            return None
    return _win


# ── 窗口查询 / 聚焦 ───────────────────────────────────────────

def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _window_title(hwnd: int) -> str:
    api = _api()
    if not api:
        return ""
    try:
        n = api.user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return ""
        buf = api.ctypes.create_unicode_buffer(n + 2)
        api.user32.GetWindowTextW(hwnd, buf, n + 2)
        return buf.value
    except Exception:
        return ""


def _cabinet_windows() -> List[Tuple[int, str]]:
    """枚举所有资源管理器文件夹窗口 → [(hwnd, 标题)]；失败返回空列表。"""
    api = _api()
    if not api:
        return []
    out: List[Tuple[int, str]] = []
    u, ct = api.user32, api.ctypes

    def _cb(hwnd, _lparam):
        try:
            buf = ct.create_unicode_buffer(64)
            u.GetClassNameW(hwnd, buf, 64)
            if buf.value in _EXPLORER_CLASSES:
                n = u.GetWindowTextLengthW(hwnd)
                tb = ct.create_unicode_buffer(n + 2)
                u.GetWindowTextW(hwnd, tb, n + 2)
                out.append((int(hwnd), tb.value))
        except Exception:
            pass
        return True

    try:
        u.EnumWindows(api.WNDENUMPROC(_cb), 0)
    except Exception:
        return []
    return out


def _title_is_folder(title: str, base: str, target: str) -> bool:
    """标题是否代表目标目录：等于目录名，或以「目录名 + 分隔」开头（Win11 多标签标题），
    或本身就是完整路径（资源管理器开启“显示完整路径”时）。"""
    if not title:
        return False
    t = title.strip()
    tl = t.casefold()
    bl = base.casefold()
    if tl == bl:
        return True
    for sep in (" - ", " – ", " — ", " · ", " and "):
        if tl.startswith(bl + sep):
            return True
    try:
        return _norm(t) == _norm(target)
    except Exception:
        return False


def _find_window(target: str) -> Optional[int]:
    """按标题定位已打开该目录的资源管理器窗口；不可靠时不猜（返回 None）。"""
    full = _norm(target)
    base = os.path.basename(os.path.normpath(target))
    wins = _cabinet_windows()
    # 1) 标题即完整路径：最精确
    for hwnd, title in wins:
        try:
            if title and _norm(title) == full:
                return hwnd
        except Exception:
            continue
    # 2) 标题即目录名：仅在唯一命中时才采用，避免聚焦到同名的无关目录
    hits = [hwnd for hwnd, title in wins if _title_is_folder(title, base, target)]
    return hits[0] if len(hits) == 1 else None


def _cached_window(key: str, base: str, target: str) -> Optional[int]:
    """本进程最近聚焦过的窗口（精确）；窗口已关闭或被导航到别处则失效。"""
    with _lock:
        hwnd = _hwnd_cache.get(key)
    if not hwnd:
        return None
    api = _api()
    if api and not api.user32.IsWindow(hwnd):
        hwnd = None                                    # 窗口已关闭
    elif not _title_is_folder(_window_title(hwnd), base, target):
        hwnd = None                                    # 窗口还在，但已不在目标目录（被导航走了）
    if not hwnd:
        with _lock:
            _hwnd_cache.pop(key, None)
    return hwnd


def _focus_window(hwnd: int) -> bool:
    """把窗口前置并激活。

    本进程是 Electron 的子进程、不是前台进程，SetForegroundWindow 会被前台锁定规则拒绝；
    先 AttachThreadInput 到前台线程的输入队列，再 SetForegroundWindow 即可绕过（标准做法）。
    """
    api = _api()
    if not api:
        return False
    u, k = api.user32, api.kernel32
    try:
        if not u.IsWindow(hwnd):
            return False
        u.ShowWindow(hwnd, SW_RESTORE)     # 最小化时先还原
        u.ShowWindow(hwnd, SW_SHOW)
        fg = u.GetForegroundWindow()
        if fg and int(fg) != int(hwnd):
            tid_fg = u.GetWindowThreadProcessId(fg, None)
            tid_cur = k.GetCurrentThreadId()
            attached = False
            if tid_fg and tid_fg != tid_cur:
                attached = bool(u.AttachThreadInput(tid_fg, tid_cur, True))
            try:
                u.BringWindowToTop(hwnd)
                u.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    u.AttachThreadInput(tid_fg, tid_cur, False)
        else:
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        return int(u.GetForegroundWindow()) == int(hwnd)
    except Exception as e:
        log("debug", f"shell_open: focus window failed: {e}")
        return False


def _remember(key: str, hwnd: int) -> None:
    with _lock:
        _hwnd_cache[key] = hwnd
        while len(_hwnd_cache) > _CACHE_MAX:
            _hwnd_cache.pop(next(iter(_hwnd_cache)))
        while len(_recent) > _CACHE_MAX:
            _recent.pop(next(iter(_recent)))


# ── 打开 ─────────────────────────────────────────────────────

def _startfile(target: str) -> None:
    """交给系统默认行为打开（Windows: ShellExecute；其它平台: open / xdg-open）。"""
    if _IS_WIN:
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen(
            [opener, target],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _wait_window(target: str, before: Set[int]) -> Optional[int]:
    """等待本次打开的窗口出现：优先窗口集合里新增的那个（精确），否则回退标题匹配。"""
    base = os.path.basename(os.path.normpath(target))
    deadline = time.monotonic() + _FOCUS_TIMEOUT
    while True:
        fresh = [(h, t) for h, t in _cabinet_windows() if h not in before]
        if fresh:
            for hwnd, title in fresh:          # 多个新窗口时优先标题匹配
                if _title_is_folder(title, base, target):
                    return hwnd
            return fresh[0][0]
        if time.monotonic() >= deadline:
            # 没有新窗口：系统把已有窗口导航/激活到了该目录 → 按标题回退定位
            return _find_window(target)
        time.sleep(_POLL_INTERVAL)


def _worker(target: str, key: str) -> None:
    base = os.path.basename(os.path.normpath(target))
    try:
        hwnd = _cached_window(key, base, target) or _find_window(target)
        if hwnd:
            # 该目录已在资源管理器中打开：只聚焦，不再开新窗口
            _remember(key, hwnd)
            _focus_window(hwnd)
            return
        with _lock:
            last = _recent.get(key, 0.0)
            if time.monotonic() - last < _REOPEN_TTL:
                return           # 刚刚已发起过打开（窗口可能仍在创建中）：避免重复开窗
            _recent[key] = time.monotonic()
        before = {h for h, _t in _cabinet_windows()}
        _startfile(target)
        hwnd = _wait_window(target, before)
        if hwnd:
            _remember(key, hwnd)
            _focus_window(hwnd)
    except Exception as e:
        log("debug", f"shell_open: open folder enhance failed: {e}")
    finally:
        with _lock:
            _inflight.discard(key)


def open_folder(path) -> None:
    """在文件管理器中打开目录：已打开则复用并聚焦，否则打开后聚焦（异步，立即返回）。

    路径是文件时保持原有系统行为（交给默认程序打开）。任何异常都不会抛出。
    """
    try:
        target = str(Path(path))
        if not _IS_WIN or not os.path.isdir(target):
            _startfile(target)
            return
    except Exception as e:
        log("warning", f"open folder failed: {e}")
        return

    key = _norm(target)
    with _lock:
        if key in _inflight:
            return               # 同一目录正在打开/聚焦中：交给进行中的那一次
        _inflight.add(key)
    threading.Thread(target=_worker, args=(target, key), name="open-folder", daemon=True).start()


# ── 定位文件（打开所在目录并选中）──────────────────────────────

def _shell_reveal(target: str) -> bool:
    """用 Shell 官方 API 打开该路径所在目录并选中它（已打开的窗口会被复用）；成功返回 True。"""
    api = _api()
    if not api or not api.shell32:
        return False
    ct = api.ctypes
    hr = api.ole32.CoInitializeEx(None, 0x2)      # COINIT_APARTMENTTHREADED
    if hr < 0:                                    # 含 RPC_E_CHANGED_MODE：本线程 COM 不可用
        return False
    pidl = ct.c_void_p()
    try:
        if api.shell32.SHParseDisplayName(str(target), None, ct.byref(pidl), 0, None) < 0 or not pidl.value:
            return False
        return api.shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0) >= 0
    except Exception as e:
        log("debug", f"shell_open: reveal via shell failed: {e}")
        return False
    finally:
        if pidl.value:
            try:
                api.ole32.CoTaskMemFree(pidl)
            except Exception:
                pass
        api.ole32.CoUninitialize()                # 与上面的 CoInitializeEx 配对


def _reveal_worker(target: str, key: str) -> None:
    parent = os.path.dirname(os.path.normpath(target))
    win_key = _norm(parent)                       # 窗口缓存按所在目录记（同一目录的多个文件共用一个窗口）
    base = os.path.basename(os.path.normpath(parent))
    try:
        with _lock:
            last = _recent.get(key, 0.0)
            if time.monotonic() - last < _REOPEN_TTL:
                # 刚刚已定位过：只再聚焦一次，不重复调 Shell
                hwnd = _cached_window(win_key, base, parent) or _find_window(parent)
                if hwnd:
                    _focus_window(hwnd)
                return
            _recent[key] = time.monotonic()
        before = {h for h, _t in _cabinet_windows()}
        if not _shell_reveal(target):
            _startfile(parent)                    # 回退：至少把所在目录打开
        hwnd = _wait_window(parent, before)
        if hwnd:
            _remember(win_key, hwnd)
            _focus_window(hwnd)
    except Exception as e:
        log("debug", f"shell_open: reveal failed: {e}")
    finally:
        with _lock:
            _inflight.discard(key)


def reveal(path) -> None:
    """在文件管理器中定位路径：打开所在目录并选中它，复用并聚焦已打开的窗口（异步，不抛异常）。

    目录按“打开目录”处理（与 open_folder 一致）；路径不存在时回退系统默认行为。
    """
    try:
        target = str(Path(path))
        if not _IS_WIN or not os.path.exists(target):
            _startfile(target)
            return
        if os.path.isdir(target):
            open_folder(target)
            return
    except Exception as e:
        log("warning", f"reveal in file manager failed: {e}")
        return

    key = _norm(target)
    with _lock:
        if key in _inflight:
            return               # 同一文件正在定位中：交给进行中的那一次
        _inflight.add(key)
    threading.Thread(target=_reveal_worker, args=(target, key), name="reveal-file", daemon=True).start()

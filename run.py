"""
魔法少女的魔女审判 - 角色立绘提取与拼接工具（业务逻辑层）

工作流程:
    1. 选择游戏目录 → 加载所有角色 bundle
    2. 点击角色 → 自动检测是否有组件数据
       - 无组件 → 直接导出所有精灵
       - 有组件 → 询问用户操作模式
    3. 拼接模式 → 选择部件 + 预览 + 保存合成图

架构（唯一启动链路）:
    start.bat → electron/main.js → spawn(backend.py) → JsApi（本模块）

要点:
    - 本模块是**纯业务模块**，不依赖任何 GUI 框架（无 pywebview / pythonnet / WinForms）。
      窗口控制、文件对话框由 Electron 主进程承担（preload 白名单拦截，根本不会调用到这里）。
    - 事件推送走 stdout 单行 JSON（`{"event": ..., "payload": ...}`），与
      `backend.py` 的 JSON-RPC 响应共用同一管道，由 stdout 锁保证行级原子。
    - 前端页面: webui/ (HTML/CSS/JS)，经 preload 暴露的 `window.pywebview.api` 调用本模块。
"""

from __future__ import annotations

import base64
import io
import json
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from src.bundle_loader import BundleLoader
from src.background_assets import BackgroundPreviewCache, scan_backgrounds
from src.cache_manager import load_extracted_data, save_extracted_data
from src.compositor import (
    LoadCancelled,
    SpriteCompositor,
    has_component_data,
)
from src.export_manager import (
    export_preview_images,
    output_group_name,
    save_composite,
    save_png,
)
from src import nameplate
from src import preset_store
from src.worker_client import (
    BackgroundPreviewWorker,
    LoadCancelledInWorker,
    WorkerTimeoutError,
    run_extract_worker,
)
from src.i18n import (
    LANG_CN,
    LANG_EN,
    LANG_JA,
    LANGUAGE_CODES,
    T,
    _,
    current_lang,
    set_lang,
)
from src.logtools import clear_logs, configure, log
try:
    # 文件管理器打开/定位（复用并聚焦资源管理器窗口）
    from src.shell_open import open_folder, reveal
except Exception:          # 极端情况（如打包遗漏该模块）：置空 → 调用处退回原实现 os.startfile
    open_folder = None     # type: ignore[assignment]
    reveal = None          # type: ignore[assignment]
from src.resource_monitor import ResourceMonitor
from src.settings import (
    ACCENT_NAMES,
    get_accent,
    get_auto_find_characters,
    get_disable_animations,
    get_disable_hardware_accel,
    get_export_count,
    get_export_original_quality,
    get_last_directory,
    get_mode,
    get_no_spoiler,
    GAME_MODES,
    get_output_dir,
    get_preview_quality,
    get_show_original_name,
    get_show_release_notes,
    get_theme,
    get_tutorial_done,
    save_settings,
)
from src.updater import UpdateError, check_for_update
from src.version import __version__


# ── 在文件管理器中打开 / 定位路径（含兜底）──────────────────
def _open_in_file_manager(path: Path) -> None:
    """在文件管理器中打开/定位路径。

    优先走 src.shell_open 的增强实现（目录：复用并聚焦已打开的窗口；文件：打开所在目录并选中该文件）；
    增强实现不可用或抛错时，退回**原实现**（os.startfile 交给系统打开）。
    """
    try:
        if open_folder is None:                     # 兜底 1：增强模块不可用
            os.startfile(str(path))
        elif path.is_file() and reveal is not None:
            reveal(path)
        else:
            open_folder(path)
        return
    except Exception as e:
        log("warning", f"open path failed: {e}")
    try:                                            # 兜底 2：增强实现抛错 → 原实现
        os.startfile(str(path))
    except Exception as e:
        log("warning", f"open path failed: {e}")


# ── 更新检查错误 → 友好提示 ────────────────────────────────
# 网络不可达（如 GitHub 被拦截、代理未开启）时不把底层异常原文直接展示给用户，
# 按 UpdateError.reason 映射到对应文案；无法识别的错误保留原始信息便于排查。
_UPDATE_ERROR_I18N = {
    "network": "dialog.update_error_network",
    "timeout": "dialog.update_error_timeout",
    "rate_limit": "dialog.update_error_rate_limit",
}


def _update_error_message(exc: UpdateError) -> str:
    key = _UPDATE_ERROR_I18N.get(exc.reason)
    if key:
        return _(key)
    return _("dialog.update_error_unknown", msg=str(exc))


# ── 启动静默检查的重试策略 ─────────────────────────────────
# 启动瞬间网络/代理可能尚未就绪，静默检查失败时重试至多 5 次；
# 静默模式不弹窗，因此每次尝试与最终结果都写入日志（logs/ 与控制台窗口）。
SILENT_UPDATE_RETRIES = 5
SILENT_UPDATE_RETRY_DELAY = 3.0   # 重试间隔（秒）


# ── 程序基础路径（兼容 PyInstaller 冻结环境） ──────────────
# BASE_DIR = 业务数据（output/ temp/）的根目录。
# backend.py 在受保护目录（Program Files 等）下会把 BASE_DIR 重定向到可写的 MCE_DATA_DIR。
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent   # 打包成 exe 后：exe 所在目录
else:
    BASE_DIR = Path(__file__).parent         # 源码运行时：脚本所在目录

# 日志文件：logs/ 目录，文件名含程序启动时间（每次启动一个新文件）
LOG_FILE: Optional[Path] = None


# ===================================================================
# 事件输出（stdout JSON，与 backend.py 的 JSON-RPC 协议共用管道）
# ===================================================================
# 事件异步写出：调用方只入队，由后台 daemon 线程持锁写 stdout。
# 避免 stdout 管道缓冲满（Electron 主进程渲染慢 → 不读管道）时阻塞业务线程
# （表现为首次提取卡死、无日志）。
_STDOUT_LOCK = threading.Lock()
_EMIT_QUEUE: "queue.Queue[Optional[str]]" = queue.Queue()
_EMIT_THREAD: Optional[threading.Thread] = None
_EMIT_THREAD_LOCK = threading.Lock()


def emit_event(event: str, payload: dict) -> None:
    """推送事件：入队一行 JSON，由后台线程写 stdout（不阻塞调用线程）。"""
    try:
        line = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        _ensure_emit_thread()
        _EMIT_QUEUE.put(line)
    except Exception as e:
        log("warning", f"[emit] {event} failed: {e}")


def _ensure_emit_thread() -> None:
    global _EMIT_THREAD
    if _EMIT_THREAD is not None:
        return
    with _EMIT_THREAD_LOCK:
        if _EMIT_THREAD is None:
            _EMIT_THREAD = threading.Thread(target=_emit_worker, name="emit-writer", daemon=True)
            _EMIT_THREAD.start()


def _emit_worker() -> None:
    """事件写线程：消费队列，持锁写 stdout（行级原子）"""
    while True:
        line = _EMIT_QUEUE.get()
        if line is None:
            return
        _write_stdout_line(line)


def flush_events(timeout: float = 2.0) -> None:
    """退出前同步消费事件队列直到空（超时放弃，避免卡死退出流程）"""
    import time as _t
    deadline = _t.monotonic() + timeout
    while _t.monotonic() < deadline:
        try:
            line = _EMIT_QUEUE.get(timeout=0.1)
        except queue.Empty:
            if _EMIT_QUEUE.empty():
                return
            continue
        if line is not None:
            _write_stdout_line(line)


def write_response(rid: Any, obj: Dict) -> None:
    """写出 JSON-RPC 响应行（backend.py 主循环使用；与事件共用 stdout 锁）"""
    _write_stdout_line(json.dumps({"id": rid, **obj}, ensure_ascii=False, default=str))


def _write_stdout_line(line: str) -> None:
    try:
        with _STDOUT_LOCK:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except Exception:
        pass


# ── 控制台标题（跟随语言切换） ──────────────────────
def set_console_title():
    """设置后端控制台窗口标题，跟随当前语言（非 Windows 平台静默跳过）"""
    title = f"{_('console.title')} v{__version__}"
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass


# ── 系统语言检测 ──────────────────────────────────────────────

def _detect_system_language() -> str:
    """根据系统区域设置自动选择语言（不返回 LANG_MGL）"""
    try:
        import locale
        sys_lang, _ = locale.getlocale(locale.LC_CTYPE)
        if sys_lang:
            lang_lower = sys_lang.lower()
            if lang_lower.startswith("zh") or "chinese" in lang_lower:
                return LANG_CN
            if lang_lower.startswith("ja") or "japanese" in lang_lower:
                return LANG_JA
    except Exception:
        pass
    return LANG_EN


# ===================================================================
# 图像 → data URL 工具
# ===================================================================

def _pil_to_data_url(img: Image.Image, max_side: int = 0) -> str:
    """PIL Image → base64 PNG data URL（可选限制最大边长）"""
    out = img
    if max_side and max(img.size) > max_side:
        out = img.copy()
        out.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _downscale_for_preview(img: Image.Image, max_side: int = 0) -> Image.Image:
    """按预览画质的最大边长等比降采样图像（返回新图像；max_side<=0 或无需缩放时返回原图）"""
    if max_side and max(img.size) > max_side:
        out = img.copy()
        out.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return out
    return img


def _pil_preview(img: Image.Image, max_side: int = 0) -> Tuple[str, List[int]]:
    """生成预览 data URL 并返回 (data_url, 实际尺寸)；按 max_side 等比缩放。

    返回的实际尺寸供前端“图像大小卡片”动态显示（随预览画质变化）。
    """
    out = _downscale_for_preview(img, max_side)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}", list(out.size)


def _sprite_thumb_data_url(path: Path, size=(96, 96)) -> Optional[str]:
    """生成精灵缩略图 data URL（透明背景居中）"""
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        canvas.alpha_composite(img, dest=offset)
        return _pil_to_data_url(canvas)
    except Exception:
        return None


def _sprite_full_data_url(path: Path, max_side: int = 512) -> Optional[str]:
    """生成精灵完整预览图 data URL（等比缩放，不裁剪、不居中，透明背景）"""
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return _pil_to_data_url(img)
    except Exception:
        return None


def _to_int(v: object, default: int = 0) -> int:
    """宽松转 int（预设代码 / 文件里的排序值可能是字符串）"""
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ===================================================================
# JS ↔ Python 桥接 API
# ===================================================================

class JsApi:
    """暴露给前端的全部方法（前端经 `window.pywebview.api.<method>(...)` 调用）。

    约定:
      - 快操作（getter / 设置）为同步方法，直接返回结果（JSON-RPC result）。
      - 耗时操作启动后台线程，通过 `emit_event` 推送进度与结果
        （前端 `window.__pywebview.events.<事件>` 接收）。
      - 窗口控制 / 文件对话框由 Electron 主进程承担（preload 白名单拦截），
        不存在于本类中。
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self._loader = BundleLoader()
        self._compositor = SpriteCompositor(scale=100.0)
        # 单部件放大预览用的“临时画布”合成器（与主合成器分离：各自持有画布，
        # 避免单部件预览把主预览共享的大画布清空重画）
        self._part_compositor: Optional[SpriteCompositor] = None

        # 内部状态（均为私有，避免被 JSON-RPC 递归暴露到前端）
        self._bundles: Dict[str, str] = {}            # {角色名: bundle路径}
        self._character_data: Optional[Dict] = None   # 当前角色的提取数据
        self._composite_image: Optional[Image.Image] = None
        self._preview_sprites: Optional[List] = None  # 无组件角色的预览精灵

        # 目录
        self._output_dir = output_dir or get_output_dir(BASE_DIR / "output")
        self._temp_dir = BASE_DIR / "temp"
        self._export_count = get_export_count()  # 累计导出次数（每次成功导出 +1，跨会话持久化）
        self._show_original_name = get_show_original_name()  # 是否显示原始文件名（默认显示本地化角色名，settings.json）
        self._no_spoiler = get_no_spoiler()  # 是否不再提示剧透警告（settings.json）
        self._preview_quality = get_preview_quality()  # 预览画质（缩放 % 10~100）
        self._disable_hardware_accel = get_disable_hardware_accel()  # 是否禁用硬件加速（UI 渲染）
        self._export_original_quality = get_export_original_quality()  # 导出原始画质（关闭时导出与预览一致）
        self._disable_animations = get_disable_animations()  # 是否禁用界面动画（低配 GPU 提速）
        self._auto_find_characters = get_auto_find_characters()  # 是否自动查找 characters 目录（False 时需手动指定 characters 目录）
        self._show_release_notes = get_show_release_notes()  # 更新弹窗是否展示 Release 更新内容（默认开启）
        self._tutorial_done = get_tutorial_done()  # 是否已完成首次使用引导（False 时前端首次启动自动弹出）
        self._load_generation = 0               # 目录查找代号：新查找开始时递增，用于打断上一次未完成的查找
        self._loading_path: Optional[str] = None  # 当前进行中的加载目录（用于取消日志显示）
        self._load_cancel = threading.Event()   # 「取消加载」标志：用户中止正在进行的目录扫描（每次加载开始时复位）
        self._debug_monitor = False             # 调试模式（仅本次运行有效，不持久化）：debug 日志 + 资源占用监视
        self._monitor: Optional[ResourceMonitor] = None  # 资源占用监视线程（调试模式开启时创建）
        self._char_gen = 0                      # 角色加载代号：递增以中断旧加载
        self._state_lock = threading.RLock()   # 代号检查、状态更新和发送结果作为一个短事务
        self._cache_ready = threading.Event()
        self._cache_ready.set()
        self._cache_clear_pending = 0
        self._char_busy = False                 # 是否正在加载角色/导出（读条中禁止切换）
        self._work_lock = threading.Lock()      # 提取类任务互斥锁：避免并发写 temp/（旧任务取消清理与新任务写入竞争）
        self._composite_lock = threading.Lock()  # 合成串行锁：共享画布/精灵缓存同一时刻仅一个 worker 使用
        self._composite_gen = 0                  # 合成代号：新请求递增，旧请求被取代（防抖/最新优先）
        self._char_has_component: Dict[str, bool] = {}  # 加载目录时缓存的角色组件状态（避免点击时重复解析 bundle）

        self._background_bundles: Dict[str, dict] = {}
        self._background_lock = threading.Lock()
        self._background_cancel = threading.Event()
        self._background_preview_worker = BackgroundPreviewWorker()
        self._background_preview_cache = BackgroundPreviewCache(directory=self._temp_dir / "background-previews")

        # 名片合成（素材/字体见 src/nameplate.py；渲染器按素材路径缓存）
        self._nameplate_renderer: Optional["nameplate.NameplateRenderer"] = None
        self._nameplate_key: Optional[Tuple[str, str]] = None
        self._nameplate_image: Optional[Image.Image] = None
        self._nameplate_cancel: bool = False        # 素材查找中止标志（前端「停止查找」置位）
        self._nameplate_gen: int = 0               # 查找代号（新一次查找让仍在跑的旧查找自行退出）

        # 内置预设镜像：启动时即把 builtin/presets（打包版为包内 builtin_presets）写回
        # data/presets，误删 / 损坏的「Default」在此自动恢复
        try:
            healed = preset_store.ensure_builtins()
            if healed:
                log("info", f"[preset] 已恢复 {healed} 个内置预设")
        except Exception as e:
            log("warning", f"[preset] 内置预设镜像失败: {e}")

    # ── 事件推送 ──────────────────────────────────────────

    def _emit(self, event: str, payload: dict):
        """推送到前端 `window.__pywebview.events.<event>(payload)`（经 stdout 协议）"""
        emit_event(event, payload)

    @staticmethod
    def _run_async(fn):
        threading.Thread(target=fn, daemon=True).start()

    # ── 应用信息 / 语言 ────────────────────────────────────

    @staticmethod
    def _translations(lang: str) -> Dict[str, str]:
        """返回某语言的完整翻译模板表"""
        return {key: entry.get(lang, entry.get(LANG_CN, key)) for key, entry in T.items()}

    def get_app_info(self) -> dict:
        """前端初始化时调用：版本、语言、翻译表、输出目录等"""
        return {
            "version": __version__,
            "langs": LANGUAGE_CODES,
            "current_lang": current_lang(),
            "mode": get_mode(),
            "modes": list(GAME_MODES),
            "lang_names": {code: _(f"lang.{code}") for code in LANGUAGE_CODES},
            "translations": self._translations(current_lang()),
            "output_dir": str(self._output_dir),
            "bundle_count": len(self._bundles),
            "frozen": getattr(sys, "frozen", False),
            "theme": get_theme(),
            "accent": get_accent(),
            "export_count": self._export_count,
            "show_original_name": self._show_original_name,
            "no_spoiler": self._no_spoiler,
            "preview_quality": self._preview_quality,
            "disable_hardware_accel": self._disable_hardware_accel,
            "export_original_quality": self._export_original_quality,
            "disable_animations": self._disable_animations,
            "auto_find_characters": self._auto_find_characters,
            "show_release_notes": self._show_release_notes,
            "tutorial_done": self._tutorial_done,
            "debug": self._debug_monitor,
        }

    def set_lang(self, code: str) -> dict:
        """切换语言并持久化，返回新翻译表（同时更新控制台标题）"""
        if code in LANGUAGE_CODES:
            set_lang(code)
            save_settings(lang=code)
            log("info", _("log.lang_changed", code=code))
            set_console_title()
        return {
            "current_lang": current_lang(),
            "lang_names": {c: _(f"lang.{c}") for c in LANGUAGE_CODES},
            "translations": self._translations(current_lang()),
        }

    def set_theme(self, theme: str) -> dict:
        """保存界面主题（dark/light）到 settings.json，供下次启动恢复"""
        if theme in ("dark", "light"):
            save_settings(theme=theme)
            log("info", _("log.theme_changed", theme=theme))
        return {"theme": theme}

    def set_accent(self, accent: str) -> dict:
        """保存主题色（default/角色名）到 settings.json，供下次启动恢复"""
        if accent in ACCENT_NAMES:
            save_settings(accent=accent)
            log("info", _("log.accent_changed", accent=accent))
        return {"accent": accent}

    def set_show_original_name(self, enable: bool) -> dict:
        """保存是否显示原始文件名到 settings.json"""
        self._show_original_name = bool(enable)
        save_settings(show_original_name=self._show_original_name)
        log("info", _("log.original_name_on") if self._show_original_name else _("log.original_name_off"))
        return {"show_original_name": self._show_original_name}

    def set_no_spoiler(self, enable: bool) -> dict:
        """保存是否不再提示剧透警告到 settings.json"""
        self._no_spoiler = bool(enable)
        save_settings(no_spoiler_notice=self._no_spoiler)
        return {"no_spoiler": self._no_spoiler}

    def set_preview_quality(self, quality: int) -> dict:
        """保存预览合成画质（缩放百分比 10~100）到 settings.json，供下次启动恢复。

        预览以降低分辨率合成以减轻低配机负载；导出始终按原始画质重新合成，不受影响。
        """
        q = max(10, min(100, int(quality or 100)))
        self._preview_quality = q
        save_settings(preview_quality=q)
        log("info", _("log.preview_quality_set", q=q))
        return {"preview_quality": q}

    def set_disable_hardware_accel(self, enable: bool) -> dict:
        """保存是否禁用硬件加速（UI 渲染）到 settings.json（重启 Electron 生效）"""
        self._disable_hardware_accel = bool(enable)
        save_settings(disable_hardware_accel=self._disable_hardware_accel)
        log("info", _("log.hw_accel_on") if self._disable_hardware_accel else _("log.hw_accel_off"))
        return {"disable_hardware_accel": self._disable_hardware_accel}

    def set_export_original_quality(self, enable: bool) -> dict:
        """保存是否导出原始画质图像到 settings.json（关闭时导出与预览画质一致）"""
        self._export_original_quality = bool(enable)
        save_settings(export_original_quality=self._export_original_quality)
        log("info", _("log.export_original_on") if self._export_original_quality else _("log.export_original_off"))
        return {"export_original_quality": self._export_original_quality}

    def set_disable_animations(self, enable: bool) -> dict:
        """保存是否禁用界面动画（纯前端行为，立即生效，无需重启）"""
        self._disable_animations = bool(enable)
        save_settings(disable_animations=self._disable_animations)
        log("info", _("log.animations_off") if self._disable_animations else _("log.animations_on"))
        return {"disable_animations": self._disable_animations}

    def set_auto_find_characters(self, enable: bool) -> dict:
        """保存是否自动查找 characters 目录（关闭后需手动指定 characters 目录；下次加载生效）"""
        self._auto_find_characters = bool(enable)
        save_settings(auto_find_characters=self._auto_find_characters)
        log("info", _("log.auto_find_on") if self._auto_find_characters else _("log.auto_find_off"))
        return {"auto_find_characters": self._auto_find_characters}

    def set_show_release_notes(self, enable: bool) -> dict:
        """保存是否在更新弹窗中展示 Release 更新内容（默认开启；下次检查更新生效）"""
        self._show_release_notes = bool(enable)
        save_settings(show_release_notes=self._show_release_notes)
        log("info", _("log.release_notes_on") if self._show_release_notes else _("log.release_notes_off"))
        return {"show_release_notes": self._show_release_notes}

    def set_tutorial_done(self, done: bool) -> dict:
        """保存首次使用引导是否已完成到 settings.json（完成后不再自动弹出）"""
        self._tutorial_done = bool(done)
        save_settings(tutorial_done=self._tutorial_done)
        return {"tutorial_done": self._tutorial_done}

    def _preview_max_side(self) -> int:
        """预览 data URL 的最大边长（随预览画质缩放；100% → 1600px）"""
        q = max(10, min(100, self._preview_quality))
        return max(200, int(1600 * q / 100))

    def _preview_thumb_side(self) -> int:
        """无组件预览缩略图的最大边长（随预览画质缩放；100% → 768px）"""
        q = max(10, min(100, self._preview_quality))
        return max(128, int(768 * q / 100))

    def set_debug(self, enable: bool) -> dict:
        """开启/关闭调试模式（仅本次运行有效，不持久化）。

        开启后：输出 debug 日志 + 后台线程每 5 秒采集内存/CPU，推送 res_monitor 事件
        供前端状态栏/标题栏显示（窗口分辨率由 Electron 侧在前端展示，后端不再采集）。
        """
        enable = bool(enable)
        if enable == self._debug_monitor:
            return {"debug": self._debug_monitor}
        self._debug_monitor = enable
        if enable:
            configure(level="debug")
            log("info", _("log.debug_on"))
            self._monitor = ResourceMonitor(emit=self._on_res_monitor_payload)
            self._monitor.start()
        else:
            if self._monitor is not None:
                self._monitor.stop()
            self._monitor = None
            configure(level="info")
            log("info", _("log.debug_off"))
        return {"debug": self._debug_monitor}

    def _on_res_monitor_payload(self, payload: dict):
        """资源占用采集回调：记录 debug 日志并推送 res_monitor 事件。

        只上报内存 / CPU（进程级指标）；窗口分辨率与 FPS 由前端自行采集，
        无需跨进程获取窗口句柄。
        """
        log("debug", _("log.resource_usage", mem=payload["mem_mb"], cpu=payload["cpu"]))
        self._emit("res_monitor", payload)

    # ── 目录 / 设置 ────────────────────────────────────────

    def save_native_settings(self, window: Optional[Dict] = None,
                             last_directory: Optional[str] = None) -> dict:
        """Electron 的设置也由后端持久化，避免两个进程读改写同一文件。"""
        save_settings(window=window, last_directory=last_directory)
        return {"ok": True}

    def _begin_character_task(self) -> int:
        with self._state_lock:
            self._char_gen += 1
            self._char_busy = True
            return self._char_gen

    def _emit_character(self, gen: int, event: str, payload: dict) -> None:
        with self._state_lock:
            if gen == self._char_gen:
                self._emit(event, payload)

    def _finish_export(self, name: str, result: Dict) -> None:
        count = result.get("count", 0)
        errors = result.get("errors", [])
        if count > 0:
            self._export_count += 1
            save_settings(export_count=self._export_count)
        payload = {"name": name, **result, "export_count": self._export_count}
        if errors or not count:
            payload["message"] = "\n".join(str(e.get("message", e)) for e in errors) or "No images exported"
            self._emit("export_error", payload)
        else:
            log("info", _("log.export_complete", name=name, count=count))
            self._emit("export_complete", payload)

    # 说明：文件/文件夹选择对话框由 Electron 主进程承担（preload 白名单拦截
    # `select_directory` / `select_output_dir` → `dialog:folder*`），因此本类不再提供
    # 这两个方法。若前端调用它们，会得到 "no such method" 错误 —— 这是刻意的显式失败，
    # 避免两套对话框实现并存后行为漂移。

    def set_output_dir(self, path: str) -> dict:
        """保存并应用输出目录"""
        if path and Path(path).is_absolute():
            self._output_dir = Path(path).resolve()
        else:
            self._output_dir = (BASE_DIR / "output").resolve()
        save_settings(self._output_dir)
        log("info", _("log.output_dir_set", path=str(self._output_dir)))
        return {"output_dir": str(self._output_dir)}

    def open_output(self):
        """打开输出文件夹（已在资源管理器中打开时复用并聚焦该窗口，不重复开窗）"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        _open_in_file_manager(self._output_dir)

    def open_path(self, path: str):
        """在资源管理器中打开指定路径（目录：打开并聚焦；文件：打开所在目录并选中该文件）"""
        if not path:
            return
        _open_in_file_manager(Path(path))

    def open_url(self, url: str):
        """在系统浏览器打开链接"""
        try:
            webbrowser.open(url)
        except Exception as e:
            log("warning", f"open url failed: {e}")

    # ── 目录加载 ──────────────────────────────────────────

    def _start_background_job(self, operation: str, task) -> dict:
        """Serialize background jobs and report completion even on failure/cancellation."""
        if self._char_busy or self._loading_path is not None:
            return {"ok": False, "error": _("background.busy")}
        if not self._background_lock.acquire(blocking=False):
            return {"ok": False, "error": _("background.busy")}
        self._background_cancel.clear()

        def worker():
            payload = {"operation": operation}
            try:
                self._cache_ready.wait()
                with self._work_lock:
                    if self._background_cancel.is_set():
                        raise LoadCancelled()
                    payload.update(task())
            except (LoadCancelled, LoadCancelledInWorker):
                payload["cancelled"] = True
            except Exception as exc:
                payload["error"] = str(exc)
                log("error", f"[background] {operation}: {exc}")
            finally:
                self._background_lock.release()
            self._emit("background_complete", payload)

        self._run_async(worker)
        return {"ok": True}

    def load_backgrounds(self, path: str) -> dict:
        """Discover backgrounds and individual images independently of characters."""
        def task():
            result = scan_backgrounds(Path(path), self._background_cancel.is_set)
            small = run_extract_worker(
                "scan_small_assets", {"directory": result["directory"]},
                progress_callback=lambda cur, total: self._emit("background_progress", {
                    "operation": "scan", "current": cur, "total": total,
                }), cancel_check=self._background_cancel.is_set,
            )
            result["bundles"].extend(small["bundles"])
            result["count"] = len(result["bundles"])
            result["errors"] = small["errors"]
            if self._background_cancel.is_set():
                raise LoadCancelled()
            self._background_bundles = {item["id"]: item for item in result["bundles"]}
            save_settings(last_directory=path)
            # Import UnityPy in the preview process before the first preview click.
            try:
                self._background_preview_worker.warmup()
            except Exception as exc:
                log("warning", f"[background] preview warmup: {exc}")
            return result
        return self._start_background_job("scan", task)

    def preview_background(self, background_id: str) -> dict:
        """Reuse cached thumbnails or decode in the prewarmed preview process."""
        item = self._background_bundles.get(background_id)
        if item is None:
            return {"ok": False, "error": _("background.invalid_selection")}

        def task():
            result = self._get_background_preview(item)
            return {"id": background_id, **result}
        return self._start_background_job("preview", task)

    def _get_background_preview(self, item: dict) -> dict:
        if self._background_cancel.is_set():
            raise LoadCancelled()
        path = Path(item["bundle_path"])
        selector = {key: item[key] for key in ("object_id", "asset_type") if key in item}
        key = self._background_preview_cache.key(path, **selector)
        result = self._background_preview_cache.get(key)
        if result is None:
            result = self._background_preview_worker.preview(
                path, cancel_check=self._background_cancel.is_set, **selector,
            )
            if self._background_cancel.is_set():
                raise LoadCancelled()
            if self._background_preview_cache.key(path, **selector) == key:
                self._background_preview_cache.put(key, result)
        return result

    def prewarm_backgrounds(self) -> dict:
        """Cache previews for every loaded asset, independently of UI filters."""
        if not self._background_bundles:
            return {"ok": False, "error": _("background.invalid_selection")}
        items = list(self._background_bundles.values())

        def task():
            count, errors = 0, []
            for index, item in enumerate(items):
                if self._background_cancel.is_set():
                    raise LoadCancelled()
                try:
                    self._get_background_preview(item)
                    count += 1
                except (LoadCancelled, LoadCancelledInWorker):
                    raise
                except Exception as exc:
                    errors.append({"id": item["id"], "message": str(exc)})
                self._emit("background_progress", {
                    "operation": "prewarm", "current": index + 1, "total": len(items),
                })
            return {"count": count, "total": len(items), "errors": errors}
        return self._start_background_job("prewarm", task)

    def export_backgrounds(self, selected_ids: List[str]) -> dict:
        """Export native PNGs into flat, named category folders under backgrounds/."""
        if (not isinstance(selected_ids, list) or not selected_ids
                or any(not isinstance(key, str) or key not in self._background_bundles
                       for key in selected_ids)):
            return {"ok": False, "error": _("background.invalid_selection")}
        items = [self._background_bundles[key] for key in dict.fromkeys(selected_ids)]
        output_dir = self._output_dir / "backgrounds"

        def task():
            result = self._extract_background_batch(items, output_dir, "export")
            groups = {output_group_name(item.get("group")) for item in items}
            if len(groups) == 1:
                result["output_dir"] = str(output_dir / next(iter(groups)))
            if result["count"] > 0:
                self._export_count += 1
                save_settings(export_count=self._export_count)
            result["export_count"] = self._export_count
            return result
        return self._start_background_job("export", task)

    def _extract_background_batch(self, items: List[dict], output_dir: Path, operation: str) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        # The parent owns staging cleanup even when the extraction process is killed.
        with tempfile.TemporaryDirectory(prefix=".background-", dir=output_dir) as staging:
            return run_extract_worker(
                "export_backgrounds",
                {"bundles": items, "output_dir": str(output_dir), "staging_dir": staging},
                progress_callback=lambda cur, total: self._emit("background_progress", {
                    "operation": operation, "current": cur, "total": total,
                }), cancel_check=self._background_cancel.is_set,
            )

    def cancel_backgrounds(self) -> dict:
        """Stop the active scan/preview/export; completed output files are retained."""
        self._background_cancel.set()
        return {"ok": True}

    def _close_background_preview(self) -> None:
        self._background_cancel.set()
        self._background_preview_worker.close()
        self._background_preview_cache.clear()

    def cancel_load(self) -> dict:
        """中止正在进行的「加载游戏目录」扫描（前端「取消加载」）。

        仅中止本次扫描：已加载完成的角色列表保持不变，被取代/取消的加载不会写回结果。
        """
        self._load_cancel.set()
        return {"ok": True}

    def load_directory(self, path: str):
        """加载游戏目录（后台线程，事件: progress / load_complete）；新查找会打断上一次未完成的查找"""
        # 若上一次加载仍在进行，立即记录其被新加载取代（显示旧目录，避免取消日志滞后）
        if self._loading_path is not None:
            log("info", _("log.load_cancelled_dir", path=self._loading_path))
        self._load_generation += 1
        gen = self._load_generation
        self._loading_path = path
        self._load_cancel.clear()   # 本次加载不继承上一次的「取消加载」请求
        log("info", _("log.loading_dir", path=path))

        # 取消来源：user=用户点击「取消加载」；replaced=被新一次加载取代（供前端区分提示）
        cancel_state: Dict[str, bool] = {"user": False}

        def worker():
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "load"})
            def cancel():
                # 用户手动取消 → 记录来源并中断；否则一旦有新一次 load_directory 调用（代号变化）也中断
                if self._load_cancel.is_set():
                    cancel_state["user"] = True
                    return True
                return gen != self._load_generation
            self._emit("status", {"text": _("app.progress.loading_bundles")})
            # 立即显示进度区（0%）：目录查找阶段也要能点到「取消加载」
            self._emit("progress", {"current": 0, "total": 0, "phase": "load"})
            result = self._loader.load_from_directory(
                path, progress_callback=cb, cancel_check=cancel, auto_find=self._auto_find_characters
            )
            if result.get("cancelled"):
                result["cancelled_reason"] = "user" if cancel_state["user"] else "replaced"
                if cancel_state["user"]:
                    log("info", _("log.load_cancelled_dir", path=path))
                    if gen == self._load_generation:
                        self._loading_path = None
                # 被新加载取代时：中断标记交给新加载持有，取消日志已在 load_directory 同步打印
                self._emit("load_complete", result)
                return
            # 本次加载正常结束（未被取代）：清空进行中标记
            if gen == self._load_generation:
                self._loading_path = None
            if result["success"]:
                self._bundles = result["bundles"]
                self._char_has_component = result.get("components", {})
                # 记忆本次加载的目录（settings.json 为权威）——覆盖“选择目录”/“拖拽导入”两种入口。
                # 目录选择对话框由 Electron 主进程承担（不经本进程），
                # 因此只能在统一的 load_directory 入口保存，才能保证两种入口行为一致。
                save_settings(last_directory=path)
                log("info", _("log.load_complete", count=result["count"]))
            else:
                log("warning", _("log.load_error", errors=result["errors"]))
            self._emit("load_complete", result)
        self._run_async(worker)
        return True

    def select_character(self, name: str):
        """分析角色 bundle 是否含组件（事件: analyze_complete / analyze_error）。

        无论新角色是否有组件，都先清理上一个角色的内存临时数据
        （提取数据/合成图），释放内存；不删除 temp/ 磁盘缓存（保留缓存复用）。
        """
        # 取消正在进行的前一个任务（preview_bundle / export_sprites / load_char）：
        # 递增代号使其 cancel_check 触发 LoadCancelled 退出，避免并发写同一 preview 目录
        # 导致文件交错/被删（如快速重复选择角色时出现提取失败）
        with self._state_lock:
            self._char_gen += 1
            gen = self._char_gen
            self._composite_gen += 1
            self._char_busy = False
            self._character_data = None
            self._composite_image = None
            self._preview_sprites = None
        # 清理合成器缓存的精灵解码图/可复用画布（切换角色后旧精灵路径不再需要）
        with self._composite_lock:
            self._compositor.clear_cache()
            if self._part_compositor is not None:
                self._part_compositor.clear_cache()
        # 切换角色时清理 preview 临时预览目录
        preview_dir = self._temp_dir / "preview"
        # 目录删除由提取 worker 在 _work_lock 内执行，避免切换角色时删到正在写入的文件。
        import gc
        gc.collect()

        def worker():
            self._cache_ready.wait()
            with self._work_lock:
                if gen != self._char_gen:
                    return
                if preview_dir.exists():
                    shutil.rmtree(preview_dir, ignore_errors=True)
            bundle_path = Path(self._bundles.get(name, ""))
            if not bundle_path.exists():
                self._emit_character(gen, "analyze_complete", {
                    "name": name, "has_components": False,
                    "error": _("dialog.bundle_not_found", path=str(bundle_path)),
                })
                return
            self._emit_character(gen, "status", {"text": _("app.status.analyzing", name=name)})
            try:
                # 优先使用加载目录时缓存的组件状态（不再重复解析 bundle）；无缓存时回退实时分析
                has = self._char_has_component.get(name)
                if has is None:
                    has = has_component_data(bundle_path)
                log("info", _("log.analyze_has", name=name) if has else _("log.analyze_none", name=name))
            except Exception as e:
                log("error", _("log.analyze_failed", name=name, e=e))
                self._emit_character(gen, "analyze_error", {"name": name, "message": str(e)})
                return
            self._emit_character(gen, "analyze_complete", {
                "name": name, "bundle_path": str(bundle_path), "has_components": has,
            })
        self._run_async(worker)
        return True

    # ── 导出 / 提取 / 合成 ────────────────────────────────

    def preview_bundle(self, name: str):
        """提取无组件角色的精灵到临时预览目录（事件: progress / preview_ready / preview_error）"""
        gen = self._begin_character_task()
        def worker():
            self._cache_ready.wait()
            bundle_path = Path(self._bundles.get(name, ""))
            target = self._temp_dir / "preview" / name
            def cb(cur, total):
                self._emit_character(gen, "progress", {"current": cur, "total": total, "phase": "preview"})
            # 立即给出反馈（等待锁期间也显示，避免首次 UnityPy 解析 bundle 看似卡死）
            self._emit_character(gen, "status", {"text": _("app.status.extracting", name=name)})
            self._emit_character(gen, "progress", {"current": 0, "total": 1, "phase": "preview"})
            with self._work_lock:   # 等待前一个任务（含取消清理）完全退出，避免并发写 preview/ 目录
                try:
                    if gen != self._char_gen:
                        return
                    existing = list(target.glob("*.png")) if target.exists() else []
                    if existing:
                        # 复用已提取的预览缓存（不重新解析 bundle）
                        sprites = []
                        for p in sorted(existing):
                            if gen != self._char_gen:
                                raise LoadCancelled()
                            try:
                                with Image.open(p) as im:
                                    size = list(im.size)
                            except Exception:
                                size = [0, 0]
                            sprites.append({"name": p.stem, "path_id": -1, "file_path": str(p), "size": size})
                    else:
                        target.mkdir(parents=True, exist_ok=True)
                        sprites = self._extract_via_worker(
                            "extract_sprites",
                            {
                                "bundle_path": str(bundle_path),
                                "output_dir": str(self._temp_dir / "preview"),
                            },
                            cb,
                            lambda: gen != self._char_gen,
                        )
                    if gen != self._char_gen:
                        raise LoadCancelled()
                except LoadCancelled:
                    # 用户中断：清理预览临时数据（锁内执行，不会与新任务并发删除）
                    shutil.rmtree(self._temp_dir / "preview", ignore_errors=True)
                    log("info", _("log.char_load_cancelled"))
                    return
                except Exception as e:
                    log("error", _("log.process_data_failed", e=e))
                    self._emit_character(gen, "preview_error", {"name": name, "message": str(e)})
                    return
                finally:
                    with self._state_lock:
                        if gen == self._char_gen:
                            self._char_busy = False
                with self._state_lock:
                    if gen != self._char_gen:
                        return
                    self._preview_sprites = sprites
                    log("info", _("log.preview_ready", name=name, count=len(sprites)))
                    self._emit("preview_ready", {
                        "name": name, "count": len(sprites),
                        "sprites": [{"name": s["name"], "size": s["size"]} for s in sprites],
                    })
        self._run_async(worker)
        return True

    def get_preview_thumbnails(self):
        """流式生成无组件预览缩略图（事件: progress / preview_thumb 逐张 / preview_thumbs_ready）

        每生成一张立即推送 preview_thumb，前端增量填充网格（避免一次生成全部再渲染导致卡顿）。
        缩略图分辨率随预览画质设置（_preview_thumb_side）。
        """
        with self._state_lock:
            gen = self._char_gen
            sprites = self._preview_sprites or []
        def worker():
            total = len(sprites)
            max_side = self._preview_thumb_side()
            for i, s in enumerate(sprites):
                if gen != self._char_gen:
                    return
                self._emit_character(gen, "progress", {"current": i + 1, "total": total, "phase": "preview_thumbs"})
                url = _sprite_full_data_url(Path(s["file_path"]), max_side=max_side)
                if url:
                    # 流式：逐张推送，前端立即显示该张
                    self._emit_character(gen, "preview_thumb", {"name": s["name"], "data_url": url})
            self._emit_character(gen, "preview_thumbs_ready", {"count": total})
        self._run_async(worker)
        return True

    def export_preview(self, name: str, selected_names: Optional[List[str]] = None):
        """导出预览精灵到输出目录；selected_names 为空则导出全部（事件: progress / export_complete / export_error）"""
        def worker():
            self._cache_ready.wait()
            with self._work_lock:
                src_dir = self._temp_dir / "preview" / name
                if not src_dir.exists():
                    self._emit("export_error", {"name": name, "message": "no_preview"})
                    return
                out_dir = self._output_dir / name
                files = sorted(src_dir.glob("*.png"))
                if selected_names:
                    sel = set(selected_names)
                    files = [f for f in files if f.stem in sel]
                self._finish_export(name, export_preview_images(files, out_dir))
        self._run_async(worker)
        return True

    def cancel_character_load(self) -> dict:
        """中断当前角色加载/导出，并清理临时数据"""
        with self._state_lock:
            self._char_gen += 1
            gen = self._char_gen
            self._composite_gen += 1
            self._char_busy = False
            self._character_data = None
            self._composite_image = None
            self._preview_sprites = None
        def cleanup():
            with self._work_lock:
                if gen == self._char_gen:
                    shutil.rmtree(self._temp_dir / "preview", ignore_errors=True)
        self._run_async(cleanup)
        import gc
        gc.collect()
        log("info", _("log.char_load_cancelled"))
        return {"ok": True}

    def _extract_via_worker(self, kind: str, args: Dict, cb, cancel_check) -> Any:
        """经独立子进程执行 UnityPy 提取（方案 A，绕开 backend 内首次提取卡死）。

        - 子进程无进展超时（killed）→ 自动重试一次；仍失败则抛 WorkerTimeoutError
        - 用户取消 → 抛 LoadCancelled（上层按原逻辑清理）
        """
        for attempt in (1, 2):
            try:
                return run_extract_worker(
                    kind, args, progress_callback=cb, cancel_check=cancel_check,
                )
            except LoadCancelledInWorker:
                raise LoadCancelled()
            except WorkerTimeoutError as e:
                if attempt == 2:
                    raise
                log("warning", f"[worker] {kind} 子进程无进展(killed)，重试… ({e})")
            except (OSError, BrokenPipeError) as e:
                if attempt == 2:
                    raise
                log("warning", f"[worker] {kind} 子进程启动失败，重试… ({e})")

    def export_sprites(self, name: str, has_components: bool):
        """导出角色全部精灵（事件: progress / export_complete / export_error）"""
        gen = self._begin_character_task()
        def worker():
            self._cache_ready.wait()
            bundle_path = Path(self._bundles.get(name, ""))
            def cb(cur, total):
                self._emit_character(gen, "progress", {"current": cur, "total": total, "phase": "export"})
            self._emit_character(gen, "status", {"text": _("app.status.exporting", name=name)})
            self._emit_character(gen, "progress", {"current": 0, "total": 1, "phase": "export"})
            log("info", _("log.export_start", name=name))
            with self._work_lock:   # 与提取类任务互斥，避免并发读写临时/输出目录
                try:
                    if gen != self._char_gen:
                        return
                    results = self._extract_via_worker(
                        "export_sprites",
                        {
                            "bundle_path": str(bundle_path),
                            "output_dir": str(self._output_dir),
                            "has_components": bool(has_components),
                        },
                        cb,
                        lambda: gen != self._char_gen,
                    )
                except LoadCancelled:
                    log("info", _("log.char_load_cancelled"))
                    return
                except Exception as e:
                    log("error", _("log.export_failed", name=name, e=e))
                    self._emit_character(gen, "export_error", {"name": name, "message": str(e)})
                    return
                finally:
                    with self._state_lock:
                        if gen == self._char_gen:
                            self._char_busy = False
                with self._state_lock:
                    if gen == self._char_gen:
                        self._finish_export(name, results)
        self._run_async(worker)
        return True

    def start_composite_mode(self, name: str):
        """进入拼接模式：提取角色数据（优先缓存）（事件: progress / data_ready / data_error）"""
        gen = self._begin_character_task()
        def worker():
            self._cache_ready.wait()
            bundle_path = Path(self._bundles.get(name, ""))
            def cb(cur, total):
                self._emit_character(gen, "progress", {"current": cur, "total": total, "phase": "extract"})
            # 立即给出反馈（等待锁期间也显示，避免首次 UnityPy 解析 bundle 看似卡死）
            self._emit_character(gen, "status", {"text": _("app.status.extracting", name=name)})
            self._emit_character(gen, "progress", {"current": 0, "total": 1, "phase": "extract"})
            with self._work_lock:   # 等待前一个任务（含取消清理）完全退出，避免并发写 temp/ 导致文件被删
                try:
                    if gen != self._char_gen:
                        return
                    data = load_extracted_data(self._temp_dir, name, bundle_path)
                    if data is None:
                        self._temp_dir.mkdir(parents=True, exist_ok=True)
                        data = self._extract_via_worker(
                            "extract_character",
                            {"bundle_path": str(bundle_path), "output_dir": str(self._temp_dir)},
                            cb, lambda: gen != self._char_gen,
                        )
                        if gen != self._char_gen:
                            raise LoadCancelled()
                        save_extracted_data(data, self._temp_dir, name, bundle_path)
                except LoadCancelled:
                    # 用户中断：清理本次提取的内存与磁盘数据（锁内执行，不会与新任务并发删除）
                    shutil.rmtree(self._temp_dir / name, ignore_errors=True)
                    log("info", _("log.char_load_cancelled"))
                    return
                except Exception as e:
                    log("error", _("log.process_data_failed", e=e))
                    self._emit_character(gen, "data_error", {"name": name, "message": str(e)})
                    return
                finally:
                    with self._state_lock:
                        if gen == self._char_gen:
                            self._char_busy = False
                with self._state_lock:
                    if gen != self._char_gen:
                        return
                    self._character_data = data
                    count = len(data.get("transform_data", []))
                    log("info", _("log.extract_complete", name=name, count=count))
                    self._emit("data_ready", self._data_summary(data))
        self._run_async(worker)
        return True

    def _data_summary(self, data: Dict) -> dict:
        """裁剪数据体积，仅向前端发送渲染所需字段"""
        transform = []
        for p in data.get("transform_data", []):
            transform.append({
                "name": p["name"],
                "sprite_name": p.get("sprite_name", p["name"]),
                "sprite_size": p.get("sprite_size", [0, 0]),
                "position": p.get("position", {"x": 0, "y": 0, "z": 0}),
                "sorting_order": p.get("sorting_order", 0),
                "color": p.get("color", {"r": 1, "g": 1, "b": 1, "a": 1}),
                "category": p.get("category", "other"),
            })
        # ClippingMask 部件（role=masked 的叠加层）来自 mask_mapping 权威数据，供前端“快速勾选”使用
        clipping_parts = sorted(
            (data.get("mask_mapping") or {}).get("clipping_masks", {}).keys()
        )
        # 用户预设（data/presets/<角色>/）：随角色数据一并下发，前端下拉直接渲染
        name = data.get("character_name", "")
        return {
            "name": name,
            "count": len(transform),
            "transform_data": transform,
            "hierarchy": data.get("hierarchy", []),
            "clipping_mask_parts": clipping_parts,
            "presets": preset_store.list_presets(name) if name else [],
        }

    # ── 用户预设（记录部件 sorting_order，用户自行保存 / 删除）────

    def list_presets(self, name: str) -> dict:
        """列出某角色的预设（{name, presets: [...]}），供前端下拉渲染"""
        return {"name": name, "presets": preset_store.list_presets(name)}

    def save_preset(
        self,
        name: str,
        preset_name: str,
        selected_names: Optional[List[str]] = None,
        sketch_text: str = "",
        sketch_size: int = 56,
        sketch_align: str = "center",
    ) -> dict:
        """把当前选中的部件（记录 sorting_order）与素描本参数保存为预设。

        预设存于 data/presets/<角色>/<预设名>.json，由用户自行保存 / 删除；
        应用（恢复勾选）在前端按 sorting_order 匹配完成，后端只负责持久化。
        """
        data = self._character_data
        if not data or data.get("character_name") != name:
            bundle = self._bundles.get(name)
            data = load_extracted_data(self._temp_dir, name, Path(bundle)) if bundle else None
        parts: List[Dict] = []
        if data:
            wanted = set(selected_names or [])
            parts = [
                {"name": p["name"], "sorting_order": p.get("sorting_order", 0)}
                for p in data.get("transform_data", [])
                if p["name"] in wanted
            ]
            parts.sort(key=lambda p: (p["sorting_order"], p["name"]))
        try:
            entry = preset_store.save_preset(name, preset_name, parts, {
                "text": sketch_text, "size": sketch_size, "align": sketch_align,
            })
        except preset_store.BuiltinPresetError:
            # 内置预设名受保护：不可覆盖 / 不可同名新建
            log("info", f"[preset] 拒绝覆盖内置预设 {name}/{preset_name}")
            return {"success": False, "error": "builtin",
                    "presets": preset_store.list_presets(name)}
        except Exception as e:
            log("warning", f"[preset] 保存预设失败 {name}/{preset_name}: {e}")
            return {"success": False, "error": str(e),
                    "presets": preset_store.list_presets(name)}
        log("info", f"[preset] 已保存预设 {name}/{entry['name']}（{len(parts)} 个部件）")
        return {"success": True, "preset": entry,
                "presets": preset_store.list_presets(name)}

    def delete_preset(self, name: str, preset_name: str) -> dict:
        """删除指定预设（前端确认后调用）"""
        try:
            ok = preset_store.delete_preset(name, preset_name)
        except preset_store.BuiltinPresetError:
            # 内置预设不可删除
            log("info", f"[preset] 拒绝删除内置预设 {name}/{preset_name}")
            return {"success": False, "error": "builtin",
                    "presets": preset_store.list_presets(name)}
        except Exception as e:
            log("warning", f"[preset] 删除预设失败 {name}/{preset_name}: {e}")
            return {"success": False, "error": str(e),
                    "presets": preset_store.list_presets(name)}
        if ok:
            log("info", f"[preset] 已删除预设 {name}/{preset_name}")
        return {"success": ok, "presets": preset_store.list_presets(name)}

    def import_preset(
        self,
        character: str,
        preset_name: str,
        orders: Optional[List] = None,
        parts: Optional[List[Dict]] = None,
        game: str = "",
        overwrite: bool = False,
        sketch: Optional[Dict] = None,
    ) -> dict:
        """导入预设（代码导入传 orders=[排序值…]；文件导入传 parts=[{name, sorting_order}]）。

        规则:
        - 只能导入到**当前已加载**的角色；代码/文件里的角色标识不一致 → error=character_mismatch
        - 标识校验：游戏标识缺失/未知/不符 → no_game / unknown_game / game_mismatch；
          角色标识缺失/未知/不符 → no_character_id / unknown_character / character_mismatch
        - 预设名校验（空/超长/含 <>:"/\\|?* / 结尾点空格）→ error=bad_name；
          与其他预设搭成同一文件（大小写扭名等）→ error=name_conflict
        - 部件匹配：带 name 时优先按名字（更精确，排序值仅兜底），否则按 sorting_order
          取该排序下的**全部**部件；匹配不到的条目计入 skipped，全不中 → error=no_match
        - 内置预设名禁止导入（error=builtin）；已存在同名用户预设且未确认覆盖 → error=exists
        """
        current = (self._character_data or {}).get("character_name", "")
        presets_now = preset_store.list_presets(current) if current else []

        def fail(code: str, **extra) -> dict:
            return {"success": False, "error": code, "presets": presets_now, **extra}

        # ── 游戏标识：缺失 / 未知作品 / 与当前作品不符 ──
        game = (game or "").strip()
        if not game:
            return fail("no_game")
        if game.lower() not in [g.lower() for g in GAME_MODES]:
            return fail("unknown_game", game=game)
        if game.lower() != get_mode().lower():
            return fail("game_mismatch", game=game)

        # ── 角色标识：缺失 / 未知角色 / 与当前角色不符（忽略大小写比较）──
        character = (character or "").strip()
        if not character:
            return fail("no_character_id")
        known_chars = [k.lower() for k in (self._bundles or {})]
        if known_chars and character.lower() not in known_chars:
            return fail("unknown_character", character=character)
        if not current:
            return fail("no_character")
        if character.lower() != current.lower():
            return fail("character_mismatch", character=character, current=current)

        td = self._character_data.get("transform_data", [])
        by_name = {p["name"]: p for p in td}
        by_order: Dict[int, List[Dict]] = {}
        for p in td:
            by_order.setdefault(_to_int(p.get("sorting_order", 0)), []).append(p)

        picked: Dict[str, Dict] = {}    # 部件名 → {name, sorting_order}（天然去重）
        skipped: List = []
        for item in (parts or []):
            item = item if isinstance(item, dict) else {}
            name = str(item.get("name") or "")
            order = item.get("sorting_order", item.get("order"))
            hit = by_name.get(name)
            if hit is None and order is not None:
                cands = by_order.get(_to_int(order), [])
                hit = cands[0] if cands else None
            if hit is None:
                skipped.append(name or _to_int(order))
                continue
            picked[hit["name"]] = {"name": hit["name"],
                                   "sorting_order": _to_int(hit.get("sorting_order", 0))}
        for order in (orders or []):
            cands = by_order.get(_to_int(order), [])
            if not cands:
                skipped.append(_to_int(order))
                continue
            for c in cands:
                picked[c["name"]] = {"name": c["name"],
                                     "sorting_order": _to_int(c.get("sorting_order", 0))}
        if not picked:
            return {"success": False, "error": "no_match",
                    "presets": preset_store.list_presets(current)}

        entries = sorted(picked.values(), key=lambda p: (p["sorting_order"], p["name"]))
        # 预设名校验（与其他入口一致；不合法不落盘）
        try:
            target = preset_store.validate_preset_name(preset_name)
        except preset_store.PresetNameError as e:
            log("info", f"[preset] 拒绝导入非法预设名 {current}/{preset_name!r}: {e}")
            return fail("name_conflict" if str(e) == "conflict" else "bad_name",
                        name=(preset_name or "").strip())
        if not overwrite:
            existing = next((p for p in preset_store.list_presets(current)
                             if p["name"] == target), None)
            if existing is not None:
                return {"success": False,
                        "error": "builtin" if existing.get("builtin") else "exists",
                        "name": target, "presets": preset_store.list_presets(current)}
        try:
            entry = preset_store.save_preset(current, target, entries, sketch)
        except preset_store.BuiltinPresetError:
            log("info", f"[preset] 拒绝导入内置预设名 {current}/{target}")
            return {"success": False, "error": "builtin", "name": target,
                    "presets": preset_store.list_presets(current)}
        except preset_store.PresetNameError as e:
            log("info", f"[preset] 拒绝导入非法预设名 {current}/{target}: {e}")
            return fail("name_conflict" if str(e) == "conflict" else "bad_name", name=target)
        except Exception as e:
            log("warning", f"[preset] 导入预设失败 {current}/{target}: {e}")
            return {"success": False, "error": "failed", "message": str(e),
                    "presets": preset_store.list_presets(current)}
        log("info", f"[preset] 已导入预设 {current}/{entry['name']}"
                    f"（{len(entries)} 个部件，跳过 {len(skipped)}）")
        return {"success": True, "preset": entry, "count": len(entries),
                "skipped": skipped, "presets": preset_store.list_presets(current)}

    def get_thumbnails(self):
        """为当前角色所有部件生成缩略图 data URL（事件: thumbnails_ready）"""
        with self._state_lock:
            gen, data = self._char_gen, self._character_data
        def worker():
            result = {}
            if data:
                for part in data.get("transform_data", []):
                    if gen != self._char_gen:
                        return
                    url = _sprite_thumb_data_url(Path(part["sprite_path"]), size=(96, 96))
                    if url:
                        result[part["name"]] = url
            self._emit_character(gen, "thumbnails_ready", result)
        self._run_async(worker)
        return True

    def composite(self, selected_names: List[str], sketch_text: str = "", sketch_size: int = 56, sketch_align: str = "center"):
        """合成角色图像并推送预览 data URL（事件: progress / composite_done）

        sketch_text: Anan 素描本自定义文字（空则忽略）；sketch_size: 文字字号（像素）
        sketch_align: 文字对齐方式（left/center/right）
        """
        with self._state_lock:
            self._composite_gen += 1
            gen, char_gen = self._composite_gen, self._char_gen
            data = self._character_data

        def send(event, payload):
            with self._state_lock:
                if gen == self._composite_gen and char_gen == self._char_gen:
                    self._emit(event, payload)

        def worker():
            if not data:
                send("composite_done", {"ok": False, "error": "no_data"})
                return

            def cb(cur, total):
                if gen != self._composite_gen:
                    return  # 已被更新的请求取代，不再上报进度
                send("progress", {"current": cur, "total": total, "phase": "composite"})

            send("status", {"text": _("app.status.compositing")})
            # 合成串行化：共享画布/精灵缓存同一时刻仅一个 worker 使用（防止并发写污染）
            with self._composite_lock:
                if gen != self._composite_gen or char_gen != self._char_gen:
                    return  # 等待锁期间已被更新的请求取代，丢弃
                try:
                    img = self._compositor.composite(
                        data["transform_data"],
                        selected_names=selected_names,
                        progress_callback=cb,
                        sketchbook_text=sketch_text or None,
                        sketch_font_size=int(sketch_size or 56),
                        sketch_align=(sketch_align or "center"),
                        mask_mapping=data.get("mask_mapping"),
                    )
                    # The compositor returns a reusable canvas. Snapshot it before unlocking.
                    if img is not None:
                        img = img.copy()
                except Exception as e:
                    log("error", _("log.composite_failed", e=e))
                    send("composite_done", {"ok": False, "error": str(e)})
                    return
            if gen != self._composite_gen or char_gen != self._char_gen:
                return  # 合成期间被更新的请求取代，丢弃结果（不覆盖最新预览）
            if img is None:
                send("composite_done", {"ok": False, "error": "empty"})
                return
            log("info", _("log.composite_done", size=f"{img.width}x{img.height}"))
            data_url, pv_size = _pil_preview(img, max_side=self._preview_max_side())
            with self._state_lock:
                if gen != self._composite_gen or char_gen != self._char_gen:
                    return
                self._composite_image = img
                self._emit("composite_done", {
                    "ok": True, "data_url": data_url,
                    "size": pv_size, "full_size": list(img.size),
                })
        self._run_async(worker)
        return True

    def preview_part(self, name: str):
        """单部件放大预览：把该部件画到“临时画布”上（事件: part_preview_ready）

        使用合成逻辑放置精灵：临时画布尺寸沿用当前合成图（尚无合成图时按整角色计算），
        因此该精灵呈现在它在角色中的真实位置，而不是屏幕/画面中央。
        不套用 ClippingMask 裁剪（mask_mapping=None）：否则被裁剪的叠加层会被裁成空区域、完全看不到。
        """
        with self._state_lock:
            gen = self._char_gen
            data = self._character_data
        def worker():
            if not data:
                self._emit("part_preview_ready", {"ok": False, "name": name, "error": "no_data"})
                return
            parts = data.get("transform_data") or []
            if not any(p.get("name") == name for p in parts):
                self._emit("part_preview_ready", {"ok": False, "name": name, "error": "not_found"})
                return

            comp = self._part_compositor
            if comp is None:
                comp = SpriteCompositor(scale=self._compositor.scale)
                self._part_compositor = comp

            # 与主合成串行：画布尺寸取自共享的 _composite_image，避免读到合成中途的尺寸
            with self._composite_lock:
                size = (self._composite_image.size if self._composite_image is not None
                        else comp.calc_canvas_size(parts))
                try:
                    img = comp.composite(
                        parts,
                        selected_names=[name],
                        mask_mapping=None,
                        canvas_size=size,
                    )
                    if img is not None:
                        img = img.copy()
                except Exception as e:
                    log("error", _("log.composite_failed", e=e))
                    self._emit("part_preview_ready", {"ok": False, "name": name, "error": str(e)})
                    return

            if img is None:
                self._emit("part_preview_ready", {"ok": False, "name": name, "error": "empty"})
                return
            data_url, pv_size = _pil_preview(img, max_side=self._preview_max_side())
            self._emit_character(gen, "part_preview_ready", {
                "ok": True,
                "name": name,
                "data_url": data_url,
                "size": pv_size,               # 实际显示的预览尺寸（随预览画质变化）
                "full_size": list(img.size),   # 临时画布完整尺寸
            })
        self._run_async(worker)
        return True

    def save_composite(self):
        """保存合成图（事件: save_complete）"""
        def worker():
            with self._state_lock:
                if self._composite_image is None:
                    self._emit("save_complete", {"ok": False, "error": "no_image"})
                    return
                out_img = self._composite_image.copy()
                char_name = (self._character_data or {}).get("character_name", "composite")
            try:
                # 关闭“导出原始画质”时：导出与预览画质一致（按预览缩放比例降采样）
                if not self._export_original_quality:
                    out_img = _downscale_for_preview(out_img, self._preview_max_side())
                path = save_composite(out_img, self._output_dir, char_name)
            except Exception as e:
                self._emit("save_complete", {"ok": False, "error": str(e)})
                return
            # 保存合成图（导出图像）也计入累计导出
            self._export_count += 1
            save_settings(export_count=self._export_count)
            log("info", _("log.composite_saved", path=path))
            self._emit("save_complete", {"ok": True, "path": str(path), "dir": str(path.parent), "export_count": self._export_count})
        self._run_async(worker)
        return True

    # ── 名片合成 ──────────────────────────────────────────
    #
    # 素材与排版参数解析自游戏 bundle（见 src/nameplate.py 顶部说明）：
    #   general-sprites_assets_all.bundle → Sprite "NamePlateBase"（601x289 空白名片底板）
    #   naninovel-ui_assets_all.bundle    → AuthorBase / AuthorLabel 节点（字号 136、文本左边界 −213、
    #                                        垂直中心 +14，均相对底板中心）
    # 底板提取到 data/nameplate/（与 temp/ 解耦：清缓存不丢，无需重复提取）；
    # 字体放 data/fonts/，由用户自备。

    def _nameplate_assets(self) -> Dict:
        """名片素材现状（按候选目录顺序查找底板）"""
        for d in nameplate.nameplate_dirs():
            base = d / nameplate.BASE_PNG_NAME
            if base.exists():
                return {"dir": str(d), "base": str(base), "ready": True}
        d = nameplate.nameplate_dir(writable=True)
        return {"dir": str(d), "base": "", "ready": False}

    def _nameplate_renderer_instance(self) -> "nameplate.NameplateRenderer":
        """返回（并缓存）名片渲染器；素材变化时自动重建"""
        assets = self._nameplate_assets()
        if not assets["ready"]:
            raise nameplate.NameplateAssetsMissing(assets["dir"])
        key = assets["base"]
        if self._nameplate_renderer is None or self._nameplate_key != key:
            self._nameplate_renderer = nameplate.NameplateRenderer(Path(assets["base"]))
            self._nameplate_key = key
            log("info", f"[nameplate] 已加载名片底板 {assets['base']}")
        return self._nameplate_renderer

    def get_nameplate_info(self) -> dict:
        """名片合成的静态信息（同步）：素材状态 / 字体列表 / 权威排版参数 / 上次目录"""
        assets = self._nameplate_assets()
        try:
            nameplate.fonts_dir(writable=True)      # 确保可写字体目录存在，便于用户直接往里放字体
        except Exception:
            pass
        fonts_dir = nameplate.fonts_dir()
        return {
            "ready": assets["ready"],
            "assets": assets,
            "fonts": nameplate.list_fonts_all(),
            "fonts_dir": str(fonts_dir),
            "system_font": nameplate.system_font_path() or "",
            # 现读 settings.json（不取 BundleLoader 的启动快照），与 prepare_nameplate 的起点一致
            "last_directory": get_last_directory() or self._loader.last_path,
            "layout": {
                # 以下数字全部来自解析出的 UI 节点，前端只做展示/校准
                "base_size": list(nameplate.BASE_SPRITE_SIZE),
                "font_size": nameplate.LABEL_FONT_SIZE,
                "label_size": list(nameplate.LABEL_SIZE),
                "label_pos": list(nameplate.LABEL_ANCHORED_POS),
                "margin_left": nameplate.LABEL_MARGIN_LEFT,
                "center_y": nameplate.LABEL_CENTER_Y,
                "steps": dict(nameplate.DEFAULT_FONT_STEPS),
            },
        }

    def prepare_nameplate(self, bundle_path: str = "", with_fonts: bool = True):
        """自动查找并提取名片素材 +（可选）游戏原版字体（事件: nameplate_assets）

        查找起点 = settings.json 的 `last_directory`（**每次查找现读**，用户刚选的游戏目录立即生效）：
        先在该目录及其下级查找（优先 `StandaloneWindows64`，素材实际存放处），
        找不到再逐级向上做**浅层探测**；仅对最接近起点的少数几层做浅递归兜底
        （见 src/nameplate.py 的 _RECURSE_ROOTS / _DEFAULT_DOWN_DEPTH）。
        自动查找失败时返回 searched / hint 供前端提示；`bundle_path` 可手动指定：
        传**目录** = 以它为搜索起点，传**文件** = 直接用它。
        查找期间用户可调 `cancel_nameplate_prepare` 中止（事件带 cancelled=True）。

        with_fonts: 顺带提取游戏字体（TsukushiMincho / SourceHanSerifSC 等）到
                    webui/assets/fonts/，已存在的同名文件跳过
        """
        self._nameplate_gen += 1                      # 新一次查找：让仍在跑的旧查找自行退出
        gen = self._nameplate_gen

        def worker():
            self._nameplate_cancel = False            # 每次查找独立（上次的停止不留到这次）

            def cancelled():
                # 用户点了「停止查找」，或已被更新的一次查找取代
                return self._nameplate_cancel or gen != self._nameplate_gen
            try:
                # 起点以 settings.json 为权威：**每次查找现读**，保证对 last_directory 的变化敏感
                # （BundleLoader.last_path 只是进程启动时的快照，用户新选了游戏目录后可能仍是旧值）
                start = Path(get_last_directory() or self._loader.last_path or ".")
                searched: List[str] = []

                # bundle_path 可为：bundle 文件（直接用它）或**目录**（作为搜索起点）
                src: Optional[Path] = None
                if bundle_path:
                    given = Path(bundle_path)
                    if given.is_dir():
                        start = given     # 用户指定的搜索起点目录
                    elif given.exists():
                        src = given       # 用户指定的 bundle 文件 → 直接用
                if src is None:
                    log("info", f"[nameplate] 查找名片素材，起点: {start}")
                    src, searched = nameplate.find_sprites_bundle(start, should_cancel=cancelled)

                if src is None or not src.exists():
                    log("warning", f"[nameplate] 未找到名片素材 bundle（已搜索: {searched[:6]}）")
                    if cancelled():                    # 期间已取消/已被新查找取代 → 不回灌陈旧结果
                        return
                    self._emit("nameplate_assets", {
                        "ok": False,
                        "error": "bundle_not_found",
                        "manual": bool(bundle_path) and Path(bundle_path).exists(),
                        #         True = 用户确实指定过路径（目录起点/素材文件）且无效 → 不再自动弹提示模态；
                        #         False = 用户给的路径不存在（实际走的是自动查找）→ 仍弹指引模态
                        "start": str(start),
                        "searched": searched[:6],
                        # 人工查找的位置指引（前端模态窗口展示：去哪里找、该选哪个文件）
                        "hint": {
                            "rel": nameplate.GAME_REL_HINT,
                            "file": nameplate.BUNDLE_HINT_FILE,
                        },
                    })
                    return

                if cancelled():
                    raise nameplate.NameplateSearchCancelled()
                info = nameplate.extract_base_assets(src)   # 自动选可写目录（优先 webui/assets/nameplate）

                # 顺带提取游戏原版字体（明朝体/宋体等），失败不影响底板提取
                fonts_saved: List[Dict] = []
                fonts_dir = nameplate.fonts_dir(writable=True)   # 只读安装 → 回退 data/nameplate/fonts
                if with_fonts:
                    try:
                        bundles = nameplate.find_font_bundles(src.parent, should_cancel=cancelled)
                        if bundles:
                            fonts_saved = nameplate.extract_font_assets(bundles, fonts_dir)
                    except Exception as e:
                        log("warning", f"[nameplate] 提取游戏字体失败（可手动放入字体）: {e}")

                self._nameplate_renderer = None       # 素材已更新 → 重建
                self._nameplate_key = None
                if cancelled():                       # 期间已取消/已被新查找取代 → 静默丢弃
                    return
                self._emit("nameplate_assets", {
                    "ok": True,
                    "bundle": str(src),
                    "size": info["size"],
                    "assets": self._nameplate_assets(),
                    "fonts_extracted": fonts_saved,
                    "fonts": nameplate.list_fonts_all(),
                    "fonts_dir": str(fonts_dir),
                    "searched": searched[:6],
                })
            except nameplate.NameplateSearchCancelled:
                # 中止事件由 cancel_nameplate_prepare **立即**发出（点击即响应）；
                # 这里只静默退出 —— 单次目录枚举在超大目录上可能耗数秒，等检测到标志再回报就太迟了
                log("info", "[nameplate] 素材查找已中止（后台静默退出）")
            except Exception as e:
                log("error", f"[nameplate] 提取名片素材失败: {e}")
                self._emit("nameplate_assets", {"ok": False, "error": str(e)})
        self._run_async(worker)
        return True

    def cancel_nameplate_prepare(self) -> dict:
        """中止正在进行的名片素材查找（用户点「停止查找」）

        **立即回报 cancelled 事件**，前端即刻复位；后台 worker 会在下一个检查点静默退出
        （单次目录枚举在超大目录上可能要数秒，等 worker 自己发现标志再回报会明显卡顿）。
        """
        self._nameplate_cancel = True
        self._emit("nameplate_assets", {"ok": False, "cancelled": True})
        log("info", "[nameplate] 收到中止素材查找的请求（已立即回报前端）")
        return {"success": True}

    def import_nameplate_font(self, path: str) -> dict:
        """把用户选定的字体文件复制到可写字体目录（同步），返回最新字体列表"""
        try:
            src = Path(path)
            if not src.is_file() or src.suffix.lower() not in nameplate.FONT_EXTS:
                return {"success": False, "error": "bad_file"}
            dest_dir = nameplate.fonts_dir(writable=True)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            log("info", f"[nameplate] 已导入字体 {src.name}")
            return {"success": True, "fonts": nameplate.list_fonts_all()}
        except Exception as e:
            log("warning", f"[nameplate] 导入字体失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _nameplate_kwargs(params: Dict) -> Dict:
        """把前端参数整理为 NameplateRenderer.render 的关键字参数"""
        params = params or {}
        raw_steps = params.get("steps") or {}
        steps = {}
        for key in ("surname_head", "given_head", "rest"):
            try:
                if key in raw_steps and raw_steps[key] is not None:
                    steps[key] = float(raw_steps[key])
            except (TypeError, ValueError):
                pass
        try:
            scale = float(params.get("scale") or 1.0)
        except (TypeError, ValueError):
            scale = 1.0
        return {
            "font_path": str(params.get("font") or "") or None,
            "scale": max(0.1, min(4.0, scale)),
            "color": str(params.get("color") or "#FFFFFF"),
            "head_color": str(params.get("head_color") or "") or None,
            "steps": steps or None,
        }

    def render_nameplate(self, params: Dict):
        """渲染名片预览（事件: nameplate_rendered）"""
        def worker():
            try:
                renderer = self._nameplate_renderer_instance()
                with self._composite_lock:      # 与角色合成互斥：PIL 解码/渲染串行，避免内存峰值叠加
                    img = renderer.render(
                        surname=str((params or {}).get("surname") or ""),
                        given=str((params or {}).get("given") or ""),
                        **self._nameplate_kwargs(params),
                    )
                self._nameplate_image = img
                data_url, pv_size = _pil_preview(img, max_side=self._preview_max_side())
                log("info", f"[nameplate] 已渲染名片 {img.width}x{img.height}")
                self._emit("nameplate_rendered", {
                    "ok": True,
                    "data_url": data_url,
                    "size": pv_size,
                    "full_size": list(img.size),
                })
            except nameplate.NameplateAssetsMissing:
                self._emit("nameplate_rendered", {"ok": False, "error": "assets_missing",
                                                  "assets": self._nameplate_assets()})
            except Exception as e:
                log("error", f"[nameplate] 渲染名片失败: {e}")
                self._emit("nameplate_rendered", {"ok": False, "error": str(e)})
        self._run_async(worker)
        return True

    def save_nameplate(self, params: Dict = None):
        """保存名片 PNG 到输出目录 output/nameplate/（事件: nameplate_saved）"""
        def worker():
            img = self._nameplate_image
            if img is None:
                self._emit("nameplate_saved", {"ok": False, "error": "no_image"})
                return
            try:
                params_d = params or {}
                stem = nameplate.safe_file_stem(
                    f"{params_d.get('surname') or ''}{params_d.get('given') or ''}")
                out_img = img
                if not self._export_original_quality:
                    out_img = _downscale_for_preview(img, self._preview_max_side())
                path = save_png(out_img, self._output_dir / "nameplate", stem)
            except Exception as e:
                self._emit("nameplate_saved", {"ok": False, "error": str(e)})
                return
            self._export_count += 1
            save_settings(export_count=self._export_count)
            log("info", f"[nameplate] 名片已保存: {path}")
            self._emit("nameplate_saved", {
                "ok": True,
                "path": str(path),
                "dir": str(path.parent),
                "export_count": self._export_count,
            })
        self._run_async(worker)
        return True

    # ── 清理 / 更新 ────────────────────────────────────────

    def clear_cache(self, keep_preview: bool = False):
        """清空 temp 缓存（事件: cache_cleared）；keep_preview=True 时保留 preview 预览临时目录"""
        with self._state_lock:
            self._cache_clear_pending += 1
            self._cache_ready.clear()
            self._char_gen += 1
            self._composite_gen += 1
            self._char_busy = False
            self._character_data = None
            self._composite_image = None
            self._preview_sprites = None
        self._background_cancel.set()
        def worker():
            try:
                self._clear_cache_files(keep_preview)
            finally:
                with self._state_lock:
                    self._cache_clear_pending -= 1
                    if self._cache_clear_pending == 0:
                        self._cache_ready.set()
        self._run_async(worker)
        return True

    def _clear_cache_files(self, keep_preview: bool) -> None:
        with self._work_lock, self._composite_lock:
            self._background_preview_cache.clear()
            self._compositor.clear_cache()
            if self._part_compositor is not None:
                self._part_compositor.clear_cache()
            if keep_preview and self._temp_dir.exists():
                for child in self._temp_dir.iterdir():
                    if child.name == "preview":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        try:
                            child.unlink(missing_ok=True)
                        except OSError as error:
                            log("warning", f"Failed to remove cache file {child}: {error}")
            else:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            log("info", _("log.cache_cleared"))
            self._emit("cache_cleared", {"temp_dir": str(self._temp_dir)})

    def clear_output(self):
        """清空输出目录（事件: output_cleared）"""
        def worker():
            shutil.rmtree(self._output_dir, ignore_errors=True)
            log("info", _("log.output_dir_cleared"))
            self._emit("output_cleared", {"output_dir": str(self._output_dir)})
        self._run_async(worker)
        return True

    def clear_log(self):
        """清理日志目录中的所有日志文件（事件: log_cleared）"""
        def worker():
            count = clear_logs()
            log("info", _("log.logs_cleared"))
            self._emit("log_cleared", {"ok": True, "count": count, "path": str(LOG_FILE) if LOG_FILE else ""})
        self._run_async(worker)
        return True

    def check_update(self, silent: bool = False):
        """检查更新（事件: update_result）

        启动时的静默检查失败会重试至多 SILENT_UPDATE_RETRIES 次（网络/超时类错误）；
        静默模式不弹窗，每次尝试与最终结果都会写入日志。
        """
        def worker():
            max_retries = SILENT_UPDATE_RETRIES if silent else 0
            for attempt in range(max_retries + 1):
                try:
                    info = check_for_update(__version__)
                except UpdateError as e:
                    if attempt < max_retries:
                        log("warning", f"update check failed ({e.reason}), "
                                       f"retry {attempt + 1}/{max_retries}: {e}")
                        time.sleep(SILENT_UPDATE_RETRY_DELAY)
                        continue
                    log("warning", f"update check failed ({e.reason}) after {attempt + 1} attempt(s): {e}")
                    self._emit("update_result", {
                        "status": "error", "current": __version__,
                        "message": _update_error_message(e), "silent": bool(silent),
                    })
                    return
                except Exception as e:
                    log("warning", f"update check failed after {attempt + 1} attempt(s): {e}")
                    self._emit("update_result", {
                        "status": "error", "current": __version__,
                        "message": str(e), "silent": bool(silent),
                    })
                    return

                suffix = f" (after {attempt + 1} attempts)" if attempt else ""
                if info is None:
                    log("info", f"update check: already latest (v{__version__}){suffix}")
                    self._emit("update_result", {
                        "status": "latest", "current": __version__, "silent": bool(silent),
                    })
                else:
                    log("info", f"update check: v{info.latest_version} available{suffix}")
                    self._emit("update_result", {
                        "status": "available", "current": __version__,
                        "latest": info.latest_version, "url": info.release_url,
                        "notes": info.notes, "silent": bool(silent),
                    })
                return
        self._run_async(worker)
        return True

    def log_js(self, level: str, message: str) -> None:
        """接收前端 JavaScript 的 console 输出，标记为 [JS] 来源与控制台日志区分"""
        try:
            log(level, str(message)[:2000], source="JS")
        except Exception as e:
            log("warning", f"log_js failed: {e}")


# ===================================================================
# 无启动入口（设计如此）
# ===================================================================
# 本模块只是业务逻辑层，不提供 `python run.py` 启动方式。
# 唯一启动链路：start.bat → electron/main.js → spawn(backend.py) → JsApi
# 打包版：MCE.exe → resources/backend/backend.exe
# ===================================================================

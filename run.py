"""
魔法少女的魔女审判 - 角色立绘提取与拼接工具 (PyWebView 版)

工作流程:
    1. 选择游戏目录 → 加载所有角色 bundle
    2. 点击角色 → 自动检测是否有组件数据
       - 无组件 → 直接导出所有精灵
       - 有组件 → 询问用户操作模式
    3. 拼接模式 → 选择部件 + 预览 + 保存合成图

前端: webui/ (HTML/CSS/JS)，通过 js_api 桥接调用本模块。
"""

from __future__ import annotations  # 注解惰性求值：Electron 后端子进程（backend.py）无需真正导入 pywebview/pythonnet

import base64
import io
import json
import os
import shutil
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import webview
except ImportError:
    webview = None  # type: ignore[assignment]  # Electron 模式（backend.py）不依赖 pywebview

# 类型标注：PyWebView 模式为模块，Electron 模式为 None（Any 使两模式均可通过类型检查）
webview: Any  # type: ignore[misc]

from PIL import Image

# pythonnet：PyWebView 模式访问 .NET（WinForms/WebView2）必需；Electron 模式不需要
try:
    import clr  # noqa: F401
except ImportError:
    clr = None  # Electron 模式（backend.py）不依赖 pythonnet

from src.bundle_loader import BundleLoader
from src.cache_manager import load_extracted_data, save_extracted_data
from src.compositor import (
    LoadCancelled,
    SpriteCompositor,
    has_component_data,
)
from src.export_manager import save_composite
from src.worker_client import (
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
from src.logtools import clear_logs, configure, flush_logs, log, log_raw
from src.resource_monitor import ResourceMonitor
from src.settings import ACCENT_NAMES, get_accent, get_export_count, get_lang, get_last_directory, get_no_spoiler, get_output_dir, get_show_original_name, get_theme, save_settings
from src.updater import check_for_update
from src.version import __version__


# ── 程序基础路径（兼容 PyInstaller 冻结环境） ──────────────
if getattr(sys, "frozen", False):
    # 打包成 exe 后：exe 所在目录
    BASE_DIR = Path(sys.executable).parent
    # PyInstaller 解压目录（用于访问打包的数据文件）
    MEI_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    # 源码运行时：脚本所在目录
    BASE_DIR = Path(__file__).parent
    MEI_DIR = BASE_DIR

# 日志文件：logs/ 目录，文件名含程序启动时间（每次启动一个新文件）
LOG_FILE: Optional[Path] = None

# 调试模式：设置环境变量 PYWEBVIEW_DEBUG=1 可打开开发者工具
_DEBUG = os.environ.get("PYWEBVIEW_DEBUG", "") == "1"


# ── 控制台标题（跟随语言切换） ──────────────────────
def set_console_title():
    """设置控制台窗口标题，跟随当前语言"""
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


def _sprite_thumb_data_url(path: Path, size=(96, 96)) -> Optional[str]:
    """生成精灵缩略图 data URL（透明背景居中）"""
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        canvas.paste(img, offset, img)
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


# ===================================================================
# 资源定位（兼容 PyInstaller）
# ===================================================================

def _find_icon() -> Optional[str]:
    """查找应用图标文件路径（assets/ 目录）"""
    for p in [
        MEI_DIR / "icon.ico",                     # 打包后：--add-data 放到 _MEIPASS 根
        MEI_DIR / "assets" / "icon.ico",
        BASE_DIR / "assets" / "icon.ico",
        Path(__file__).parent / "assets" / "icon.ico",
    ]:
        if p.exists():
            return str(p)
    return None


def _get_webui_url() -> str:
    """返回前端 index.html 的 file:// URL"""
    for p in [
        MEI_DIR / "webui" / "index.html",
        BASE_DIR / "webui" / "index.html",
        Path(__file__).parent / "webui" / "index.html",
    ]:
        if p.exists():
            return p.as_uri()
    raise FileNotFoundError("webui/index.html not found")


# ===================================================================
# JS ↔ Python 桥接 API（js_api）
# ===================================================================

class JsApi:
    """暴露给前端 (pywebview.api.*) 的所有方法。

    约定:
      - 快操作（getter / 设置 / 文件对话框）为同步方法，直接返回结果。
      - 耗时操作启动后台线程，通过 window.__pywebview.events.<事件> 推送进度与结果。
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self._window: Optional[Any] = None
        self._loader = BundleLoader()
        self._compositor = SpriteCompositor(scale=100.0)

        # 内部状态（均为私有，避免被 js_api 递归暴露到前端）
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
        self._load_generation = 0               # 目录查找代号：新查找开始时递增，用于打断上一次未完成的查找
        self._loading_path: Optional[str] = None  # 当前进行中的加载目录（用于取消日志显示）
        self._debug_monitor = False             # 调试模式（仅本次运行有效，不持久化）：debug 日志 + 资源占用监视
        self._monitor: Optional[ResourceMonitor] = None  # 资源占用监视线程（调试模式开启时创建）
        self._base_title: str = ""              # 窗口基础标题（调试模式时附加资源占用信息）
        self._char_gen = 0                      # 角色加载代号：递增以中断旧加载
        self._char_busy = False                 # 是否正在加载角色/导出（读条中禁止切换）
        self._work_lock = threading.Lock()      # 提取类任务互斥锁：避免并发写 temp/（旧任务取消清理与新任务写入竞争）
        self._char_has_component: Dict[str, bool] = {}  # 加载目录时缓存的角色组件状态（避免点击时重复解析 bundle）

    # ── 事件推送 ──────────────────────────────────────────

    def _emit(self, event: str, payload: dict):
        """向前端推送事件: window.__pywebview.events.<event>(payload)"""
        if self._window is None:
            return
        try:
            js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
            self._window.evaluate_js(
                "window.__pywebview && window.__pywebview.events && "
                f"window.__pywebview.events.{event} && "
                f"window.__pywebview.events.{event}({js})"
            )
        except Exception as e:
            log("warning", f"[webview] emit {event} failed: {e}")

    @staticmethod
    def _run_async(fn):
        threading.Thread(target=fn, daemon=True).start()

    def _on_gui_thread(self, fn):
        """在 WinForms GUI 线程执行 fn 并返回结果。

        pywebview 的 js_api 方法都在独立线程中执行，而 WinForms 的
        create_file_dialog 不允许跨线程访问控件，因此需要借助
        Control.Invoke 把调用投递回 GUI 线程。若投递失败则直接调用（保守回退）。
        """
        if self._window is None:
            return fn()
        try:
            from webview.platforms import winforms as _wf
            view = _wf.BrowserView.instances.get(self._window.uid)
            if view is not None and hasattr(view, "Invoke"):
                from System import Action  # type: ignore[reportMissingImports]
                box = {}

                def _wrapper():
                    box["r"] = fn()

                view.Invoke(Action(_wrapper))
                return box.get("r")
        except Exception as e:
            log("warning", f"[webview] GUI thread invoke failed: {e}")
        return fn()

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
            "debug": self._debug_monitor,
        }

    def set_lang(self, code: str) -> dict:
        """切换语言并持久化，返回新翻译表（同时更新窗口标题）"""
        if code in LANGUAGE_CODES:
            set_lang(code)
            save_settings(lang=code)
            log("info", _("log.lang_changed", code=code))
            set_console_title()
            # 同步更新主窗口标题（create_window 时标题固定，需手动 set_title）
            self._base_title = f"{_('app.title')} v{__version__}"
            if self._window is not None:
                try:
                    self._window.set_title(self._base_title)
                except Exception as e:
                    log("warning", f"set window title failed: {e}")
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

    def set_debug(self, enable: bool) -> dict:
        """开启/关闭调试模式（仅本次运行有效，不持久化）。

        开启后：输出 debug 日志 + 后台线程每 5 秒采集内存/CPU/窗口分辨率，
        推送 res_monitor 事件供前端状态栏显示。
        """
        enable = bool(enable)
        if enable == self._debug_monitor:
            return {"debug": self._debug_monitor}
        self._debug_monitor = enable
        if enable:
            configure(level="debug")
            log("info", _("log.debug_on"))
            self._monitor = ResourceMonitor(
                emit=self._on_res_monitor_payload,
                window_size=self._window_size,
            )
            self._monitor.start()
        else:
            if self._monitor is not None:
                self._monitor.stop()
            self._monitor = None
            configure(level="info")
            log("info", _("log.debug_off"))
            # 恢复标题栏（去掉资源占用信息）
            try:
                if self._window is not None:
                    self._window.set_title(self._base_title)
            except Exception:
                pass
        return {"debug": self._debug_monitor}

    def _on_res_monitor_payload(self, payload: dict):
        """资源占用采集回调：记录 debug 日志、推送 res_monitor 事件，并同步到窗口标题栏"""
        win = _("log.resource_win", width=payload["width"], height=payload["height"]) if "width" in payload else ""
        log("debug", _("log.resource_usage", mem=payload["mem_mb"], cpu=payload["cpu"], win=win))
        self._emit("res_monitor", payload)
        # 同步到标题栏（含窗口分辨率，文案跟随当前语言）
        try:
            if self._window is not None:
                self._window.set_title(
                    self._base_title + _("log.resource_title", mem=payload["mem_mb"], cpu=payload["cpu"], win=win)
                )
        except Exception:
            pass

    def _window_size(self):
        """获取当前窗口尺寸 (w, h)；失败返回 None（跨线程访问控件需投递 GUI 线程）"""
        window = self._window
        if window is None:
            return None
        try:
            return self._on_gui_thread(
                lambda: (int(getattr(window, "width", 0)), int(getattr(window, "height", 0)))
            )
        except Exception:
            return None

    # ── 目录 / 设置 ────────────────────────────────────────

    def select_directory(self) -> Optional[str]:
        """打开文件夹选择对话框；初始目录使用 settings.json 中记忆的上次路径"""
        window = self._window
        if window is None:
            return None
        initial = get_last_directory() or str(Path.home())
        if not Path(initial).exists():
            initial = str(Path.home())

        def do_dialog():
            # 原生对话框必须在 GUI 线程；js_api 方法运行在子线程，
            # 故由 _on_gui_thread 投递到 GUI 线程后调用。
            from webview.platforms import winforms as _wf
            return _wf.create_file_dialog(
                webview.FileDialog.FOLDER, initial, False, "", (), window.uid
            )

        result = self._on_gui_thread(do_dialog)
        chosen = None
        if isinstance(result, str) and result:
            chosen = result
        elif isinstance(result, (tuple, list)) and result:
            chosen = result[0]
        if chosen:
            # 记忆本次选择到 settings.json，供下次启动使用
            save_settings(last_directory=chosen)
        return chosen

    def select_output_dir(self) -> Optional[str]:
        """打开输出目录选择对话框（不修改 last_directory 记忆）"""
        window = self._window
        if window is None:
            return None
        initial = str(self._output_dir)
        if not Path(initial).exists():
            initial = str(Path.home())

        def do_dialog():
            from webview.platforms import winforms as _wf
            return _wf.create_file_dialog(
                webview.FileDialog.FOLDER, initial, False, "", (), window.uid
            )

        result = self._on_gui_thread(do_dialog)
        chosen = None
        if isinstance(result, str) and result:
            chosen = result
        elif isinstance(result, (tuple, list)) and result:
            chosen = result[0]
        return chosen

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
        """打开输出文件夹"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(self._output_dir))
        except Exception as e:
            log("warning", f"open output failed: {e}")

    def open_path(self, path: str):
        """在资源管理器中打开指定路径"""
        if not path:
            return
        try:
            os.startfile(str(path))
        except Exception as e:
            log("warning", f"open path failed: {e}")

    def open_url(self, url: str):
        """在系统浏览器打开链接"""
        try:
            webbrowser.open(url)
        except Exception as e:
            log("warning", f"open url failed: {e}")

    # ── 目录加载 ──────────────────────────────────────────

    def load_directory(self, path: str):
        """加载游戏目录（后台线程，事件: progress / load_complete）；新查找会打断上一次未完成的查找"""
        # 若上一次加载仍在进行，立即记录其被新加载取代（显示旧目录，避免取消日志滞后）
        if self._loading_path is not None:
            log("info", _("log.load_cancelled_dir", path=self._loading_path))
        self._load_generation += 1
        gen = self._load_generation
        self._loading_path = path
        log("info", _("log.loading_dir", path=path))

        def worker():
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "load"})
            def cancel():
                # 一旦有新一次 load_directory 调用（代号变化），中断本次查找
                return gen != self._load_generation
            self._emit("status", {"text": _("app.progress.loading_bundles")})
            result = self._loader.load_from_directory(path, progress_callback=cb, cancel_check=cancel)
            if result.get("cancelled"):
                # 已被更新的加载取代（取消日志已在 load_directory 同步打印）
                self._emit("load_complete", result)
                return
            # 本次加载正常结束（未被取代）：清空进行中标记
            if gen == self._load_generation:
                self._loading_path = None
            if result["success"]:
                self._bundles = result["bundles"]
                self._char_has_component = result.get("components", {})
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
        self._char_gen += 1
        self._char_busy = False
        # 清理上一个角色的内存临时数据
        self._character_data = None
        self._composite_image = None
        self._preview_sprites = None
        # 切换角色时清理 preview 临时预览目录
        preview_dir = self._temp_dir / "preview"
        if preview_dir.exists():
            shutil.rmtree(preview_dir, ignore_errors=True)
            log("info", _("log.preview_cleaned", path=str(preview_dir)))
        import gc
        gc.collect()

        def worker():
            bundle_path = Path(self._bundles.get(name, ""))
            if not bundle_path.exists():
                self._emit("analyze_complete", {
                    "name": name, "has_components": False,
                    "error": _("dialog.bundle_not_found", path=str(bundle_path)),
                })
                return
            self._emit("status", {"text": _("app.status.analyzing", name=name)})
            try:
                # 优先使用加载目录时缓存的组件状态（不再重复解析 bundle）；无缓存时回退实时分析
                has = self._char_has_component.get(name)
                if has is None:
                    has = has_component_data(bundle_path)
                log("info", _("log.analyze_has", name=name) if has else _("log.analyze_none", name=name))
            except Exception as e:
                log("error", _("log.analyze_failed", name=name, e=e))
                self._emit("analyze_error", {"name": name, "message": str(e)})
                return
            self._emit("analyze_complete", {
                "name": name, "bundle_path": str(bundle_path), "has_components": has,
            })
        self._run_async(worker)
        return True

    # ── 导出 / 提取 / 合成 ────────────────────────────────

    def preview_bundle(self, name: str):
        """提取无组件角色的精灵到临时预览目录（事件: progress / preview_ready / preview_error）"""
        def worker():
            gen = self._char_gen
            self._char_busy = True
            bundle_path = Path(self._bundles.get(name, ""))
            target = self._temp_dir / "preview" / name
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "preview"})
            # 立即给出反馈（等待锁期间也显示，避免首次 UnityPy 解析 bundle 看似卡死）
            self._emit("status", {"text": _("app.status.extracting", name=name)})
            self._emit("progress", {"current": 0, "total": 1, "phase": "preview"})
            with self._work_lock:   # 等待前一个任务（含取消清理）完全退出，避免并发写 preview/ 目录
                try:
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
                except LoadCancelled:
                    # 用户中断：清理预览临时数据（锁内执行，不会与新任务并发删除）
                    shutil.rmtree(self._temp_dir / "preview", ignore_errors=True)
                    self._preview_sprites = None
                    log("info", _("log.char_load_cancelled"))
                    return
                except Exception as e:
                    log("error", _("log.process_data_failed", e=e))
                    self._emit("preview_error", {"name": name, "message": str(e)})
                    return
                finally:
                    self._char_busy = False
                self._preview_sprites = sprites
                log("info", _("log.preview_ready", name=name, count=len(sprites)))
                self._emit("preview_ready", {
                    "name": name,
                    "count": len(sprites),
                    "sprites": [{"name": s["name"], "size": s["size"]} for s in sprites],
                })
        self._run_async(worker)
        return True

    def get_preview_thumbnails(self):
        """为当前预览精灵生成完整预览图 data URL（事件: progress / preview_thumbs_ready）"""
        def worker():
            sprites = self._preview_sprites or []
            total = len(sprites)
            result = {}
            for i, s in enumerate(sprites):
                self._emit("progress", {"current": i, "total": total, "phase": "preview_thumbs"})
                url = _sprite_full_data_url(Path(s["file_path"]), max_side=768)
                if url:
                    result[s["name"]] = url
            self._emit("preview_thumbs_ready", result)
        self._run_async(worker)
        return True

    def export_preview(self, name: str, selected_names: Optional[List[str]] = None):
        """导出预览精灵到输出目录；selected_names 为空则导出全部（事件: progress / export_complete / export_error）"""
        def worker():
            src_dir = self._temp_dir / "preview" / name
            if not src_dir.exists():
                self._emit("export_error", {"name": name, "message": "no_preview"})
                return
            out_dir = self._output_dir / name
            out_dir.mkdir(parents=True, exist_ok=True)
            files = sorted(src_dir.glob("*.png"))
            if selected_names:
                sel = set(selected_names)
                files = [f for f in files if f.stem in sel]
            count = 0
            for f in files:
                try:
                    shutil.copy2(f, out_dir / f.name)
                    count += 1
                except Exception as e:
                    log("error", _("log.sprite_extract_failed", id=f.name, e=e))
            self._export_count += 1
            save_settings(export_count=self._export_count)
            log("info", _("log.export_complete", name=name, count=count))
            self._emit("export_complete", {
                "name": name, "count": count,
                "output_dir": str(out_dir),
                "export_count": self._export_count,
            })
        self._run_async(worker)
        return True

    def cancel_character_load(self) -> dict:
        """中断当前角色加载/导出，并清理临时数据"""
        self._char_gen += 1
        self._char_busy = False
        self._character_data = None
        self._composite_image = None
        self._preview_sprites = None
        try:
            shutil.rmtree(self._temp_dir / "preview", ignore_errors=True)
        except Exception:
            pass
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
        def worker():
            gen = self._char_gen
            self._char_busy = True
            bundle_path = Path(self._bundles.get(name, ""))
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "export"})
            self._emit("status", {"text": _("app.status.exporting", name=name)})
            self._emit("progress", {"current": 0, "total": 1, "phase": "export"})
            log("info", _("log.export_start", name=name))
            with self._work_lock:   # 与提取类任务互斥，避免并发读写临时/输出目录
                try:
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
                    self._char_busy = False
                    return
                except Exception as e:
                    log("error", _("log.export_failed", name=name, e=e))
                    self._emit("export_error", {"name": name, "message": str(e)})
                    self._char_busy = False
                    return
                # 累计导出次数（每次成功导出 +1，不按图片数量）
                self._export_count += 1
                save_settings(export_count=self._export_count)
                self._char_busy = False
                log("info", _("log.export_complete", name=name, count=len(results)))
                self._emit("export_complete", {
                    "name": name, "count": len(results),
                    "output_dir": str(self._output_dir / name),
                    "export_count": self._export_count,
                })
        self._run_async(worker)
        return True

    def start_composite_mode(self, name: str):
        """进入拼接模式：提取角色数据（优先缓存）（事件: progress / data_ready / data_error）"""
        def worker():
            gen = self._char_gen
            self._char_busy = True
            bundle_path = Path(self._bundles.get(name, ""))
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "extract"})
            # 立即给出反馈（等待锁期间也显示，避免首次 UnityPy 解析 bundle 看似卡死）
            self._emit("status", {"text": _("app.status.extracting", name=name)})
            self._emit("progress", {"current": 0, "total": 1, "phase": "extract"})
            with self._work_lock:   # 等待前一个任务（含取消清理）完全退出，避免并发写 temp/ 导致文件被删
                cached = load_extracted_data(self._temp_dir, name)
                if cached:
                    self._character_data = cached
                    log("info", _("log.extract_cache_hit", name=name))
                    self._char_busy = False
                    self._emit("data_ready", self._data_summary(cached))
                    return
                try:
                    self._temp_dir.mkdir(parents=True, exist_ok=True)
                    data = self._extract_via_worker(
                        "extract_character",
                        {
                            "bundle_path": str(bundle_path),
                            "output_dir": str(self._temp_dir),
                        },
                        cb,
                        lambda: gen != self._char_gen,
                    )
                    save_extracted_data(data, self._temp_dir, name)
                except LoadCancelled:
                    # 用户中断：清理本次提取的内存与磁盘数据（锁内执行，不会与新任务并发删除）
                    self._character_data = None
                    shutil.rmtree(self._temp_dir / name, ignore_errors=True)
                    log("info", _("log.char_load_cancelled"))
                    self._char_busy = False
                    return
                except Exception as e:
                    log("error", _("log.process_data_failed", e=e))
                    self._emit("data_error", {"name": name, "message": str(e)})
                    self._char_busy = False
                    return
                self._character_data = data
                self._char_busy = False
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
        return {
            "name": data.get("character_name", ""),
            "count": len(transform),
            "transform_data": transform,
            "hierarchy": data.get("hierarchy", []),
        }

    def get_thumbnails(self):
        """为当前角色所有部件生成缩略图 data URL（事件: thumbnails_ready）"""
        def worker():
            result = {}
            if self._character_data:
                for part in self._character_data.get("transform_data", []):
                    url = _sprite_thumb_data_url(Path(part["sprite_path"]), size=(96, 96))
                    if url:
                        result[part["name"]] = url
            self._emit("thumbnails_ready", result)
        self._run_async(worker)
        return True

    def composite(self, selected_names: List[str], sketch_text: str = "", sketch_size: int = 56, sketch_align: str = "center"):
        """合成角色图像并推送预览 data URL（事件: progress / composite_done）

        sketch_text: Anan 素描本自定义文字（空则忽略）；sketch_size: 文字字号（像素）
        sketch_align: 文字对齐方式（left/center/right）
        """
        def worker():
            if not self._character_data:
                self._emit("composite_done", {"ok": False, "error": "no_data"})
                return
            def cb(cur, total):
                self._emit("progress", {"current": cur, "total": total, "phase": "composite"})
            self._emit("status", {"text": _("app.status.compositing")})
            try:
                img = self._compositor.composite(
                    self._character_data["transform_data"],
                    selected_names=selected_names,
                    progress_callback=cb,
                    sketchbook_text=sketch_text or None,
                    sketch_font_size=int(sketch_size or 56),
                    sketch_align=(sketch_align or "center"),
                    mask_mapping=self._character_data.get("mask_mapping"),
                )
            except Exception as e:
                log("error", _("log.composite_failed", e=e))
                self._emit("composite_done", {"ok": False, "error": str(e)})
                return
            if img is None:
                self._emit("composite_done", {"ok": False, "error": "empty"})
                return
            self._composite_image = img
            log("info", _("log.composite_done", size=f"{img.width}x{img.height}"))
            self._emit("composite_done", {
                "ok": True,
                "data_url": _pil_to_data_url(img, max_side=1600),
                "size": list(img.size),
            })
        self._run_async(worker)
        return True

    def save_composite(self):
        """保存合成图（事件: save_complete）"""
        def worker():
            if self._composite_image is None:
                self._emit("save_complete", {"ok": False, "error": "no_image"})
                return
            char_name = (self._character_data or {}).get("character_name", "composite")
            try:
                path = save_composite(self._composite_image, self._output_dir, char_name)
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

    # ── 清理 / 更新 ────────────────────────────────────────

    def clear_cache(self, keep_preview: bool = False):
        """清空 temp 缓存（事件: cache_cleared）；keep_preview=True 时保留 preview 预览临时目录"""
        def worker():
            if keep_preview and self._temp_dir.exists():
                # 保留预览临时目录，仅清理其余缓存（精灵/角色数据等）
                for child in self._temp_dir.iterdir():
                    if child.name == "preview":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        try:
                            child.unlink()
                        except Exception:
                            pass
            else:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._character_data = None
            self._composite_image = None
            self._preview_sprites = None
            log("info", _("log.cache_cleared"))
            self._emit("cache_cleared", {"temp_dir": str(self._temp_dir)})
        self._run_async(worker)
        return True

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

    def quit_app(self) -> dict:
        """退出程序（关闭主窗口触发退出流程）"""
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception as e:
            log("warning", f"quit_app failed: {e}")
        return {"ok": True}

    # ── 无边框标题栏窗口控制（frameless）──────────────────

    def window_minimize(self) -> dict:
        """最小化窗口（标题栏最小化按钮）"""
        try:
            if self._window is not None:
                self._window.minimize()
        except Exception as e:
            log("warning", f"window_minimize failed: {e}")
        return {"ok": True}

    def window_maximize(self) -> dict:
        """最大化/还原切换：最大化到工作区（不覆盖任务栏），还原恢复原位置大小"""
        hwnd = self._get_hwnd()
        if not hwnd:
            return {"ok": False}
        try:
            if getattr(self, "_win_max", False):
                restore = getattr(self, "_win_restore", None)
                if restore:
                    self._win_set(hwnd, *restore)
                self._win_max = False
            else:
                self._win_restore = self._win_rect(hwnd)
                self._win_set(hwnd, *self._work_area())
                self._win_max = True
        except Exception as e:
            log("warning", f"window_maximize failed: {e}")
        return {"ok": True, "maximized": getattr(self, "_win_max", False)}

    def window_drag_start(self, screen_x: int, screen_y: int) -> dict:
        """开始拖动标题栏：若处于最大化状态则还原为原大小，并使标题栏贴合鼠标位置"""
        hwnd = self._get_hwnd()
        if not hwnd:
            return {"ok": False}
        try:
            if getattr(self, "_win_max", False):
                restore = getattr(self, "_win_restore", None)
                rect = self._win_rect(hwnd)
                if restore and rect:
                    _, _, rw, rh = restore
                    scale = self._system_scale()
                    # 前端 screen 坐标为逻辑像素 → 转物理像素（与 GetWindowRect 单位一致）
                    sx_p = int(screen_x * scale)
                    sy_p = int(screen_y * scale)
                    # 鼠标在当前（最大化）窗口内的物理偏移；横偏移限制在还原宽度内、纵偏移限制在标题栏高度内
                    off_x = sx_p - rect[0]
                    off_y = sy_p - rect[1]
                    title_h = int(36 * scale)
                    off_x = max(0, min(off_x, max(rw - 1, 0)))
                    off_y = max(0, min(off_y, title_h))
                    # 还原窗口左上角 = 鼠标位置 - 鼠标在窗口内的偏移（贴合鼠标）
                    self._win_set(hwnd, sx_p - off_x, sy_p - off_y, rw, rh)
                    self._win_max = False
        except Exception as e:
            log("warning", f"window_drag_start failed: {e}")
        return {"ok": True, "maximized": getattr(self, "_win_max", False)}

    def window_move(self, dx: int, dy: int) -> dict:
        """按增量移动窗口（前端 screen 坐标为逻辑像素，需 ×DPI 转为物理像素）"""
        hwnd = self._get_hwnd()
        if not hwnd:
            return {"ok": False}
        try:
            r = self._win_rect(hwnd)
            if r:
                scale = self._system_scale()
                self._win_set(hwnd, r[0] + int(dx * scale), r[1] + int(dy * scale), r[2], r[3])
        except Exception as e:
            log("warning", f"window_move failed: {e}")
        return {"ok": True}

    def window_resize(self, direction: str, dx: int, dy: int) -> dict:
        """按方向调整窗口大小（边缘/角落缩放）。
        direction 为 l/r/t/b 组合（如 'l'、'r'、'tl'、'br'），增量单位为物理像素。
        以「固定边不动」推导新位置，尺寸达到最小值后相应边保持不动，避免窗口偏移。
        """
        hwnd = self._get_hwnd()
        if not hwnd:
            return {"ok": False}
        try:
            r = self._win_rect(hwnd)
            if not r:
                return {"ok": False}
            ox, oy, ow, oh = r
            dx, dy = int(dx), int(dy)
            # 计算新尺寸
            nw, nh = ow, oh
            if "l" in direction:
                nw = ow - dx
            if "r" in direction:
                nw = ow + dx
            if "t" in direction:
                nh = oh - dy
            if "b" in direction:
                nh = oh + dy
            # 最小尺寸（物理像素 ≈ 逻辑 960x640 × 系统缩放）
            scale = self._system_scale()
            min_w, min_h = int(960 * scale), int(640 * scale)
            nw = max(nw, min_w)
            nh = max(nh, min_h)
            # 计算新位置：固定对边，缩放边移动
            nx, ny = ox, oy
            if "l" in direction:
                nx = ox + (ow - nw)   # 右边固定：左边 = 原左 + (原宽 - 新宽)
            if "t" in direction:
                ny = oy + (oh - nh)   # 下边固定：上边 = 原上 + (原高 - 新高)
            self._win_set(hwnd, nx, ny, nw, nh)
        except Exception as e:
            log("warning", f"window_resize failed: {e}")
        return {"ok": True}

    # ── Win32 窗口操作辅助 ─────────────────────────────

    def _get_hwnd(self) -> Optional[int]:
        """获取主窗口句柄（WinForms 控件需在 GUI 线程访问，仅首次获取后缓存）"""
        if getattr(self, "_hwnd", None):
            return self._hwnd

        def _g() -> Optional[int]:
            w = self._window
            native = getattr(w, "native", None) if w is not None else None
            if native is None:
                return None
            handle = getattr(native, "Handle", None)
            # pythonnet 的 IntPtr 不能直接 int()，需先 ToInt64()
            return int(handle.ToInt64()) if handle is not None else None

        try:
            hwnd = self._on_gui_thread(_g)
        except Exception as e:
            log("warning", f"get hwnd failed: {e}")
            hwnd = None
        self._hwnd = hwnd
        return hwnd

    @staticmethod
    def _win_rect(hwnd: int) -> Optional[tuple]:
        """获取窗口位置与大小（物理像素）"""
        import ctypes
        from ctypes import wintypes
        r = wintypes.RECT()
        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return r.left, r.top, r.right - r.left, r.bottom - r.top
        return None

    @staticmethod
    def _win_set(hwnd: int, x: int, y: int, w: int, h: int) -> None:
        """设置窗口位置与大小（SetWindowPos，跨线程安全）"""
        import ctypes
        SWP_NOZORDER = 0x0004
        ctypes.windll.user32.SetWindowPos(hwnd, 0, int(x), int(y), int(w), int(h), SWP_NOZORDER)

    @staticmethod
    def _work_area() -> tuple:
        """主显示器工作区（物理像素，不含任务栏）：(left, top, width, height)"""
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

    @staticmethod
    def _system_scale() -> float:
        """系统 DPI 缩放系数（物理像素 / 逻辑像素）"""
        try:
            import ctypes
            return ctypes.windll.user32.GetDpiForSystem() / 96.0
        except Exception:
            return 1.0

    def check_update(self, silent: bool = False):
        """检查更新（事件: update_result）"""
        def worker():
            try:
                info = check_for_update(__version__)
                if info is None:
                    self._emit("update_result", {
                        "status": "latest", "current": __version__, "silent": bool(silent),
                    })
                else:
                    self._emit("update_result", {
                        "status": "available", "current": __version__,
                        "latest": info.latest_version, "url": info.release_url,
                        "notes": info.notes, "silent": bool(silent),
                    })
            except Exception as e:
                self._emit("update_result", {
                    "status": "error", "current": __version__,
                    "message": str(e), "silent": bool(silent),
                })
        self._run_async(worker)
        return True

    def log_js(self, level: str, message: str) -> None:
        """接收前端 JavaScript 的 console 输出，标记为 [JS] 来源与控制台日志区分"""
        try:
            log(level, str(message)[:2000], source="JS")
        except Exception as e:
            log("warning", f"log_js failed: {e}")


# ===================================================================
# 入口
# ===================================================================

def main():
    global LOG_FILE
    # 日志文件：logs/ 目录，文件名含程序启动时间（每次启动一个新文件）
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    LOG_FILE = BASE_DIR / "logs" / f"{ts}.log"
    configure(log_file=LOG_FILE, level="info")

    # 语言：优先使用设置中保存的语言，否则按系统自动检测
    saved_lang = get_lang()
    if saved_lang and saved_lang in LANGUAGE_CODES:
        set_lang(saved_lang)
        log("info", _("log.lang_from_settings", code=saved_lang))
    else:
        detected_lang = _detect_system_language()
        set_lang(detected_lang)
        log("info", _("log.lang_detected", code=detected_lang))

    # 程序启动日志（置于语言加载完成后，确保文案跟随当前语言）
    log("info", _("log.app_started", version=__version__))
    # 启动时记录免责声明（第三方非官方工具提示）
    log("info", _("app.disclaimer"))

    set_console_title()

    # 启动提示走日志队列（与日志串行写流，避免并发写导致换行粘连）
    log_raw("")
    log_raw("=" * 48)
    log_raw(_("console.startup_msg"))
    log_raw("=" * 48)
    log_raw("")
    flush_logs()

    api = JsApi()
    window = webview.create_window(
        title=f"{_('app.title')} v{__version__}",
        url=_get_webui_url(),
        js_api=api,
        width=1280,
        height=860,
        min_size=(960, 640),
        background_color="#0f1115",
        text_select=True,
        frameless=False,   # 原生窗口（无边框体验请使用 Electron 模式；PyWebView 作为备用回退）
    )
    assert window is not None  # pywebview 的 create_window 始终返回 Window 实例
    api._window = window
    api._base_title = f"{_('app.title')} v{__version__}"  # 供调试模式标题栏附加资源占用信息
    webview.start(icon=_find_icon(), debug=_DEBUG)

    # 结束时记录免责声明（第三方非官方工具提示）
    log("info", _("app.disclaimer"))

    # 主窗口已关闭，进入退出流程：记录退出日志（此时 WebView2 等后台子进程可能仍在清理，故措辞为“正在退出”而非“已关闭”；若直接关闭控制台则进程立即终止，此段不会执行）
    log("info", _("log.app_exited"))

    # 退出前清理 preview 临时预览目录
    try:
        preview_dir = BASE_DIR / "temp" / "preview"
        if preview_dir.exists():
            shutil.rmtree(preview_dir, ignore_errors=True)
            log("info", _("log.preview_cleaned", path=str(preview_dir)))
    except Exception:
        pass

    # 退出前强制回收（释放 UnityPy / WebView2 等大对象），并输出资源检测日志
    try:
        import gc
        collected = gc.collect()
        from src.resource_monitor import process_memory_mb
        mem = round(process_memory_mb(), 1)
        log("info", _("log.gc_before_exit", mem=mem, count=collected))
    except Exception:
        log("info", _("log.gc_before_exit", mem=0, count=0))

    # 控制台输出退出提示（走日志队列，与日志串行；退出前 flush 保证写出）
    log_raw("")
    log_raw("=" * 48)
    log_raw(_("console.exit_msg"))
    log_raw("=" * 48)
    log_raw("")
    flush_logs()


if __name__ == "__main__":
    main()

"""
魔法少女的魔女审判 - 角色立绘提取与拼接工具

工作流程:
    1. 选择游戏目录 → 加载所有角色 bundle
    2. 点击角色 → 自动检测是否有组件数据
       - 无组件 → 直接导出所有精灵
       - 有组件 → 询问用户操作模式
    3. 拼接模式 → 选择部件 + 预览 + 保存合成图
"""

import argparse
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from src.bundleloader import BundleLoader
from src.compositor import (
    has_component_data,
    extract_character_data,
    SpriteCompositor,
)
from src.export_manager import export_sprites, save_composite
from src.cache_manager import save_extracted_data, load_extracted_data, clear_cache as clear_cache_dir
from src.ui_builder import (
    build_main_ui,
    build_welcome,
    set_window_icon,
    set_toplevel_icon,
)
from src.updater import check_for_update
from src.ui_helpers import (
    set_status, start_progress, update_progress, stop_progress,
    clear_preview, show_preview, clear_character_cache,
    load_thumbnail, update_selected_sprites_list,
    populate_hierarchy_tree,
)
from src.logtools import log, configure
from src.version import __version__
from src.i18n import _, set_lang, current_lang, LANGUAGE_CODES, LANG_CN, LANG_EN


# ── 程序基础路径（兼容 PyInstaller 冻结环境） ──────────────
if getattr(sys, 'frozen', False):
    # 打包成 exe 后：exe 所在目录
    BASE_DIR = Path(sys.executable).parent
    # PyInstaller 解压目录（用于访问打包的数据文件）
    MEI_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    # 源码运行时：脚本所在目录
    BASE_DIR = Path(__file__).parent
    MEI_DIR = BASE_DIR


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
    except Exception:
        pass
    return LANG_EN


# ===================================================================
# 主应用
# ===================================================================

class SpriteToolApp:
    """魔法少女的魔女审判 - 角色立绘提取工具主窗口"""

    # ── UI 组件（由 build_main_ui 动态创建，仅供类型检查） ──
    load_btn: ttk.Button
    open_output_btn: ttk.Button
    _char_list_title: ttk.Label
    char_listbox: tk.Listbox
    progress_bar: ttk.Progressbar
    lang_combo: ttk.Combobox
    clear_cache_btn: ttk.Button
    update_btn: ttk.Button
    status_bar: ttk.Label
    notebook: ttk.Notebook
    info_frame: ttk.Frame
    selection_frame: ttk.Frame
    hierarchy_frame: ttk.Frame
    select_all_btn: ttk.Button
    deselect_all_btn: ttk.Button
    sel_count_label: ttk.Label
    save_btn: ttk.Button
    clear_preview_btn: ttk.Button
    composite_btn: ttk.Button
    auto_update_cb: ttk.Checkbutton
    _json_hint: ttk.Label
    parts_canvas: tk.Canvas
    parts_inner: ttk.Frame
    sel_header: ttk.Label
    sel_listbox: tk.Listbox
    preview_status: ttk.Label
    preview_canvas: tk.Canvas
    preview_image_id: int
    _info_text: tk.Text
    _hierarchy_hint: ttk.Label
    _expand_btn: ttk.Button
    _collapse_btn: ttk.Button
    hierarchy_tree: ttk.Treeview

    def __init__(self, output_dir: Optional[Path] = None):
        self.root = tk.Tk()
        self.root.title(f"{_('app.title')} v{__version__}")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # 设置窗口图标
        set_window_icon(self)

        # 记录启动时语言，供 _setup_ui 初始化下拉框
        self._start_lang = current_lang()

        # 核心组件
        self.loader = BundleLoader()
        self.compositor = SpriteCompositor(scale=100.0)

        # 状态
        self.bundles: Dict[str, str] = {}          # {角色名: bundle路径}
        self.character_data: Optional[Dict] = None  # extract_character_data 的结果
        self.composite_image: Optional[Image.Image] = None
        self._thumb_refs: List[ImageTk.PhotoImage] = []  # 缩略图引用

        # 部件列表状态
        self.part_vars: List[tk.BooleanVar] = []
        self.part_labels: List[Dict] = []

        # 实时预览标志与防抖定时器
        self.auto_update = tk.BooleanVar(value=True)
        self._preview_timer: Optional[str] = None

        # 输出目录（默认基于程序所在目录，可通过命令行参数 -o 指定）
        self.output_dir = output_dir or (BASE_DIR / "output")

        # 临时缓存目录（精灵提取过程中的中间文件，关闭或切换角色时自动清空）
        self.temp_dir = BASE_DIR / "temp"

        # ── 构建 UI（UI 组件由 build_main_ui 动态创建） ──
        build_main_ui(self)
        self._bind_events()

        # 启动后自动静默检查更新（仅在有新版本时提示，最新版本不打扰）
        self.root.after(500, lambda: self._on_check_update(silent=True))

    # ── UI 构建/层级/欢迎页等方法已移至 src/ui_builder.py ──

    def _expand_all_nodes(self):
        """展开所有节点"""
        def expand(parent: str = ""):
            for child in self.hierarchy_tree.get_children(parent):
                self.hierarchy_tree.item(child, open=True)
                expand(child)
        expand()

    def _collapse_all_nodes(self):
        """折叠所有节点"""
        def collapse(parent: str = ""):
            for child in self.hierarchy_tree.get_children(parent):
                self.hierarchy_tree.item(child, open=False)
                collapse(child)
        collapse()

    # ── 语言切换 ──────────────────────────────────────────────

    def _on_language_change(self, event=None):
        """语言下拉框切换事件"""
        idx = self.lang_combo.current()
        code = LANGUAGE_CODES[idx]
        set_lang(code)
        self._apply_language()

    def _apply_language(self):
        """刷新所有 UI 文本以匹配当前语言"""
        # 窗口标题 + 控制台标题
        self.root.title(f"{_('app.title')} v{__version__}")
        set_console_title()

        # 左侧面板
        self.load_btn.config(text=_("left.load_button"))
        self.open_output_btn.config(text=_("left.open_output"))
        self._char_list_title.config(text=_("left.char_list_title"))
        self.clear_cache_btn.config(text=_("left.clear_cache"))
        self.update_btn.config(text=_("left.check_update"))
        self.status_bar.config(text=_("app.status.ready"))

        # 语言下拉框更新（保持当前选中项不变）
        current_idx = self.lang_combo.current()
        self.lang_combo["values"] = [_(f"lang.{code}") for code in LANGUAGE_CODES]
        self.lang_combo.current(current_idx)

        # Notebook 标签
        self.notebook.tab(self.info_frame, text=_("info.tab_title"))
        self.notebook.tab(self.selection_frame, text=_("tabs.parts"))
        self.notebook.tab(self.hierarchy_frame, text=_("tabs.hierarchy"))

        # 部件选择页
        self._on_composite()
        self.select_all_btn.config(text=_("parts.select_all"))
        self.deselect_all_btn.config(text=_("parts.deselect_all"))
        selected = sum(1 for v in self.part_vars if v.get())
        self.sel_count_label.config(text=_("parts.selected_count", count=selected))
        self.save_btn.config(text=_("parts.save_composite"))
        self.clear_preview_btn.config(text=_("parts.clear_preview"))
        self.composite_btn.config(text=_("parts.composite_btn"))
        self.auto_update_cb.config(text=_("parts.auto_update"))
        self.preview_status.config(text=_("parts.no_preview"))
        self.sel_header.config(text=_("parts.selected_list_title"))
        self._json_hint.config(text=_("parts.json_hint"))


        # 组件结构页
        self._hierarchy_hint.config(text=_("hierarchy.hint"))
        self._expand_btn.config(text=_("hierarchy.expand_all"))
        self._collapse_btn.config(text=_("hierarchy.collapse_all"))

        # 信息页重建
        if self.bundles:
            self._show_character_list()
        else:
            build_welcome(self)

        # 如果当前有角色数据已加载，刷新层次树中的显示文本
        if self.character_data:
            hierarchy = self.character_data.get("hierarchy", [])
            populate_hierarchy_tree(self, hierarchy)

    def _bind_events(self):
        self.char_listbox.bind("<<ListboxSelect>>", self._on_character_select)

    # ── 目录加载 ───────────────────────────────────────────────

    def _on_open_output(self):
        """打开输出文件夹"""
        output_path = self.output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_path))

    # ── 更新检查 ────────────────────────────────────────────────

    def _on_check_update(self, silent: bool = False):
        """检查 GitHub 是否有新版本（后台线程，完成后在主线程处理）

        silent=True（启动自动检查）: 不改变状态栏/按钮，已是最新或检查失败均不弹窗，仅在有新版本时提示。
        """
        if not silent:
            self.status_bar.config(text=_("app.status.checking_update"))
            self.update_btn.config(state=tk.DISABLED)

        def task():
            try:
                info = check_for_update(__version__)
                self.root.after(0, lambda: self._on_update_result(info, silent))
            except Exception as e:
                log("error", f"check update failed: {e}")
                self.root.after(0, lambda: self._on_update_error(str(e), silent))

        threading.Thread(target=task, daemon=True).start()

    def _on_update_result(self, info, silent: bool = False):
        """更新检查完成：无新版本或提示是否前往下载"""
        if not silent:
            self.update_btn.config(state=tk.NORMAL)
            self.status_bar.config(text=_("app.status.ready"))

        if info is None:
            # 已是最新：手动检查时弹窗确认，启动自动检查时静默不打扰
            if not silent:
                messagebox.showinfo(
                    _("dialog.update_latest_title"),
                    _("dialog.update_latest_msg", current=__version__),
                )
            return

        if messagebox.askyesno(
            _("dialog.update_available_title"),
            _("dialog.update_available_msg",
              new=info.latest_version, current=__version__),
        ):
            import webbrowser
            webbrowser.open(info.release_url)

    def _on_update_error(self, msg: str, silent: bool = False):
        """更新检查失败提示"""
        if not silent:
            self.update_btn.config(state=tk.NORMAL)
            self.status_bar.config(text=_("app.status.ready"))
            messagebox.showerror(
                _("dialog.update_check_error_title"),
                _("dialog.update_check_error_msg", msg=msg),
            )

    def _on_load_directory(self):
        dir_path = self.loader.select_directory(_("dir.select_title"))
        if not dir_path:
            return

        self._start_progress(_("app.progress.loading_bundles"))
        self.load_btn.config(state=tk.DISABLED)
        self.char_listbox.delete(0, tk.END)

        def load_task():
            def cb(current, total):
                self.root.after(0, lambda: self._update_progress(current, total))
            result = self.loader.load_from_directory(dir_path, progress_callback=cb)
            self.root.after(0, lambda: self._on_load_complete(result))

        threading.Thread(target=load_task, daemon=True).start()

    def _on_load_complete(self, result: Dict):
        self.load_btn.config(state=tk.NORMAL)
        self._stop_progress()
        if result["success"]:
            self.bundles = result["bundles"]
            self.char_listbox.delete(0, tk.END)
            for name in sorted(self.bundles.keys()):
                self.char_listbox.insert(tk.END, name)
            set_status(self,_("app.status.loaded", count=result['count']))
            self.notebook.select(0)

            # 切换到信息页并显示列表
            self._show_character_list()
        else:
            msg = "\n".join(result["errors"])
            messagebox.showerror(_("dialog.load_error_title"), msg)
            set_status(self,_("app.status.load_failed"))

    def _show_character_list(self):
        """在信息页显示已加载的角色列表"""
        for w in self.info_frame.winfo_children():
            w.destroy()

        text = tk.Text(self.info_frame, wrap=tk.WORD, padx=20, pady=20, font=("Consolas", 10))
        text.insert(tk.END, _("info.char_list_header", count=len(self.bundles)))
        for i, name in enumerate(sorted(self.bundles.keys()), 1):
            text.insert(tk.END, f"  {i:2d}. {name}\n")
        text.insert(tk.END, _("info.char_list_footer"))
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)

    # ── 角色选择 ───────────────────────────────────────────────

    # _clear_character_cache moved to src/ui_helpers.py

    def _on_character_select(self, event):
        sel = self.char_listbox.curselection()
        if not sel:
            return
        name = self.char_listbox.get(sel[0])
        bundle_path = Path(self.bundles[name])

        # 清除上一个角色的缓存
        clear_character_cache(self)

        self._start_progress(_("app.status.analyzing", name=name))
        self.notebook.select(0)

        def analyze_task():
            try:
                has_components = has_component_data(bundle_path)
                self.root.after(0, lambda: self._on_analyze_complete(name, bundle_path, has_components))
            except Exception as e:
                log("error", _("log.analyze_failed", name=name, e=e))
                self.root.after(0, lambda: self._stop_progress(_("app.status.analyze_failed")))
                self.root.after(0, lambda: messagebox.showerror(_("dialog.analyze_error_title"),
                    _("dialog.analyze_error_msg", name=name, msg=e)))

        threading.Thread(target=analyze_task, daemon=True).start()

    def _on_analyze_complete(self, name: str, bundle_path: Path, has_components: bool):
        self._stop_progress(_("app.status.ready"))

        if not has_components:
            # ── 无组件 → 弹窗确认后导出 ──
            log("info", _("log.no_component_exporting", name=name))
            if not messagebox.askyesno(
                _("dialog.export_confirm_title"),
                _("dialog.export_confirm_msg", name=name)
            ):
                set_status(self,_("app.status.cancelled"))
                return

            self._start_progress(_("app.status.exporting", name=name))
            def export_task():
                def cb(current, total):
                    self.root.after(0, lambda: self._update_progress(current, total))
                count = len(export_sprites(bundle_path, self.output_dir, has_components=False, progress_callback=cb))
                self.root.after(0, lambda: self._on_export_complete(name, count))
            threading.Thread(target=export_task, daemon=True).start()
        else:
            # ── 有组件 → 询问模式 ──
            log("info", _("log.component_detected", name=name))
            self._ask_mode_dialog(name, bundle_path)

    def _on_export_complete(self, name: str, count: int):
        self._stop_progress(_("app.status.export_done", name=name, count=count))
        output_path = self.output_dir / name
        messagebox.showinfo(_("dialog.export_complete_title"),
                           _("dialog.export_complete_msg", name=name, count=count, path=output_path))

        # 打开输出目录
        os.startfile(str(output_path))

    # ── 模式选择对话框 ────────────────────────────────────────

    def _ask_mode_dialog(self, name: str, bundle_path: Path):
        """弹出对话框让用户选择处理方式"""
        dialog = tk.Toplevel(self.root)
        dialog.title(_("dialog.ask_mode_title", name=name))
        set_toplevel_icon(dialog)
        dialog.geometry("480x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=_("dialog.ask_mode_title", name=name), font=("Arial", 12, "bold")).pack(pady=(20, 5))
        ttk.Label(dialog, text=_("dialog.ask_mode_msg"),
                  wraplength=420).pack(pady=(0, 15))

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(expand=True)

        result: Dict[str, Optional[str]] = {"mode": None}  # 用于在回调中传值

        def choose_mode(mode: str):
            result["mode"] = mode
            dialog.destroy()

        ttk.Button(btn_frame, text=_("dialog.ask_mode_export"),
                   command=lambda: choose_mode("export"),
                   width=30).pack(pady=8)
        ttk.Label(btn_frame, text=_("dialog.ask_mode_export_hint"),
                  font=("Arial", 9), foreground="gray").pack()

        ttk.Button(btn_frame, text=_("dialog.ask_mode_composite"),
                   command=lambda: choose_mode("composite"),
                   width=30).pack(pady=(20, 8))
        ttk.Label(btn_frame, text=_("dialog.ask_mode_composite_hint"),
                  font=("Arial", 9), foreground="gray").pack()

        # 等待对话框关闭
        self.root.wait_window(dialog)

        mode = result["mode"]
        if mode == "export":
            self._start_progress(_("app.status.exporting", name=name))
            def export_task():
                def cb(current, total):
                    self.root.after(0, lambda: self._update_progress(current, total))
                count = len(export_sprites(bundle_path, self.output_dir, has_components=True, progress_callback=cb))
                self.root.after(0, lambda: self._on_export_complete(name, count))
            threading.Thread(target=export_task, daemon=True).start()
        elif mode == "composite":
            self._start_composite_mode(name, bundle_path)

    # ── 拼接模式 ─────────────────────────────────────────────

    def _start_composite_mode(self, name: str, bundle_path: Path):
        # 检查是否有完整缓存
        cached = load_extracted_data(self.temp_dir, name)
        if cached:
            self.root.after(0, lambda: self._on_data_ready(name, cached))
            return

        self._start_progress(_("app.status.extracting", name=name))

        def extract_task():
            def cb(current, total):
                self.root.after(0, lambda: self._update_progress(current, total))
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            data = extract_character_data(bundle_path, self.temp_dir, progress_callback=cb)
            save_extracted_data(data, self.temp_dir, name)
            self.root.after(0, lambda: self._on_data_ready(name, data))

        threading.Thread(target=extract_task, daemon=True).start()

    # _try_load_cached 已移至 cache_manager.load_extracted_data

    def _on_data_ready(self, name: str, data: Dict):
        """角色数据提取完成后，填充部件列表（全部默认选中），等待用户手动合成"""
        try:
            self.character_data = data
            transform_data = data.get("transform_data", [])
            self._stop_progress(_("app.status.extract_done", name=name, count=len(transform_data)))

            if not transform_data:
                messagebox.showwarning(_("dialog.warning_no_parts"), _("dialog.warning_no_parts_msg", name=name))
                return

            # 先切换到选择标签页，确保界面可见
            self.notebook.select(1)
            self.root.update_idletasks()

            # 填充部件列表
            self._populate_parts(transform_data)

            # 强制刷新 Canvas 滚动区域并回到顶部
            self.parts_canvas.configure(scrollregion=self.parts_canvas.bbox("all"))
            self.parts_canvas.yview_moveto(0)

            # 默认全部不选中，由用户手动勾选
            self._on_part_toggle()
            self.root.update_idletasks()

            log("info", _("log.parts_loaded", count=len(transform_data)))

            # 填充组件结构树
            hierarchy = data.get("hierarchy", [])
            populate_hierarchy_tree(self, hierarchy)
        except Exception as e:
            log("error", _("log.process_data_failed", e=e))
            import traceback
            traceback.print_exc()
            messagebox.showerror(_("dialog.analyze_error_title"), _("dialog.process_error_msg", msg=e))

    def _populate_parts(self, transform_data: List[Dict]):
        """填充部件选择列表（带精灵缩略图预览）"""
        for w in self.parts_inner.winfo_children():
            w.destroy()
        self.part_vars.clear()
        self.part_labels.clear()

        # 按分类分组
        categories: Dict[str, List[Dict]] = {}
        for part in transform_data:
            cat = part.get("category", "other")
            categories.setdefault(cat, []).append(part)

        # 存储 PhotoImage 引用防止被 GC
        self._thumb_refs: List[ImageTk.PhotoImage] = []

        for cat, parts in categories.items():
            # 分类标题
            header = ttk.Label(self.parts_inner, text=_("parts.category_header", cat=cat, count=len(parts)),
                               font=("Arial", 10, "bold"), foreground="#555")
            header.pack(fill=tk.X, pady=(10, 2), padx=5)

            for part in parts:
                frame = ttk.Frame(self.parts_inner)
                frame.pack(fill=tk.X, padx=10, pady=2)

                var = tk.BooleanVar()
                cb = ttk.Checkbutton(frame, variable=var,
                                     command=self._on_part_toggle)
                cb.pack(side=tk.LEFT)

                # ── 精灵缩略图预览 ──
                thumb = load_thumbnail(part["sprite_path"], size=(48, 48))
                if thumb:
                    thumb_label = ttk.Label(frame, image=thumb)
                    thumb_label.pack(side=tk.LEFT, padx=(4, 8))
                    self._thumb_refs.append(thumb)
                else:
                    ttk.Label(frame, text=_("parts.no_img"), font=("Consolas", 7),
                              foreground="gray").pack(side=tk.LEFT, padx=(4, 8))

                pos = part["position"]
                c = part.get("color", {})
                alpha = c.get("a", 1.0)
                info = _("parts.item_info",
                          name=part['name'], x=pos['x'], y=pos['y'],
                          order=part['sorting_order'], size=part['sprite_size'],
                          alpha=alpha)
                lbl = ttk.Label(frame, text=info, font=("Consolas", 9))
                lbl.pack(side=tk.LEFT, padx=(5, 0))

                self.part_vars.append(var)
                self.part_labels.append({"frame": frame, "part": part, "var": var})

        # 全部创建完毕后保持默认未选中状态
        self.sel_count_label.config(text=_("parts.selected_count", count=0))

    # _load_thumbnail, _update_selected_sprites_list moved to src/ui_helpers.py

    def _on_part_toggle(self):
        selected = sum(1 for v in self.part_vars if v.get())
        self.sel_count_label.config(text=_("parts.selected_count", count=selected))
        # 刷新右侧已选精灵列表
        update_selected_sprites_list(self)
        # 实时预览：勾选状态变化后自动调度合成（防抖 500ms）
        if self.auto_update.get():
            self._schedule_auto_preview()

    def _schedule_auto_preview(self):
        """防抖调度自动预览"""
        if self._preview_timer:
            self.root.after_cancel(self._preview_timer)
        self._preview_timer = self.root.after(500, self._on_composite)

    def _on_auto_update_toggle(self):
        """自动更新开关切换"""
        if self.auto_update.get():
            # 开启时立即生成一次
            self._schedule_auto_preview()

    def _select_all(self):
        for v in self.part_vars:
            v.set(True)
        self.sel_count_label.config(text=_("parts.selected_count", count=len(self.part_vars)))
        update_selected_sprites_list(self)
        if self.auto_update.get():
            self._schedule_auto_preview()

    def _deselect_all(self):
        for v in self.part_vars:
            v.set(False)
        self.sel_count_label.config(text=_("parts.selected_count", count=0))
        update_selected_sprites_list(self)
        if self.auto_update.get():
            self._schedule_auto_preview()

    # ── 合成 + 预览 ──────────────────────────────────────────

    def _on_composite(self):
        if not self.character_data:
            return

        transform_data = self.character_data.get("transform_data", [])
        selected = []
        for item in self.part_labels:
            if item["var"].get():
                selected.append(item["part"]["name"])

        if not selected:
            log("warning", _("log.no_parts_selected"))
            if not self.auto_update.get():
                messagebox.showinfo(_("info.tab_title"), _("parts.no_selection_hint"))
            return

        log("info", _("log.compositing", selected=len(selected), total=len(transform_data)))

        self.preview_status.config(text=_("parts.generating"))
        self._start_progress(_("app.status.compositing"))

        def composite_task():
            try:
                def cb(current, total):
                    self.root.after(0, lambda: self._update_progress(current, total))
                img = self.compositor.composite(transform_data, selected_names=selected, progress_callback=cb)
                self.root.after(0, lambda: self._on_composite_done(img))
            except Exception as e:
                log("error", _("log.composite_failed", e=e))
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self._show_composite_error(str(e)))

        threading.Thread(target=composite_task, daemon=True).start()

    def _on_composite_done(self, img: Optional[Image.Image]):
        if img is None:
            self.preview_status.config(text=_("parts.no_preview"))
            self._stop_progress(_("app.status.composite_failed"))
            return

        self.composite_image = img
        self.preview_status.config(text=_("parts.composite_done_fmt", w=img.size[0], h=img.size[1]))
        self._stop_progress(_("app.status.composite_done"))

        # 在同一页面显示预览（无需切换标签）
        self.root.update_idletasks()
        show_preview(self,img)

    def _show_composite_error(self, error_msg: str):
        """显示合成错误"""
        self.preview_status.config(text=_("parts.no_preview"))
        set_status(self,_("app.status.composite_failed"))
        messagebox.showerror(_("dialog.composite_error_title"), _("dialog.composite_error_msg", msg=error_msg))

    def _clear_preview(self):
        """清空预览画布"""
        self.preview_canvas.delete("all")
        self.preview_status.config(text=_("parts.no_preview"))
        self.composite_image = None
        set_status(self,_("app.status.preview_cleared"))

    def _show_preview(self, img: Image.Image):
        """在画布上显示预览图"""
        # 安全检查：图像尺寸必须有效
        if img.width < 1 or img.height < 1:
            log("error", _("log.invalid_preview_size", size=img.size))
            self.preview_status.config(text=_("parts.preview_failed"))
            return

        canvas = self.preview_canvas
        canvas.update_idletasks()

        # 获取画布可见尺寸（确保不小于 100x100）
        cw = max(canvas.winfo_width(), 100)
        ch = max(canvas.winfo_height(), 100)

        # 计算缩放比例，确保 display_w/display_h 至少为 1
        scale = min(cw / img.width, ch / img.height, 1.0)
        display_w = max(int(img.width * scale), 1)
        display_h = max(int(img.height * scale), 1)

        if scale < 1.0:
            thumb = img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        else:
            thumb = img

        self._photo = ImageTk.PhotoImage(thumb)

        canvas.delete("all")
        canvas.config(scrollregion=(0, 0, img.width, img.height))
        self.preview_image_id = canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

        # 如果缩放小于1，显示提示
        if scale < 1.0:
            canvas.create_text(cw // 2, 20, text=_("parts.scale_hint", scale=scale),
                               fill="red", font=("Arial", 10), tags="scale_hint")

    def _on_save(self):
        if self.composite_image is None:
            messagebox.showwarning(_("dialog.save_warning_title"), _("dialog.save_warning_msg"))
            return

        if not self.character_data:
            return

        char_name = self.character_data['character_name']
        try:
            save_path = save_composite(self.composite_image, self.output_dir, char_name)
            save_dir = save_path.parent
            messagebox.showinfo(_("dialog.save_success_title"), _("dialog.save_success_msg", path=save_path))
            os.startfile(str(save_dir))
        except Exception as e:
            messagebox.showerror(_("dialog.save_error_title"), _("dialog.save_error_msg", msg=e))

    # ── 工具 ──────────────────────────────────────────────────

    def _set_status(self, text: str):
        self.status_bar.config(text=text)
        self.root.update_idletasks()

    def _start_progress(self, text: str = "", maximum: int = 100):
        """显示进度条并更新状态文字（determinate 模式）"""
        set_status(self,text or _("app.progress.default"))
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = maximum
        self.progress_bar.pack(fill=tk.X, pady=(5, 0), before=self.status_bar)
        self.root.update_idletasks()

    def _update_progress(self, current: int, total: int):
        """更新进度条当前值（determinate 模式，自动换算百分比）"""
        self.progress_bar["maximum"] = total
        self.progress_bar["value"] = current
        self.root.update_idletasks()

    def _stop_progress(self, text: str = ""):
        """停止并隐藏进度条，恢复状态文字"""
        self.progress_bar["value"] = 0
        self.progress_bar.pack_forget()
        set_status(self,text or _("app.status.ready"))
        self.root.update_idletasks()

    def _on_clear_cache(self):
        """手动清除 temp 缓存目录（带确认对话框）"""
        if not self.temp_dir.exists():
            set_status(self,_("app.status.ready"))
            return
        if not messagebox.askyesno(
            _("left.clear_cache_confirm_title"),
            _("left.clear_cache_confirm_msg")
        ):
            return
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        log("info", _("log.temp_cleared", path=self.temp_dir))
        # 还原界面并切换到信息页
        clear_character_cache(self)
        self.notebook.select(0)
        set_status(self, _("app.status.ready"))

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.mainloop()


# ===================================================================
# 入口
# ===================================================================

if __name__ == "__main__":
    configure(level="info")

    parser = argparse.ArgumentParser(description=_("cli.description"))
    parser.add_argument(
        "-c", "--clean",
        action="store_true",
        help=_("cli.help.clean")
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help=_("cli.help.output")
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help=_("cli.help.clear_cache")
    )
    parser.add_argument(
        "--git-clean",
        action="store_true",
        help=_("cli.help.git_clean")
    )
    args = parser.parse_args()

    # 解析输出路径：相对路径基于程序所在目录，绝对路径直接使用
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = BASE_DIR / output_path
        output_path = output_path.resolve()
    else:
        output_path = BASE_DIR / "output"

    if args.clean:
        if output_path.exists():
            shutil.rmtree(output_path)
            log("info", _("log.output_cleared", path=output_path))

    # --clear-cache：仅清除缓存，不启动 GUI
    if getattr(args, "clear_cache", False):
        cache_dir = BASE_DIR / "temp"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            log("info", _("log.temp_cleared", path=cache_dir))
        else:
            log("info", "Cache folder does not exist.")
        exit(0)

    # --git-clean：清除 output 和 temp 目录后退出（用于 git 提交前清理）
    if getattr(args, "git_clean", False):
        script_dir = Path(__file__).parent
        for d in ["output", "temp"]:
            p = script_dir / d
            if p.exists():
                shutil.rmtree(p)
                log("info", f"Removed: {p}")
        exit(0)

    # 系统语言自动检测
    detected_lang = _detect_system_language()
    set_lang(detected_lang)
    log("info", f"System language detected: {detected_lang}")

    # 设置控制台标题
    set_console_title()

    app = SpriteToolApp(output_dir=output_path)
    app.run()

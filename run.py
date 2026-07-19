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
import locale
import os
import shutil
import threading
from pathlib import Path
from typing import Optional, Dict, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from src.bundleloader import BundleLoader
from src.compositor import (
    has_component_data,
    extract_sprites,
    extract_character_data,
    SpriteCompositor,
)
from src.tools import log, configure
from src.i18n import _, set_lang, current_lang, LANGUAGE_CODES, LANG_CN, LANG_EN


# ── 系统语言检测 ──────────────────────────────────────────────

def _detect_system_language() -> str:
    """根据系统区域设置自动选择语言（不返回 LANG_MGL）"""
    try:
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang and sys_lang.startswith("zh"):
            return LANG_CN
    except Exception:
        pass
    return LANG_EN


# ===================================================================
# 主应用
# ===================================================================

class SpriteToolApp:
    """魔法少女的魔女审判 - 角色立绘提取工具主窗口"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.root = tk.Tk()
        self.root.title(_("app.title"))
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

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

        # 输出目录（默认基于脚本所在目录，可通过命令行参数 -o 指定）
        self.output_dir = output_dir or (Path(__file__).parent / "output")

        # 临时缓存目录（精灵提取过程中的中间文件，关闭或切换角色时自动清空）
        self.temp_dir = Path(__file__).parent / "temp"

        # 设置 UI
        self._setup_ui()
        self._bind_events()

    # ── UI 构建 ────────────────────────────────────────────────

    def _setup_ui(self):
        # 主布局：左侧导航 + 右侧内容
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== 左侧面板 ==========
        left_frame = ttk.Frame(main_paned, width=280)
        main_paned.add(left_frame, weight=0)

        # 加载按钮
        self.load_btn = ttk.Button(left_frame, text=_("left.load_button"), command=self._on_load_directory)
        self.load_btn.pack(fill=tk.X, pady=(0, 5))

        # 打开输出文件夹按钮
        self.open_output_btn = ttk.Button(left_frame, text=_("left.open_output"), command=self._on_open_output)
        self.open_output_btn.pack(fill=tk.X, pady=(0, 10))

        # 角色列表标题
        self._char_list_title = ttk.Label(left_frame, text=_("left.char_list_title"), font=("Arial", 11, "bold"))
        self._char_list_title.pack(anchor=tk.W, pady=(0, 5))

        # 角色列表 (带滚动条)
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.char_listbox = tk.Listbox(list_frame, font=("Consolas", 10), selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
        self.char_listbox.configure(yscrollcommand=scrollbar.set)
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 进度条（默认隐藏，determinate 模式显示实际进度）
        self.progress_bar = ttk.Progressbar(left_frame, mode="determinate", length=280)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        self.progress_bar.pack_forget()

        # 语言切换
        self.lang_combo = ttk.Combobox(
            left_frame, state="readonly", width=20,
            values=[_(f"lang.{code}") for code in LANGUAGE_CODES]
        )
        try:
            idx = LANGUAGE_CODES.index(self._start_lang)
        except ValueError:
            idx = 0
        self.lang_combo.current(idx)
        self.lang_combo.pack(fill=tk.X, pady=(5, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # 清除缓存按钮
        self.clear_cache_btn = ttk.Button(left_frame, text=_("left.clear_cache"), command=self._on_clear_cache)
        self.clear_cache_btn.pack(fill=tk.X, pady=(5, 0))

        # 状态栏
        self.status_bar = ttk.Label(left_frame, text=_("app.status.ready"), relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

        # ========== 右侧内容面板 ==========
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # 用 Notebook 来切换不同视图
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 欢迎/信息页
        self.info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.info_frame, text=_("info.tab_title"))
        self._show_welcome()

        # 精灵选择页（拼接模式用，包含内嵌预览）
        self.selection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.selection_frame, text=_("tabs.parts"))
        self._setup_selection_tab()

        # 组件结构页（层级信息）
        self.hierarchy_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hierarchy_frame, text=_("tabs.hierarchy"))
        self._setup_hierarchy_tab()

    def _show_welcome(self):
        for w in self.info_frame.winfo_children():
            w.destroy()
        self._info_text = tk.Text(self.info_frame, wrap=tk.WORD, padx=20, pady=20, font=("Arial", 10))
        self._info_text.insert(tk.END, _("info.welcome"))
        self._info_text.insert(tk.END, _("info.usage_title"))
        self._info_text.insert(tk.END, _("info.usage_1"))
        self._info_text.insert(tk.END, _("info.usage_2"))
        self._info_text.insert(tk.END, _("info.usage_3"))
        self._info_text.insert(tk.END, _("info.usage_4"))
        self._info_text.insert(tk.END, _("info.logic_title"))
        self._info_text.insert(tk.END, _("info.logic_no_component"))
        self._info_text.insert(tk.END, _("info.logic_has_component"))
        self._info_text.insert(tk.END, _("info.logic_export"))
        self._info_text.insert(tk.END, _("info.logic_composite"))
        self._info_text.insert(tk.END, _("info.cache_warning"))
        self._info_text.config(state=tk.DISABLED)
        self._info_text.pack(fill=tk.BOTH, expand=True)

    def _setup_selection_tab(self):
        """部件选择界面（左：部件列表，右：内嵌预览）"""
        # ── 控制栏 ──
        ctrl_frame = ttk.Frame(self.selection_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.select_all_btn = ttk.Button(ctrl_frame, text=_("parts.select_all"), command=self._select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.deselect_all_btn = ttk.Button(ctrl_frame, text=_("parts.deselect_all"), command=self._deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=5)

        self.sel_count_label = ttk.Label(ctrl_frame, text=_("parts.selected_count", count=0))
        self.sel_count_label.pack(side=tk.LEFT, padx=(20, 0))

        # 右侧按钮组（三个按钮在同一行）
        self.save_btn = ttk.Button(ctrl_frame, text=_("parts.save_composite"), command=self._on_save)
        self.save_btn.pack(side=tk.RIGHT, padx=2)

        self.clear_preview_btn = ttk.Button(ctrl_frame, text=_("parts.clear_preview"), command=self._clear_preview)
        self.clear_preview_btn.pack(side=tk.RIGHT, padx=2)

        self.composite_btn = ttk.Button(ctrl_frame, text=_("parts.composite_btn"), command=self._on_composite)
        self.composite_btn.pack(side=tk.RIGHT, padx=2)

        self.auto_update_cb = ttk.Checkbutton(
            ctrl_frame, text=_("parts.auto_update"), variable=self.auto_update,
            command=self._on_auto_update_toggle
        )
        self.auto_update_cb.pack(side=tk.RIGHT, padx=(10, 5))

        # ── 主区域：PanedWindow 左中右三栏分割 ──
        paned = ttk.PanedWindow(self.selection_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)

        # ===== 左：部件列表 =====
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=2)

        self.parts_canvas = tk.Canvas(list_frame, highlightthickness=0)
        v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.parts_canvas.yview)
        self.parts_canvas.configure(yscrollcommand=v_scroll.set)

        self.parts_inner = ttk.Frame(self.parts_canvas)
        self.parts_inner.bind("<Configure>", lambda e: self.parts_canvas.configure(
            scrollregion=self.parts_canvas.bbox("all")))

        self.parts_canvas.create_window((0, 0), window=self.parts_inner, anchor="nw", tags="inner")
        self.parts_canvas.grid(row=0, column=0, sticky=tk.NSEW)
        v_scroll.grid(row=0, column=1, sticky=tk.NS)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.parts_canvas.bind("<MouseWheel>", lambda e: self.parts_canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        self.part_vars: List[tk.BooleanVar] = []
        self.part_labels: List[Dict] = []

        # ===== 中：已选精灵列表 =====
        sel_frame = ttk.Frame(paned)
        paned.add(sel_frame, weight=1)

        self.sel_header = ttk.Label(sel_frame, text=_("parts.selected_list_title"), font=("Arial", 10, "bold"))
        self.sel_header.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # 列表区域子容器，用于容纳 listbox + scrollbar
        sel_body = ttk.Frame(sel_frame)
        sel_body.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)
        sel_frame.columnconfigure(0, weight=1)
        sel_frame.rowconfigure(1, weight=1)

        self.sel_listbox = tk.Listbox(sel_body, font=("Consolas", 9), selectmode=tk.SINGLE)
        sel_scrollbar = ttk.Scrollbar(sel_body, orient=tk.VERTICAL, command=self.sel_listbox.yview)
        self.sel_listbox.configure(yscrollcommand=sel_scrollbar.set)
        self.sel_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        sel_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        sel_body.columnconfigure(0, weight=1)
        sel_body.rowconfigure(0, weight=1)

        # ===== 右：内嵌预览 =====
        preview_panel = ttk.Frame(paned)
        paned.add(preview_panel, weight=2)

        self.preview_status = ttk.Label(preview_panel, text=_("parts.no_preview"), anchor=tk.CENTER)
        self.preview_status.pack(fill=tk.X, pady=(0, 5))

        canvas_frame = ttk.Frame(preview_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(canvas_frame, bg="#e0e0e0")
        h_s = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        v_s = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        self.preview_canvas.configure(xscrollcommand=h_s.set, yscrollcommand=v_s.set)

        self.preview_canvas.grid(row=0, column=0, sticky=tk.NSEW)
        h_s.grid(row=1, column=0, sticky=tk.EW)
        v_s.grid(row=0, column=1, sticky=tk.NS)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.preview_image_id: Optional[int] = None

    def _setup_hierarchy_tab(self):
        """组件结构页 — TreeView """
        # 控制栏
        ctrl = ttk.Frame(self.hierarchy_frame)
        ctrl.pack(fill=tk.X, pady=5)
        self._hierarchy_hint = ttk.Label(ctrl, text=_("hierarchy.hint"),
                  font=("Arial", 9, "italic"))
        self._hierarchy_hint.pack(side=tk.LEFT, padx=5)
        self._expand_btn = ttk.Button(ctrl, text=_("hierarchy.expand_all"), command=self._expand_all_nodes)
        self._expand_btn.pack(side=tk.RIGHT, padx=2)
        self._collapse_btn = ttk.Button(ctrl, text=_("hierarchy.collapse_all"), command=self._collapse_all_nodes)
        self._collapse_btn.pack(side=tk.RIGHT, padx=2)

        # TreeView
        tree_frame = ttk.Frame(self.hierarchy_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 使用 show="tree" 只显示树状结构，#0 列显示路径+信息
        self.hierarchy_tree = ttk.Treeview(tree_frame, show="tree", height=12)

        v_s = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.hierarchy_tree.yview)
        self.hierarchy_tree.configure(yscrollcommand=v_s.set)
        self.hierarchy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_s.pack(side=tk.RIGHT, fill=tk.Y)

    def _populate_hierarchy_tree(self, hierarchy: List[Dict]):
        """用 hierarchy 数据填充 TreeView — 注册表风格"""
        for item in self.hierarchy_tree.get_children():
            self.hierarchy_tree.delete(item)

        def add_node(parent_id: str, nodes: List[Dict]):
            for node in nodes:
                pos = node.get("position", {})
                pos_str = f"({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f})"
                order = node.get("sorting_order", 0)

                name = node.get("name", "")
                children = node.get("children", [])

                if node.get("has_sprite"):
                    display = _("hierarchy.item_sprite", name=name, pos=pos_str, order=order)
                elif children:
                    display = _("hierarchy.item_children", name=name, count=len(children))
                else:
                    display = _("hierarchy.item_empty", name=name, pos=pos_str)

                item_id = self.hierarchy_tree.insert(
                    parent_id, tk.END, text=display, open=False
                )
                add_node(item_id, children)

        for i, node in enumerate(hierarchy):
            name = node.get("name", "")
            children = node.get("children", [])
            display = _("hierarchy.level_fmt", level=i + 1, name=name, count=len(children))
            root_id = self.hierarchy_tree.insert("", tk.END, text=display, open=True)
            add_node(root_id, children)

    def _on_tree_double_click(self, event):
        """双击展开/折叠节点"""
        item = self.hierarchy_tree.selection()
        if item:
            item = item[0]
            if self.hierarchy_tree.get_children(item):
                if self.hierarchy_tree.item(item, "open"):
                    self.hierarchy_tree.item(item, open=False)
                else:
                    self.hierarchy_tree.item(item, open=True)

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
        # 窗口标题
        self.root.title(_("app.title"))

        # 左侧面板
        self.load_btn.config(text=_("left.load_button"))
        self.open_output_btn.config(text=_("left.open_output"))
        self._char_list_title.config(text=_("left.char_list_title"))
        self.clear_cache_btn.config(text=_("left.clear_cache"))
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


        # 组件结构页
        self._hierarchy_hint.config(text=_("hierarchy.hint"))
        self._expand_btn.config(text=_("hierarchy.expand_all"))
        self._collapse_btn.config(text=_("hierarchy.collapse_all"))

        # 信息页重建
        if self.bundles:
            self._show_character_list()
        else:
            self._show_welcome()

        # 如果当前有角色数据已加载，刷新层次树中的显示文本
        if self.character_data:
            hierarchy = self.character_data.get("hierarchy", [])
            self._populate_hierarchy_tree(hierarchy)

    def _bind_events(self):
        self.char_listbox.bind("<<ListboxSelect>>", self._on_character_select)

    # ── 目录加载 ───────────────────────────────────────────────

    def _on_open_output(self):
        """打开输出文件夹"""
        output_path = self.output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_path))

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
            self._set_status(_("app.status.loaded", count=result['count']))
            self.notebook.select(0)

            # 切换到信息页并显示列表
            self._show_character_list()
        else:
            msg = "\n".join(result["errors"])
            messagebox.showerror(_("dialog.load_error_title"), msg)
            self._set_status(_("app.status.load_failed"))

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

    def _clear_character_cache(self):
        """清除上一个角色的缓存数据"""
        # 记录上一个角色名以便清理输出目录
        old_name = None
        if self.character_data:
            old_name = self.character_data.get("character_name")

        self.character_data = None
        self.composite_image = None
        self._thumb_refs.clear()
        # 清空部件列表
        for w in self.parts_inner.winfo_children():
            w.destroy()
        self.part_vars.clear()
        self.part_labels.clear()
        # 重置选择计数
        self.sel_count_label.config(text=_("parts.selected_count", count=0))
        # 清空已选精灵列表
        self.sel_listbox.delete(0, tk.END)
        # 清空预览画布
        self.preview_canvas.delete("all")
        self.preview_status.config(text=_("parts.no_preview"))

        # 清空组件结构树
        for item in self.hierarchy_tree.get_children():
            self.hierarchy_tree.delete(item)

    def _on_character_select(self, event):
        sel = self.char_listbox.curselection()
        if not sel:
            return
        name = self.char_listbox.get(sel[0])
        bundle_path = Path(self.bundles[name])

        # 清除上一个角色的缓存
        self._clear_character_cache()

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
                self._set_status(_("app.status.cancelled"))
                return

            self._start_progress(_("app.status.exporting", name=name))
            def export_task():
                def cb(current, total):
                    self.root.after(0, lambda: self._update_progress(current, total))
                output_dir = self.output_dir
                count = len(extract_sprites(bundle_path, output_dir, progress_callback=cb))
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

        result = {"mode": None}  # 用于在回调中传值

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
                count = len(extract_sprites(bundle_path, self.output_dir, progress_callback=cb))
                self.root.after(0, lambda: self._on_export_complete(name, count))
            threading.Thread(target=export_task, daemon=True).start()
        elif mode == "composite":
            self._start_composite_mode(name, bundle_path)

    # ── 拼接模式 ─────────────────────────────────────────────

    def _start_composite_mode(self, name: str, bundle_path: Path):
        # 检查是否有完整缓存
        cached = self._try_load_cached(name)
        if cached:
            self.root.after(0, lambda: self._on_data_ready(name, cached))
            return

        self._start_progress(_("app.status.extracting", name=name))

        def extract_task():
            def cb(current, total):
                self.root.after(0, lambda: self._update_progress(current, total))
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            data = extract_character_data(bundle_path, self.temp_dir, progress_callback=cb)
            self.root.after(0, lambda: self._on_data_ready(name, data))

        threading.Thread(target=extract_task, daemon=True).start()

    def _try_load_cached(self, name: str) -> Optional[Dict]:
        """尝试从 temp 缓存加载角色数据，缓存不完整时返回 None"""
        json_path = self.temp_dir / name / "character_data.json"
        sprites_dir = self.temp_dir / name / "sprites"
        if not json_path.exists() or not sprites_dir.exists():
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 验证所有精灵文件都存在
            for part in data.get("transform_data", []):
                sprite_path = Path(part["sprite_path"])
                if not sprite_path.exists():
                    log("info", f"Cache incomplete, missing: {sprite_path}")
                    return None
            transform_data = data.get("transform_data", [])
            log("info", _("log.cache_loaded", name=name, count=len(transform_data)))
            return data
        except Exception as e:
            log("warning", f"Cache load failed: {e}")
            return None

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
            self._populate_hierarchy_tree(hierarchy)
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
                thumb = self._load_thumbnail(part["sprite_path"], size=(48, 48))
                if thumb:
                    thumb_label = ttk.Label(frame, image=thumb)
                    thumb_label.pack(side=tk.LEFT, padx=(4, 8))
                    self._thumb_refs.append(thumb)
                else:
                    ttk.Label(frame, text=_("parts.no_img"), font=("Consolas", 7),
                              foreground="gray").pack(side=tk.LEFT, padx=(4, 8))

                pos = part["position"]
                info = _("parts.item_info",
                          name=part['name'], x=pos['x'], y=pos['y'],
                          order=part['sorting_order'], size=part['sprite_size'])
                lbl = ttk.Label(frame, text=info, font=("Consolas", 9))
                lbl.pack(side=tk.LEFT, padx=(5, 0))

                self.part_vars.append(var)
                self.part_labels.append({"frame": frame, "part": part, "var": var})

        # 全部创建完毕后保持默认未选中状态
        self.sel_count_label.config(text=_("parts.selected_count", count=0))

    def _load_thumbnail(self, image_path: str, size: tuple = (48, 48)) -> Optional[ImageTk.PhotoImage]:
        """加载精灵图片并生成缩略图"""
        try:
            img = Image.open(image_path).convert("RGBA")
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # 在透明背景上绘制缩略图
            thumb = Image.new("RGBA", size, (240, 240, 240, 255))
            offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
            thumb.paste(img, offset, img)
            return ImageTk.PhotoImage(thumb)
        except Exception:
            return None

    def _update_selected_sprites_list(self):
        """刷新已选精灵列表（显示在右侧 Listbox 中）"""
        self.sel_listbox.delete(0, tk.END)
        for item in self.part_labels:
            if item["var"].get():
                name = item["part"]["name"]
                self.sel_listbox.insert(tk.END, name)

    def _on_part_toggle(self):
        selected = sum(1 for v in self.part_vars if v.get())
        self.sel_count_label.config(text=_("parts.selected_count", count=selected))
        # 刷新右侧已选精灵列表
        self._update_selected_sprites_list()
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
        self._update_selected_sprites_list()
        if self.auto_update.get():
            self._schedule_auto_preview()

    def _deselect_all(self):
        for v in self.part_vars:
            v.set(False)
        self.sel_count_label.config(text=_("parts.selected_count", count=0))
        self._update_selected_sprites_list()
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
        self._show_preview(img)

    def _show_composite_error(self, error_msg: str):
        """显示合成错误"""
        self.preview_status.config(text=_("parts.no_preview"))
        self._set_status(_("app.status.composite_failed"))
        messagebox.showerror(_("dialog.composite_error_title"), _("dialog.composite_error_msg", msg=error_msg))

    def _clear_preview(self):
        """清空预览画布"""
        self.preview_canvas.delete("all")
        self.preview_status.config(text=_("parts.no_preview"))
        self.composite_image = None
        self._set_status(_("app.status.preview_cleared"))

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

        default_name = f"{self.character_data['character_name']}_composite.png"
        save_path = filedialog.asksaveasfilename(
            title=_("save.file_title"),
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[(_("save.png_filter"), "*.png")]
        )
        if not save_path:
            return

        try:
            self.composite_image.save(save_path)
            messagebox.showinfo(_("dialog.save_success_title"), _("dialog.save_success_msg", path=save_path))
            os.startfile(str(Path(save_path).parent))
        except Exception as e:
            messagebox.showerror(_("dialog.save_error_title"), _("dialog.save_error_msg", msg=e))

    # ── 工具 ──────────────────────────────────────────────────

    def _set_status(self, text: str):
        self.status_bar.config(text=text)
        self.root.update_idletasks()

    def _start_progress(self, text: str = "", maximum: int = 100):
        """显示进度条并更新状态文字（determinate 模式）"""
        self._set_status(text or _("app.progress.default"))
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
        self._set_status(text or _("app.status.ready"))
        self.root.update_idletasks()

    def _on_clear_cache(self):
        """手动清除 temp 缓存目录（带确认对话框）"""
        if not self.temp_dir.exists():
            self._set_status(_("app.status.ready"))
            return
        if not messagebox.askyesno(
            _("left.clear_cache_confirm_title"),
            _("left.clear_cache_confirm_msg")
        ):
            return
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        log("info", _("log.temp_cleared", path=self.temp_dir))
        # 还原界面并切换到信息页
        self._clear_character_cache()
        self.notebook.select(0)
        self._set_status(_("app.status.ready"))

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
    args = parser.parse_args()

    # 解析输出路径：相对路径基于脚本所在目录，绝对路径直接使用
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path(__file__).parent / output_path
        output_path = output_path.resolve()
    else:
        output_path = Path(__file__).parent / "output"

    if args.clean:
        if output_path.exists():
            shutil.rmtree(output_path)
            log("info", _("log.output_cleared", path=output_path))

    # --clear-cache：仅清除缓存，不启动 GUI
    if getattr(args, "clear_cache", False):
        cache_dir = Path(__file__).parent / "temp"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            log("info", _("log.temp_cleared", path=cache_dir))
        else:
            log("info", "Cache folder does not exist.")
        exit(0)

    # 系统语言自动检测
    detected_lang = _detect_system_language()
    set_lang(detected_lang)
    log("info", f"System language detected: {detected_lang}")

    app = SpriteToolApp(output_dir=output_path)
    app.run()

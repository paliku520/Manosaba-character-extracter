"""
UI 构建模块 — 负责所有 GUI 控件的创建与布局

所有函数接收 app（SpriteToolApp 实例）作为第一个参数，
通过 app.xxx 访问和设置界面组件。
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Dict

from PIL import Image, ImageTk

from src.i18n import _, current_lang, LANGUAGE_CODES


def find_app_icon():
    """查找应用图标文件路径（兼容 PyInstaller 冻结环境），找不到返回 None"""
    from run import MEI_DIR, BASE_DIR
    icon_candidates = [
        MEI_DIR / "icon.ico",
        BASE_DIR / "scripts" / "icon.ico",
        Path(__file__).parent.parent / "scripts" / "icon.ico",
    ]
    for p in icon_candidates:
        if p.exists():
            return p
    return None


def set_window_icon(app):
    """设置 tkinter 主窗口图标"""
    icon = find_app_icon()
    if icon is None:
        return
    try:
        app.root.iconbitmap(str(icon))
    except Exception:
        pass


def set_toplevel_icon(window):
    """设置子窗口（Toplevel）图标"""
    icon = find_app_icon()
    if icon is None:
        return
    try:
        window.iconbitmap(str(icon))
    except Exception:
        pass


def build_main_ui(app):
    """构建主界面布局"""
    # 主布局：左侧导航 + 右侧内容
    main_paned = ttk.PanedWindow(app.root, orient=tk.HORIZONTAL)
    main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    app._main_paned = main_paned

    # ========== 左侧面板 ==========
    left_frame = ttk.Frame(main_paned, width=185)
    main_paned.add(left_frame, weight=0)

    # 加载按钮
    app.load_btn = ttk.Button(left_frame, text=_("left.load_button"), command=app._on_load_directory)
    app.load_btn.pack(fill=tk.X, pady=(0, 5))

    # 打开输出文件夹按钮
    app.open_output_btn = ttk.Button(left_frame, text=_("left.open_output"), command=app._on_open_output)
    app.open_output_btn.pack(fill=tk.X, pady=(0, 5))

    # 设置按钮
    app.settings_btn = ttk.Button(left_frame, text=_("left.settings"), command=app._open_settings)
    app.settings_btn.pack(fill=tk.X, pady=(0, 10))

    # 角色列表标题
    app._char_list_title = ttk.Label(left_frame, text=_("left.char_list_title"), font=("Arial", 11, "bold"))
    app._char_list_title.pack(anchor=tk.W, pady=(0, 5))

    # 角色列表 (带滚动条)
    list_frame = ttk.Frame(left_frame)
    list_frame.pack(fill=tk.BOTH, expand=True)

    app.char_listbox = tk.Listbox(list_frame, font=("Consolas", 10), selectmode=tk.SINGLE)
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=app.char_listbox.yview)
    app.char_listbox.configure(yscrollcommand=scrollbar.set)
    app.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 进度条（默认隐藏）
    app.progress_bar = ttk.Progressbar(left_frame, mode="determinate", length=185)
    app.progress_bar.pack(fill=tk.X, pady=(5, 0))
    app.progress_bar.pack_forget()

    # 清除缓存按钮
    app.clear_cache_btn = ttk.Button(left_frame, text=_("left.clear_cache"), command=app._on_clear_cache)
    app.clear_cache_btn.pack(fill=tk.X, pady=(5, 0))

    # 状态栏
    app.status_bar = ttk.Label(left_frame, text=_("app.status.ready"), relief=tk.SUNKEN, anchor=tk.W)
    app.status_bar.pack(fill=tk.X, pady=(10, 0))

    # ========== 右侧内容面板 ==========
    right_frame = ttk.Frame(main_paned)
    main_paned.add(right_frame, weight=1)

    # Notebook
    app.notebook = ttk.Notebook(right_frame)
    app.notebook.pack(fill=tk.BOTH, expand=True)

    # 欢迎/信息页
    app.info_frame = ttk.Frame(app.notebook)
    app.notebook.add(app.info_frame, text=_("info.tab_title"))
    build_welcome(app)

    # 精灵选择页
    app.selection_frame = ttk.Frame(app.notebook)
    app.notebook.add(app.selection_frame, text=_("tabs.parts"))
    build_selection_tab(app)

    # 组件结构页
    app.hierarchy_frame = ttk.Frame(app.notebook)
    app.notebook.add(app.hierarchy_frame, text=_("tabs.hierarchy"))
    build_hierarchy_tab(app)


def build_welcome(app):
    """构建欢迎/信息页"""
    for w in app.info_frame.winfo_children():
        w.destroy()
    app._info_text = tk.Text(app.info_frame, wrap=tk.WORD, padx=20, pady=20, font=("Arial", 10))
    app._info_text.insert(tk.END, _("info.welcome"))
    app._info_text.insert(tk.END, _("info.usage_title"))
    app._info_text.insert(tk.END, _("info.usage_1"))
    app._info_text.insert(tk.END, _("info.usage_2"))
    app._info_text.insert(tk.END, _("info.usage_3"))
    app._info_text.insert(tk.END, _("info.usage_4"))
    app._info_text.insert(tk.END, _("info.logic_title"))
    app._info_text.insert(tk.END, _("info.logic_no_component"))
    app._info_text.insert(tk.END, _("info.logic_has_component"))
    app._info_text.insert(tk.END, _("info.logic_export"))
    app._info_text.insert(tk.END, _("info.logic_composite"))
    app._info_text.insert(tk.END, _("info.cache_warning"))
    app._info_text.config(state=tk.DISABLED)
    app._info_text.pack(fill=tk.BOTH, expand=True)


def build_selection_tab(app):
    """构建部件选择页"""
    # ── 控制栏 ──
    ctrl_frame = ttk.Frame(app.selection_frame)
    ctrl_frame.pack(fill=tk.X, pady=5)

    app.select_all_btn = ttk.Button(ctrl_frame, text=_("parts.select_all"), command=app._select_all)
    app.select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

    app.deselect_all_btn = ttk.Button(ctrl_frame, text=_("parts.deselect_all"), command=app._deselect_all)
    app.deselect_all_btn.pack(side=tk.LEFT, padx=5)

    app.sel_count_label = ttk.Label(ctrl_frame, text=_("parts.selected_count", count=0))
    app.sel_count_label.pack(side=tk.LEFT, padx=(20, 0))

    app.save_btn = ttk.Button(ctrl_frame, text=_("parts.save_composite"), command=app._on_save)
    app.save_btn.pack(side=tk.RIGHT, padx=2)

    app.clear_preview_btn = ttk.Button(ctrl_frame, text=_("parts.clear_preview"), command=app._clear_preview)
    app.clear_preview_btn.pack(side=tk.RIGHT, padx=2)

    app.composite_btn = ttk.Button(ctrl_frame, text=_("parts.composite_btn"), command=app._on_composite)
    app.composite_btn.pack(side=tk.RIGHT, padx=2)

    app.auto_update_cb = ttk.Checkbutton(
        ctrl_frame, text=_("parts.auto_update"), variable=app.auto_update,
        command=app._on_auto_update_toggle
    )
    app.auto_update_cb.pack(side=tk.RIGHT, padx=(10, 5))

    # ── 主区域 ──
    paned = ttk.PanedWindow(app.selection_frame, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True, pady=5)

    app._json_hint = ttk.Label(app.selection_frame, text=_("parts.json_hint"),
                                 font=("Consolas", 8), foreground="gray")
    app._json_hint.pack(fill=tk.X, padx=5, pady=(0, 2), before=paned)

    # 左：部件列表
    list_frame = ttk.Frame(paned)
    paned.add(list_frame, weight=2)

    app.parts_canvas = tk.Canvas(list_frame, highlightthickness=0)
    v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=app.parts_canvas.yview)
    h_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=app.parts_canvas.xview)
    app.parts_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    app.parts_inner = ttk.Frame(app.parts_canvas)
    app.parts_inner.bind("<Configure>", lambda e: app.parts_canvas.configure(
        scrollregion=app.parts_canvas.bbox("all")))

    app.parts_canvas.create_window((0, 0), window=app.parts_inner, anchor="nw", tags="inner")
    app.parts_canvas.grid(row=0, column=0, sticky=tk.NSEW)
    v_scroll.grid(row=0, column=1, sticky=tk.NS)
    h_scroll.grid(row=1, column=0, sticky=tk.EW)
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)

    app.parts_canvas.bind("<MouseWheel>", lambda e: app.parts_canvas.yview_scroll(
        int(-1 * (e.delta / 120)), "units"))

    app.part_vars = []  # List[tk.BooleanVar]
    app.part_labels = []  # List[Dict]

    # 中：已选精灵列表
    sel_frame = ttk.Frame(paned)
    paned.add(sel_frame, weight=1)

    app.sel_header = ttk.Label(sel_frame, text=_("parts.selected_list_title"), font=("Arial", 10, "bold"))
    app.sel_header.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

    sel_body = ttk.Frame(sel_frame)
    sel_body.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)
    sel_frame.columnconfigure(0, weight=1)
    sel_frame.rowconfigure(1, weight=1)

    app.sel_listbox = tk.Listbox(sel_body, font=("Consolas", 9), selectmode=tk.SINGLE)
    sel_scrollbar = ttk.Scrollbar(sel_body, orient=tk.VERTICAL, command=app.sel_listbox.yview)
    app.sel_listbox.configure(yscrollcommand=sel_scrollbar.set)
    app.sel_listbox.grid(row=0, column=0, sticky=tk.NSEW)
    sel_scrollbar.grid(row=0, column=1, sticky=tk.NS)
    sel_body.columnconfigure(0, weight=1)
    sel_body.rowconfigure(0, weight=1)

    # 右：内嵌预览
    preview_panel = ttk.Frame(paned)
    paned.add(preview_panel, weight=2)

    app.preview_status = ttk.Label(preview_panel, text=_("parts.no_preview"), anchor=tk.CENTER)
    app.preview_status.pack(fill=tk.X, pady=(0, 5))

    canvas_frame = ttk.Frame(preview_panel)
    canvas_frame.pack(fill=tk.BOTH, expand=True)

    app.preview_canvas = tk.Canvas(canvas_frame, bg="#e0e0e0")
    h_s = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=app.preview_canvas.xview)
    v_s = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=app.preview_canvas.yview)
    app.preview_canvas.configure(xscrollcommand=h_s.set, yscrollcommand=v_s.set)

    app.preview_canvas.grid(row=0, column=0, sticky=tk.NSEW)
    h_s.grid(row=1, column=0, sticky=tk.EW)
    v_s.grid(row=0, column=1, sticky=tk.NS)
    canvas_frame.columnconfigure(0, weight=1)
    canvas_frame.rowconfigure(0, weight=1)

    app.preview_image_id = None  # Optional[int]


def build_hierarchy_tab(app):
    """构建组件结构页"""
    ctrl = ttk.Frame(app.hierarchy_frame)
    ctrl.pack(fill=tk.X, pady=5)
    app._hierarchy_hint = ttk.Label(ctrl, text=_("hierarchy.hint"),
              font=("Arial", 9, "italic"))
    app._hierarchy_hint.pack(side=tk.LEFT, padx=5)
    app._expand_btn = ttk.Button(ctrl, text=_("hierarchy.expand_all"), command=app._expand_all_nodes)
    app._expand_btn.pack(side=tk.RIGHT, padx=2)
    app._collapse_btn = ttk.Button(ctrl, text=_("hierarchy.collapse_all"), command=app._collapse_all_nodes)
    app._collapse_btn.pack(side=tk.RIGHT, padx=2)

    tree_frame = ttk.Frame(app.hierarchy_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    app.hierarchy_tree = ttk.Treeview(tree_frame, show="tree", height=12)
    v_s = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=app.hierarchy_tree.yview)
    app.hierarchy_tree.configure(yscrollcommand=v_s.set)
    app.hierarchy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    v_s.pack(side=tk.RIGHT, fill=tk.Y)


def build_settings_dialog(app):
    """构建设置子窗口（语言 / 输出目录 / 清理 / 检查更新）"""
    dialog = tk.Toplevel(app.root)
    dialog.title(_("settings.title"))
    dialog.geometry("560x440")
    dialog.resizable(False, False)
    dialog.transient(app.root)
    dialog.grab_set()
    set_toplevel_icon(dialog)

    # 居中
    dialog.update_idletasks()
    x = app.root.winfo_x() + (app.root.winfo_width() - 560) // 2
    y = app.root.winfo_y() + (app.root.winfo_height() - 440) // 2
    dialog.geometry(f"+{x}+{y}")

    app._settings_dialog = dialog

    # ── 语言 ──
    app._settings_lang_label = ttk.Label(dialog, text=_("lang.label"), font=("Arial", 10, "bold"))
    app._settings_lang_label.pack(anchor=tk.W, padx=20, pady=(20, 5))
    lang_frame = ttk.Frame(dialog)
    lang_frame.pack(fill=tk.X, padx=20)
    app._settings_lang_combo = ttk.Combobox(
        lang_frame, state="readonly", width=20,
        values=[_(f"lang.{code}") for code in LANGUAGE_CODES]
    )
    try:
        idx = LANGUAGE_CODES.index(app._start_lang)
    except ValueError:
        idx = 0
    app._settings_lang_combo.current(idx)
    app._settings_lang_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
    app._settings_lang_combo.bind("<<ComboboxSelected>>", app._on_language_change)

    # ── 输出目录 ──
    app._settings_output_label = ttk.Label(dialog, text=_("settings.output_dir_label"), font=("Arial", 10, "bold"))
    app._settings_output_label.pack(anchor=tk.W, padx=20, pady=(15, 5))
    dir_frame = ttk.Frame(dialog)
    dir_frame.pack(fill=tk.X, padx=20)

    app._settings_output_var = tk.StringVar(value=str(app.output_dir))
    app._settings_output_entry = ttk.Entry(dir_frame, textvariable=app._settings_output_var)
    app._settings_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    app._settings_browse_btn = ttk.Button(dir_frame, text=_("settings.browse"), command=app._on_settings_browse)
    app._settings_browse_btn.pack(side=tk.LEFT, padx=(5, 0))
    app._settings_restore_btn = ttk.Button(dir_frame, text=_("settings.restore_default"), command=app._on_settings_restore_default)
    app._settings_restore_btn.pack(side=tk.LEFT, padx=(5, 0))

    # ── 清理 ──
    ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=(15, 10))
    app._settings_cleanup_label = ttk.Label(dialog, text=_("settings.cleanup_label"), font=("Arial", 10, "bold"))
    app._settings_cleanup_label.pack(anchor=tk.W, padx=20, pady=(0, 5))

    clean_frame = ttk.Frame(dialog)
    clean_frame.pack(fill=tk.X, padx=20)
    app._settings_clear_cache_btn = ttk.Button(clean_frame, text=_("settings.clear_cache_btn"), command=app._on_settings_clear_cache)
    app._settings_clear_cache_btn.pack(side=tk.LEFT)
    app._settings_clear_output_btn = ttk.Button(clean_frame, text=_("settings.clear_output_btn"), command=app._on_settings_clear_output)
    app._settings_clear_output_btn.pack(side=tk.LEFT, padx=(10, 0))

    # ── 检查更新 ──
    ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=(15, 10))
    app._settings_update_btn = ttk.Button(dialog, text=_("left.check_update"), command=app._on_check_update)
    app._settings_update_btn.pack(anchor=tk.W, padx=20)

    # ── 底部按钮 ──
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
    app._settings_cancel_btn = ttk.Button(btn_frame, text=_("settings.cancel"), command=dialog.destroy)
    app._settings_cancel_btn.pack(side=tk.RIGHT)
    app._settings_save_btn = ttk.Button(btn_frame, text=_("settings.save"), command=app._on_settings_save)
    app._settings_save_btn.pack(side=tk.RIGHT, padx=(0, 10))

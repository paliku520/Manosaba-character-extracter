"""
魔法少女的魔女审判 - 角色立绘提取与拼接工具

工作流程:
    1. 选择游戏目录 → 加载所有角色 bundle
    2. 点击角色 → 自动检测是否有组件数据
       - 无组件 → 直接导出所有精灵
       - 有组件 → 询问用户操作模式
    3. 拼接模式 → 选择部件 + 预览 + 保存合成图
"""

import os
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


# ===================================================================
# 主应用
# ===================================================================

class SpriteToolApp:
    """魔法少女的魔女审判 - 角色立绘提取工具主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("魔法少女的魔女审判 - 角色立绘提取工具")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

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

        # 输出目录（后续封装 .exe 时改为 sys.executable 同级路径）
        self.output_dir = Path("./output")

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
        self.load_btn = ttk.Button(left_frame, text="加载游戏目录", command=self._on_load_directory)
        self.load_btn.pack(fill=tk.X, pady=(0, 5))

        # 打开输出文件夹按钮
        self.open_output_btn = ttk.Button(left_frame, text="打开输出文件夹", command=self._on_open_output)
        self.open_output_btn.pack(fill=tk.X, pady=(0, 10))

        # 角色列表标题
        ttk.Label(left_frame, text="角色列表", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # 角色列表 (带滚动条)
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.char_listbox = tk.Listbox(list_frame, font=("Consolas", 10), selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
        self.char_listbox.configure(yscrollcommand=scrollbar.set)
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        self.status_bar = ttk.Label(left_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

        # ========== 右侧内容面板 ==========
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # 用 Notebook 来切换不同视图
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 欢迎/信息页
        self.info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.info_frame, text="信息")
        self._show_welcome()

        # 精灵选择页（拼接模式用，包含内嵌预览）
        self.selection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.selection_frame, text="部件选择")
        self._setup_selection_tab()

        # 组件结构页（层级信息）
        self.hierarchy_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hierarchy_frame, text="组件结构")
        self._setup_hierarchy_tab()

    def _show_welcome(self):
        for w in self.info_frame.winfo_children():
            w.destroy()
        text = tk.Text(self.info_frame, wrap=tk.WORD, padx=20, pady=20, font=("Arial", 10))
        text.insert(tk.END, "魔法少女的魔女审判 - 角色立绘提取工具\n\n")
        text.insert(tk.END, "使用说明:\n")
        text.insert(tk.END, "1. 点击左侧「加载游戏目录」按钮，选择游戏安装目录\n")
        text.insert(tk.END, "2. 程序自动扫描 characters 目录并加载所有角色\n")
        text.insert(tk.END, "3. 在角色列表中点击要处理的角色\n")
        text.insert(tk.END, "4. 程序将自动检测 bundle 类型并执行相应操作\n\n")
        text.insert(tk.END, "处理逻辑:\n")
        text.insert(tk.END, "• 无组件数据的 bundle → 直接导出所有精灵\n")
        text.insert(tk.END, "• 有组件数据的 bundle → 询问处理方式:\n")
        text.insert(tk.END, "   - 「直接导出所有精灵」导出原始精灵图片\n")
        text.insert(tk.END, "   - 「拼接角色图像」按位置和深度合成完整立绘\n\n")
        text.insert(tk.END, "⚠ 注意: output/<角色名>/sprites/ 目录为自动生成的缓存\n")
        text.insert(tk.END, "  切换角色或关闭程序时会自动清空，请勿存放个人文件！\n")
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)

    def _setup_selection_tab(self):
        """部件选择界面（左：部件列表，右：内嵌预览）"""
        # ── 控制栏 ──
        ctrl_frame = ttk.Frame(self.selection_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.select_all_btn = ttk.Button(ctrl_frame, text="全选", command=self._select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.deselect_all_btn = ttk.Button(ctrl_frame, text="取消全选", command=self._deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=5)

        self.sel_count_label = ttk.Label(ctrl_frame, text="已选择: 0 个部件")
        self.sel_count_label.pack(side=tk.LEFT, padx=(20, 0))

        # 右侧按钮组（三个按钮在同一行）
        self.save_btn = ttk.Button(ctrl_frame, text="保存合成图像", command=self._on_save)
        self.save_btn.pack(side=tk.RIGHT, padx=2)

        self.clear_preview_btn = ttk.Button(ctrl_frame, text="清空预览", command=self._clear_preview)
        self.clear_preview_btn.pack(side=tk.RIGHT, padx=2)

        self.composite_btn = ttk.Button(ctrl_frame, text="生成合成图像", command=self._on_composite)
        self.composite_btn.pack(side=tk.RIGHT, padx=2)

        self.auto_update_cb = ttk.Checkbutton(
            ctrl_frame, text="自动更新", variable=self.auto_update,
            command=self._on_auto_update_toggle
        )
        self.auto_update_cb.pack(side=tk.RIGHT, padx=(10, 5))

        # ── 主区域：PanedWindow 左右分割 ──
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
        self.parts_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.parts_canvas.bind("<MouseWheel>", lambda e: self.parts_canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        self.part_vars: List[tk.BooleanVar] = []
        self.part_labels: List[Dict] = []

        # ===== 右：内嵌预览 =====
        preview_panel = ttk.Frame(paned)
        paned.add(preview_panel, weight=1)

        self.preview_status = ttk.Label(preview_panel, text="未生成预览", anchor=tk.CENTER)
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
        ttk.Label(ctrl, text="组件层级结构（点击 + 展开/折叠）",
                  font=("Arial", 9, "italic")).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="全部展开", command=self._expand_all_nodes).pack(side=tk.RIGHT, padx=2)
        ttk.Button(ctrl, text="全部折叠", command=self._collapse_all_nodes).pack(side=tk.RIGHT, padx=2)

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

                # 注册表风格：键名 (默认值)
                if node.get("has_sprite"):
                    display = f"{name}  —  [位置: {pos_str}]  [排序: {order}]"
                elif children:
                    display = f"{name}  —  [{len(children)} 个子项]"
                else:
                    display = f"{name}  —  (位置: {pos_str})"

                item_id = self.hierarchy_tree.insert(
                    parent_id, tk.END, text=display, open=False
                )
                add_node(item_id, children)

        for i, node in enumerate(hierarchy):
            name = node.get("name", "")
            children = node.get("children", [])
            display = f"层级 {i+1}:  {name}  —  [{len(children)} 个子项]"
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

    def _bind_events(self):
        self.char_listbox.bind("<<ListboxSelect>>", self._on_character_select)

    # ── 目录加载 ───────────────────────────────────────────────

    def _on_open_output(self):
        """打开输出文件夹"""
        output_path = self.output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_path))

    def _on_load_directory(self):
        dir_path = self.loader.select_directory("选择游戏根目录或 characters 目录")
        if not dir_path:
            return

        self._set_status("加载中...")
        self.load_btn.config(state=tk.DISABLED)
        self.char_listbox.delete(0, tk.END)

        def load_task():
            result = self.loader.load_from_directory(dir_path)
            self.root.after(0, lambda: self._on_load_complete(result))

        threading.Thread(target=load_task, daemon=True).start()

    def _on_load_complete(self, result: Dict):
        self.load_btn.config(state=tk.NORMAL)
        if result["success"]:
            self.bundles = result["bundles"]
            self.char_listbox.delete(0, tk.END)
            for name in sorted(self.bundles.keys()):
                self.char_listbox.insert(tk.END, name)
            self._set_status(f"已加载 {result['count']} 个角色")
            self.notebook.select(0)

            # 切换到信息页并显示列表
            self._show_character_list()
        else:
            msg = "\n".join(result["errors"])
            messagebox.showerror("加载失败", msg)
            self._set_status("加载失败")

    def _show_character_list(self):
        """在信息页显示已加载的角色列表"""
        for w in self.info_frame.winfo_children():
            w.destroy()

        text = tk.Text(self.info_frame, wrap=tk.WORD, padx=20, pady=20, font=("Consolas", 10))
        text.insert(tk.END, f"已加载 {len(self.bundles)} 个角色:\n\n")
        for i, name in enumerate(sorted(self.bundles.keys()), 1):
            text.insert(tk.END, f"  {i:2d}. {name}\n")
        text.insert(tk.END, "\n请在左侧列表中点击角色名称开始处理。")
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
        self.sel_count_label.config(text="已选择: 0 个部件")
        # 清空预览画布
        self.preview_canvas.delete("all")
        self.preview_status.config(text="未生成预览")

        # 清空组件结构树
        for item in self.hierarchy_tree.get_children():
            self.hierarchy_tree.delete(item)

        # 清理上一个角色的精灵缓存（只删 sprites 子目录，保留 character_data.json）
        if old_name:
            sprites_dir = self.output_dir / old_name / "sprites"
            if sprites_dir.exists():
                import shutil
                shutil.rmtree(sprites_dir, ignore_errors=True)
                log("info", f"已清理精灵缓存: {sprites_dir}")

    def _on_character_select(self, event):
        sel = self.char_listbox.curselection()
        if not sel:
            return
        name = self.char_listbox.get(sel[0])
        bundle_path = Path(self.bundles[name])

        # 清除上一个角色的缓存
        self._clear_character_cache()

        self._set_status(f"分析中: {name} ...")
        self.notebook.select(0)

        def analyze_task():
            try:
                has_components = has_component_data(bundle_path)
                self.root.after(0, lambda: self._on_analyze_complete(name, bundle_path, has_components))
            except Exception as e:
                log("error", f"分析 bundle 失败 {name}: {e}")
                self.root.after(0, lambda: messagebox.showerror("分析失败",
                    f"分析角色「{name}」时出错:\n{e}"))
                self.root.after(0, lambda: self._set_status("分析失败"))

        threading.Thread(target=analyze_task, daemon=True).start()

    def _on_analyze_complete(self, name: str, bundle_path: Path, has_components: bool):
        self._set_status(f"已选择: {name}")

        if not has_components:
            # ── 无组件 → 弹窗确认后导出 ──
            log("info", f"{name}: 无组件数据，直接导出精灵")
            if not messagebox.askyesno(
                "确认导出",
                f"角色「{name}」的 bundle 不包含组件数据。\n\n"
                "将直接导出所有精灵文件到 output 目录。\n\n是否继续？"
            ):
                self._set_status("已取消")
                return

            self._set_status(f"正在导出 {name} 的精灵...")
            def export_task():
                output_dir = Path("./output")
                count = len(extract_sprites(bundle_path, output_dir))
                self.root.after(0, lambda: self._on_export_complete(name, count))
            threading.Thread(target=export_task, daemon=True).start()
        else:
            # ── 有组件 → 询问模式 ──
            log("info", f"{name}: 检测到组件数据")
            self._ask_mode_dialog(name, bundle_path)

    def _on_export_complete(self, name: str, count: int):
        self._set_status(f"完成: {name} — 导出 {count} 个精灵")
        output_path = self.output_dir / name
        messagebox.showinfo("导出完成",
                           f"角色「{name}」的 {count} 个精灵已导出到:\n{output_path}")

        # 打开输出目录
        os.startfile(str(output_path))

    # ── 模式选择对话框 ────────────────────────────────────────

    def _ask_mode_dialog(self, name: str, bundle_path: Path):
        """弹出对话框让用户选择处理方式"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"处理方式 - {name}")
        dialog.geometry("480x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=f"角色: {name}", font=("Arial", 12, "bold")).pack(pady=(20, 5))
        ttk.Label(dialog, text="该 bundle 包含组件数据，请选择处理方式:",
                  wraplength=420).pack(pady=(0, 15))

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(expand=True)

        result = {"mode": None}  # 用于在回调中传值

        def choose_mode(mode: str):
            result["mode"] = mode
            dialog.destroy()

        ttk.Button(btn_frame, text="直接导出所有精灵文件",
                   command=lambda: choose_mode("export"),
                   width=30).pack(pady=8)
        ttk.Label(btn_frame, text="将所有精灵图片保存到文件夹，不做任何拼接处理",
                  font=("Arial", 9), foreground="gray").pack()

        ttk.Button(btn_frame, text="拼接角色图像",
                   command=lambda: choose_mode("composite"),
                   width=30).pack(pady=(20, 8))
        ttk.Label(btn_frame, text="按组件的位置和深度信息合成完整立绘",
                  font=("Arial", 9), foreground="gray").pack()

        # 等待对话框关闭
        self.root.wait_window(dialog)

        mode = result["mode"]
        if mode == "export":
            self._set_status(f"正在导出 {name} 的精灵...")
            def export_task():
                count = len(extract_sprites(bundle_path, self.output_dir))
                self.root.after(0, lambda: self._on_export_complete(name, count))
            threading.Thread(target=export_task, daemon=True).start()
        elif mode == "composite":
            self._start_composite_mode(name, bundle_path)

    # ── 拼接模式 ─────────────────────────────────────────────

    def _start_composite_mode(self, name: str, bundle_path: Path):
        self._set_status(f"正在提取 {name} 的角色数据...")

        def extract_task():
            data = extract_character_data(bundle_path, self.output_dir)
            self.root.after(0, lambda: self._on_data_ready(name, data))

        threading.Thread(target=extract_task, daemon=True).start()

    def _on_data_ready(self, name: str, data: Dict):
        """角色数据提取完成后，填充部件列表（全部默认选中），等待用户手动合成"""
        try:
            self.character_data = data
            transform_data = data.get("transform_data", [])
            self._set_status(f"已就绪: {name} — {len(transform_data)} 个部件")

            if not transform_data:
                messagebox.showwarning("警告", f"角色「{name}」未提取到有效的部件数据")
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

            log("info", f"已加载 {len(transform_data)} 个部件，请勾选要合成的部件后点击「生成合成图像」")

            # 填充组件结构树
            hierarchy = data.get("hierarchy", [])
            self._populate_hierarchy_tree(hierarchy)
        except Exception as e:
            log("error", f"处理角色数据失败: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"处理角色数据时出错:\n{e}")

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
            header = ttk.Label(self.parts_inner, text=f"【{cat}】({len(parts)})",
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
                    ttk.Label(frame, text="[NoImg]", font=("Consolas", 7),
                              foreground="gray").pack(side=tk.LEFT, padx=(4, 8))

                pos = part["position"]
                info = (f"{part['name']:28s}  "
                        f"位置:({pos['x']:6.1f}, {pos['y']:6.1f})  "
                        f"排序:{part['sorting_order']:3d}  "
                        f"大小:{part['sprite_size']}")
                lbl = ttk.Label(frame, text=info, font=("Consolas", 9))
                lbl.pack(side=tk.LEFT, padx=(5, 0))

                self.part_vars.append(var)
                self.part_labels.append({"frame": frame, "part": part, "var": var})

        # 全部创建完毕后保持默认未选中状态
        self.sel_count_label.config(text="已选择: 0 个部件")

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

    def _on_part_toggle(self):
        selected = sum(1 for v in self.part_vars if v.get())
        self.sel_count_label.config(text=f"已选择: {selected} 个部件")
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
        self.sel_count_label.config(text=f"已选择: {len(self.part_vars)} 个部件")
        if self.auto_update.get():
            self._schedule_auto_preview()

    def _deselect_all(self):
        for v in self.part_vars:
            v.set(False)
        self.sel_count_label.config(text="已选择: 0 个部件")
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
            log("warning", "没有选中任何部件，跳过合成")
            if not self.auto_update.get():
                messagebox.showinfo("提示", "请至少选择一个部件")
            return

        log("info", f"开始合成: {len(selected)}/{len(transform_data)} 个部件")

        self.preview_status.config(text="正在生成合成图像...")
        self._set_status("正在合成图像...")

        def composite_task():
            try:
                img = self.compositor.composite(transform_data, selected_names=selected)
                self.root.after(0, lambda: self._on_composite_done(img))
            except Exception as e:
                log("error", f"合成失败: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self._show_composite_error(str(e)))

        threading.Thread(target=composite_task, daemon=True).start()

    def _on_composite_done(self, img: Optional[Image.Image]):
        if img is None:
            self.preview_status.config(text="合成失败")
            return

        self.composite_image = img
        self.preview_status.config(text=f"合成完成 ({img.size[0]}x{img.size[1]})")
        self._set_status("合成完成")

        # 在同一页面显示预览（无需切换标签）
        self.root.update_idletasks()
        self._show_preview(img)

    def _show_composite_error(self, error_msg: str):
        """显示合成错误"""
        self.preview_status.config(text="合成出错")
        self._set_status("合成出错")
        messagebox.showerror("合成错误", f"图像合成失败:\n{error_msg}")

    def _clear_preview(self):
        """清空预览画布"""
        self.preview_canvas.delete("all")
        self.preview_status.config(text="未生成预览")
        self.composite_image = None
        self._set_status("预览已清除")

    def _show_preview(self, img: Image.Image):
        """在画布上显示预览图"""
        # 安全检查：图像尺寸必须有效
        if img.width < 1 or img.height < 1:
            log("error", f"预览图像尺寸无效: {img.size}")
            self.preview_status.config(text="预览失败: 图像尺寸无效")
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
            canvas.create_text(cw // 2, 20, text=f"预览已缩放 ({scale:.0%})，保存的为原始大小",
                               fill="red", font=("Arial", 10))

    def _on_save(self):
        if self.composite_image is None:
            messagebox.showwarning("警告", "请先生成合成图像")
            return

        if not self.character_data:
            return

        default_name = f"{self.character_data['character_name']}_composite.png"
        save_path = filedialog.asksaveasfilename(
            title="保存合成图像",
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png")]
        )
        if not save_path:
            return

        try:
            self.composite_image.save(save_path)
            messagebox.showinfo("成功", f"图像已保存:\n{save_path}")
            os.startfile(str(Path(save_path).parent))
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    # ── 工具 ──────────────────────────────────────────────────

    def _set_status(self, text: str):
        self.status_bar.config(text=text)
        self.root.update_idletasks()

    def _cleanup_sprites_cache(self):
        """关闭时自动清理所有角色的精灵缓存（sprites 子目录）"""
        if not self.output_dir.exists():
            return
        cleaned = 0
        for char_dir in self.output_dir.iterdir():
            if char_dir.is_dir():
                sprites_dir = char_dir / "sprites"
                if sprites_dir.exists():
                    import shutil
                    shutil.rmtree(sprites_dir, ignore_errors=True)
                    cleaned += 1
        if cleaned > 0:
            log("info", f"已清理 {cleaned} 个角色的精灵缓存")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        """窗口关闭时清理缓存后退出"""
        self._cleanup_sprites_cache()
        self.root.destroy()


# ===================================================================
# 入口
# ===================================================================

if __name__ == "__main__":
    configure(level="info")
    app = SpriteToolApp()
    app.run()

"""
UI 工具模块 — 进度条、状态栏、预览等复用逻辑
"""

import tkinter as tk
from pathlib import Path
from typing import Optional, List, Dict

from PIL import Image, ImageTk

from typing import List, Dict

from src.i18n import _


# ── 进度条 / 状态 ──────────────────────────────────────────

def set_status(app, text: str):
    """更新状态栏文字"""
    app.status_bar.config(text=text)
    app.root.update_idletasks()


def start_progress(app, text: str = "", maximum: int = 100):
    """显示进度条并更新状态文字"""
    set_status(app, text or _("app.progress.default"))
    app.progress_bar["value"] = 0
    app.progress_bar["maximum"] = maximum
    app.progress_bar.pack(fill=tk.X, pady=(5, 0), before=app.status_bar)
    app.root.update_idletasks()


def update_progress(app, current: int, total: int):
    """更新进度条当前值"""
    app.progress_bar["maximum"] = total
    app.progress_bar["value"] = current
    app.root.update_idletasks()


def stop_progress(app, text: str = ""):
    """停止并隐藏进度条，恢复状态文字"""
    app.progress_bar["value"] = 0
    app.progress_bar.pack_forget()
    set_status(app, text or _("app.status.ready"))
    app.root.update_idletasks()


# ── 预览 ──────────────────────────────────────────────────

def clear_preview(app):
    """清空预览画布"""
    app.preview_canvas.delete("all")
    app.preview_status.config(text=_("parts.no_preview"))
    app.composite_image = None
    set_status(app, _("app.status.preview_cleared"))


def show_preview(app, img: Image.Image):
    """在画布上显示预览图"""
    if img.width < 1 or img.height < 1:
        from src.logtools import log
        log("error", _("log.invalid_preview_size", size=img.size))
        app.preview_status.config(text=_("parts.preview_failed"))
        return

    canvas = app.preview_canvas
    canvas.update_idletasks()

    cw = max(canvas.winfo_width(), 100)
    ch = max(canvas.winfo_height(), 100)

    scale = min(cw / img.width, ch / img.height, 1.0)
    display_w = max(int(img.width * scale), 1)
    display_h = max(int(img.height * scale), 1)

    if scale < 1.0:
        thumb = img.resize((display_w, display_h), Image.Resampling.LANCZOS)
    else:
        thumb = img

    # 保持引用防止 GC
    app._photo = ImageTk.PhotoImage(thumb)

    canvas.delete("all")
    canvas.config(scrollregion=(0, 0, img.width, img.height))
    app.preview_image_id = canvas.create_image(0, 0, anchor=tk.NW, image=app._photo)

    if scale < 1.0:
        canvas.create_text(cw // 2, 20, text=_("parts.scale_hint", scale=scale),
                           fill="red", font=("Arial", 10), tags="scale_hint")


# ── 字符缓存清理 ──────────────────────────────────────────

def clear_character_cache(app):
    """清除当前角色的 UI 状态（不清除磁盘文件）"""
    app.character_data = None
    app.composite_image = None
    app._thumb_refs.clear()
    app.part_vars.clear()
    app.part_labels.clear()

    try:
        app.sel_count_label.config(text=_("parts.selected_count", count=0))
        app.sel_listbox.delete(0, tk.END)
        app.preview_canvas.delete("all")
        app.preview_status.config(text=_("parts.no_preview"))
        for item in app.hierarchy_tree.get_children():
            app.hierarchy_tree.delete(item)
        for w in app.parts_inner.winfo_children():
            w.destroy()
    except Exception:
        pass


# ── 部件列表 ──────────────────────────────────────────────

def load_thumbnail(image_path: Path, size: tuple = (48, 48)) -> Optional[ImageTk.PhotoImage]:
    """加载精灵图片并生成缩略图（透明背景上居中绘制）"""
    try:
        img = Image.open(image_path).convert("RGBA")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        thumb = Image.new("RGBA", size, (240, 240, 240, 255))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        thumb.paste(img, offset, img)
        return ImageTk.PhotoImage(thumb)
    except Exception:
        return None


def update_selected_sprites_list(app):
    """刷新已选精灵列表（显示在右侧 Listbox 中）"""
    app.sel_listbox.delete(0, tk.END)
    for item in app.part_labels:
        if item["var"].get():
            name = item["part"]["name"]
            app.sel_listbox.insert(tk.END, name)


# ── 层级树 ──────────────────────────────────────────────

def populate_hierarchy_tree(app, hierarchy: List[Dict]):
    """用 hierarchy 数据填充 TreeView"""
    for item in app.hierarchy_tree.get_children():
        app.hierarchy_tree.delete(item)

    alpha_map: Dict[str, float] = {}
    if app.character_data:
        for td in app.character_data.get("transform_data", []):
            c = td.get("color", {})
            alpha_map[td["name"]] = c.get("a", 1.0)

    def add_node(parent_id: str, nodes: List[Dict]):
        for node in nodes:
            pos = node.get("position", {})
            pos_str = f"({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f})"
            order = node.get("sorting_order", 0)
            name = node.get("name", "")
            children = node.get("children", [])

            if node.get("has_sprite"):
                alpha = alpha_map.get(name, 1.0)
                display = _("hierarchy.item_sprite", name=name, pos=pos_str, order=order, alpha=f"{alpha:.2f}")
            elif children:
                display = _("hierarchy.item_children", name=name, count=len(children))
            else:
                display = _("hierarchy.item_empty", name=name, pos=pos_str)

            item_id = app.hierarchy_tree.insert(parent_id, tk.END, text=display, open=False)
            add_node(item_id, children)

    for i, node in enumerate(hierarchy):
        name = node.get("name", "")
        children = node.get("children", [])
        display = _("hierarchy.level_fmt", level=i + 1, name=name, count=len(children))
        root_id = app.hierarchy_tree.insert("", tk.END, text=display, open=True)
        add_node(root_id, children)

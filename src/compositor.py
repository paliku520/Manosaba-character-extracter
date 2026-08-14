"""
魔法少女の魔女审判 - 角色立绘合成模块

从 Unity bundle 中提取角色部件并拼接完整立绘。

功能:
    1. 检测 bundle 是否包含组件数据 (SpriteRenderer + Transform)
    2. 无组件数据的 bundle → 直接导出所有精灵
    3. 有组件数据的 bundle → 提取层级数据后拼接角色图像
"""

import gc
import json
import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple, cast

import UnityPy
from PIL import Image, ImageDraw, ImageFont

from src.logtools import log
from src.i18n import _


class LoadCancelled(Exception):
    """用户中断加载/导出（后台任务取消）"""


# ---------------------------------------------------------------------------
# 组件检测
# ---------------------------------------------------------------------------

def has_component_data(bundle_path: Path) -> bool:
    """
    检测 bundle 文件中是否存在 SpriteRenderer 组件数据。
    有组件数据说明可以尝试拼接角色图像。
    """
    env = None
    try:
        env = UnityPy.load(str(bundle_path))
        for obj in env.objects:
            if obj.type.name == "SpriteRenderer":
                return True
        return False
    except Exception as e:
        log("error", _("log.component_detect_failed", name=bundle_path.name, e=e))
        return False
    finally:
        # 释放 UnityPy 环境，避免每次分析都累积 bundle 内存
        if env is not None:
            try:
                env.files.clear()
            except Exception:
                pass
            env = None


# ---------------------------------------------------------------------------
# 精灵提取（无组件模式）
# ---------------------------------------------------------------------------

def extract_sprites(
    bundle_path: Path,
    output_dir: Path,
    progress_callback=None,
    cancel_check=None,
    log_each: bool = True,
) -> List[Dict]:
    """
    从 bundle 中提取所有精灵，保存为 PNG 文件。

    Args:
        bundle_path: bundle 文件路径
        output_dir:  输出目录
        progress_callback: 可选进度回调 fn(current, total)
        cancel_check: 可选取消检查 fn() -> bool，返回 True 时抛 LoadCancelled
        log_each:     是否逐条记录导出精灵日志（预览等批量场景可关闭避免刷屏）

    Returns:
        [{ "name": str, "path_id": int, "file_path": str, "size": [w, h] }, ...]
    """
    character_name = bundle_path.stem
    save_dir = output_dir / character_name
    save_dir.mkdir(parents=True, exist_ok=True)

    env = UnityPy.load(str(bundle_path))

    # 预先统计精灵对象总数用于进度显示
    all_objects = list(env.objects)
    sprite_objs = [obj for obj in all_objects if obj.type.name == "Sprite"]
    total = len(sprite_objs)
    results = []

    for idx, obj in enumerate(sprite_objs):
        if cancel_check and cancel_check():
            raise LoadCancelled()
        try:
            data = obj.read()
            if not hasattr(data, "image") or data.image is None:
                continue

            sprite_name = getattr(data, "m_Name", f"sprite_{obj.path_id}")
            safe_name = re.sub(r'[<>:"/\\|?*]', "_", sprite_name)
            file_path = save_dir / f"{safe_name}.png"

            data.image.save(str(file_path))
            results.append({
                "name": sprite_name,
                "path_id": obj.path_id,
                "file_path": str(file_path),
                "size": [data.image.size[0], data.image.size[1]],
            })
            if log_each:
                log("info", _("log.loaded_sprite", name=safe_name))
        except Exception as e:
            log("error", _("log.sprite_extract_failed", id=obj.path_id, e=e))

        if progress_callback:
            progress_callback(idx + 1, total)

    log("info", _("log.export_done", file=bundle_path.name, count=len(results), dir=save_dir))
    # 释放 UnityPy 环境并回收，降低导出过程内存峰值
    try:
        env.files.clear()
    except Exception:
        pass
    gc.collect()
    return results


# ---------------------------------------------------------------------------
# 角色数据提取（有组件模式）
# ---------------------------------------------------------------------------

def extract_character_data(
    bundle_path: Path,
    output_dir: Path,
    progress_callback=None,
    cancel_check=None,
) -> Dict:
    """
    完整提取角色数据，包括精灵、变换（位置/排序）和层级结构。

    Args:
        bundle_path: bundle 文件路径
        output_dir:  输出目录
        progress_callback: 可选进度回调 fn(current, total)
        cancel_check: 可选取消检查 fn() -> bool，返回 True 时抛 LoadCancelled

    Returns:
        {
            "character_name": str,
            "sprites_dir": str,
            "sprite_mapping": { path_id: { name, file_path, size } },
            "transform_data": [
                {
                    "name": str,
                    "sprite_name": str,
                    "sprite_path": str,
                    "sprite_size": [w, h],
                    "position": { "x": float, "y": float, "z": float },
                    "sorting_order": int,
                    "category": str,
                }
            ],
            "hierarchy": [ ... ]  # 树形结构
        }
    """
    character_name = bundle_path.stem
    save_dir = output_dir / character_name
    sprites_dir = save_dir / "sprites"
    sprites_dir.mkdir(parents=True, exist_ok=True)

    env = UnityPy.load(str(bundle_path))

    # ---- 第1步: 建立对象映射 ----
    game_objects: Dict[int, Dict] = {}
    transforms: Dict[int, Dict] = {}
    sprite_renderers: Dict[int, Dict] = {}

    for obj in env.objects:
        try:
            t = obj.type.name
            # 只 read 需要的类型；跳过 Texture2D/AudioClip 等无关大对象（其 read 会解码，首次冷加载极慢）
            if t not in ("GameObject", "Transform", "SpriteRenderer"):
                continue
            data = obj.read()

            if t == "GameObject":
                comps = getattr(data, "m_Component", [])
                game_objects[obj.path_id] = {
                    "name": getattr(data, "m_Name", f"GO_{obj.path_id}"),
                    "components": comps,
                }

            elif t == "Transform":
                go_ref = getattr(data, "m_GameObject", None)
                go_id = getattr(go_ref, "m_PathID", 0) if go_ref else 0
                children = list(getattr(data, "m_Children", []))
                father = getattr(data, "m_Father", None)
                parent_id = getattr(father, "m_PathID", 0) if father else 0

                transforms[obj.path_id] = {
                    "game_object": go_id,
                    "position": _read_vector3(getattr(data, "m_LocalPosition", None)),
                    "children": children,
                    "parent": parent_id,
                }

            elif t == "SpriteRenderer":
                go_ref = getattr(data, "m_GameObject", None)
                go_id = getattr(go_ref, "m_PathID", 0) if go_ref else 0
                sprite_ref = getattr(data, "m_Sprite", None)
                sprite_id = getattr(sprite_ref, "m_PathID", 0) if sprite_ref else 0

                sprite_renderers[obj.path_id] = {
                    "game_object": go_id,
                    "sprite": sprite_id,
                    "sorting_order": getattr(data, "m_SortingOrder", 0),
                    "color": _read_color(getattr(data, "m_Color", None)),
                }
        except Exception:
            continue

    # ---- 第2步: 关联 GameObj → Transform + SpriteRenderer ----
    character_parts = []
    for go_id, go_data in game_objects.items():
        tf = next((t for t in transforms.values() if t["game_object"] == go_id), None)
        sr = next((r for r in sprite_renderers.values() if r["game_object"] == go_id), None)
        if tf and sr:
            character_parts.append({
                "name": go_data["name"],
                "game_object_id": go_id,
                "position": tf["position"],
                "sorting_order": sr["sorting_order"],
                "sprite_id": sr["sprite"],
                "color": sr["color"],
            })

    # ---- 第3步: 提取精灵图像 ----
    sprite_mapping: Dict[int, Dict] = {}
    sprite_objs = [obj for obj in env.objects if obj.type.name == "Sprite"]
    sprite_total = len(sprite_objs)
    for idx, obj in enumerate(sprite_objs):
        if cancel_check and cancel_check():
            raise LoadCancelled()
        try:
            data = obj.read()
            if not hasattr(data, "image") or data.image is None:
                continue
            sprite_name = getattr(data, "m_Name", f"sprite_{obj.path_id}")
            safe_name = re.sub(r'[<>:"/\\|?*]', "_", sprite_name)
            file_path = sprites_dir / f"{safe_name}.png"
            data.image.save(str(file_path))
            sprite_mapping[obj.path_id] = {
                "name": sprite_name,
                "file_path": str(file_path),
                "size": [data.image.size[0], data.image.size[1]],
            }
            log("info", _("log.loaded_sprite", name=safe_name))
        except Exception:
            continue

        if progress_callback:
            progress_callback(idx + 1, sprite_total)

    # ---- 第4步: 组装 transform_data ----
    if cancel_check and cancel_check():
        raise LoadCancelled()
    transform_data = []
    for part in character_parts:
        si = sprite_mapping.get(part["sprite_id"])
        if si:
            transform_data.append({
                "name": part["name"],
                "sprite_name": si["name"],
                "sprite_path": si["file_path"],
                "sprite_size": si["size"],
                "position": part["position"],
                "sorting_order": part["sorting_order"],
                "color": part["color"],
                "category": _categorize(part["name"]),
            })

    # ---- 第5步: 构建层级树 ----
    def build_hierarchy(tid: int, level: int = 0) -> Optional[Dict]:
        tf = transforms.get(tid)
        if not tf:
            return None
        go = game_objects.get(tf["game_object"], {})
        sr = next((r for r in sprite_renderers.values() if r["game_object"] == tf["game_object"]), None)
        node = {
            "name": go.get("name", "Unknown"),
            "level": level,
            "position": tf["position"],
            "has_sprite": sr is not None,
            "sorting_order": sr["sorting_order"] if sr else 0,
            "children": [],
        }
        for child_ref in tf["children"]:
            child_id = getattr(child_ref, "m_PathID", 0)
            child_node = build_hierarchy(child_id, level + 1)
            if child_node:
                node["children"].append(child_node)
        return node

    hierarchy = []
    for tid, tf in transforms.items():
        if tf["parent"] == 0:
            node = build_hierarchy(tid)
            if node:
                hierarchy.append(node)

    # ---- 保存 JSON 调试数据到角色根目录（与 sprites/ 同级）----
    with open(save_dir / "character_data.json", "w", encoding="utf-8") as f:
        json.dump({
            "character_name": character_name,
            "transform_data": transform_data,
            "hierarchy": hierarchy,
        }, f, indent=2, ensure_ascii=False)

    log("info", _("log.char_data_extracted", name=character_name, count=len(transform_data)))

    # 释放 UnityPy 环境（含大量已解码对象），降低提取过程内存峰值
    try:
        env.files.clear()
    except Exception:
        pass
    env = None
    gc.collect()

    return {
        "character_name": character_name,
        "sprites_dir": str(sprites_dir),
        "save_dir": str(save_dir),
        "sprite_mapping": sprite_mapping,
        "transform_data": transform_data,
        "hierarchy": hierarchy,
    }


# ---------------------------------------------------------------------------
# 图像拼接
# ---------------------------------------------------------------------------

class SpriteCompositor:
    """将角色部件按位置和深度顺序拼接为完整立绘。"""

    def __init__(self, scale: float = 100.0):
        self.scale = scale
        self.canvas_size = (2000, 4000)

    def composite(
        self,
        transform_data: List[Dict],
        selected_names: Optional[List[str]] = None,
        custom_depths: Optional[Dict[str, int]] = None,
        progress_callback=None,
        sketchbook_text: Optional[str] = None,
        sketch_font_size: int = 56,
        sketch_align: str = "center",
    ) -> Optional[Image.Image]:
        """
        合成角色图像。

        Args:
            transform_data: extract_character_data 返回的 transform_data 列表
            selected_names: 要包含的部件名称列表，None 表示全部
            custom_depths:  自定义深度 {部件名: 排序值}，None 用原始顺序
            progress_callback: 可选进度回调 fn(current, total)
            sketchbook_text: 自定义素描本文字（Anan 选中 Arms01/Arms02 时生效）；
                             提供后隐藏默认笔迹（Option_Arms*）并在其位置绘制自定义文字
            sketch_font_size: 素描本文字字号（像素），默认 56
            sketch_align: 素描本文字对齐方式（left/center/right），默认 center

        Returns:
            PIL Image (RGBA)，失败返回 None
        """
        if not transform_data:
            return None

        if selected_names is None:
            selected_names = [p["name"] for p in transform_data]

        # 筛选并排序
        if custom_depths:
            sorted_parts = sorted(
                [p for p in transform_data if p["name"] in selected_names],
                key=lambda x: custom_depths[x["name"]] if x["name"] in custom_depths else x["sorting_order"],
            )
        else:
            sorted_parts = sorted(
                [p for p in transform_data if p["name"] in selected_names],
                key=lambda x: x["sorting_order"],
            )

        # ── 自定义素描本文字（Anan 专属：选中 Arms01/Arms02 时）──
        # 锚点取 Option_Arms01_01 / Option_Arms02_01 的坐标；提供文字时隐藏默认笔迹（Option_Arms*）
        sketch_anchor = None
        if sketchbook_text and sketchbook_text.strip():
            sel = set(selected_names)
            variant = "Arms01" if "Arms01" in sel else ("Arms02" if "Arms02" in sel else None)
            if variant:
                ref_name = f"Option_{variant}_01"
                ref = next((p for p in transform_data if p["name"] == ref_name), None)
                if ref:
                    sketch_anchor = (float(ref["position"]["x"]), float(ref["position"]["y"]))
                    sorted_parts = [p for p in sorted_parts if not p["name"].startswith("Option_Arms")]

        # 计算画布大小
        canvas_size = self._calc_canvas_size(sorted_parts)
        composite = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        cx = canvas_size[0] // 2
        cy = canvas_size[1] // 2

        total = len(sorted_parts)
        for i, part in enumerate(sorted_parts):
            try:
                img = Image.open(part["sprite_path"]).convert("RGBA")
                try:
                    # 应用 SpriteRenderer.m_Color（RGBA，默认白色全不透明）
                    c = part.get("color", {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})
                    cr, cg, cb, ca = c["r"], c["g"], c["b"], c["a"]
                    if (cr, cg, cb, ca) != (1.0, 1.0, 1.0, 1.0):
                        r, g, b, a = img.split()
                        r = r.point(lambda v: int(v * cr))
                        g = g.point(lambda v: int(v * cg))
                        b = b.point(lambda v: int(v * cb))
                        a = a.point(lambda v: int(v * ca))
                        img = Image.merge("RGBA", (r, g, b, a))

                    px = int(part["position"]["x"] * self.scale + cx)
                    py = int(part["position"]["y"] * -self.scale + cy)
                    sx, sy = img.size
                    place_x = px - sx // 2
                    place_y = py - sy // 2

                    # alpha_composite 实例方法支持 dest 且原地合成，避免创建全画布临时图（内存峰值↓）
                    composite.alpha_composite(img, dest=(place_x, place_y))
                finally:
                    img.close()  # 用后立即释放图片对象
            except Exception as e:
                log("error", _("log.composite_failed_part", name=part['name'], e=e))

            if progress_callback:
                progress_callback(i + 1, total)

            # 每合成 20 个部件回收一次，释放中间图像对象
            if (i + 1) % 20 == 0:
                gc.collect()

        # 在素描本上绘制自定义文字（锚点 = Option_Arms0x_01 坐标）
        if sketch_anchor is not None:
            self._draw_sketch_text(composite, sketchbook_text or "", sketch_anchor, cx, cy,
                                   font_size=sketch_font_size, align=sketch_align)

        return composite

    # ── 自定义素描本文字绘制 ──────────────────────────────

    # 常见中文字体（Windows）；按顺序尝试，找不到则退回默认字体
    _SKETCH_FONTS = [
        "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",   # 微软雅黑 Bold
        "C:/Windows/Fonts/simhei.ttf",   # 黑体
        "C:/Windows/Fonts/simsun.ttc",   # 宋体
        "C:/Windows/Fonts/arial.ttf",
    ]

    def _load_sketch_font(self, size: int = 56) -> ImageFont.FreeTypeFont:
        """加载用于素描本文字的字体（优先中文字体）"""
        for path in self._SKETCH_FONTS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return cast(ImageFont.FreeTypeFont, ImageFont.load_default())

    def _draw_sketch_text(
        self,
        canvas: Image.Image,
        text: str,
        anchor: Tuple[float, float],
        cx: int,
        cy: int,
        font_size: int = 56,
        align: str = "center",
    ) -> None:
        """在素描本上以 anchor（Unity 坐标）为锚点绘制自定义文字。

        深灰铅笔笔迹风格，支持多行（\n 换行）；整体以锚点为中心（垂直居中，
        水平方向文字块居中），行内按 align（left/center/right）对齐。
        """
        try:
            lines = [ln for ln in str(text).split("\n") if ln]
            if not lines:
                return
            font = self._load_sketch_font(font_size)
            draw = ImageDraw.Draw(canvas)
            px = int(anchor[0] * self.scale + cx)
            py = int(-anchor[1] * self.scale + cy)
            align = (align or "center").lower()

            line_h = int(font.size * 1.4)
            widths = []
            for ln in lines:
                bbox = draw.textbbox((0, 0), ln, font=font)
                widths.append(bbox[2] - bbox[0])
            max_w = max(widths)
            # 文字块整体垂直居中于锚点；水平方向以锚点为中心
            total_h = line_h * len(lines) - int(font.size * 0.4)
            y = py - total_h // 2
            color = (70, 70, 70, 255)  # 深灰，接近铅笔笔迹
            for ln, w in zip(lines, widths):
                bbox = draw.textbbox((0, 0), ln, font=font)
                if align == "left":
                    x = px - max_w // 2 - bbox[0]
                elif align == "right":
                    x = px + max_w // 2 - w - bbox[0]
                else:  # center
                    x = px - w // 2 - bbox[0]
                draw.text((x, y - bbox[1]), ln, font=font, fill=color)
                y += line_h
            # 记录完整文字内容（多行时保留换行，方便日志里核对输入）
            log("info", f"[composite] 素描本自定义文字 ({len(lines)} 行, 宽 {max_w}px, 对齐 {align}):\n" + "\n".join(lines))
        except Exception as e:
            log("warning", f"[composite] 绘制素描本文字失败: {e}")

    def _calc_canvas_size(self, parts: List[Dict]) -> Tuple[int, int]:
        """根据部件位置和尺寸计算画布大小"""
        if not parts:
            return self.canvas_size

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for part in parts:
            try:
                w, h = part["sprite_size"]
                px = part["position"]["x"] * self.scale
                py = part["position"]["y"] * -self.scale
                min_x = min(min_x, px - w // 2)
                max_x = max(max_x, px + w // 2)
                min_y = min(min_y, py - h // 2)
                max_y = max(max_y, py + h // 2)
            except Exception:
                continue

        if min_x == float("inf"):
            return self.canvas_size

        w = max(2000, int(max_x - min_x) + 400)
        h = max(4000, int(max_y - min_y) + 400)
        return (w, h)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _read_vector3(v: object) -> Dict[str, float]:
    try:
        if v and hasattr(v, "x"):
            return {"x": getattr(v, "x", 0.0), "y": getattr(v, "y", 0.0), "z": getattr(v, "z", 0.0)}
    except Exception:
        pass
    return {"x": 0.0, "y": 0.0, "z": 0.0}


def _read_color(c: object) -> Dict[str, float]:
    try:
        if c and hasattr(c, "r"):
            return {"r": getattr(c, "r", 1.0), "g": getattr(c, "g", 1.0),
                    "b": getattr(c, "b", 1.0), "a": getattr(c, "a", 1.0)}
    except Exception:
        pass
    return {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}


def _categorize(name: str) -> str:
    """与原始 tkinter_app.py 的 categorize_part 保持一致的分类逻辑"""
    n = name.lower()
    if any(w in n for w in ["body", "torso"]):
        return "body"
    if any(w in n for w in ["head", "face"]):
        return "head"
    if "arml" in n or "leftarm" in n:
        return "arm_left"
    if "armr" in n or "rightarm" in n:
        return "arm_right"
    if "arm" in n:
        return "arms"
    if "eye" in n:
        return "eyes"
    if "mouth" in n:
        return "mouth"
    if "hair" in n:
        return "hair"
    if any(w in n for w in ["blend", "effect", "shadow"]):
        return "effects"
    return "other"

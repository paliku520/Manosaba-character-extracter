"""
魔法少女の魔女审判 - 角色立绘合成模块

从 Unity bundle 中提取角色部件并拼接完整立绘。

功能:
    1. 检测 bundle 是否包含组件数据 (SpriteRenderer + Transform)
    2. 无组件数据的 bundle → 直接导出所有精灵
    3. 有组件数据的 bundle → 提取层级数据后拼接角色图像
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import UnityPy
from PIL import Image

from src.tools import log
from src.i18n import _


# ---------------------------------------------------------------------------
# 组件检测
# ---------------------------------------------------------------------------

def has_component_data(bundle_path: Path) -> bool:
    """
    检测 bundle 文件中是否存在 SpriteRenderer 组件数据。
    有组件数据说明可以尝试拼接角色图像。
    """
    try:
        env = UnityPy.load(str(bundle_path))
        for obj in env.objects:
            if obj.type.name == "SpriteRenderer":
                return True
        return False
    except Exception as e:
        log("error", _("log.component_detect_failed", name=bundle_path.name, e=e))
        return False


# ---------------------------------------------------------------------------
# 精灵提取（无组件模式）
# ---------------------------------------------------------------------------

def extract_sprites(
    bundle_path: Path,
    output_dir: Path,
    progress_callback=None,
) -> List[Dict]:
    """
    从 bundle 中提取所有精灵，保存为 PNG 文件。

    Args:
        bundle_path: bundle 文件路径
        output_dir:  输出目录
        progress_callback: 可选进度回调 fn(current, total)

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
            log("info", _("log.exported_sprite", name=safe_name))
        except Exception as e:
            log("error", _("log.sprite_extract_failed", id=obj.path_id, e=e))

        if progress_callback:
            progress_callback(idx + 1, total)

    log("info", _("log.export_done", file=bundle_path.name, count=len(results), dir=save_dir))
    return results


# ---------------------------------------------------------------------------
# 角色数据提取（有组件模式）
# ---------------------------------------------------------------------------

def extract_character_data(
    bundle_path: Path,
    output_dir: Path,
    progress_callback=None,
) -> Dict:
    """
    完整提取角色数据，包括精灵、变换（位置/排序）和层级结构。

    Args:
        bundle_path: bundle 文件路径
        output_dir:  输出目录
        progress_callback: 可选进度回调 fn(current, total)

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
            data = obj.read()
            t = obj.type.name

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
        except Exception:
            continue

        if progress_callback:
            progress_callback(idx + 1, sprite_total)

    # ---- 第4步: 组装 transform_data ----
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
    ) -> Optional[Image.Image]:
        """
        合成角色图像。

        Args:
            transform_data: extract_character_data 返回的 transform_data 列表
            selected_names: 要包含的部件名称列表，None 表示全部
            custom_depths:  自定义深度 {部件名: 排序值}，None 用原始顺序
            progress_callback: 可选进度回调 fn(current, total)

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
                key=lambda x: custom_depths.get(x["name"], x["sorting_order"]),
            )
        else:
            sorted_parts = sorted(
                [p for p in transform_data if p["name"] in selected_names],
                key=lambda x: x["sorting_order"],
            )

        # 计算画布大小
        canvas_size = self._calc_canvas_size(sorted_parts)
        composite = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        cx = canvas_size[0] // 2
        cy = canvas_size[1] // 2

        total = len(sorted_parts)
        for i, part in enumerate(sorted_parts):
            try:
                img = Image.open(part["sprite_path"]).convert("RGBA")

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

                # alpha_composite 正确处理半透明像素
                if img.mode == "RGBA":
                    temp = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                    temp.paste(img, (place_x, place_y))
                    composite = Image.alpha_composite(composite, temp)
                else:
                    composite.paste(img, (place_x, place_y), img)
            except Exception as e:
                log("error", _("log.composite_failed_part", name=part['name'], e=e))

            if progress_callback:
                progress_callback(i + 1, total)

        return composite

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

"""
导出管理模块 — 处理精灵导出和合成图保存的目录结构

目录规则:
  - 无组件角色: output/<name>/        (精灵直接平铺)
  - 有组件角色: output/<name>/sprites/   (导出的精灵)
                output/<name>/composite/  (合成图)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from src.logtools import log
from src.i18n import _
from src.compositor import LoadCancelled

# ---------------------------------------------------------------------------
# 精灵导出
# ---------------------------------------------------------------------------

def export_sprites(
    bundle_path: Path,
    output_dir: Path,
    has_components: bool = False,
    progress_callback=None,
    cancel_check=None,
) -> List[Dict]:
    """
    从 bundle 中提取所有精灵并保存为 PNG。

    Args:
        bundle_path:       bundle 文件路径
        output_dir:        输出根目录
        has_components:    角色是否拥有组件结构
        progress_callback: 可选进度回调 fn(current, total)
        cancel_check:      可选取消检查 fn() -> bool，返回 True 时抛 LoadCancelled

    Returns:
        [{ "name": str, "path_id": int, "file_path": str, "size": [w, h] }, ...]
    """
    import UnityPy

    character_name = bundle_path.stem
    if has_components:
        save_dir = output_dir / character_name / "sprites"
    else:
        save_dir = output_dir / character_name
    save_dir.mkdir(parents=True, exist_ok=True)

    env = UnityPy.load(str(bundle_path))

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
            log("info", _("log.exported_sprite", name=safe_name))
        except Exception as e:
            log("error", _("log.sprite_extract_failed", id=obj.path_id, e=e))

        if progress_callback:
            progress_callback(idx + 1, total)

    log("info", _("log.export_done", file=bundle_path.name, count=len(results), dir=save_dir))
    return results


# ---------------------------------------------------------------------------
# 合成图保存
# ---------------------------------------------------------------------------

def save_composite(
    image: Image.Image,
    output_dir: Path,
    character_name: str,
) -> Path:
    """
    保存合成图到 output/<name>/composite/ 目录。

    自动生成不重复文件名: <name>_composite.png / <name>_composite_1.png ...

    Args:
        image:          合成后的 PIL Image
        output_dir:     输出根目录
        character_name: 角色名

    Returns:
        保存的文件路径
    """
    save_dir = output_dir / character_name / "composite"
    save_dir.mkdir(parents=True, exist_ok=True)

    base_path = save_dir / f"{character_name}_composite"
    save_path = save_dir / f"{character_name}_composite.png"
    counter = 1
    while save_path.exists():
        save_path = save_dir / f"{character_name}_composite_{counter}.png"
        counter += 1

    image.save(save_path)
    log("info", f"Composite saved to: {save_path}")
    return save_path

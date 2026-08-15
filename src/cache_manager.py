"""
缓存管理模块 — 处理角色数据的缓存读写

缓存目录: temp/<name>/
  ├── character_data.json    # 提取的完整角色数据
  └── sprites/               # 缓存的精灵 PNG
"""

import json
from pathlib import Path
from typing import Dict, Optional

from src.logtools import log
from src.i18n import _


def save_extracted_data(data: Dict, cache_dir: Path, character_name: str) -> None:
    """
    将提取的角色数据写入缓存。

    注意：精灵文件由 extract_character_data 直接保存到缓存目录。
    此函数仅写入 character_data.json。

    Args:
        data:           extract_character_data 返回的完整数据字典
        cache_dir:      缓存根目录（通常为 temp/）
        character_name: 角色名
    """
    save_dir = cache_dir / character_name
    save_dir.mkdir(parents=True, exist_ok=True)

    json_path = save_dir / "character_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log("info", _("log.cache_saved", name=character_name, path=json_path))


def load_extracted_data(cache_dir: Path, character_name: str) -> Optional[Dict]:
    """
    从缓存加载角色数据，验证完整性。

    验证条件:
      1. character_data.json 存在
      2. sprites/ 目录存在
      3. JSON 中所有 sprite_path 对应的文件存在

    任一不满足则返回 None。

    Args:
        cache_dir:      缓存根目录（通常为 temp/）
        character_name: 角色名

    Returns:
        完整数据字典，或 None（缓存无效）
    """
    json_path = cache_dir / character_name / "character_data.json"
    sprites_dir = cache_dir / character_name / "sprites"

    if not json_path.exists() or not sprites_dir.exists():
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 旧缓存可能没有 mask_mapping：尝试读取同目录的 mask_mapping.json（独立生成的文件）
        if "mask_mapping" not in data:
            mm_path = save_dir / "mask_mapping.json"
            if mm_path.exists():
                try:
                    data["mask_mapping"] = json.loads(mm_path.read_text(encoding="utf-8"))
                except Exception:
                    data["mask_mapping"] = None
            else:
                data["mask_mapping"] = None

        # 验证所有精灵文件都存在
        for part in data.get("transform_data", []):
            sprite_path = Path(part["sprite_path"])
            if not sprite_path.exists():
                log("info", f"Cache incomplete, missing: {sprite_path}")
                return None

        transform_data = data.get("transform_data", [])
        log("info", _("log.cache_loaded", name=character_name, count=len(transform_data)))
        return data
    except Exception as e:
        log("warning", f"Failed to load cache: {e}")
        return None


def clear_cache(cache_dir: Path) -> None:
    """
    清空整个缓存目录。

    Args:
        cache_dir: 缓存根目录
    """
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
        log("info", _("log.temp_cleared", path=cache_dir))

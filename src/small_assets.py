"""Catalog individual game images, including sprites packed into UI atlases."""

from __future__ import annotations

import gc
import re
from pathlib import Path

import UnityPy

from src.background_assets import (
    _check_cancel, _natural_key, find_backgrounds_dir, preview_objects,
    prune_texture_cache, release_environment,
)
from src.compositor import LoadCancelled


SOURCES = (
    "general-witchbook_assets_all.bundle",
    "general-sprites_assets_all.bundle",
    "naninovel-ui_assets_all.bundle",
    "naninovel-spawn_assets_all.bundle",
    "general-prefabs_assets_all.bundle",
    "general-transitions_assets_all.bundle",
)
OUTPUT_GROUPS = {
    "evidence": "证物", "profiles": "人物资料", "interface": "界面素材",
    "stage_props": "演出物件", "stage_characters": "演出人物",
    "stage_backgrounds": "演出背景", "stage_effects": "演出特效",
    "stage_other": "演出其他", "maps": "地图素材",
    "effect_textures": "特效纹理", "transitions": "转场遮罩",
}


def classify_asset(source: str, name: str) -> str:
    value = name.casefold()
    if source.startswith("general-witchbook"):
        return "profiles" if value.startswith("profile_") else "evidence"
    if source.startswith("general-transitions"):
        return "transitions"
    if source.startswith("general-prefabs"):
        return "effect_textures"
    if not source.startswith("naninovel-spawn"):
        return "interface"
    if value.startswith(("map_", "pin_")):
        return "maps"
    if any(token in value for token in ("background", "backgoround", "frontground", "trail_bg")) or value.startswith("space_"):
        return "stage_backgrounds"
    if "kari" in value:
        return "stage_other"
    if any(token in value for token in (
        "cutin", "glassfragment", "luminescence", "butterfly", "flame", "denpa",
        "bikabika", "glitch", "dot", "kirakira", "blood", "light",
    )) or value in ("black", "white", "square", "transparent"):
        return "stage_effects"
    tokens = set(re.split(r"[^a-z]+", value))
    if tokens.intersection({
        "broom", "broomstick", "bow", "rapier", "sheath", "arrow", "ribbon", "ribon",
        "string", "key", "smartphone", "knife", "gun", "monitor", "paper", "bin",
        "stretcher", "gallows", "hammock", "curtain", "balcony", "item",
    }):
        return "stage_props"
    if tokens.intersection({
        "ema", "hiro", "leia", "hanna", "anan", "alisa", "meruru", "nanoka", "noa",
        "nao", "noah", "shelly", "sherry", "mago", "margo", "milia", "miria",
        "koko", "coco", "yuki", "chiro",
    }):
        return "stage_characters"
    return "stage_other"


def find_small_asset_sources(directory: Path, cancel_check=None) -> list[Path]:
    backgrounds = find_backgrounds_dir(directory, cancel_check)
    # Accommodate selection of a backgrounds group as well as the game root.
    platform = next((parent for parent in backgrounds.parents
                     if any((parent / name).is_file() for name in SOURCES)), None)
    if platform is None:
        return []
    sources = [platform / name for name in SOURCES if (platform / name).is_file()]
    data_dir = next((parent for parent in platform.parents
                     if (parent / "resources.assets").is_file()), None)
    if data_dir:
        sources.extend(sorted(data_dir.glob("sharedassets*.assets"), key=lambda p: _natural_key(p.name)))
        sources.append(data_dir / "resources.assets")
    return sources


def _backing_textures(data) -> set[int]:
    rd = getattr(data, "m_RD", None)
    atlas = getattr(data, "m_SpriteAtlas", None)
    if atlas and atlas.path_id:
        atlas_data = atlas.read()
        rd = next((value for key, value in atlas_data.m_RenderDataMap
                   if key == data.m_RenderDataKey), rd)
    return {pointer.path_id for field in ("texture", "alphaTexture")
            if (pointer := getattr(rd, field, None)) is not None and pointer.path_id
            and pointer.file_id == 0}


def scan_small_assets(directory: Path, cancel_check=None, progress_callback=None) -> dict:
    """Read names/rectangles without decoding pixels; exclude sprite atlas textures."""
    sources = find_small_asset_sources(directory, cancel_check)
    items, errors = [], []
    for index, path in enumerate(sources):
        _check_cancel(cancel_check)
        env = None
        records, backing = [], set()
        obj = data = None
        try:
            env = UnityPy.load(str(path))
            for obj in env.objects:
                _check_cancel(cancel_check)
                kind = obj.type.name
                if kind not in ("Sprite", "Texture2D"):
                    continue
                try:
                    data = obj.read()
                    if kind == "Sprite":
                        backing.update(_backing_textures(data))
                        size = [data.m_Rect.width, data.m_Rect.height]
                    else:
                        size = [data.m_Width, data.m_Height]
                    if any(side <= 0 for side in size):
                        # Unity runtime-generated font textures have no stored pixels.
                        continue
                    name = data.m_Name or f"image_{obj.path_id}"
                    records.append({
                        "id": f"small/{path.name}/{kind}/{obj.path_id}",
                        "object_id": str(obj.path_id), "asset_type": kind,
                        "name": name, "source": path.name, "size": size,
                        "group": classify_asset(path.name, name), "bundle_path": str(path),
                    })
                except LoadCancelled:
                    raise
                except Exception as exc:
                    errors.append({"id": f"{path.name}/{obj.path_id}", "message": str(exc)})
            items.extend(record for record in records
                         if record["asset_type"] == "Sprite" or int(record["object_id"]) not in backing)
        except LoadCancelled:
            raise
        except Exception as exc:
            errors.append({"id": path.name, "message": str(exc)})
        finally:
            release_environment(env)
            env = data = obj = None
            gc.collect()
        if progress_callback:
            progress_callback(index + 1, len(sources))
    # Keep images from each source adjacent for efficient preview prewarming.
    items.sort(key=lambda item: (_natural_key(item["source"]), _natural_key(item["name"]), item["object_id"]))
    return {"bundles": items, "count": len(items), "errors": errors}


class SmallAssetPreviewer:
    """Reuse one parsed source and a bounded decoded-atlas cache inside the worker."""

    def __init__(self):
        self._key = None
        self._env = None
        self._objects = {}

    def preview(self, path: Path, object_id: str, asset_type: str, max_side=1280, cancel_check=None) -> dict:
        _check_cancel(cancel_check)
        stat = path.stat()
        key = (str(path.resolve()), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        if key != self._key:
            self.close()
            self._env = UnityPy.load(str(path))
            self._objects = {(obj.type.name, str(obj.path_id)): obj for obj in self._env.objects
                             if obj.type.name in ("Sprite", "Texture2D")}
            self._key = key
        obj = self._objects.get((asset_type, str(object_id)))
        if obj is None:
            raise ValueError("image object no longer exists; reload the asset directory")
        try:
            return preview_objects([obj], max_side, cancel_check)
        finally:
            prune_texture_cache(self._env)

    def close(self):
        release_environment(self._env)
        self._objects.clear()
        self._env = self._key = None
        gc.collect()

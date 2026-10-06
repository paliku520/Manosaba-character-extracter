"""
导出管理模块 — 所有资源导出的统一入口（命名、落盘与目录结构）

目录规则:
  - 无组件角色: output/<name>/                (精灵直接平铺)
  - 有组件角色: output/<name>/sprites/        (导出的精灵)
                output/<name>/composite/      (合成图)
  - 无组件预览导出: output/<name>/
  - 名片:       output/nameplate/
  - 背景/小素材: output/backgrounds/<分类键>/  (分类键为 i18n 英文键，与界面语言无关)

命名规则:
  - Windows 非法字符、控制字符与设备保留名统一转换为安全名称
  - 默认不覆盖已有文件，自动追加 _1、_2 等后缀；overwrite=True 时原子替换
"""

from __future__ import annotations

import gc
import os
import re
import tempfile
from collections import OrderedDict
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from PIL import Image

from src.logtools import log
from src.i18n import _
from src.compositor import LoadCancelled
from src.background_assets import (
    _check_cancel,
    prune_texture_cache,
    release_environment,
)

# 背景/小素材分类目录的兜底键：backgrounds 根目录下的素材归入主背景分类
DEFAULT_OUTPUT_GROUP = "mainbackground"

# Windows 设备保留名（不能直接作为文件名主干）
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
}


# ---------------------------------------------------------------------------
# 共用命名与落盘
# ---------------------------------------------------------------------------

def safe_name(name: str) -> str:
    """把任意名称转换为 Windows 可用的文件名（保留中文与原始可读性）。"""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name)).strip().rstrip(". ")
    if not name or name in (".", ".."):
        return "image"
    if name.split(".")[0].upper() in _RESERVED_NAMES:
        name = "_" + name
    return name[:160]


def output_group_name(group: str) -> str:
    """背景/小素材的分类目录名：取分类键（i18n 英文键），与界面语言无关。

    分类键来自 `small_assets.classify_asset` 或背景包的相对目录名；
    根目录/未知分类回退到 DEFAULT_OUTPUT_GROUP。
    """
    key = str(group or "").replace("\\", "/").split("/")[0].strip()
    if not key or key in (".", ".."):
        key = DEFAULT_OUTPUT_GROUP
    return safe_name(key)


def save_png(image: Image.Image, directory: Path, name: str,
             staging_dir: Optional[Path] = None, overwrite: bool = False) -> Path:
    """统一的 PNG 落盘：先在临时文件编码，再原子移动到最终文件名。

    默认不覆盖已有文件（追加 _1、_2 等后缀）；overwrite=True 时原子替换。
    编码与最终文件分离，取消或异常不会留下不完整的 PNG。
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = safe_name(name)
    with tempfile.NamedTemporaryFile(dir=staging_dir or directory, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        image.save(temporary, format="PNG")
        index = 0
        while True:
            target = directory / f"{stem}{'_' + str(index) if index else ''}.png"
            try:
                if overwrite:
                    os.replace(temporary, target)
                elif os.name == "nt":
                    # Windows rename 与 POSIX 硬链接都拒绝已存在目标
                    temporary.rename(target)
                else:
                    target.hardlink_to(temporary)
                break
            except FileExistsError:
                index += 1
    finally:
        temporary.unlink(missing_ok=True)
    return target


# ---------------------------------------------------------------------------
# 精灵导出
# ---------------------------------------------------------------------------

def export_sprites(
    bundle_path: Path,
    output_dir: Path,
    has_components: bool = False,
    progress_callback=None,
    cancel_check=None,
) -> Dict:
    """
    从 bundle 中提取所有精灵并保存为 PNG。

    Args:
        bundle_path:       bundle 文件路径
        output_dir:        输出根目录
        has_components:    角色是否拥有组件结构
        progress_callback: 可选进度回调 fn(current, total)
        cancel_check:      可选取消检查 fn() -> bool，返回 True 时抛 LoadCancelled

    Returns:
        {"files": [精灵记录...], "errors": [错误记录...], "count": 成功数量, "output_dir": 保存目录}
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
    errors = []

    for idx, obj in enumerate(sprite_objs):
        if cancel_check and cancel_check():
            raise LoadCancelled()
        try:
            data = obj.read()
            if not hasattr(data, "image") or data.image is None:
                raise ValueError("Sprite has no image")

            sprite_name = getattr(data, "m_Name", f"sprite_{obj.path_id}")
            file_path = save_png(data.image, save_dir, sprite_name, overwrite=True)

            results.append({
                "name": sprite_name,
                "path_id": obj.path_id,
                "file_path": str(file_path),
                "size": [data.image.size[0], data.image.size[1]],
            })
            log("info", _("log.exported_sprite", name=file_path.stem))
        except Exception as e:
            log("error", _("log.sprite_extract_failed", id=obj.path_id, e=e))
            errors.append({"path_id": obj.path_id, "message": str(e)})

        if progress_callback:
            progress_callback(idx + 1, total)

    log("info", _("log.export_done", file=bundle_path.name, count=len(results), dir=save_dir))
    return {"files": results, "errors": errors, "count": len(results), "output_dir": str(save_dir)}


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
    save_path = save_png(image, save_dir, f"{character_name}_composite")
    log("info", f"Composite saved to: {save_path}")
    return save_path


# ---------------------------------------------------------------------------
# 预览精灵导出
# ---------------------------------------------------------------------------

def export_preview_images(files: List[Path], output_dir: Path) -> Dict:
    """把已生成的预览 PNG 平铺导出，返回实际成功数量和错误（同名覆盖）。

    预览图已由后台提取并按名称落盘，这里复用角色精灵一致的安全命名与落盘逻辑。
    """
    count = 0
    errors = []
    for path in files:
        path = Path(path)
        try:
            with Image.open(path) as image:
                save_png(image, output_dir, path.stem, overwrite=True)
            count += 1
        except Exception as e:
            log("error", _("log.sprite_extract_failed", id=path.name, e=e))
            errors.append({"name": path.name, "message": str(e)})
    return {"count": count, "errors": errors, "output_dir": str(output_dir)}


# ---------------------------------------------------------------------------
# 背景 / 小素材导出
# ---------------------------------------------------------------------------

def export_backgrounds(bundles: list, output_dir: Path,
                       progress_callback=None, cancel_check=None,
                       staging_dir: Optional[Path] = None) -> dict:
    """按分类平铺导出背景/小素材的原始尺寸 PNG。

    每个来源只解析一次。整包导出优先取 Sprite，其次 Texture2D；小素材用
    type/ID 精确选择。单个来源/对象失败会记录错误，其余继续。
    分类目录名取自分类键（i18n 英文键），与界面语言无关。
    """
    import UnityPy

    files, errors = [], []
    sources = OrderedDict()
    for item in bundles:
        try:
            relative = PurePosixPath(item["id"])
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError("invalid asset id")
            sources.setdefault(item["bundle_path"], []).append(item)
        except Exception as exc:
            errors.append({"id": item.get("id", ""), "message": str(exc)})
    completed = len(errors)
    for source, items in sources.items():
        _check_cancel(cancel_check)
        env = None
        objects, images = [], []
        data = obj = None
        try:
            env = UnityPy.load(source)
            objects = list(env.objects)
            selectors = {(obj.type.name, str(obj.path_id)): obj for obj in objects}
            defaults = [obj for obj in objects if obj.type.name == "Sprite"]
            if not defaults:
                defaults = [obj for obj in objects if obj.type.name == "Texture2D"]
            for item in items:
                _check_cancel(cancel_check)
                try:
                    if "object_id" in item:
                        kind = item.get("asset_type")
                        if kind not in ("Sprite", "Texture2D"):
                            raise ValueError("invalid image type")
                        selected = selectors.get((kind, str(item["object_id"])))
                        images = [selected] if selected else []
                    else:
                        images = defaults
                    if not images:
                        raise ValueError(_("background.no_images"))
                    directory = output_dir / output_group_name(
                        item.get("output_group") or item.get("group"))
                    for obj in images:
                        _check_cancel(cancel_check)
                        image = None
                        try:
                            data = obj.read()
                            name = getattr(data, "m_Name", "") or f"image_{obj.path_id}"
                            image = data.image
                            if image is None:
                                raise ValueError(_("background.no_images"))
                            target = save_png(image, directory, name, staging_dir)
                            files.append({"id": item["id"], "name": name, "file_path": str(target),
                                          "size": list(image.size), "type": obj.type.name})
                        except LoadCancelled:
                            raise
                        except Exception as exc:
                            errors.append({"id": item["id"], "path_id": str(obj.path_id), "message": str(exc)})
                        finally:
                            if image is not None:
                                image.close()
                            prune_texture_cache(env)
                except LoadCancelled:
                    raise
                except Exception as exc:
                    errors.append({"id": item["id"], "message": str(exc)})
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(bundles))
        except LoadCancelled:
            raise
        except Exception as exc:
            for item in items:
                errors.append({"id": item["id"], "message": str(exc)})
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(bundles))
        finally:
            release_environment(env)
            # UnityPy readers can retain large buffers in reference cycles.
            env = None
            objects.clear()
            images.clear()
            selectors = defaults = None
            data = obj = selected = None
            gc.collect()
    return {"count": len(files), "files": files, "errors": errors,
            "output_dir": str(output_dir)}

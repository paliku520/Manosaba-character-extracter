"""Discover and export Naninovel backgrounds without loading character components."""

from __future__ import annotations

import gc
import os
import re
import tempfile
from pathlib import Path, PurePosixPath

import UnityPy

from src.bundle_loader import SKIP_DIRS
from src.compositor import LoadCancelled
from src.i18n import _


BACKGROUND_PATTERNS = (
    "manosaba_Data/StreamingAssets/aa/StandaloneWindows64/"
    "naninovel-backgrounds_assets_naninovel/backgrounds",
    "StreamingAssets/aa/StandaloneWindows64/naninovel-backgrounds_assets_naninovel/backgrounds",
    "aa/StandaloneWindows64/naninovel-backgrounds_assets_naninovel/backgrounds",
    "StandaloneWindows64/naninovel-backgrounds_assets_naninovel/backgrounds",
    "naninovel-backgrounds_assets_naninovel/backgrounds",
    "backgrounds",
)


def _check_cancel(cancel_check) -> None:
    if cancel_check and cancel_check():
        raise LoadCancelled()


def _natural_key(value: str) -> list:
    return [int(part) if part.isdigit() else part.casefold()
            for part in re.split(r"(\d+)", value)]


def find_backgrounds_dir(directory: Path, cancel_check=None) -> Path:
    """Accept the game root, an assets directory, backgrounds, or one of its groups."""
    root = directory.resolve()
    if not root.is_dir():
        raise ValueError(_("background.not_found", path=directory))
    for candidate in (root, *root.parents):
        _check_cancel(cancel_check)
        if candidate.name.casefold() == "backgrounds":
            return candidate
    for pattern in BACKGROUND_PATTERNS:
        target = root / pattern
        if target.is_dir():
            return target

    # Alternate Unity builds may use a different data/platform folder name.
    stack = [(root, 0)]
    while stack:
        _check_cancel(cancel_check)
        current, depth = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for child in children:
            _check_cancel(cancel_check)
            if not child.is_dir() or child.is_symlink():
                continue
            if child.name.casefold() == "backgrounds":
                return child
            if depth < 7 and not child.name.startswith(".") and child.name not in SKIP_DIRS:
                stack.append((child, depth + 1))
    # Prefer the selected subtree over unrelated siblings in ancestor folders.
    for ancestor in root.parents:
        _check_cancel(cancel_check)
        for pattern in BACKGROUND_PATTERNS:
            target = ancestor / pattern
            if target.is_dir():
                return target
    raise ValueError(_("background.not_found", path=directory))


def scan_backgrounds(directory: Path, cancel_check=None) -> dict:
    """List bundles by relative path; identical stems in different groups stay distinct."""
    root = find_backgrounds_dir(directory, cancel_check)
    bundles = []
    for path in root.rglob("*.bundle"):
        _check_cancel(cancel_check)
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        bundles.append({
            "id": relative.with_suffix("").as_posix(),
            "name": path.stem,
            "group": relative.parent.as_posix(),
            "bundle_path": str(path),
        })
    bundles.sort(key=lambda item: _natural_key(item["id"]))
    if not bundles:
        raise ValueError(_("background.no_bundles", path=root))
    return {"directory": str(root), "bundles": bundles, "count": len(bundles)}


def _safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(". ")
    if not name or name in (".", ".."):
        return "image"
    if name.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
    }:
        name = "_" + name
    return name[:160]


def _save_png(image, directory: Path, name: str, staging_dir: Path | None = None) -> Path:
    """Encode away from final PNGs so cancellation cannot leave an incomplete PNG."""
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(name)
    with tempfile.NamedTemporaryFile(dir=staging_dir or directory, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        image.save(temporary, format="PNG")
        index = 0
        while True:
            target = directory / f"{stem}{'_' + str(index) if index else ''}.png"
            try:
                # Windows rename and POSIX hard-link both refuse existing targets.
                if os.name == "nt":
                    temporary.rename(target)
                else:
                    target.hardlink_to(temporary)
                break
            except FileExistsError:
                index += 1
    finally:
        temporary.unlink(missing_ok=True)
    return target


def export_backgrounds(bundles: list[dict], output_dir: Path,
                       progress_callback=None, cancel_check=None, staging_dir: Path | None = None) -> dict:
    """Export native-size Sprites, falling back to Texture2D in sprite-less bundles.

    Sprite backing textures are intentionally not exported a second time. Bundles
    and objects that fail are reported while the rest of the batch continues.
    """
    files, errors = [], []
    for index, item in enumerate(bundles):
        _check_cancel(cancel_check)
        env = None
        objects, images = [], []
        data = obj = None
        try:
            relative = PurePosixPath(item["id"])
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError("invalid background id")
            target_dir = output_dir.joinpath(*(_safe_name(p) for p in relative.parts))
            env = UnityPy.load(item["bundle_path"])
            objects = list(env.objects)
            images = [obj for obj in objects if obj.type.name == "Sprite"]
            if not images:
                images = [obj for obj in objects if obj.type.name == "Texture2D"]
            if not images:
                raise ValueError(_("background.no_images"))
            for obj in images:
                _check_cancel(cancel_check)
                image = None
                try:
                    data = obj.read()
                    name = getattr(data, "m_Name", "") or f"image_{obj.path_id}"
                    image = data.image
                    if image is None:
                        raise ValueError(_("background.no_images"))
                    target = _save_png(image, target_dir, name, staging_dir)
                    files.append({"id": item["id"], "name": name, "file_path": str(target),
                                  "size": list(image.size), "type": obj.type.name})
                except LoadCancelled:
                    raise
                except Exception as exc:
                    errors.append({"id": item["id"], "path_id": obj.path_id, "message": str(exc)})
                finally:
                    if image is not None:
                        image.close()
        except LoadCancelled:
            raise
        except Exception as exc:
            errors.append({"id": item["id"], "message": str(exc)})
        finally:
            if env is not None:
                env.files.clear()
            # UnityPy readers can retain large buffers in reference cycles.
            env = None
            objects.clear()
            images.clear()
            data = obj = None
            gc.collect()
        if progress_callback:
            progress_callback(index + 1, len(bundles))
    return {"count": len(files), "files": files, "errors": errors,
            "output_dir": str(output_dir)}

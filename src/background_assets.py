"""Discover and export Naninovel backgrounds without loading character components."""

from __future__ import annotations

import base64
import gc
import hashlib
import io
import json
import os
import re
import tempfile
from collections import OrderedDict
from pathlib import Path, PurePosixPath

import UnityPy
from PIL import Image

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


class BackgroundPreviewCache:
    """Bound preview memory with LRU eviction; changed source files get new keys."""

    def __init__(self, max_bytes: int = 64 * 1024 * 1024, directory: Path | None = None):
        self.max_bytes = max_bytes
        self.directory = directory
        self._entries = OrderedDict()
        self._bytes = 0

    @staticmethod
    def key(path: Path, max_side: int = 1280) -> tuple:
        path = path.resolve()
        stat = path.stat()
        return (str(path), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, max_side)

    def get(self, key: tuple) -> dict | None:
        entry = self._entries.get(key)
        if entry is not None:
            self._entries.move_to_end(key)
            return entry[0].copy()
        if self.directory is not None:
            png, metadata = self._disk_paths(key)
            try:
                stored = json.loads(metadata.read_text(encoding="utf-8"))
                if stored["key"] != list(key):
                    return None
                result = stored["preview"]
                if (not isinstance(result["name"], str) or len(result["size"]) != 2
                        or not all(isinstance(n, int) and n > 0 for n in result["size"])
                        or not isinstance(result["count"], int) or result["count"] < 1):
                    return None
                data = png.read_bytes()
                with Image.open(io.BytesIO(data)) as image:
                    if image.format != "PNG" or max(image.size) > key[-1]:
                        return None
                    image.verify()
                result["data_url"] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
                self._remember(key, result)
                return result.copy()
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Missing, stale or corrupt cache entries are decoded again.
        return None

    def put(self, key: tuple, result: dict) -> None:
        if self.directory is not None:
            png, metadata = self._disk_paths(key)
            data = base64.b64decode(result["data_url"].split(",", 1)[1], validate=True)
            stored = {"key": list(key), "preview": {k: v for k, v in result.items() if k != "data_url"}}
            self._write_atomic(png, data)
            self._write_atomic(metadata, json.dumps(stored, ensure_ascii=False).encode("utf-8"))
        self._remember(key, result)

    def _disk_paths(self, key: tuple) -> tuple[Path, Path]:
        # Overwrite older source versions, keeping one thumbnail per source/size.
        digest = hashlib.sha256(json.dumps([1, key[0], key[-1]]).encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.png", self.directory / f"{digest}.json"

    @staticmethod
    def _write_atomic(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _remember(self, key: tuple, result: dict) -> None:
        # Drop older versions of this bundle rather than retaining stale previews.
        for old_key in list(self._entries):
            if old_key[0] == key[0]:
                self._bytes -= self._entries.pop(old_key)[1]
        size = len(result["data_url"]) + len(result.get("name", "").encode("utf-8"))
        if size > self.max_bytes:
            return
        while self._entries and self._bytes + size > self.max_bytes:
            _, (_, old_size) = self._entries.popitem(last=False)
            self._bytes -= old_size
        self._entries[key] = (result.copy(), size)
        self._bytes += size

    def clear(self) -> None:
        self._entries.clear()
        self._bytes = 0


def preview_background(bundle_path: Path, max_side: int = 1280, cancel_check=None) -> dict:
    """Decode the first usable image and encode only its in-memory thumbnail."""
    if max_side < 1:
        raise ValueError("invalid preview size")
    _check_cancel(cancel_check)
    env = UnityPy.load(str(bundle_path))
    objects, images = [], []
    obj = data = None
    errors = []
    try:
        objects = list(env.objects)
        images = [obj for obj in objects if obj.type.name == "Sprite"]
        if not images:
            images = [obj for obj in objects if obj.type.name == "Texture2D"]
        for obj in images:
            _check_cancel(cancel_check)
            image = None
            try:
                data = obj.read()
                image = data.image
                if image is None:
                    raise ValueError(_("background.no_images"))
                size = list(image.size)
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                _check_cancel(cancel_check)
                with io.BytesIO() as stream:
                    image.save(stream, format="PNG")
                    url = "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")
                return {"name": getattr(data, "m_Name", "") or f"image_{obj.path_id}",
                        "size": size, "data_url": url, "count": len(images)}
            except LoadCancelled:
                raise
            except Exception as exc:
                errors.append(str(exc))
            finally:
                if image is not None:
                    image.close()
        raise ValueError("\n".join(errors) or _("background.no_images"))
    finally:
        env.files.clear()
        objects.clear()
        images.clear()
        obj = data = env = None
        gc.collect()


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
                    target = _save_png(image, output_dir, name, staging_dir)
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

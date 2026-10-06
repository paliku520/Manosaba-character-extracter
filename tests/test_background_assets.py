"""Background discovery/export regression tests; no game assets are required."""

import base64
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from src.background_assets import (
    BackgroundPreviewCache, export_backgrounds, find_backgrounds_dir,
    preview_background, scan_backgrounds,
)
from src.compositor import LoadCancelled


def image_object(kind="Sprite", name="Background", size=(12, 6), path_id=1, error=None):
    def read():
        if error:
            raise ValueError(error)
        return SimpleNamespace(m_Name=name, image=Image.new("RGBA", size, (12, 34, 56, 78)))
    return SimpleNamespace(type=SimpleNamespace(name=kind), path_id=path_id, read=read)


def environment(*objects):
    return SimpleNamespace(objects=list(objects), files={})


class BackgroundAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.backgrounds = self.root / (
            "manosaba_Data/StreamingAssets/aa/StandaloneWindows64/"
            "naninovel-backgrounds_assets_naninovel/backgrounds"
        )
        self.backgrounds.mkdir(parents=True)
        self.output = self.root / "export"

    def tearDown(self):
        self.temporary.cleanup()

    def bundle(self, relative):
        path = self.backgrounds / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test bundle")
        return path

    def item(self, relative="mainbackground/1.bundle"):
        path = self.bundle(relative)
        return {"id": path.relative_to(self.backgrounds).with_suffix("").as_posix(),
                "bundle_path": str(path)}

    def test_find_from_game_root_assets_and_category(self):
        group = self.backgrounds / "mainbackground"
        group.mkdir()
        for path in (self.root, self.root / "manosaba_Data", self.backgrounds.parent,
                     self.backgrounds, group):
            with self.subTest(path=path):
                self.assertEqual(find_backgrounds_dir(path), self.backgrounds)

    def test_alternate_unity_data_folder(self):
        path = self.root / "alternative" / "OtherGame_Data" / "assets" / "backgrounds"
        path.mkdir(parents=True)
        self.assertEqual(find_backgrounds_dir(path.parent.parent), path)

    def test_scan_preserves_groups_duplicate_stems_and_natural_order(self):
        for name in ("mainbackground/10.bundle", "mainbackground/2.bundle", "stills/2.bundle"):
            self.bundle(name)
        result = scan_backgrounds(self.root)
        self.assertEqual([b["id"] for b in result["bundles"]],
                         ["mainbackground/2", "mainbackground/10", "stills/2"])
        self.assertEqual(result["count"], 3)

    def test_missing_and_empty_directories_report_failure(self):
        with self.assertRaises(ValueError):
            scan_backgrounds(self.root / "missing")
        with self.assertRaises(ValueError):
            scan_backgrounds(self.backgrounds)

    def test_cancel_directory_scan(self):
        with self.assertRaises(LoadCancelled):
            scan_backgrounds(self.root, cancel_check=lambda: True)

    @patch("src.background_assets.UnityPy.load")
    def test_sprite_export_preserves_pixels_and_avoids_backing_texture(self, load):
        load.return_value = environment(image_object(), image_object("Texture2D"))
        result = export_backgrounds([self.item()], self.output)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["files"][0]["type"], "Sprite")
        self.assertEqual(Path(result["files"][0]["file_path"]).parent, self.output)
        with Image.open(result["files"][0]["file_path"]) as image:
            self.assertEqual(image.size, (12, 6))
            self.assertEqual(image.getpixel((0, 0)), (12, 34, 56, 78))

    @patch("src.background_assets.UnityPy.load")
    def test_texture_only_bundle(self, load):
        load.return_value = environment(image_object("Texture2D", size=(32, 16)))
        result = export_backgrounds([self.item()], self.output)
        self.assertEqual(result["files"][0]["type"], "Texture2D")
        self.assertEqual(result["files"][0]["size"], [32, 16])

    @patch("src.background_assets.UnityPy.load")
    def test_export_does_not_overwrite_existing_or_duplicate_names(self, load):
        load.side_effect = lambda _: environment(image_object(name="CON"), image_object(name="CON"))
        item = self.item()
        first = export_backgrounds([item], self.output)
        again = export_backgrounds([item], self.output)
        paths = [f["file_path"] for f in first["files"] + again["files"]]
        self.assertEqual(len(set(paths)), 4)
        self.assertTrue(all(Path(p).name.startswith("_CON") for p in paths))
        self.assertTrue(all(Path(p).is_file() for p in paths))
        self.assertTrue(all(Path(p).parent == self.output for p in paths))
        # Identical image names from another category share the same flat directory.
        other = export_backgrounds([self.item("stills/1.bundle")], self.output)
        self.assertEqual(Path(other["files"][0]["file_path"]), self.output / "_CON_4.png")
        self.assertFalse(any(path.is_dir() for path in self.output.iterdir()))

    @patch("src.background_assets.UnityPy.load")
    def test_bad_bundle_and_object_do_not_abort_batch(self, load):
        load.side_effect = [ValueError("corrupt bundle"),
                            environment(image_object(error="bad sprite"), image_object(path_id=2))]
        progress = []
        result = export_backgrounds([self.item("stills/1.bundle"), self.item("tricks/1.bundle")],
                                    self.output, progress_callback=lambda a, b: progress.append((a, b)))
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(progress, [(1, 2), (2, 2)])

    @patch("src.background_assets.UnityPy.load", return_value=environment())
    def test_bundle_without_images_reports_error(self, load):
        result = export_backgrounds([self.item()], self.output)
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["errors"]), 1)

    @patch("src.background_assets.UnityPy.load")
    def test_cancel_between_bundles_preserves_finished_png(self, load):
        load.side_effect = lambda _: environment(image_object())
        cancelled = [False]
        with self.assertRaises(LoadCancelled):
            export_backgrounds([self.item("mainbackground/1.bundle"), self.item("mainbackground/2.bundle")],
                               self.output, cancel_check=lambda: cancelled[0],
                               progress_callback=lambda *_: cancelled.__setitem__(0, True))
        files = list(self.output.rglob("*.png"))
        self.assertEqual(len(files), 1)
        with Image.open(files[0]) as image:
            image.verify()

    @patch("src.background_assets.UnityPy.load")
    def test_invalid_relative_id_cannot_escape_output(self, load):
        result = export_backgrounds([{"id": "../outside", "bundle_path": "test"}], self.output)
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["errors"]), 1)
        load.assert_not_called()

    @patch("src.background_assets.UnityPy.load")
    def test_failed_png_encoding_leaves_no_output_or_staging_file(self, load):
        load.return_value = environment(image_object())
        staging = self.root / "staging"
        staging.mkdir()
        with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
            result = export_backgrounds([self.item()], self.output, staging_dir=staging)
        self.assertEqual(result["count"], 0)
        self.assertEqual(list(self.output.rglob("*.png")), [])
        self.assertEqual(list(staging.iterdir()), [])

    @patch("src.background_assets.UnityPy.load")
    def test_preview_resizes_in_memory_and_decodes_only_first_sprite(self, load):
        unused = image_object(path_id=2)
        unused.read = Mock(side_effect=AssertionError("unnecessary decode"))
        load.return_value = environment(image_object(size=(2560, 1280)), unused,
                                        image_object("Texture2D"))
        original_save = Image.Image.save
        destinations = []
        def save_preview(image, target, **kwargs):
            destinations.append(target)
            return original_save(image, target, **kwargs)
        with patch.object(Image.Image, "save", new=save_preview):
            result = preview_background(self.bundle("mainbackground/1.bundle"))
        self.assertEqual(result["size"], [2560, 1280])
        self.assertEqual(result["count"], 2)
        self.assertTrue(all(isinstance(target, io.BytesIO) for target in destinations))
        unused.read.assert_not_called()
        with Image.open(io.BytesIO(base64.b64decode(result["data_url"].split(",", 1)[1]))) as image:
            self.assertEqual(image.size, (1280, 640))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 78)
        self.assertFalse(self.output.exists())

    @patch("src.background_assets.UnityPy.load")
    def test_preview_falls_back_to_texture_or_next_usable_sprite(self, load):
        load.return_value = environment(image_object("Texture2D", size=(32, 16)))
        result = preview_background(self.bundle("mainbackground/1.bundle"))
        self.assertEqual(result["size"], [32, 16])
        load.return_value = environment(image_object(error="corrupt"), image_object(name="usable"))
        self.assertEqual(preview_background(Path("test.bundle"))["name"], "usable")
        load.return_value = environment()
        with self.assertRaises(ValueError):
            preview_background(Path("test.bundle"))

    @patch("src.background_assets.UnityPy.load")
    def test_preview_cancel_releases_unity_data(self, load):
        env = environment(image_object())
        env.files["bundle"] = object()
        load.return_value = env
        calls = iter((False, True))
        with self.assertRaises(LoadCancelled):
            preview_background(Path("test.bundle"), cancel_check=lambda: next(calls))
        self.assertEqual(env.files, {})

    def test_preview_cache_lru_limit_and_source_invalidation(self):
        cache = BackgroundPreviewCache(max_bytes=20)
        paths = [self.bundle(f"mainbackground/{i}.bundle") for i in range(3)]
        keys = [cache.key(path) for path in paths]
        value = {"data_url": "1234567890", "name": ""}
        cache.put(keys[0], value)
        cache.put(keys[1], value)
        self.assertEqual(cache.get(keys[0]), value)  # Refresh recency.
        cache.put(keys[2], value)
        self.assertIsNone(cache.get(keys[1]))
        paths[0].write_bytes(b"changed source")
        changed = cache.key(paths[0])
        self.assertNotEqual(changed, keys[0])
        self.assertIsNone(cache.get(changed))
        cache.put(changed, value)
        self.assertIsNone(cache.get(keys[0]))
        cache.put(changed, {"data_url": "x" * 21})
        self.assertIsNone(cache.get(changed))
        self.assertLessEqual(cache._bytes, cache.max_bytes)
        cache.clear()
        self.assertEqual(cache._bytes, 0)

    def cached_preview(self):
        with Image.new("RGBA", (16, 8), (12, 34, 56, 78)) as image, io.BytesIO() as stream:
            image.save(stream, format="PNG")
            return {"name": "sample", "size": [4096, 2048], "count": 1,
                    "data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")}

    def test_disk_cache_retains_all_entries_beyond_memory_limit_and_across_restart(self):
        directory = self.root / "cache"
        cache = BackgroundPreviewCache(max_bytes=1, directory=directory)
        keys = [cache.key(self.bundle(f"mainbackground/{i}.bundle")) for i in range(3)]
        value = self.cached_preview()
        for key in keys:
            cache.put(key, value)
        self.assertEqual(cache._bytes, 0)
        restarted = BackgroundPreviewCache(directory=directory)
        for key in keys:
            self.assertEqual(restarted.get(key), value)
        self.assertEqual(len(list(directory.glob("*.png"))), 3)
        self.assertEqual(list(directory.glob("*.tmp")), [])

    def test_disk_cache_invalidates_changed_sources_without_accumulating_old_versions(self):
        path = self.bundle("mainbackground/1.bundle")
        cache = BackgroundPreviewCache(directory=self.root / "cache")
        key = cache.key(path)
        value = self.cached_preview()
        cache.put(key, value)
        path.write_bytes(b"updated bundle")
        changed = cache.key(path)
        cache.clear()
        self.assertIsNone(cache.get(changed))
        cache.put(changed, value)
        cache.clear()
        self.assertEqual(cache.get(changed), value)
        self.assertEqual(len(list(cache.directory.glob("*.png"))), 1)

    def test_corrupt_disk_cache_is_a_miss_and_failed_write_cleans_temporary_files(self):
        cache = BackgroundPreviewCache(directory=self.root / "cache")
        key = cache.key(self.bundle("mainbackground/1.bundle"))
        value = self.cached_preview()
        cache.put(key, value)
        cache.clear()
        png, metadata = cache._disk_paths(key)
        png.write_bytes(b"broken png")
        self.assertIsNone(cache.get(key))
        cache.put(key, value)
        cache.clear()
        metadata.write_text("[]", encoding="utf-8")
        self.assertIsNone(cache.get(key))
        with patch("src.background_assets.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                cache.put(key, value)
        self.assertEqual(list(cache.directory.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()

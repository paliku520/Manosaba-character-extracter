"""Background discovery/export regression tests; no game assets are required."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from src.background_assets import export_backgrounds, find_backgrounds_dir, scan_backgrounds
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


if __name__ == "__main__":
    unittest.main()

"""Regression tests run exclusively in temporary directories; no game files required."""
import atexit
import base64
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_runtime = tempfile.TemporaryDirectory(prefix="mce-tests-")
atexit.register(_runtime.cleanup)
os.environ["MCE_DATA_DIR"] = _runtime.name
from PIL import Image
import run
from src import cache_manager, export_manager, preset_store, settings, shell_open


class Regressions(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=_runtime.name)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.obj = object.__new__(run.JsApi)
        obj = self.obj
        obj._char_gen = obj._composite_gen = obj._export_count = 0
        obj._char_busy = False
        obj._character_data = obj._composite_image = obj._preview_sprites = None
        obj._part_compositor = None
        obj._compositor = SimpleNamespace(clear_cache=lambda: None)
        obj._temp_dir, obj._output_dir = self.root / "temp", self.root / "output"
        self.source = self.root / "sample.bundle"
        self.source.write_bytes(b"source")
        obj._bundles = {"sample": str(self.source), "anan": str(self.source)}
        obj._state_lock = threading.RLock()
        obj._cache_ready = threading.Event()
        obj._cache_ready.set()
        obj._cache_clear_pending = 0
        obj._work_lock = threading.Lock()
        obj._composite_lock = threading.Lock()
        obj._background_cancel = threading.Event()
        obj._background_preview_cache = SimpleNamespace(clear=lambda: None)
        obj._data_summary = lambda data: data
        obj._preview_max_side = lambda: 0
        obj.events, obj.threads, self.thread_errors = [], [], []
        obj._emit = lambda event, payload: obj.events.append((event, payload))
        def launch(fn):
            def checked():
                try:
                    fn()
                except BaseException as error:
                    self.thread_errors.append(error)
            thread = threading.Thread(target=checked, daemon=True)
            obj.threads.append(thread)
            thread.start()
        obj._run_async = launch
        self.addCleanup(patch.stopall)
        patch.object(settings, 'CONFIG_FILE', self.root / 'data/settings.json').start()

    def join(self):
        for thread in self.obj.threads:
            thread.join(5)
            self.assertFalse(thread.is_alive(), 'worker did not finish')
        self.assertEqual(self.thread_errors, [])

    def cached_data(self):
        sprites = self.obj._temp_dir / 'sample/sprites'
        sprites.mkdir(parents=True)
        image = sprites / 'part.png'
        Image.new('RGBA', (2, 2), 'red').save(image)
        return {'character_name': 'sample', 'transform_data': [{'name': 'Old', 'sprite_path': str(image)}]}

    def test_cancel_while_reading_cache_does_not_restore_character(self):
        entered, release = threading.Event(), threading.Event()
        data = self.cached_data()
        def delayed(*args):
            entered.set()
            self.assertTrue(release.wait(5))
            return data
        with patch.object(run, 'load_extracted_data', delayed):
            try:
                self.obj.start_composite_mode('sample')
                self.assertTrue(entered.wait(5))
                self.obj.cancel_character_load()
            finally:
                release.set()
            self.join()
        self.assertIsNone(self.obj._character_data)
        self.assertFalse(any(event == 'data_ready' for event, _ in self.obj.events))

    def test_cancel_after_extraction_before_save_does_not_publish(self):
        entered, release = threading.Event(), threading.Event()
        def extract(*args):
            entered.set()
            self.assertTrue(release.wait(5))
            return {'character_name': 'sample', 'transform_data': []}
        with patch.object(self.obj, '_extract_via_worker', extract), patch.object(run, 'save_extracted_data') as save:
            try:
                self.obj.start_composite_mode('sample')
                self.assertTrue(entered.wait(5))
                self.obj.cancel_character_load()
            finally:
                release.set()
            self.join()
            save.assert_not_called()
        self.assertFalse(any(event == 'data_ready' for event, _ in self.obj.events))

    def test_queued_cancelled_load_never_starts(self):
        tasks = []
        self.obj._run_async = tasks.append
        self.obj.start_composite_mode('sample')
        self.obj.cancel_character_load()
        with patch.object(run, 'load_extracted_data') as cache:
            for task in tasks:
                task()
            cache.assert_not_called()
        self.assertEqual(self.obj.events, [])

    def test_cache_checks_source_changes_and_source_path(self):
        data = self.cached_data()
        cache_manager.save_extracted_data(data, self.obj._temp_dir, 'sample', self.source)
        self.assertIsNotNone(cache_manager.load_extracted_data(self.obj._temp_dir, 'sample', self.source))
        alternative = self.root / 'different.bundle'
        alternative.write_bytes(b'source')
        self.assertIsNone(cache_manager.load_extracted_data(self.obj._temp_dir, 'sample', alternative))
        self.source.write_bytes(b'updated source')
        self.assertIsNone(cache_manager.load_extracted_data(self.obj._temp_dir, 'sample', self.source))

    def test_legacy_cache_reextracts_and_current_cache_reuses(self):
        data = self.cached_data()
        cache_manager.save_extracted_data(data, self.obj._temp_dir, 'sample')
        with patch.object(self.obj, '_extract_via_worker', return_value=data) as extract:
            self.obj.start_composite_mode('sample')
            self.join()
            extract.assert_called_once()
            self.obj.start_composite_mode('sample')
            self.join()
            extract.assert_called_once()
        self.assertEqual(sum(e == 'data_ready' for e, _ in self.obj.events), 2)

    def test_clear_cache_finishes_before_new_load_commits(self):
        entered, release = threading.Event(), threading.Event()
        data = {'character_name': 'sample', 'transform_data': []}
        def deletion(*args, **kwargs):
            self.assertTrue(self.obj._work_lock.locked())
            entered.set()
            self.assertTrue(release.wait(5))
        with patch.object(run.shutil, 'rmtree', deletion), patch.object(run, 'load_extracted_data', return_value=data):
            try:
                self.obj.clear_cache()
                self.assertTrue(entered.wait(5))
                self.obj.start_composite_mode('sample')
                self.assertFalse(any(e == 'data_ready' for e, _ in self.obj.events))
            finally:
                release.set()
            self.join()
        events = [e for e, _ in self.obj.events]
        self.assertLess(events.index('cache_cleared'), events.index('data_ready'))
        self.assertIs(self.obj._character_data, data)

    def test_clear_cache_removes_disk_previews_but_preserves_presets(self):
        self.obj._temp_dir.mkdir()
        (self.obj._temp_dir / 'thumbnail.json').write_text('{}')
        preset = self.root / 'data/presets/custom.json'
        preset.parent.mkdir(parents=True)
        preset.write_text('{}')
        self.obj.clear_cache()
        self.join()
        self.assertFalse(self.obj._temp_dir.exists())
        self.assertTrue(preset.exists())

    def test_load_waits_even_when_clear_worker_has_not_started(self):
        tasks = []
        self.obj._run_async = tasks.append
        self.obj.clear_cache()
        self.obj.start_composite_mode('sample')
        ready = threading.Event()
        data = {'character_name': 'sample', 'transform_data': []}
        def load(*args):
            ready.set()
            return data
        with patch.object(run, 'load_extracted_data', load):
            thread = threading.Thread(target=tasks[1], daemon=True)
            thread.start()
            try:
                self.assertFalse(ready.wait(.05))
            finally:
                tasks[0]()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertIs(self.obj._character_data, data)

    def test_cancel_during_thumbnail_encoding_drops_old_thumbnail_map(self):
        self.obj._character_data = self.cached_data()
        def thumbnail(*args, **kwargs):
            self.obj.cancel_character_load()
            return 'old-thumbnail'
        with patch.object(run, '_sprite_thumb_data_url', thumbnail):
            self.obj.get_thumbnails()
            self.join()
        self.assertFalse(any(e == 'thumbnails_ready' for e, _ in self.obj.events))

    def test_settings_concurrent_read_modify_write_keeps_all_updates(self):
        settings.save_settings(theme='dark', export_count=0)
        write = settings._write_settings
        entered, release, theme_done = threading.Event(), threading.Event(), threading.Event()
        errors = []
        def delayed(data):
            if threading.current_thread().name == 'counter':
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('writer timed out')
            write(data)
        def change_theme():
            try:
                settings.save_settings(theme='light')
                theme_done.set()
            except Exception as error:
                errors.append(error)
        with patch.object(settings, '_write_settings', delayed):
            counter = threading.Thread(target=lambda: settings.save_settings(export_count=1), name='counter')
            theme = threading.Thread(target=change_theme)
            try:
                counter.start()
                self.assertTrue(entered.wait(5))
                theme.start()
                self.assertFalse(theme_done.wait(.05))
            finally:
                release.set()
                counter.join(5)
                if theme.ident is not None:
                    theme.join(5)
        self.assertFalse(counter.is_alive() or theme.is_alive())
        self.assertEqual(errors, [])
        actual = settings.load_settings()['global']
        self.assertEqual((actual['theme'], actual['export_count']), ('light', 1))
        self.obj.save_native_settings({'width': 1200, 'height': 700, 'maximized': True}, str(self.root))
        actual = settings.load_settings()
        self.assertEqual(actual['global']['theme'], 'light')
        self.assertEqual(actual['global']['window']['width'], 1200)
        self.assertEqual(actual['game']['manosaba']['last_directory'], str(self.root))

    def test_settings_failed_replace_preserves_original_file(self):
        settings.save_settings(theme='dark')
        before = settings.CONFIG_FILE.read_bytes()
        with patch.object(settings.os, 'replace', side_effect=OSError('disk full')):
            settings.save_settings(theme='light')
        self.assertEqual(settings.CONFIG_FILE.read_bytes(), before)
        self.assertEqual(list(settings.CONFIG_FILE.parent.glob('.settings-*.tmp')), [])

    def test_failed_and_partial_exports_report_actual_results(self):
        image = Image.new('RGBA', (2, 2), 'red')
        objects = [SimpleNamespace(type=SimpleNamespace(name='Sprite'), path_id=n,
                                  read=lambda: SimpleNamespace(image=image, m_Name='part')) for n in (1, 2)]
        env = SimpleNamespace(objects=objects)
        for saved, expected_count in [(OSError('disk full'), 0), ([self.root / 'ok.png', OSError('disk full')], 1)]:
            with self.subTest(count=expected_count), patch('UnityPy.load', return_value=env), \
                    patch.object(export_manager, 'save_png', side_effect=saved):
                result = export_manager.export_sprites(self.source, self.root / 'export')
            self.assertEqual(result['count'], expected_count)
            self.assertTrue(result['errors'])
            self.obj.events.clear()
            with patch.object(self.obj, '_extract_via_worker', return_value=result):
                self.obj.export_sprites('sample', True)
                self.join()
            self.assertFalse(any(e == 'export_complete' for e, _ in self.obj.events))
            payload = next(p for e, p in self.obj.events if e == 'export_error')
            self.assertEqual(payload['count'], expected_count)
            self.assertEqual(payload['export_count'], expected_count)

    def test_empty_export_does_not_increment_success_count(self):
        self.obj._finish_export('sample', {'count': 0, 'errors': [], 'output_dir': str(self.root)})
        self.assertEqual(self.obj._export_count, 0)
        self.assertEqual(self.obj.events[-1][0], 'export_error')

    def test_preview_export_reports_failure_and_success(self):
        source = self.root / 'preview.png'
        Image.new('RGBA', (3, 4), 'red').save(source)
        with patch.object(export_manager, 'save_png', side_effect=OSError('disk full')):
            failed = export_manager.export_preview_images([source], self.root / 'failed')
        self.assertEqual(failed['count'], 0)
        self.assertTrue(failed['errors'])
        good = export_manager.export_preview_images([source], self.root / 'good')
        self.assertEqual(good['count'], 1)
        self.assertFalse(good['errors'])
        with Image.open(self.root / 'good/preview.png') as image:
            self.assertEqual(image.size, (3, 4))

    def test_older_encoding_cannot_overwrite_new_preview_or_shared_canvas(self):
        self.obj._character_data = {'transform_data': [{}]}
        canvas = Image.new('RGBA', (2, 2))
        def composite(*args, selected_names, **kwargs):
            canvas.paste('red' if selected_names == ['old'] else 'blue', (0, 0, 2, 2))
            return canvas
        self.obj._compositor = SimpleNamespace(composite=composite)
        encode = run._pil_preview
        entered, release = threading.Event(), threading.Event()
        old_pixels = []
        def delayed(image, **kwargs):
            if image.getpixel((0, 0)) == (255, 0, 0, 255):
                entered.set()
                self.assertTrue(release.wait(5))
                old_pixels.append(image.getpixel((0, 0)))
            return encode(image, **kwargs)
        with patch.object(run, '_pil_preview', delayed):
            try:
                self.obj.composite(['old'])
                self.assertTrue(entered.wait(5))
                self.obj.composite(['new'])
                self.obj.threads[-1].join(5)
            finally:
                release.set()
            self.join()
        self.assertEqual(old_pixels, [(255, 0, 0, 255)])
        self.assertEqual(sum(e == 'composite_done' for e, _ in self.obj.events), 1)
        self.assertEqual(self.obj._composite_image.getpixel((0, 0)), (0, 0, 255, 255))

    def test_composite_order_uses_submission_not_thread_start_order(self):
        self.obj._character_data = {'transform_data': [{}]}
        calls, tasks = [], []
        def composite(*args, selected_names, **kwargs):
            calls.append(selected_names)
            return Image.new('RGBA', (2, 2), 'red')
        self.obj._compositor = SimpleNamespace(composite=composite)
        self.obj._run_async = tasks.append
        self.obj.composite(['old'])
        self.obj.composite(['new'])
        for task in reversed(tasks):
            task()
        self.assertEqual(calls, [['new']])

    def test_cancel_during_composite_encoding_suppresses_result(self):
        self.obj._character_data = {'transform_data': [{}]}
        self.obj._compositor = SimpleNamespace(composite=lambda *a, **kw: Image.new('RGBA', (2, 2), 'red'))
        def cancelled(image, **kwargs):
            self.obj.cancel_character_load()
            return 'old', [2, 2]
        with patch.object(run, '_pil_preview', cancelled):
            self.obj.composite(['part'])
            self.join()
        self.assertFalse(any(e == 'composite_done' for e, _ in self.obj.events))
        self.assertIsNone(self.obj._composite_image)

    def test_thumbnail_preserves_rgba_opacity(self):
        source = self.root / 'alpha.png'
        Image.new('RGBA', (2, 2), (255, 0, 0, 128)).save(source)
        url = run._sprite_thumb_data_url(source, (2, 2))
        with Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))) as image:
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 128))

    def test_repeat_reveal_does_not_hold_global_lock_during_window_lookup(self):
        key = 'regression-reveal'
        shell_open._recent[key] = shell_open.time.monotonic()
        calls = []
        def windows(*args):
            acquired = shell_open._lock.acquire(timeout=.5)
            self.assertTrue(acquired)
            if acquired:
                shell_open._lock.release()
            calls.append(args)
            return None
        with patch.object(shell_open, '_cached_window', windows), patch.object(shell_open, '_find_window', return_value=None):
            shell_open._reveal_worker(str(self.root / 'sample.png'), key)
        self.assertEqual(len(calls), 1)
        shell_open._recent.pop(key, None)

    def test_json_preset_sketch_roundtrip_and_validation(self):
        self.obj._character_data = {'character_name': 'anan', 'transform_data': [{'name': 'Arms01', 'sorting_order': 1}]}
        with patch.object(preset_store, 'get_presets_dir', return_value=self.root / 'presets'):
            sketch = {'text': 'Keep this text', 'size': 72, 'align': 'right'}
            result = self.obj.import_preset('anan', 'Roundtrip', None, [{'name': 'Arms01'}], 'manosaba', False, sketch)
            self.assertTrue(result['success'])
            self.assertEqual(result['preset']['sketch'], sketch)
            loaded = preset_store.load_presets('anan')['Roundtrip']
            self.assertEqual(loaded['sketch'], sketch)
            result = self.obj.import_preset('anan', 'Roundtrip', None, [{'name': 'Arms01'}], 'manosaba', True,
                                            {'size': 999999, 'align': 'invalid'})
            self.assertTrue(result['success'])
            self.assertEqual(result['preset']['sketch']['align'], 'center')
            self.assertLess(result['preset']['sketch']['size'], 999999)


if __name__ == '__main__':
    unittest.main()

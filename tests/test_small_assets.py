"""Small image catalog, atlas de-duplication, selectors and native PNG regression tests."""

import base64
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from PIL import Image

from run import JsApi
from src.background_assets import BackgroundPreviewCache, export_backgrounds, prune_texture_cache
from src.compositor import LoadCancelled
from src.small_assets import SmallAssetPreviewer, classify_asset, find_small_asset_sources, scan_small_assets


def pointer(path_id=0):
    return NS(path_id=path_id, file_id=0)


def reader(kind, name, path_id, texture=0, atlas=None):
    def read():
        return NS(m_Name=name, m_Width=12, m_Height=6, m_Rect=NS(width=12, height=6),
                  m_RD=NS(texture=pointer(texture), alphaTexture=pointer()),
                  m_SpriteAtlas=atlas, m_RenderDataKey='key',
                  image=Image.new('RGBA', (12, 6), (12, 34, 56, 78)))
    return NS(type=NS(name=kind), path_id=path_id, read=read)


def environment(*objects):
    return NS(objects=list(objects), files={'source': object()}, assets=[])


class SmallAssetsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.data = self.root / 'manosaba_Data'
        self.platform = self.data / 'StreamingAssets/aa/StandaloneWindows64'
        self.backgrounds = self.platform / 'naninovel-backgrounds_assets_naninovel/backgrounds'
        (self.backgrounds / 'mainbackground').mkdir(parents=True)
        self.source = self.platform / 'general-sprites_assets_all.bundle'
        self.source.write_bytes(b'bundle')

    def item(self, kind='Sprite', path_id=1, group='界面素材'):
        return {'id': f'small/{kind}/{path_id}', 'asset_type': kind, 'object_id': str(path_id),
                'bundle_path': str(self.source), 'output_group': group}

    def test_classifies_sources_and_stage_images_including_unknowns(self):
        cases = [
            ('general-witchbook', 'Clue_001_013', 'evidence'),
            ('general-witchbook', 'Profile_001', 'profiles'),
            ('general-sprites', 'Button', 'interface'),
            ('general-transitions', 'wipe', 'transitions'),
            ('general-prefabs', 'noise', 'effect_textures'),
            ('naninovel-spawn', 'Map_Background', 'maps'),
            ('naninovel-spawn', 'Pin_Ema', 'maps'),
            ('naninovel-spawn', 'Noa_Background', 'stage_backgrounds'),
            ('naninovel-spawn', 'Hiro_CutIn_001', 'stage_effects'),
            ('naninovel-spawn', '1-2-3_Smartphone', 'stage_props'),
            ('naninovel-spawn', '2-4-2_Ema', 'stage_characters'),
            ('naninovel-spawn', 'kari_1-1-2', 'stage_other'),
            ('naninovel-spawn', 'unknown', 'stage_other'),
        ]
        for source, name, group in cases:
            self.assertEqual(classify_asset(source, name), group)

    def test_discovery_from_group_includes_native_assets_and_excludes_engine_assets(self):
        for name in ('resources.assets', 'sharedassets0.assets', 'globalgamemanagers.assets'):
            (self.data / name).write_bytes(b'asset')
        result = find_small_asset_sources(self.backgrounds / 'mainbackground')
        self.assertEqual(set(result), {self.source, self.data / 'resources.assets', self.data / 'sharedassets0.assets'})

    @patch('src.small_assets.UnityPy.load')
    def test_scan_keeps_sprites_and_independent_textures_excludes_atlas_and_alpha(self, load):
        rd = NS(texture=pointer(2), alphaTexture=pointer(3))
        atlas = NS(path_id=9, read=lambda: NS(m_RenderDataMap=[('key', rd)]))
        env = environment(reader('Sprite', 'Icon', 9007199254740993, atlas=atlas),
                          reader('Texture2D', 'Atlas', 2), reader('Texture2D', 'Alpha', 3),
                          reader('Texture2D', 'InputIndicator', 4))
        load.return_value = env
        result = scan_small_assets(self.root)
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['errors'], [])
        self.assertEqual([x['name'] for x in result['bundles']], ['Icon', 'InputIndicator'])
        self.assertEqual(result['bundles'][0]['object_id'], '9007199254740993')
        self.assertEqual(env.files, {})

    @patch('src.small_assets.UnityPy.load')
    def test_empty_runtime_texture_is_not_listed_as_an_exportable_image(self, load):
        empty = reader('Texture2D', 'Font Texture', 9)
        data = empty.read()
        data.m_Width = data.m_Height = 0
        empty.read = lambda: data
        load.return_value = environment(empty, reader('Texture2D', 'InputIndicator', 4))
        result = scan_small_assets(self.root)
        self.assertEqual([x['name'] for x in result['bundles']], ['InputIndicator'])
        self.assertEqual(result['errors'], [])

    @patch('src.small_assets.UnityPy.load')
    def test_scan_duplicate_names_have_distinct_ids_and_bad_source_continues(self, load):
        (self.platform / 'general-witchbook_assets_all.bundle').write_bytes(b'bad')
        load.side_effect = [environment(reader('Sprite', 'same', 1), reader('Sprite', 'same', 2)), ValueError('bad')]
        result = scan_small_assets(self.root)
        self.assertEqual(len({x['id'] for x in result['bundles']}), 2)
        self.assertEqual(len(result['errors']), 1)

    @patch('src.small_assets.UnityPy.load')
    def test_scan_cancel_does_not_open_source(self, load):
        with self.assertRaises(LoadCancelled):
            scan_small_assets(self.root, cancel_check=lambda: True)
        load.assert_not_called()

    @patch('src.small_assets.UnityPy.load')
    def test_individual_preview_reuses_source_and_reloads_changed_source(self, load):
        load.side_effect = lambda _: environment(reader('Sprite', 'one', 1), reader('Sprite', 'two', 2))
        previewer = SmallAssetPreviewer()
        self.addCleanup(previewer.close)
        self.assertEqual(previewer.preview(self.source, '1', 'Sprite')['name'], 'one')
        result = previewer.preview(self.source, '2', 'Sprite')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['name'], 'two')
        self.assertEqual(load.call_count, 1)
        self.source.write_bytes(b'changed source')
        self.assertEqual(previewer.preview(self.source, '1', 'Sprite')['name'], 'one')
        self.assertEqual(load.call_count, 2)
        with self.assertRaises(ValueError):
            previewer.preview(self.source, '1', 'Texture2D')

    def test_atlas_cache_is_bounded_and_closes_evicted_images(self):
        first, second = Image.new('RGBA', (12, 6)), Image.new('RGBA', (12, 6))
        env = NS(assets=[NS(_cache={1: first, 2: second})])
        prune_texture_cache(env, max_bytes=12 * 6 * 4)
        self.assertEqual(list(env.assets[0]._cache), [2])
        with self.assertRaises(ValueError):
            first.getpixel((0, 0))
        prune_texture_cache(env, max_bytes=0)
        self.assertEqual(env.assets[0]._cache, {})

    def test_object_thumbnail_cache_isolated_in_memory_and_on_disk(self):
        cache = BackgroundPreviewCache(directory=self.root / 'cache')
        keys = [cache.key(self.source, object_id=str(n), asset_type='Sprite') for n in (1, 2)]
        with Image.new('RGBA', (12, 6)) as image, io.BytesIO() as stream:
            image.save(stream, format='PNG')
            url = 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')
        for n, key in enumerate(keys):
            cache.put(key, {'name': str(n), 'size': [12, 6], 'count': 1, 'data_url': url})
        self.assertEqual(len(cache._entries), 2)
        self.assertEqual(len(list(cache.directory.glob('*.png'))), 2)
        cache.clear()
        self.assertEqual([cache.get(key)['name'] for key in keys], ['0', '1'])

    @patch('src.background_assets.UnityPy.load')
    def test_selected_export_loads_source_once_and_places_only_native_images_in_categories(self, load):
        load.return_value = environment(reader('Sprite', 'same', 1), reader('Sprite', 'same', 2),
                                        reader('Texture2D', 'Atlas', 3))
        output = self.root / 'output/backgrounds'
        result = export_backgrounds([self.item(), self.item(path_id=2, group='演出物件')], output)
        load.assert_called_once()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['count'], 2)
        self.assertEqual({Path(x['file_path']).parent.name for x in result['files']}, {'界面素材', '演出物件'})
        for entry in result['files']:
            with Image.open(entry['file_path']) as image:
                self.assertEqual(image.size, (12, 6))
                self.assertEqual(image.getpixel((0, 0)), (12, 34, 56, 78))
        self.assertEqual(len(list(output.rglob('*.png'))), 2)
        self.assertEqual(len(list(output.glob('*/*/'))), 0)

    @patch('src.background_assets.UnityPy.load')
    def test_invalid_selector_does_not_export_whole_bundle(self, load):
        load.return_value = environment(reader('Sprite', 'one', 1))
        result = export_backgrounds([self.item(path_id=2)], self.root / 'output')
        self.assertEqual(result['count'], 0)
        self.assertEqual(len(result['errors']), 1)

    def test_api_mixed_export_uses_category_paths_and_preserves_background_folder(self):
        api = object.__new__(JsApi)
        api._background_bundles = {'bg': {'id': 'bg', 'group': 'stills'},
                                   'apple': {'id': 'apple', 'group': 'evidence'}}
        api._output_dir, api._export_count = self.root, 0
        api._start_background_job = lambda operation, task: task()
        api._extract_background_batch = Mock(return_value={'count': 2, 'output_dir': str(self.root / 'backgrounds')})
        with patch('run.save_settings'):
            result = api.export_backgrounds(['bg', 'apple', 'apple'])
        items, directory, _ = api._extract_background_batch.call_args.args
        self.assertEqual([item['output_group'] for item in items], ['背景', '证物'])
        self.assertEqual(directory, self.root / 'backgrounds')
        self.assertEqual(result['export_count'], 1)


if __name__ == '__main__':
    unittest.main()

# Background & Small Asset Extraction

[![English](https://img.shields.io/badge/English-blue)](backgrounds.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-red)](backgrounds.md)

On the **Assets** page, select the game root directory, the `backgrounds` directory, or one of its category folders. The program automatically locates the background and adjacent general asset bundles, independent of the character directory settings. You can also drag the game directory onto this page.

## Usage

1. Click **Load asset folder**. Scene backgrounds are shown by default; the category dropdown switches to CG illustrations, Evidence, Profiles, Interface, stage images, and more.
2. Search by asset name, resource relative path, or source bundle name. Checkboxes are for export; **Select visible** only selects the currently visible items, and selections persist across categories; **Deselect all** clears every selection.
3. Click an asset row to preview it, or focus the row and press Enter/Space. Clicking the checkbox only changes the selection. Original background bundles preview their first available image; small assets are previewed one by one.
4. **Prewarm all**, to the right of **Load asset folder**, caches thumbnails for all loaded items — unaffected by category or search, and it does not change selections. It can be cancelled; prewarming again reuses the already-cached results.
5. Click **Export selected**. Original background bundles export every image in the bundle; small assets export only the selected images. Export can be cancelled, completed PNGs are kept, and failed items are listed separately.

Previews are capped at 1280 px on the longest side, while the UI displays the original dimensions. Export is always a native-size PNG with the alpha channel preserved, independent of the character quality settings. Assets may contain spoilers.

## Categories & Output

All output follows the output directory in the settings. PNGs are placed directly inside each category folder — no per-bundle subfolders. For example:

```text
output/backgrounds/背景/Background_001_001.png
output/backgrounds/证物/Clue_001_013.png
output/backgrounds/人物资料/Profile_Alisa.png
output/backgrounds/界面素材/InputIndicator.png
output/backgrounds/演出物件/1-2-3_Smartphone.png
```

| Category folder | Source & classification rules |
| --- | --- |
| 背景 (Scene backgrounds) | Scene backgrounds, CG illustrations and stage resource bundles under the original `backgrounds` |
| 证物 (Evidence), 人物资料 (Profiles) | `Clue_*` and `Profile_*` from `general-witchbook` |
| 界面素材 (Interface) | `general-sprites`, `naninovel-ui`, `resources.assets`, `sharedassets*.assets` |
| 演出物件 (Stage props) | Images named after weapons, phones, keys, paper, curtains, etc. in `naninovel-spawn` |
| 演出人物 (Stage characters) | Images and parts named after characters in stage bundles |
| 演出背景 (Stage backgrounds) | Background, Frontground, Space, etc. images in stage bundles |
| 演出特效 (Stage effects) | CutIn, glass shards, light effects, flames, blood stains, etc. |
| 地图素材 (Maps) | Maps and pins named Map / Pin |
| 演出其他 (Other stage images) | Placeholder images such as `kari`, and other stage images that cannot be identified by name |
| 特效纹理 (Effect textures) | Material textures from `general-prefabs` |
| 转场遮罩 (Transition masks) | Mask textures from `general-transitions` |

> The category folder names on disk are fixed Chinese names, independent of the UI language.

Every valid Sprite and standalone Texture2D in stage bundles is included; classification is based on the source and the original name, and unrecognized images go to 演出其他 (Other stage images). Small assets are not filtered by pixel size, so large UI illustrations and stage backgrounds are included as well. Atlas sprites are listed individually, and the backing textures and alpha textures they reference are not listed again; standalone textures in the same bundle that are not referenced by any sprite are kept. Runtime textures without pixels (such as 0×0) are not exportable images. Unity built-in resources, font files, audio, and scripts are out of scope for this page.

Conflicting file names automatically receive `_1`, `_2`, etc. suffixes — existing images are never overwritten. Invalid Windows characters and reserved device names are converted to safe names.

## Preview & Cache

Background scanning only enumerates paths; small-asset scanning reads Unity object names, sizes and atlas references without decoding pixels. Small-asset scanning runs in a cancellable separate process; if a single source fails, the error is logged and the other sources continue to be scanned.

Previews are decoded, downscaled and PNG-encoded directly in memory. A dedicated process is launched as soon as scanning completes and is reused afterwards. Small-asset preview reuses one resolved source bundle; the old bundle is released when you switch sources or when the source file changes. The decoded atlas cache from UnityPy is capped at 128 MiB, while a single full-size decode still has a transient memory cost. Batch-exporting selected images from the same source loads the bundle only once.

The main process keeps preview-encoded data in a 64 MiB LRU cache. Thumbnail PNGs and metadata such as original sizes are stored in `temp/background-previews/` and remain usable after a restart. Cache entries are keyed by source file path, timestamp, size, object type/ID and preview size, so different images in the same bundle never mix up. Entries are regenerated when the source file changes or the cache is corrupted; writes go through a temp file with atomic replacement.

The global "clear cache" action deletes all asset thumbnails — even when "keep character previews" is selected. Exiting only releases the preview process and memory. Cancellation or timeout kills the owning worker process tree, which can be relaunched on the next request.

## Tasks & Implementation

Scanning, preview, prewarming and export share the existing extraction lock and provide dedicated `background_progress` / `background_complete` events. While an asset task is running, character tasks and cache cleanup are blocked to avoid conflicts on the shared status bar. The UI reuses the original tabs, dropdowns, buttons, lists, modals and progress animations, and the **Disable UI Animations** setting continues to apply.

Final files are published only after PNG encoding completes; the parent process cleans up staging leftovers after cancellation. A successful export increments the total export count once per task — all-failed or cancelled tasks do not count. Batch export does not retry automatically, to avoid duplicate images after a partial completion; the worker's 45 s no-progress and 600 s total timeouts apply. A single preview request times out after 45 s.

| File | Responsibility |
| --- | --- |
| `src/background_assets.py` | Background location, thumbnails, object cache keys, PNG saving and per-source batch export |
| `src/small_assets.py` | Small-asset source location, metadata scanning, atlas dedup, classification and reusable source preview |
| `src/worker_client.py`, `backend.py` | Cancellable scan/export and reusable preview process |
| `run.py` | Load / preview / prewarm / export APIs and output categories |
| `webui/js/backgrounds.js`, `webui/css/backgrounds.css` | Categories, search, selection, preview and the original interaction styles |

## Verification

Regression checks that require no game assets:

```powershell
python -m unittest discover -s tests -v
```

Coverage includes: directory entry points, classification, atlas & alpha dedup, standalone textures, empty runtime textures, 64-bit object ID strings, per-image cache isolation within one bundle, source reuse and invalidation, the atlas cache cap, single-item and cross-category native-size PNGs, name conflict suffixes, cancellation / partial failure, cache reuse / cleanup, and process recovery.

With your own game assets, verify that evidence (e.g. the `Clue_001_013` apple), profiles, atlas sprites and stage images each preview/export correctly; check native sizes and transparency, checkbox independence, cross-category selection, prewarm cancellation, cache cleanup, and the animation setting. Game assets and locally extracted results are not committed to the repository.

# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

Extract character sprites from Unity bundle files of the game **"Magical Girl Witch Trials" (Manosaba)**: auto-detect component data, export sprites directly, composite full illustrations, or render character nameplates in the game's original layout. The UI is an **Electron frameless window**, with core logic handled by a **Python backend** (child process + stdio JSON-RPC).

## Related Projects
>- **[Manosaba-Library](https://github.com/QwQSakuya/Manosaba-Library)** — Another project from the "Magical Girl's Witch Trial" community, it's a fan-made unofficial resource site that collects story node maps, evidence compendiums, CG galleries, voice and music files, and a full material library index, with support for online character illustration previews.

## Features

**Extraction & Compositing**

- **Auto Detection** — Detect component data: preview/export directly when absent, or export/composite when present
- **Character Compositing** — Composite full illustrations by part position, depth & clipping masks, with categories/thumbnails; five blend modes (Normal / Multiply / Screen / Overlay / Softlight) to reproduce the original look
- **Sprite Preview** — one-click preview of all sprites for no-component characters, check to export
- **Part Management** — search, natural sorting, collapsible groups, select all, quick-select ClippingMask parts, click to copy name
- **Hierarchy Viewer** — component tree, copy button per row
- **Anan Sketchbook** — custom text on anan's sketchbook parts (multi-line, font size, alignment)
- **Cancellable Loading** — character analysis can be cancelled at any time, instantly returning to a usable state

**Background Export**

- A dedicated **Backgrounds** tab locates the game's `backgrounds` directory, with scene / CG / effects categories, search, selection and per-bundle previews
- Generate thumbnails in memory with a prewarmed worker and bounded cache; batch-export native-size PNGs together to `output/backgrounds/背景/`; duplicate filenames receive a numeric suffix, and cancellation retains completed images
- Export Sprites first, or Texture2D when no Sprites exist, without exporting backing textures twice; see [background documentation (Chinese)](backgrounds.md) for implementation and regression tests

**Part Presets**

- Built-in **Default presets** for all main characters — restore checks with one click (shipped with the package; automatically repaired if missing or corrupted)
- Save your own combinations and import/export them as **JSON files / codes**; built-in presets are protected and cannot be overwritten or deleted

**Nameplate Compositing**

- Enter a name on the home page to render a nameplate PNG in the game's original layout (601×289; font sizes and layout parameters are parsed from the game's UI bundle; overly long names widen the canvas instead of shrinking the font)
- Fonts are limited to TsukushiMincho / SourceHanSerifSC; output goes to `output/nameplate/`
- On first use, "Extract Assets" locates the game directory and extracts the base plate & fonts (the search can be cancelled at any time, or pick a bundle manually)

**Preview & Viewing**

- **Live Preview** — wheel zoom (cursor-centered), drag pan
- **Zoom Viewer** — zoom into composites / single parts / sprites, and export directly from the viewer
- **Preview Quality / Original Export** — preview composites at lower resolution to reduce load (100 / 75 / 50 / 25 levels); export keeps original quality by default, can switch to match preview

**UI & Experience**

- **Drag & Drop Import** — drop a game directory or bundle file onto the window to load it; remembers the last used game directory
- **Multi-language / Theme** — Simplified Chinese / English / 日本語 / Magical Girl Language; dark/light theme + 17 character accent colors, persisted
- **Low-end GPU Optimization** — can disable hardware acceleration (software rendering) and UI animations for smoother low-end devices
- **Taskbar Effects** — shows progress during loading and flashes the taskbar when done
- **Log Files / Console** — Console logs also written to `logs/`, one-click cleanup; plus a standalone log console window (level filtering, multi-line merging, save to file)

**Data & Maintenance**

- **Cache Reuse** — Extracted data cached in `temp/`, re-loading doesn't require re-unpacking
- **Memory Reclaim** — Releases resources immediately with GC triggers; forced GC before exit
- **Debug Mode** — Monitor memory/CPU/window resolution (current run only)
- **Total Exports / About / Auto Update Check / Disclaimer** (third-party unofficial tool)

## Requirements

- **Python 3.10+**: `pip install -r requirements.txt`
- **Node.js 18+**: `cd electron && npm install`

> Currently fully tested on **Windows** only; Linux/macOS compatibility is unknown.

## Minimum System Requirements

| Item | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 1809 (64-bit) | Windows 10 / 11 (64-bit) |
| CPU | Dual-core 1.6 GHz (x64) | Quad-core or better |
| RAM | 1 GB | 2 GB or more |
| GPU | DirectX 11 / WebGL capable (integrated OK) | Dedicated GPU, 1 GB+ VRAM |
| Storage | ~500 MB free space | 1 GB or more |

> - The packaged build (portable / installer) already bundles the Python backend and Electron runtime, so **no Python / Node.js installation is required** — runs out of the box.
> - Compositing creates large canvases (no smaller than 2000×4000, automatically expanded to fit the parts' actual span); on low-RAM or iGPU machines, enable **Disable Hardware Acceleration** and **Disable UI Animations** for smoother performance.
> - On low-end devices, lower the **Preview Quality** (100 / 75 / 50 / 25 levels) to reduce load; export still keeps original quality by default.

## Usage

### Run (Recommended: launcher script)

On Windows, use the `start.bat` launcher in the repo root:

```bat
start.bat                  :: Electron frameless window (default; native Aero Snap / drag / double-click maximize / edge resize)
start.bat help             :: Show help
start.bat clean [targets]  :: Remove temp files and build caches (see "Cleaning dev caches" below)
```

**Install dependencies once before first run:**

```bash
pip install -r requirements.txt        # Python dependencies
cd electron && npm install             # Electron dependencies
```

> Alternatively launch manually: `cd electron && npm start`

### Cleaning dev caches (`start.bat clean`)

Leftovers from development can be cleaned per target:

```bat
start.bat clean                  :: default: temp + logs + build + pycache (dist is kept)
start.bat clean temp             :: only the extraction cache temp/
start.bat clean logs             :: only logs/*.log (other files in that folder are kept)
start.bat clean build            :: only the PyInstaller cache build/
start.bat clean pycache          :: only __pycache__ / .pytest_cache
start.bat clean dist             :: only the packaging output dist/
start.bat clean all              :: everything above
start.bat clean temp logs build  :: targets can be combined with spaces
```

- Target names are case-insensitive; an unknown target prints a hint with the usage.
- **User data is never touched**: `data/` (settings & presets), `output/` (exports), `builtin/` (built-in presets), `electron/node_modules`.
- `__pycache__` is swept only in the repo's own `src/`, `scripts/`, `builtin/`, `i18n/` and the root, never inside `.venv` or `node_modules`.


### Steps

1. Click a character on the left → the program auto-detects:
   - **No component data** → Preview Sprites / Export All Directly / Cancel
   - **With component data** → Direct Export / Composite Character
2. Composite mode: check parts (or pick a built-in / custom preset from the preset bar) → live preview → save composite PNG
3. Nameplate: enter a name on the home page nameplate card, pick font & first-letter color → generate preview → save (run "Extract Assets" first)
4. Backgrounds: open the **Backgrounds** tab → **Load backgrounds** → select the game root or `backgrounds` folder → filter/check assets → **Export selected**. Scene backgrounds are shown by default; CGs and effects are available from the category dropdown. **Select visible** selects the current filtered list, selections persist across categories, and **Deselect all** clears every selection.

Background previews are limited to a 1280-pixel longest edge; exports always preserve native dimensions, independently of character preview/export quality settings. Dropping a game folder while the Backgrounds tab is active also loads backgrounds. Scans, previews and exports can be cancelled; completed PNGs are retained and failed assets are listed separately.

### Settings

Configure: **Output Directory** (remembered automatically), **Language**, **Theme & Accent**, **Show Original File Names**, **Auto-find characters directory** (when off, you must manually pick the folder that directly contains the character bundles), **Spoiler Notice**, **Preview Quality** (100 / 75 / 50 / 25 levels, lower preview composite resolution to reduce load), **Export Original Quality** (when off, export matches preview), **Disable Hardware Acceleration** (software rendering, restart to apply), **Disable UI Animations** (low-end boost, applies immediately), **Show Release Notes** (on by default; shows the release notes for the new version in the update dialog, can be turned off inside that dialog), **Debug Mode**, **Check for Updates**, **Cleanup** (`temp/` cache, `output/` directory, or `logs/` logs).

> Settings are stored in `data/settings.json` under the program directory (hidden attribute).

### Data Storage Paths (Packaged Build)

After installation, the app reads/writes the following data under its **install directory** (example: `D:\mce`):

| Path | Purpose |
|---|---|
| `D:\mce\data` | Settings `settings.json` + part presets `presets\` |
| `D:\mce\output` | Exported sprites / composites / nameplate PNGs |
| `D:\mce\temp` | Extraction cache (clearable) |
| `D:\mce\logs` | Runtime logs (one-click cleanup; follows the data directory) |

> Data (`data`/`output`/`temp`/`logs`) is always stored **preferentially in the program directory** (the install directory or the portable extraction directory); it only falls back to `%APPDATA%\Manosaba Character Extracter` when that directory is not writable (e.g. failed permission grant, antivirus interference, read-only drive).
>
> Extracted nameplate assets & fonts go into the **program resources directory** `resources\webui\assets\nameplate`
> (and `assets\fonts`); `data\nameplate` is only used as a fallback when the `webui` directory is not writable.
>
> When installed to the default `C:\Program Files\MCE`, the installer grants normal users write and delete permission on that directory, so data (`data`/`output`/`temp`/`logs`) is still stored directly under the install directory.
>
> **Overwriting installs / upgrades never touch that data** (matching Inno Setup): before installing, the installer moves `data`/`output`/`temp`/`logs` into a sibling `MCE-update-backup` folder and moves them back afterwards (a rename — no data is copied); the uninstaller only ever deletes files it installed (`MCE.exe`, `resources`, `locales`, and other allow-listed entries), so files you placed in the install directory are never removed.
> During uninstallation, if data folders are detected under the install directory (except in silent mode), a dialog asks whether to delete them as well: "Yes" deletes everything, "No" uninstalls the app but keeps your data, "Cancel" aborts the uninstall.

### Output & Cache Structure

```
output/
├── <name>/            # No components: sprites flat here
├── <name>/sprites/    # With components: exported sprites
├── <name>/composite/  # With components: composite images (<name>_composite.png, auto-numbered on conflict)
├── backgrounds/背景/  # Background PNGs (scene / CG / effects, auto-numbered on conflict)
└── nameplate/         # Nameplate PNGs (named after the entered name, auto-numbered on conflict)
temp/
└── <name>/            # Extraction cache: sprites/ + character_data.json + mask_mapping.json
data/presets/          # Part presets (built-in mirror + user-created; clearing the cache keeps them)
```

## Architecture

**Launch path**

- Development: `start.bat` → `electron/main.js` → `spawn(backend.py)` → `run.JsApi`
- Packaged: `MCE.exe` → `resources/backend/backend.exe` (the same backend, bundled with PyInstaller)

**Responsibility split**

- The **Electron main process** owns all OS-native UI: frameless window control (native Aero Snap / drag / double-click maximize / edge resize), directory & file pickers, taskbar progress, and the log console window. The frontend reaches it via `window.pywebview.api` (business methods) and `window.__electron` (window/dialogs/log console and other native capabilities).
- The **Python backend** only does business logic and image processing, with no GUI framework dependency; `run.py` has no standalone entry point — the only process entry is `backend.py`.

**Communication protocol** (one JSON per line over stdin/stdout)

- Request `{"id":N,"method":"...","args":[...]}` → response `{"id":N,"result":...}` / `{"id":N,"error":"..."}`
- Events `{"event":"name","payload":{...}}` (progress, preview images, update results, etc.)
- stdout is reserved for the protocol; logs always go to stderr and into `logs/`

**Extraction worker subprocess**

UnityPy extraction runs in a dedicated `backend.py --worker` subprocess (to avoid occasional freezes in the backend main process): it can be cancelled at any time (the subprocess is killed), and no output for 45 s or a total of 600 s is treated as a timeout with one automatic retry.

**Environment variables (development / debugging)**

- `MCE_PYTHON` — override the backend Python interpreter (read first by both `start.bat` and `main.js`)
- `MCE_DATA_DIR` — redirect all data directories (`data`/`output`/`temp`/`logs`); set automatically by Electron in the packaged build

## Project Structure

```
├── start.bat          # Windows launcher (start the app / clean temp files & build caches)
├── run.py             # Business logic layer (JsApi: compositing/preview/settings/extraction/nameplates/update check; no GUI dependency)
├── backend.py         # stdio JSON-RPC backend process (the only entry, reuses run.py's JsApi)
├── electron/          # Electron UI shell
│   ├── main.js        #   main process: frameless window + window control + native dialogs + Python child bridge
│   ├── preload.js     #   bridge layer: window.pywebview.api / __pywebview.events / __electron
│   ├── nsis/          #   installer customization (upgrade data protection / allow-list uninstall)
│   └── package.json
├── webui/             # Frontend (index.html + css/ + js/, fully local, no CDN; console/ is the log console window)
├── src/               # Core modules (bundle loading, compositing, export, cache, presets, nameplates, i18n, settings, update check, etc.)
├── i18n/              # Language packs (YAML: common + games/<game>; all 4 languages share the same key set)
├── builtin/           # Built-in part presets (shipped with the package, read-only)
├── scripts/           # PyInstaller packaging scripts
├── docs/              # English README, etc.
├── output/            # Output directory (generated at runtime)
└── temp/              # Extraction cache (generated at runtime)
```

Tech stack: [UnityPy](https://github.com/K0lb3/UnityPy) (bundle parsing), Pillow (image processing), [Electron](https://www.electronjs.org/) (frameless UI shell, Chromium rendering + native Aero Snap). These are the only 3 runtime dependencies on the Python side; OS capabilities such as explorer-window focusing are implemented with the ctypes standard library.

## Acknowledgments & License

### Original Game Info

The content extracted by this tool is from the game **"魔法少女ノ魔女裁判" (Manosaba)**  
© 2024 **Re,AER LLC. / Acacia** — All rights reserved by the original game developer.

### Author

**paliku520 (Yunye Fengyun)** — Development and maintenance

### Technical Acknowledgments

This project is a **deep refactoring and performance-optimized version** of the [KabeNaki](https://github.com/lingk7/KabeNaki) project. Special thanks to the original project author [lingk7](https://github.com/lingk7) for their outstanding work.

On that basis, this project received a comprehensive technical upgrade:
- **GUI framework migration**: fully migrated from `tkinter` to `Electron`, bringing a more modern, fluid UI and better platform compatibility.
- **Architecture & packaging refactor**: split into a Python backend and an Electron frontend, with a one-click packaged installer for a better distribution and installation experience.
- **Feature & UX enhancements**: on top of sprite extraction, added more precise `ClippingMask` handling, character accent colors, live preview zooming, extended multi-language support, and many other refinements.

### License

This project is licensed under the **GPL-3.0 License**. See the [LICENSE](LICENSE) file for details.

**Disclaimer**: This tool is intended for learning and personal research purposes only. The copyright of the extracted content belongs to the original game developer.

> This tool is a **third-party unofficial tool** and is not affiliated with the game official.

## Packaging as EXE

### Electron App
```bash
python scripts\build_electron_backend.py   # Build only the Python backend → dist/backend/
python scripts\build_electron.py            # One-click: backend + portable zip + installer Setup.exe
```

- `build_electron.py` options: `--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- Optional `--company/--product/--description/--copyright` to pass version info to the backend exe (defaults to the `APP_*` constants in `scripts/version_info.py`)
- Version is read automatically from `src/version.py` (artifacts `MCE-Setup-<version>.exe` / `MCE-<version>-win.zip` and the backend exe version info stay in sync; change the version in one place only)
- electron-builder config: `electron/electron-builder.yml` (requires electron/node_modules installed)
- see `--help` for more options

> **Asset copyright note**: the nameplate base plate and the game fonts are copyrighted assets and are
> **neither committed to the repository nor shipped in release packages** (`electron-builder.yml` excludes
> `webui/assets/nameplate/` and the three game fonts from `extraResources`). End users must extract them
> via "Extract Assets" in the app. The bundled UI fonts and the rest of the page resources are packaged as usual.

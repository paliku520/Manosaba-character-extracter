# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

Extract character sprites from Unity bundle files of the game **"Magical Girl Witch Trials" (Manosaba)**: auto-detect component data, export sprites directly, or composite full illustrations. The UI is an **Electron frameless window**, with core logic handled by a **Python backend** (child process + stdio JSON-RPC).

## Features

- **Auto Detection** — Detect component data: preview/export directly when absent, or export/composite when present
- **Character Compositing** — Composite full illustrations by part position, depth & clipping masks, with categories/thumbnails and Multiply / Overlay / Softlight blend modes to reproduce the original look
- **Anan Sketchbook** — Custom text on anan's sketchbook parts (font size / alignment / auto wrap)
- **Part Management** — search, natural sorting, collapsible groups, select all, click to copy name
- **Live Preview** — wheel zoom (cursor-centered), drag pan
- **Sprite Preview** — one-click preview of all sprites for no-component characters, check to export
- **Hierarchy Viewer** — component tree, copy button per row
- **Drag & Drop Import** — drop a game directory or bundle file onto the window to load it
- **Cache Reuse** — Extracted data cached in `temp/`, re-loading doesn't require re-unpacking
- **Memory Reclaim** — Releases resources immediately with GC triggers; forced GC before exit
- **Taskbar Effects** — Electron mode shows progress during loading and flashes the taskbar when done
- **Debug Mode** — Monitor memory/CPU/window resolution (current run only)
- **Log Files** — Console logs also written to `logs/`, one-click cleanup
- **Multi-language / Theme** — Simplified Chinese / English / 日本語 / Magical Girl Language; dark/light theme + character accent colors persisted
- **Total Exports / About / Auto Update Check / Disclaimer** (third-party unofficial tool)

## Requirements

- **Python 3.10+**: `pip install -r requirements.txt`
- **Node.js 18+**: `cd electron && npm install`

> Currently fully tested on **Windows** only; Linux/macOS compatibility is unknown.

## Usage

### Run (Recommended: launcher script)

On Windows, use the `start.bat` launcher in the repo root:

```bat
start.bat            :: Electron frameless window (default; native Aero Snap / drag / double-click maximize / edge resize)
start.bat py         :: PyWebView / WebView2 mode (native window)
start.bat help       :: Show help
```

**Install dependencies once before first run:**

```bash
pip install -r requirements.txt        # Python dependencies
cd electron && npm install             # Electron dependencies
```

> Alternatively launch manually: `cd electron && npm start` (Electron mode) or `python run.py` (PyWebView mode)


### Steps

1. Click a character on the left → the program auto-detects:
   - **No component data** → Preview Sprites / Export All Directly / Cancel
   - **With component data** → Direct Export / Composite Character
2. Composite mode: check parts → live preview → save composite PNG

### Settings

Configure: **Output Directory** (remembered automatically), **Language**, **Theme & Accent**, **Show Original File Names**, **Spoiler Notice**, **Debug Mode**, **Check for Updates**, **Cleanup** (`temp/` cache, `output/` directory, or `logs/` logs).

> Settings are stored in `data/settings.json` under the program directory (hidden attribute).

### Data Storage Paths (Packaged Build)

After installation, the app reads/writes the following data under its **install directory** (example: `D:\mce`):

| Path | Purpose |
|---|---|
| `D:\mce\data` | Settings `settings.json` |
| `D:\mce\output` | Exported sprites / composite PNGs |
| `D:\mce\temp` | Sprite cache (clearable) |
| `D:\mce\resources\backend\logs` | Runtime logs (one-click cleanup) |

> For the portable (zip) build, the same folders are created under the extraction directory; `data/` can be redirected via the `MCE_DATA_DIR` environment variable.
>
> If installed to a **protected directory** (e.g. under `C:\Program Files\`, not writable by normal users), the app automatically falls back to `%APPDATA%\Manosaba Character Extracter` for its data directory to keep running.

### Output Structure

```
output/
├── <name>/            # No components: sprites flat here
└── <name>/            # With components: sprites/ (sprites) + composite/ (composite images)
    ├── character_data.json  # part / hierarchy data
    └── mask_mapping.json    # mask & blend mode mapping
temp/                  # Sprite cache (clearable, speeds up re-loading)
```

## Project Structure

```
├── run.py             # PyWebView mode entry (WebView2, fallback)
├── backend.py         # Electron mode Python backend child process (stdio JSON-RPC)
├── electron/          # Electron UI shell
│   ├── main.js        #   main process: frameless window + Python child bridge + window control
│   ├── preload.js     #   bridge layer: emulates the pywebview API, zero frontend changes
│   └── package.json
├── webui/             # Frontend (index.html + css/ + js/, fully local, no CDN, shared by both modes)
├── src/               # Core modules (loading, compositing, export, cache, i18n, settings, etc.)
├── scripts/           # PyInstaller packaging scripts
├── output/            # Output directory (generated at runtime)
└── temp/              # Sprite cache (generated at runtime)
```

Tech stack: [UnityPy](https://github.com/K0lb3/UnityPy) (bundle parsing), Pillow (image processing), [Electron](https://www.electronjs.org/) (frameless UI shell, Chromium rendering + native Aero Snap), [pywebview](https://github.com/r0x0r/pywebview) (fallback WebView2 mode).

## Acknowledgments & License

### Original Game Info

The content extracted by this tool is from the game **"魔法少女ノ魔女裁判" (Manosaba)**  
© 2024 **Re,AER LLC. / Acacia** — All rights reserved by the original game developer.

### Author

**paliku520 (Yunye Fengyun)** — Development and maintenance

### Technical Acknowledgments

This project is a **deep refactoring and performance-optimized version** of the [KabeNaki](https://github.com/lingk7/KabeNaki) project. Special thanks to the original project author [lingk7](https://github.com/lingk7) for their outstanding work.

**Refactoring and optimizations include:**
- **Architecture Refactoring**: Split the original monolithic file into a modular design (`bundleloader`, `compositor`, `tools`, etc.) for improved maintainability.
- **Performance Optimization**: Optimized UI responsiveness and data processing flow, eliminating unnecessary full UI rebuilds.
- **Feature Enhancements**: Added multi-character management, batch directory scanning, path memory, TreeView hierarchy, multi-language support, and cache reuse.

### License

This project is licensed under the **GPL-3.0 License**. See the [LICENSE](LICENSE) file for details.

**Disclaimer**: This tool is intended for learning and personal research purposes only. The copyright of the extracted content belongs to the original game developer.

> This tool is a **third-party unofficial tool** and is not affiliated with the game official.

## Packaging as EXE

### PyWebView Standalone
```bash
pip install pyinstaller
python scripts\build_pywebview.py                          # Default onedir (fast startup)
python scripts\build_pywebview.py --onefile                # Single-file exe
python scripts\build_pywebview.py --name MyApp --icon icon.ico
```

- Version info auto-injected (file version / product name, etc., to reduce antivirus false positives); the version is read automatically from `src/version.py`; optional `--company/--product/--description/--copyright` (defaults to `APP_*` constants), `--console false`
- Icons must be `.ico`; `--onefile` starts slower; see `--help` for more options

### Electron App
```bash
python scripts\build_electron_backend.py   # Build only the Python backend → dist/backend/
python scripts\build_electron.py            # One-click: backend + portable zip + installer Setup.exe
```

- `build_electron.py` options: `--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- Optional `--company/--product/--description/--copyright` to pass version info to the backend exe (defaults to `APP_*` constants at the top of the script)
- Version is read automatically from `src/version.py` (artifacts `MCE-Setup-<version>.exe` / `MCE-<version>-win.zip` and the backend exe version info stay in sync; change the version in one place only)
- electron-builder config: `electron/electron-builder.yml` (requires electron/node_modules installed)
- see `--help` for more options

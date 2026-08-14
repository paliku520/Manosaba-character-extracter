# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

Extract character sprites from Unity bundle files of the game **"Magical Girl Witch Trials" (Manosaba)**: auto-detect component data, export sprites directly, or composite full illustrations. The UI is an **Electron frameless window**, with core logic handled by a **Python backend** (child process + stdio JSON-RPC).

## Features

- **Auto Detection** — Detect component data: preview/export directly when absent, or export/composite when present
- **Character Compositing** — Composite full illustrations by part position & depth, with categories, thumbnails, and live preview
- **Part Management** — search, natural sorting, collapsible groups, select all, click to copy name
- **Live Preview** — wheel zoom (cursor-centered), drag pan
- **Sprite Preview** — one-click preview of all sprites for no-component characters, check to export
- **Hierarchy Viewer** — component tree, copy button per row
- **Cache Reuse** — Extracted data cached in `temp/`, re-loading doesn't require re-unpacking
- **Memory Reclaim** — Releases resources immediately with GC triggers; forced GC before exit
- **Debug Mode** — Monitor memory/CPU/window resolution (current run only)
- **Log Files** — Console logs also written to `logs/`, one-click cleanup
- **Multi-language / Theme** — Simplified Chinese / English / fiXmArge; dark/light theme persisted
- **Total Exports / About / Auto Update Check / Disclaimer** (third-party unofficial tool)

## Requirements

- **Python 3.10+**: `pip install -r requirements.txt`
- **Node.js 18+**: `cd electron && npm install`

> Currently fully tested on **Windows** only; Linux/macOS compatibility is unknown.

## Usage

### Run

**Recommended: Electron frameless window** (native Aero Snap / drag / double-click maximize / edge resize)
```bash
cd electron
npm install        # first time only
npm start          # equivalent to npx electron .
```

**Alternative: PyWebView / WebView2 mode**
```bash
python run.py
```

### Steps

1. Click a character on the left → the program auto-detects:
   - **No component data** → Preview Sprites / Export All Directly / Cancel
   - **With component data** → Direct Export / Composite Character
2. Composite mode: check parts → live preview → save composite PNG

### Settings

Configure: **Output Directory** (remembered automatically), **Language**, **Theme**, **Debug Mode**, **Check for Updates**, **Cleanup** (`temp/` cache, `output/` directory, or `logs/` logs).

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

### Output Structure

```
output/
├── <name>/            # No components: sprites flat here
└── <name>/            # With components: sprites/ (sprites) + composite/ (composite images)
temp/                  # Sprite cache (clearable, speeds up re-loading)
```

## Known Issues

### Illustration Compositing Layer Order / Mask Handling Incomplete

**Problem Description**
The current version cannot fully reproduce the original game's illustration layer effects; some parts (eyes, hair, face masks) may differ from the in-game display.

**Specific Symptoms**
- Some layer stacking orders are inconsistent with the original game
- ClippingMask layers are rendered as normal sprites instead of invisible clipping regions

**Comparison**

![Compositing Comparison](./images/comparison.png)

**Root Cause Analysis (may be inaccurate)**
- The game's illustrations use Unity's `SpriteRenderer` + `ClippingMask` for layer clipping; the current compositor only stacks by `sorting_order`, without implementing:

1. **Clipping Mask**: `ClippingMask`-type sprites clip the display region of target layers
2. **Mask Scope**: Each mask only affects specific parts (e.g., `ClippingMask_Eyes` only affects the eye area), not globally
3. **Transparent Masks**: Masks have a `color.a < 1.0` transparency property

**Workarounds**
1. Export all sprites directly and edit manually with Photoshop or similar
2. Use the [Manosaba mod](http://manosabamoddoc.fuyumi.xyz/) by [雪莉苹果汁](https://space.bilibili.com/3546949672241842) to edit within the game (the tool provides component structure info)
3. Wait for future fixes

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

- Version info auto-injected (file version / product name, etc., to reduce antivirus false positives); optional `--company/--product/--description/--copyright` (defaults to `APP_*` constants), `--console false`
- Icons must be `.ico`; `--onefile` starts slower; see `--help` for more options

### Electron App
```bash
python scripts\build_electron_backend.py   # Build only the Python backend → dist/backend/
python scripts\build_electron.py            # One-click: backend + portable zip + installer Setup.exe
```

- `build_electron.py` options: `--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- electron-builder config: `electron/electron-builder.yml` (requires electron/node_modules installed)
- see `--help` for more options

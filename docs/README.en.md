# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

Extract character sprites from Unity bundle files of the game **"Magical Girl Witch Trials" (Manosaba)**. Supports automatic component data detection, direct sprite export, and full character illustration compositing. Built with a **modern PyWebView GUI** (WebView2 rendering).

## Features

- **Auto Detection** — Automatically detects bundle component data: exports sprites directly when absent, or exports/composites when present
- **Character Illustration Compositing** — Composites full illustrations by component position & depth, with categorized parts, thumbnail previews, and live compositing preview
- **Part Management** — search, natural sorting (prefix letters + numbers), collapsible groups, select all; click a selected sprite to copy its name
- **Live Preview** — wheel zoom (cursor-centered), drag pan, min-zoom fits full resolution
- **Hierarchy Viewer** — component tree, each row has a copy button
- **Cache Reuse** — Extracted data cached in `temp/`, re-loading doesn't require re-unpacking
- **Multi-language** — Simplified Chinese / English / fiXmArge (a constructed language), auto-follows system, switchable in Settings
- **Theme** — dark / light theme, persisted to settings
- **Total Exports** — counts successful export operations (shown on the About page)
- **About Page** — developer info, project links, rotating background, check for updates
- **Auto Update Check** — Silently checks for new GitHub versions at startup

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

> Currently fully tested on **Windows** only; Linux/macOS compatibility is unknown.

## Usage

### Run
```bash
python run.py
```

1. Click **Load Game Directory** → Select the game root directory or the `characters` directory
2. Click a character on the left → the program auto-detects:
   - **No component data** → Confirm, then directly export all sprites
   - **With component data** → Choose **Direct Export** or **Composite Character**
3. Composite mode: check parts → live preview → save composite PNG

### Settings

Click **Settings** on the left to configure: **Output Directory** (custom export location, remembered automatically), **Language**, **Theme** (dark/light), **Check for Updates**, **Cleanup** (`temp/` cache or `output/` directory).

> Settings are stored in `settings.json` in the program root directory.

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
- The current version of the illustration compositing feature cannot fully reproduce the original game's illustration layer effects. Some character parts (e.g., eyes, hair, face masks) may differ from the in-game display after compositing.

**Specific Symptoms**
- Some layer stacking orders are inconsistent with the original game
- ClippingMask layers are not handled correctly — they are rendered as normal sprites instead of invisible clipping regions
- Affected character parts include but are not limited to: eyes, hair, facial expression parts, etc.

**Comparison**

Below is a comparison between the current compositor output (left) and the original game (right):

![Compositing Comparison](./images/comparison.png)

**Root Cause Analysis**
- The game's character illustrations use Unity's `SpriteRenderer` + `ClippingMask` mechanism for complex layer clipping effects. The current compositor only performs simple layer stacking based on `sorting_order`, without implementing the following:

1. **Clipping Mask**: `ClippingMask`-type sprites are used to clip the display region of target layers
2. **Mask Scope**: Each `ClippingMask` only affects specific parts within a range (e.g., `ClippingMask_Eyes` only affects the eye area), not globally
3. **Transparent Masks**: Masks have a `color.a < 1.0` transparency property that needs proper handling

**Workarounds**
1. Export all sprite files directly and manually edit them using image editing software such as Adobe Photoshop.
2. Use the [Manosaba mod](http://manosabamoddoc.fuyumi.xyz/) by [雪莉苹果汁](https://space.bilibili.com/3546949672241842) on Bilibili, which allows editing directly within the game (the tool provides component structure information).
3. Wait for future fixes.

## Project Structure

```
├── run.py             # Main entry (PyWebView backend + JsApi bridge)
├── webui/             # Frontend (index.html + css/ + js/, fully local, no CDN)
├── src/               # Core modules (loading, compositing, export, cache, i18n, settings, etc.)
├── scripts/           # PyInstaller packaging scripts
├── output/            # Output directory (generated at runtime)
└── temp/              # Sprite cache (generated at runtime)
```

Tech stack: [UnityPy](https://github.com/K0lb3/UnityPy) (bundle parsing), Pillow (image processing), [pywebview](https://github.com/r0x0r/pywebview) (modern GUI, WebView2 rendering).

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

## Packaging as EXE

```bash
pip install pyinstaller
python scripts\build_exe.py            # Default onedir (fast startup)
python scripts\build_exe.py --onefile  # Single-file exe (good for distribution)
python scripts\build_exe.py --name MyApp --icon icon.ico
```

> Icons must be in `.ico` format. `--onefile` extracts on each run and starts slower. See `python scripts\build_exe.py --help` for more options.

# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md)
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

Extract character sprites from Unity bundle files of the game **"Mahou Shoujo no Majo Saiban" (Manosaba)**. Supports automatic component data detection, direct sprite export, and full character illustration compositing.

## Features

- **Auto Detection** — Analyzes whether a bundle contains `SpriteRenderer` + `Transform` component data
- **Two Modes**:
  - No component data → Directly export all sprites as PNG
  - With component data → Choose to export directly or composite the character image
- **Selected Sprite List** — Right panel displays checked sprite filenames in real-time
- **Live Preview** — Automatically composites a preview when toggling parts (500ms debounce)
- **Part Selection** — Parts grouped by category with thumbnail previews, supports select all / deselect all
- **Character Illustration Compositing** — Composites full character images based on component positions and sorting depth
- **Hierarchy Viewer** — TreeView displaying the character component hierarchy
- **Progress Bar** — All time-consuming operations (loading, exporting, compositing) show real progress percentages
- **Multi-language Support** — Built-in Simplified Chinese / English / fiXmArge (fictional language), auto-follows system language
- **Cache Reuse** — Extracted character data is cached in the `temp/` directory, re-loading does not require re-unpacking
- **Clear Cache Button** — One-click cache clearing to free up disk space
- **Responsive Layout** — All panels remain usable when the window is resized, scrollbars always visible
- **Path Memory** — Automatically remembers the last selected game directory
- **Custom Output Path** — Supports command-line argument to specify output directory, flexible for workflow integration

## Requirements

- Python 3.10+
- Dependencies listed in [`requirements.txt`](requirements.txt)
### Install Dependencies
```bash
pip install -r requirements.txt
```
### Adding a New Language

To add a new language, edit `src/i18n.py`:
1. Define a language constant (e.g. `LANG_JP = "ja_JP"`)
2. Add it to the `LANGUAGE_CODES` list
3. Add translations for each key in that language
4. Add a `lang.ja_JP` display name entry

> The dropdown menu is automatically generated from `LANGUAGE_CODES`, no need to modify `run.py`.

## Platform Compatibility

This project is primarily developed and tested on **Windows**. It has **not been fully tested on other operating systems**.

- **Windows 10/11**: Primary development and testing platform, fully functional.
- **Linux**: Compatibility unknown; Tkinter and UnityPy may behave differently on Linux.
- **macOS**: Compatibility unknown; UI and file path handling may have issues.

If you successfully run it on a non-Windows platform or encounter any issues, feel free to submit an Issue or Pull Request sharing your experience.

## Usage

### Basic Usage
```bash
python run.py
```
### Command Line Arguments

```bash
python run.py --help
```

| Argument | Description |
|----------|-------------|
| `-h`, `--help` | Show help message |
| `-c`, `--clean` | Clear the output directory (default or custom path) before starting |
| `-o <path>`, `--output <path>` | Specify output directory (supports absolute/relative paths; relative paths are based on the program root) |
| `--clear-cache` | Only clear the cache folder and exit (does not start GUI) |
| `--git-clean` | Clear the `output` and `temp` directories and exit (for cleanup before git commit) |

**Examples:**
```bash
# View help
python run.py --help

# Clear default output directory and start
python run.py --clean

# Specify custom output path
python run.py --output D:/game_exports

# Clear cache only, do not start GUI
python run.py --clear-cache

# Combined usage
python run.py -c -o E:/exports
```
### Workflow

1. Click **Load Game Directory** → Select the game root directory or the `characters` directory
2. Click the character you want to process in the left character list
3. The program automatically detects the bundle type:
   - **No component data** → A dialog confirms, then directly exports all sprites
   - **With component data** → A dialog asks how to proceed
4. After selecting **Composite Character Image**:
   - In the "Part Selection" tab, check/uncheck the parts to include
   - The right "Selected Sprites" panel lists checked part filenames in real-time
   - Enable **Auto Update** for real-time compositing preview
   - Click **Generate Composite Image** to manually composite
   - Click **Save Composite Image** to export as PNG

### Directory Structure

```
program_root/
├── output/                ← Final composited results (saved manually by user)
│   └── <character_name>_composite.png
├── temp/                  ← Sprite cache directory (can be manually cleared, speeds up re-loading)
│   └── <character_name>/
│       ├── character_data.json   ← Hierarchy + part data
│       └── sprites/
│           ├── ArmL01.png
│           ├── Body.png
│           └── ...
├── src/                   ← Source code directory
├── run.py                 ← Main program entry
└── ...
```

> The `temp/` directory is auto-generated cache. It is not deleted automatically when switching characters. Click the "Clear Cache Folder" button on the left to manually free space.

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

| File | Description |
|------|-------------|
| `run.py` | Main program entry (GUI, event handling) |
| `src/__init__.py` | Package initialization |
| `src/i18n.py` | Internationalization module (Chinese/English/fiXmArge translation tables) |
| `src/bundleloader.py` | Bundle file loader (directory search, path memory) |
| `src/compositor.py` | Sprite extraction, component detection, character data extraction, image compositing |
| `src/tools.py` | Logging utilities |

## Tech Stack

- **[UnityPy](https://github.com/K0lb3/UnityPy)** — Unity bundle parsing
- **[Pillow](https://python-pillow.org/)** — Image processing and compositing
- **tkinter** — GUI framework

## Acknowledgments & License

### Original Game Info

The content extracted by this tool is from the game **"Mahou Shoujo no Majo Saiban" (Manosaba)**  
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

---

**Disclaimer**: This tool is intended for learning and personal research purposes only. The copyright of the extracted content belongs to the original game developer.

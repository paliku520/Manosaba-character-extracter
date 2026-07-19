# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

A tool for extracting character sprites from the game **"魔法少女の魔女审判" (Manosaba)** Unity bundle files. Supports automatic component detection, direct sprite export, or full character compositing.

## Features

- **Auto Detection** — Analyzes bundles for `SpriteRenderer` + `Transform` component data
- **Two Modes**:
  - No component data → exports all sprites as PNG
  - Has component data → choose between direct export or character compositing
- **Selected Sprite List** — Right panel displays filenames of all checked sprites in real time
- **Live Preview** — Auto-composites preview when toggling parts (500ms debounce)
- **Part Selection** — Parts grouped by category with thumbnail previews; Select All / Deselect All
- **Character Compositing** — Assembles full character image by position and sorting depth
- **Hierarchy Viewer** — TreeView displays component hierarchy
- **Progress Bar** — Shows real progress percentage for all time-consuming operations (loading, exporting, compositing)
- **Multi-language Support** — Built-in Simplified Chinese / English / fiXmArge (conlang); auto-detects system language
- **Cache Reuse** — Extracted character data cached in `temp/`; repeated loads skip re-extraction
- **Clear Cache Button** — One-click cache cleanup to free disk space
- **Adaptive Layout** — All panels remain usable and scrollable when window is resized
- **Path Memory** — Remembers the last selected game directory automatically
- **Custom Output Path** — Specify output directory via command-line argument

## Requirements

- Python 3.10+
- Dependencies listed in [`requirements.txt`](requirements.txt)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Adding a New Language

Edit `src/i18n.py`:
1. Define a language constant (e.g. `LANG_JP = "ja_JP"`)
2. Add it to the `LANGUAGE_CODES` list
3. Add entries for the new language to every translation key
4. Add a `lang.ja_JP` display name entry

> The dropdown updates automatically from `LANGUAGE_CODES` — no changes needed in `run.py`.

## Platform Compatibility

This project is primarily developed and tested on **Windows**. It has **not been thoroughly tested on other operating systems**.

- **Windows 10/11**: Primary development and testing platform — fully functional.
- **Linux**: Compatibility unknown. Tkinter and UnityPy may behave differently.
- **macOS**: Compatibility unknown. GUI and file path handling may have issues.

If you successfully run into issues on non-Windows platforms, feel free to open an Issue or Pull Request.

## Usage

### Basic
```bash
python run.py
```

### Command-line Arguments

```bash
python run.py --help
```

| Argument | Description |
|----------|-------------|
| `-h`, `--help` | Show help message |
| `-c`, `--clean` | Clear the output folder before startup |
| `-o <path>`, `--output <path>` | Specify output directory (absolute or relative to script root) |
| `--clear-cache` | Clear the cache folder and exit (without launching GUI) |

**Examples:**
```bash
# Show help
python run.py --help

# Clear default output and start
python run.py --clean

# Custom output path
python run.py --output D:/game_exports

# Clear cache only, no GUI
python run.py --clear-cache

# Combined
python run.py -c -o E:/exports
```

### Workflow

1. Click **Load Game Directory** → select the game root or `characters` folder
2. Click a character in the left character list
3. The tool auto-detects the bundle type:
   - **No component data** → confirmation dialog, then exports all sprites
   - **Has component data** → dialog asking how to proceed
4. When **Composite Character** is selected:
   - Check/uncheck parts in the **Part Selection** tab
   - The **Selected Sprites** panel lists all checked part filenames
   - Enable **Auto Update** for real-time composite preview
   - Click **Generate Composite** to manually composite
   - Click **Save Composite** to export as PNG

### Directory Structure

```
project root/
├── output/                ← Final composite images (user-saved)
│   └── <character>_composite.png
├── temp/                  ← Sprite cache (can be cleared manually; speeds up re-loads)
│   └── <character>/
│       ├── character_data.json   ← Hierarchy + part data
│       └── sprites/
│           ├── ArmL01.png
│           ├── Body.png
│           └── ...
├── src/                   ← Source code
├── run.py                 ← Main entry point
└── ...
```

> ℹ️ `temp/` is an auto-generated cache folder. It is **not** deleted automatically on character switch. Click the **Clear Cache** button on the left panel to free up space.

## Project Structure

| File | Description |
|------|-------------|
| `run.py` | Main entry point (GUI, event handling) |
| `src/__init__.py` | Package initialization |
| `src/i18n.py` | Internationalization module (CN/EN/fiXmArge translations) |
| `src/bundleloader.py` | Bundle file loader (directory search, path memory) |
| `src/compositor.py` | Sprite extraction, component detection, data extraction, image compositing |
| `src/tools.py` | Logging utility |

## Tech Stack

- **[UnityPy](https://github.com/K0lb3/UnityPy)** — Unity bundle parsing
- **[Pillow](https://python-pillow.org/)** — Image processing and compositing
- **tkinter** — GUI framework

## Credits & License

This project is a **deep refactor and performance-optimized version** of [KabeNaki](https://github.com/lingk7/KabeNaki) by [lingk7](https://github.com/lingk7). Thanks to the original author for the inspiration and architecture reference.

**Refactoring and improvements include:**
- **Architecture**: Monolithic file split into modular design (`bundleloader`, `compositor`, `tools`, etc.)
- **Performance**: Optimized UI responsiveness and data processing; eliminated unnecessary full UI rebuilds
- **Features**: Added multi-character management, batch directory scanning, path memory, hierarchy TreeView, and refined cache management

Both the original project and this project are licensed under the **GPL-3.0 License**.

See the [LICENSE](LICENSE) file for details.

---

**Disclaimer**: This tool is for learning and personal research purposes only. All extracted content is owned by the original game developers.

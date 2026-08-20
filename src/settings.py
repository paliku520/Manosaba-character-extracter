"""
应用设置管理模块 — 持久化用户配置（新版嵌套结构 v2）

配置文件: data/settings.json（程序根目录下 data/，设置隐藏属性避免用户直接接触）

新版数据结构（config_version = "2.0"）：
  {
    "global": { "mode", "config_version", "window", "theme",
                "lang", "export_count", "show_original_name", "no_spoiler_notice" },
    "game": { "<mode>": { "accent", "last_directory", "output_dir" }, ... }
  }
- global.window 为窗口大小/最大化状态（与 Electron 主进程共用；首次启动不预创建，
  由 Electron 在窗口关闭时写入）
- game.<mode> 为各作品独立配置；village / labyrinth 目前仅为占位 section（不实际应用）
- 旧版扁平结构（顶层 window/theme/accent/last_directory/output_dir/lang/...）自动迁移到新版
"""

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.logtools import log
from src.i18n import _


def _get_config_dir() -> Path:
    """返回配置目录（默认程序根目录下 data/；支持 MCE_DATA_DIR 环境变量重定向，兼容 PyInstaller 冻结环境）"""
    import os
    env = os.environ.get("MCE_DATA_DIR")
    if env:
        return Path(env) / "data"
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "data"


def _get_config_file() -> Path:
    """返回配置文件路径（data/settings.json，避免用户直接接触）"""
    return _get_config_dir() / "settings.json"


# 配置文件路径
CONFIG_FILE = _get_config_file()


def _hide_config_dir() -> None:
    """Windows 上给配置目录设置隐藏属性（普通用户看不到；目录隐藏不影响内部文件读写）"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # FILE_ATTRIBUTE_HIDDEN = 0x2（仅隐藏目录，文件本身保持普通属性以正常读写）
        ctypes.windll.kernel32.SetFileAttributesW(str(CONFIG_FILE.parent), 0x2)
    except Exception:
        pass


def _normalize_config_file() -> None:
    """Windows 上确保配置文件为普通属性（清除隐藏/系统，避免写入被拒）"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # FILE_ATTRIBUTE_NORMAL = 0x80
        ctypes.windll.kernel32.SetFileAttributesW(str(CONFIG_FILE), 0x80)
    except Exception:
        pass


def _migrate_legacy() -> None:
    """将旧版根目录 settings.json 迁移到 data/settings.json（若新文件尚不存在）"""
    try:
        old = CONFIG_FILE.parent.parent / "settings.json"
        if not old.exists() or not old.is_file() or old == CONFIG_FILE:
            return
        if not CONFIG_FILE.exists():
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            old.replace(CONFIG_FILE)
            _normalize_config_file()
            _hide_config_dir()
            log("info", f"Migrated settings: {old.name} -> {CONFIG_FILE}")
        else:
            old.unlink()  # 新文件已存在，移除旧文件避免混淆
    except OSError as e:
        log("warning", f"Failed to migrate legacy settings: {e}")

# 主题色可选值：default（默认绿）+ 各角色主题色
ACCENT_NAMES = (
    "default", "alisa", "anan", "coco", "ema", "hanna", "hiro", "jailer",
    "leia", "margo", "meruru", "miria", "nanoka", "noah", "sherry", "warden", "yuki",
)

# 配置版本号（写入 global.config_version）
CONFIG_VERSION = "2.0"

# 当前生效作品（决定读取 game.<mode> 哪个 section）
DEFAULT_MODE = "manosaba"

# 全部作品 mode：village / labyrinth 目前仅为占位（保留默认字段，暂不实际应用）
GAME_MODES = ("manosaba", "village", "labyrinth")

# 各作品独立配置的默认字段（game.<mode>）
_DEFAULT_GAME_SECTION = {
    "accent": "default",
    "last_directory": "",
    "output_dir": "",
}


def _default_settings() -> Dict[str, Any]:
    """新版默认配置骨架（village / labyrinth 为占位 section；不含 window，
    窗口状态由 Electron 在关闭时写入 global.window）"""
    return {
        "global": {
            "mode": DEFAULT_MODE,
            "config_version": CONFIG_VERSION,
            "theme": "dark",
        },
        "game": {m: dict(_DEFAULT_GAME_SECTION) for m in GAME_MODES},
    }


def _write_settings(data: Dict[str, Any]) -> None:
    """写入新版嵌套结构到配置文件（写前确保目录/文件可写并保持 data/ 隐藏）"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _normalize_config_file()   # 写前清除文件隐藏/系统属性，确保可写
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        _hide_config_dir()
    except OSError as e:
        log("warning", _("log.settings_save_failed", e=e))


def _normalize_settings(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """把（可能为旧版扁平结构的）设置数据归一化为新版嵌套结构。

    迁移规则：
    - 旧版顶层字段 window/theme/lang/export_count/show_original_name/no_spoiler_notice
      迁入 global（目标已有值时以新值为准，不覆盖）
    - 旧版 use_chinese_names（“显示中文名”）→ 新版 show_original_name（取反），仅当新值未设置
    - 旧版顶层 accent/last_directory/output_dir 迁入当前 mode 的 game.<mode> section
    - 确保所有 mode 都有完整默认字段（其他两款游戏 为占位）

    返回 (归一化后的数据, 是否发生了需要落盘的变更)。
    """
    data = copy.deepcopy(raw)

    # ── global ──
    if not isinstance(data.get("global"), dict):
        data["global"] = {}
    g = data["global"]
    if not isinstance(g.get("config_version"), str) or not g["config_version"]:
        g["config_version"] = CONFIG_VERSION
    if g.get("mode") not in GAME_MODES:
        g["mode"] = DEFAULT_MODE
    mode = g["mode"]

    # ── game ──
    if not isinstance(data.get("game"), dict):
        data["game"] = {}
    game = data["game"]

    # 旧版扁平字段迁移（仅迁移已存在的旧 window；不预创建，窗口状态由 Electron 写入）
    legacy_window = data.pop("window", None)
    if isinstance(legacy_window, dict) and not isinstance(g.get("window"), dict):
        g["window"] = legacy_window

    for src, dst in (
        ("theme", "theme"),
        ("lang", "lang"),
        ("export_count", "export_count"),
        ("show_original_name", "show_original_name"),
        ("no_spoiler_notice", "no_spoiler_notice"),
    ):
        if src in data and dst not in g:
            g[dst] = data.pop(src)
    if "use_chinese_names" in data and "show_original_name" not in g:
        g["show_original_name"] = not bool(data.pop("use_chinese_names"))

    # 当前 mode 的 section：原不存在时把旧版扁平字段迁入
    cur_section = game.get(mode)
    if not isinstance(cur_section, dict):
        cur_section = {}
        for src in ("accent", "last_directory", "output_dir"):
            if src in data:
                cur_section[src] = data.pop(src)
        game[mode] = cur_section

    # 确保所有 mode 都有完整默认字段
    for m in GAME_MODES:
        merged = dict(_DEFAULT_GAME_SECTION)
        sec = game.get(m)
        if isinstance(sec, dict):
            merged.update(sec)
        game[m] = merged

    return data, data != raw


def load_settings() -> Dict[str, Any]:
    """加载设置并归一化为新版嵌套结构（旧版扁平结构自动迁移；缺失/损坏时重建）"""
    _migrate_legacy()
    try:
        if CONFIG_FILE.exists():
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("settings.json root is not a dict")
            data, changed = _normalize_settings(raw)
        else:
            # 首次启动：直接写入新版默认骨架（避免父目录缺失导致持久化写入静默失败）
            data, changed = _default_settings(), True
        if changed:
            _write_settings(data)
        _hide_config_dir()
        return data
    except Exception as e:
        log("warning", f"Failed to load settings: {e}")
        _repair_config()
        data = _default_settings()
        _write_settings(data)
        _hide_config_dir()
        return data


def _repair_config() -> None:
    """配置文件损坏时自动修复：备份原文件（settings.json.bak）并重建为有效空配置"""
    try:
        _normalize_config_file()
        bak = CONFIG_FILE.with_name(CONFIG_FILE.name + ".bak")
        if CONFIG_FILE.exists() and not bak.exists():
            CONFIG_FILE.replace(bak)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({}, indent=2, ensure_ascii=False), encoding="utf-8")
        _hide_config_dir()
        log("info", _("log.settings_repaired", path=str(bak)))
    except OSError as e:
        log("warning", f"Failed to repair settings: {e}")


def save_settings(
    output_dir: Optional[Path] = None,
    lang: Optional[str] = None,
    last_directory: Optional[str] = None,
    theme: Optional[str] = None,
    accent: Optional[str] = None,
    export_count: Optional[int] = None,
    show_original_name: Optional[bool] = None,
    no_spoiler_notice: Optional[bool] = None,
    mode: Optional[str] = None,
) -> None:
    """保存设置到新版嵌套配置（只更新传入的字段，保留其余已有字段）

    - global：theme / lang / export_count / show_original_name / no_spoiler_notice / mode
    - game.<当前 mode>：accent / last_directory / output_dir（其他两款游戏 为占位）
    """
    data = load_settings()
    g = _global_section(data)
    if mode is not None and mode in GAME_MODES:
        g["mode"] = mode
    if lang is not None:
        g["lang"] = lang
    if theme is not None:
        g["theme"] = theme
    if export_count is not None:
        g["export_count"] = export_count
    if show_original_name is not None:
        g["show_original_name"] = bool(show_original_name)
    if no_spoiler_notice is not None:
        g["no_spoiler_notice"] = bool(no_spoiler_notice)

    section = _game_section(data, _mode_from(data))
    if output_dir is not None:
        section["output_dir"] = str(output_dir)
    if last_directory is not None:
        section["last_directory"] = str(last_directory)
    if accent is not None:
        section["accent"] = accent

    _write_settings(data)


def _global_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    """返回 global 段（缺失时返回空字典）"""
    g = settings.get("global")
    return g if isinstance(g, dict) else {}


def _mode_from(settings: Dict[str, Any]) -> str:
    """从（已归一化的）设置里取当前生效 mode，非法时回退 DEFAULT_MODE"""
    mode = _global_section(settings).get("mode")
    if isinstance(mode, str) and mode in GAME_MODES:
        return mode
    return DEFAULT_MODE


def _game_section(settings: Dict[str, Any], mode: Optional[str] = None) -> Dict[str, Any]:
    """返回指定 mode（默认当前生效 mode）的 game section（缺失时返回空字典）"""
    m = mode or _mode_from(settings)
    game = settings.get("game")
    section = game.get(m) if isinstance(game, dict) else None
    return section if isinstance(section, dict) else {}


def get_mode(default: str = DEFAULT_MODE) -> str:
    """返回当前生效作品 mode（决定读取 game.<mode> 哪个 section；未设置时返回 default）"""
    return _mode_from(load_settings())


def get_lang(default: Optional[str] = None) -> Optional[str]:
    """返回用户保存的语言代码（global.lang）；未设置时返回 default"""
    settings = load_settings()
    lang = _global_section(settings).get("lang")
    if isinstance(lang, str) and lang:
        return lang
    return default


def get_output_dir(default: Path) -> Path:
    """返回当前作品的输出目录（game.<mode>.output_dir，绝对路径）；未设置或非法时返回 default"""
    settings = load_settings()
    raw = _game_section(settings).get("output_dir")
    if raw:
        p = Path(raw)
        if p.is_absolute():
            return p
    return default


def get_last_directory(default: str = "") -> str:
    """返回当前作品上次使用的游戏目录（game.<mode>.last_directory）；未设置时返回 default"""
    settings = load_settings()
    raw = _game_section(settings).get("last_directory")
    if isinstance(raw, str) and raw:
        return raw
    return default


def get_theme(default: str = "dark") -> str:
    """返回用户保存的界面主题（global.theme，dark/light）；未设置或非法时返回 default"""
    settings = load_settings()
    theme = _global_section(settings).get("theme")
    if theme in ("dark", "light"):
        return theme
    return default


def get_accent(default: str = "default") -> str:
    """返回当前作品的主题色（game.<mode>.accent，default/角色名）；未设置或非法时返回 default"""
    settings = load_settings()
    accent = _game_section(settings).get("accent")
    if accent in ACCENT_NAMES:
        return accent
    return default


def get_export_count(default: int = 0) -> int:
    """返回累计导出精灵数（global.export_count）；未设置时返回 default"""
    settings = load_settings()
    raw = _global_section(settings).get("export_count")
    if isinstance(raw, bool):
        return default
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return default


def get_show_original_name(default: bool = False) -> bool:
    """返回是否显示原始文件名（global.show_original_name）；未设置时返回 default

    旧版扁平字段 use_chinese_names 的迁移已在 load_settings 归一化时完成。
    """
    settings = load_settings()
    raw = _global_section(settings).get("show_original_name")
    if isinstance(raw, bool):
        return raw
    return default


def get_no_spoiler(default: bool = False) -> bool:
    """返回是否已勾选“不再提示”剧透警告（global.no_spoiler_notice）；未设置时返回 default"""
    settings = load_settings()
    raw = _global_section(settings).get("no_spoiler_notice")
    if isinstance(raw, bool):
        return raw
    return default

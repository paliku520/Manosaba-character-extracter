"""
应用设置管理模块 — 持久化用户配置（如输出目录）

配置文件: data/settings.json（程序根目录下 data/，设置隐藏属性避免用户直接接触）
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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


def load_settings() -> Dict[str, Any]:
    """加载设置（缺失或损坏时返回空字典，并自动备份+重建损坏的配置文件）"""
    _migrate_legacy()
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            raise ValueError("settings.json root is not a dict")
    except Exception as e:
        log("warning", f"Failed to load settings: {e}")
        _repair_config()
    return {}


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
) -> None:
    """保存设置到配置文件（只更新传入的字段，保留其余已有字段）"""
    data = load_settings()
    if output_dir is not None:
        data["output_dir"] = str(output_dir)
    if lang is not None:
        data["lang"] = lang
    if last_directory is not None:
        data["last_directory"] = str(last_directory)
    if theme is not None:
        data["theme"] = theme
    if accent is not None:
        data["accent"] = accent
    if export_count is not None:
        data["export_count"] = export_count
    if show_original_name is not None:
        data["show_original_name"] = bool(show_original_name)
    if no_spoiler_notice is not None:
        data["no_spoiler_notice"] = bool(no_spoiler_notice)
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _normalize_config_file()   # 写前清除文件隐藏/系统属性，确保可写
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _hide_config_dir()
    except OSError as e:
        log("warning", _("log.settings_save_failed", e=e))


def get_lang(default: Optional[str] = None) -> Optional[str]:
    """返回用户保存的语言代码；未设置时返回 default"""
    settings = load_settings()
    lang = settings.get("lang")
    if isinstance(lang, str) and lang:
        return lang
    return default


def get_output_dir(default: Path) -> Path:
    """返回用户设置的输出目录（绝对路径）；未设置或非法时返回 default"""
    settings = load_settings()
    raw = settings.get("output_dir")
    if raw:
        p = Path(raw)
        if p.is_absolute():
            return p
    return default


def get_last_directory(default: str = "") -> str:
    """返回上次使用的游戏目录（未设置时返回 default）"""
    settings = load_settings()
    raw = settings.get("last_directory")
    if isinstance(raw, str) and raw:
        return raw
    return default


def get_theme(default: str = "dark") -> str:
    """返回用户保存的界面主题（dark/light）；未设置或非法时返回 default"""
    settings = load_settings()
    theme = settings.get("theme")
    if theme in ("dark", "light"):
        return theme
    return default


def get_accent(default: str = "default") -> str:
    """返回用户保存的主题色（default/角色名）；未设置或非法时返回 default"""
    settings = load_settings()
    accent = settings.get("accent")
    if accent in ACCENT_NAMES:
        return accent
    return default


def get_export_count(default: int = 0) -> int:
    """返回累计导出精灵数（未设置时返回 default）"""
    settings = load_settings()
    raw = settings.get("export_count")
    if isinstance(raw, bool):
        return default
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return default


def get_show_original_name(default: bool = False) -> bool:
    """返回是否显示原始文件名（未设置时返回 default；兼容旧版 use_chinese_names 字段）"""
    settings = load_settings()
    if isinstance(settings.get("show_original_name"), bool):
        return settings["show_original_name"]
    # 旧字段迁移：旧“显示中文名”开启 → 新“显示原始文件名”关闭
    raw = settings.get("use_chinese_names")
    if isinstance(raw, bool):
        return not raw
    return default


def get_no_spoiler(default: bool = False) -> bool:
    """返回是否已勾选“不再提示”剧透警告（未设置时返回 default）"""
    settings = load_settings()
    raw = settings.get("no_spoiler_notice")
    if isinstance(raw, bool):
        return raw
    return default

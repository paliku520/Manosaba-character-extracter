"""
应用设置管理模块 — 持久化用户配置（如输出目录）

配置文件: settings.json（程序根目录）
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from src.logtools import log
from src.i18n import _


def _get_config_file() -> Path:
    """返回配置文件路径（程序根目录，兼容 PyInstaller 冻结环境）"""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "settings.json"


# 配置文件路径
CONFIG_FILE = _get_config_file()


def load_settings() -> Dict[str, Any]:
    """加载设置（缺失或损坏时返回空字典）"""
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as e:
        log("warning", f"Failed to load settings: {e}")
    return {}


def save_settings(
    output_dir: Optional[Path] = None,
    lang: Optional[str] = None,
    last_directory: Optional[str] = None,
) -> None:
    """保存设置到配置文件（只更新传入的字段，保留其余已有字段）"""
    data = load_settings()
    if output_dir is not None:
        data["output_dir"] = str(output_dir)
    if lang is not None:
        data["lang"] = lang
    if last_directory is not None:
        data["last_directory"] = last_directory
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        log("warning", _("log.settings_save_failed", e=e))


def get_last_directory(default: Optional[str] = None) -> Optional[str]:
    """返回上次选择的游戏目录（路径不存在时回退到 default）"""
    settings = load_settings()
    raw = settings.get("last_directory")
    if isinstance(raw, str) and raw and Path(raw).exists():
        return raw
    return default


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

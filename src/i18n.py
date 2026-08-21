"""
国际化 / 本地化支持（i18n）

翻译表按「语言 × 作品」拆分到 YAML 文件（项目根 i18n/ 目录）：

    i18n/
    ├── common/                    # 通用文案（所有游戏共用）
    │   ├── zh_CN.yaml
    │   ├── en_US.yaml
    │   ├── ja_JP.yaml
    │   └── mgl_MG.yaml
    └── games/
        ├── manosaba/              # 《魔法少女的魔女审判》专有（角色名、剧情术语、含游戏名文案等）
        │   ├── zh_CN.yaml
        │   ├── en_US.yaml
        │   ├── ja_JP.yaml
        │   └── mgl_MG.yaml        # fiXmArge（魔女语）为 manosaba 独有语种
        ├── village/               # 《魔法少女的因习村》（预留）
        └── labyrinth/             # 《主播少女的秘密账号迷宫》（预留）

加载规则：
  - 先加载 common/<lang>.yaml（通用界面文案）
  - 再加载当前作品 games/<mode>/<lang>.yaml（专有名词，覆盖/补充同名键）
  - YAML 键名按 `.` 分段嵌套（如 app.status.ready = app → status → ready），
    加载时自动扁平化为 {key: {lang: text}} 的 T 表。
  - 保持原有 _() / T / set_lang / current_lang / LANGUAGE_CODES 接口不变。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict

import yaml


# ── 语言代码 ──────────────────────────────────────────────
LANG_CN = "zh_CN"       # 简体中文
LANG_EN = "en_US"       # 英语
LANG_JA = "ja_JP"       # 日本語
LANG_MGL = "mgl_MG"     # 魔女语 (fiXmArge Language / Magical girl language)(架空语言) — manosaba 独有语种

LANGUAGE_CODES = [LANG_CN, LANG_EN, LANG_JA, LANG_MGL]

# 全部作品 mode（与 src/settings.GAME_MODES 保持一致；此处不 import 以避免循环依赖）
GAME_MODES = ("manosaba", "village", "labyrinth")


# ── 当前语言 / 当前作品 ────────────────────────────────────
_current_lang: str = LANG_CN
_current_mode: str = "manosaba"


def _get_i18n_dir() -> Path:
    """i18n/ 目录（兼容 PyInstaller 冻结环境：打包后从 _MEIPASS 读取）"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "i18n"


I18N_DIR = _get_i18n_dir()


def _flatten(data: dict, prefix: str = "") -> Dict[str, str]:
    """把嵌套 dict 扁平化为 {'a.b.c': text}，仅保留字符串叶子"""
    out: Dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        elif isinstance(value, str):
            out[full] = value
    return out


def _load_lang_yaml(path: Path) -> Dict[str, str]:
    """读取单个语言 yaml，返回扁平 {key: text}；文件缺失/损坏时返回空表"""
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return _flatten(data)


# ── 翻译表（由 yaml 合并构建） ─────────────────────────────
T: Dict[str, Dict[str, str]] = {}


def _reload() -> None:
    """按 通用目录 + 当前作品目录 重建 T 表"""
    global T
    merged: Dict[str, Dict[str, str]] = {}

    for lang in LANGUAGE_CODES:
        data = _load_lang_yaml(I18N_DIR / "common" / f"{lang}.yaml")
        for key, text in data.items():
            merged.setdefault(key, {})[lang] = text

    mode_dir = I18N_DIR / "games" / _current_mode
    for lang in LANGUAGE_CODES:
        data = _load_lang_yaml(mode_dir / f"{lang}.yaml")
        for key, text in data.items():
            merged.setdefault(key, {})[lang] = text

    T = merged


def _detect_mode() -> str:
    """从 data/settings.json 读取 global.mode（不 import settings 以避免循环依赖）"""
    try:
        env = os.environ.get("MCE_DATA_DIR")
        if env:
            cfg = Path(env) / "data" / "settings.json"
        elif getattr(sys, "frozen", False):
            cfg = Path(sys.executable).parent / "data" / "settings.json"
        else:
            cfg = Path(__file__).resolve().parent.parent / "data" / "settings.json"
        if cfg.is_file():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            mode = (data.get("global") or {}).get("mode")
            if isinstance(mode, str) and mode in GAME_MODES:
                return mode
    except Exception:
        pass
    return "manosaba"


_current_mode = _detect_mode()
_reload()


# ── 语言 / 作品切换 ──────────────────────────────────────

def current_lang() -> str:
    """返回当前语言代码"""
    return _current_lang


def set_lang(code: str) -> None:
    """切换当前语言（翻译表四种语言均已加载，仅改变取词）"""
    global _current_lang
    _current_lang = code


def set_mode(mode: str) -> None:
    """切换当前作品模式（manosaba / village / labyrinth），重建翻译表。

    通常由调用方在切换作品时调用（settings.json 的 global.mode 变更后）。
    """
    global _current_mode
    _current_mode = mode if mode in GAME_MODES else "manosaba"
    _reload()


# ── 翻译函数 ──────────────────────────────────────────────

def _(key: str, **kwargs) -> str:
    """
    获取当前语言的翻译文本。

    Args:
        key: 翻译键
        **kwargs: 格式化参数，例如 _("app.status.loaded", count=5)

    Returns:
        翻译后的字符串，若 key 不存在则返回 key 本身
    """
    entry = T.get(key)
    if entry is None:
        return key
    text = entry.get(_current_lang, entry.get(LANG_CN, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

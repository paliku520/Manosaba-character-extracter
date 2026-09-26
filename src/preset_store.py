# -*- coding: utf-8 -*-
"""用户预设存储 —— 记录一批部件的 sorting_order，供「预设」下拉一键恢复。

存储位置:
    内置预设源头: builtin/presets/<角色>/<名称>.json（随程序分发、只读；打包版取
                  PyInstaller 包内的 builtin_presets/）
    运行期副本:   data/presets/<角色>/<名称>.json（用户可见；启动 / 读取时自动从源头
                  镜像与自愈，被删或损坏都会写回）

单个预设文件结构:
    {
      "character_name": "hiro",
      "name": "Default",
      "builtin": true,          # 内置预设：不可删除 / 不可覆盖 / 可自动恢复
      "parts": [{"name": "Body", "sorting_order": 1}, ...],
      "sketch": {"text": "", "size": 56, "align": "center"},
      "updated": "2026-09-26 12:00:00"
    }

预设由用户自行保存 / 删除（前端部件页「预设」工具栏）；
应用时前端按 sorting_order 在当前部件表里匹配勾选（同名优先）。
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.logtools import log
from src.settings import get_presets_dir

# 预设名长度上限（前端输入框同值）
MAX_PRESET_NAME = 40

# 文件名非法字符（与 _safe_name 替换的集合一致；预设名不允许包含，避免静默改名）
INVALID_NAME_CHARS = '<>:"/\\|?*'


class PresetNameError(ValueError):
    """预设名不合法（空 / 超长 / 含非法字符 / 与其他预设撞文件名）"""

# 素描本文字参数范围（与前端滑块 32..100 对应，写入时做一次宽松夹取）
_SKETCH_SIZE_MIN, _SKETCH_SIZE_MAX = 12, 200
_ALIGNS = ("left", "center", "right")

# 打包版内置预设目录名（scripts/build_electron_backend.py 通过 --add-data 把仓库
# builtin/ 映射为该名字；开发版直接读仓库 builtin/presets）
_FROZEN_BUILTIN_DIR = "builtin_presets"


class BuiltinPresetError(Exception):
    """内置预设受保护：不允许删除 / 覆盖 / 同名新建"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def builtin_dir() -> Path:
    """内置预设源头目录（打包版取安装包内资源，开发版取仓库 builtin/presets）"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / _FROZEN_BUILTIN_DIR
    return _repo_root() / "builtin" / "presets"


def _safe_name(name: str) -> str:
    """角色名 / 预设名 → 合法文件名（非法字符替换为下划线，去掉结尾的点与空格）"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", (name or "").strip()).rstrip(". ")
    return cleaned or "unknown"


def preset_dir(character_name: str) -> Path:
    """返回角色的预设目录（data/presets/<角色>/）"""
    return get_presets_dir() / _safe_name(character_name)


def preset_file(character_name: str, preset_name: str) -> Path:
    """返回单个预设的文件路径（data/presets/<角色>/<预设名>.json）"""
    return preset_dir(character_name) / f"{_safe_name(preset_name)}.json"


def validate_preset_name(preset_name: str) -> str:
    """校验并返回规范化后的预设名；不合法抛 PresetNameError（消息即错误码）。

    规则：非空；长度 ≤ MAX_PRESET_NAME；不含 < > : " / \\ | ? * 与控制字符；
    不以点或空格结尾（Windows 会静默去尾，导致名字与文件名不一致）。
    """
    raw = (preset_name or "").strip()
    if not raw:
        raise PresetNameError("empty")
    if len(raw) > MAX_PRESET_NAME:
        raise PresetNameError("too_long")
    if any(c in INVALID_NAME_CHARS for c in raw) or any(ord(c) < 32 for c in raw):
        raise PresetNameError("invalid_chars")
    if raw[-1] in ". ":
        raise PresetNameError("trailing_dot_space")
    return raw


def find_name_conflict(character_name: str, preset_name: str) -> Optional[str]:
    """返回与 preset_name 落成同一个文件的**其他**预设名（大小写撞名等），无则 None"""
    try:
        target = preset_file(character_name, preset_name)
    except Exception:
        return None
    for other in list_presets(character_name):
        if other["name"] == preset_name:
            continue
        if preset_file(character_name, other["name"]) == target:
            return other["name"]
    return None


# ── 内置预设：源头清单 / 镜像自愈 / 保护判定 ───────────────

def _read_json(path: Path) -> Optional[Dict]:
    """读取 JSON 文件；缺失 / 损坏 / 不是对象 一律返回 None"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _builtin_sources(character_name: Optional[str] = None) -> List[Tuple[str, str, Dict]]:
    """内置预设源头清单 [(角色, 预设名, 预设数据)]；指定角色时只看该角色。

    源头文件缺失 / 损坏只记 warning 并跳过，不阻断预设功能。
    """
    src = builtin_dir()
    if not src.is_dir():
        return []
    pattern = f"{_safe_name(character_name)}/*.json" if character_name else "*/*.json"
    out: List[Tuple[str, str, Dict]] = []
    for path in sorted(src.glob(pattern)):
        raw = _read_json(path)
        if raw is None:
            log("warning", f"[preset] 内置预设源头损坏，已跳过: {path.name}")
            continue
        char = path.parent.name            # 目录名权威（不信任文件里的值）
        raw["builtin"] = True
        raw["character_name"] = char
        out.append((char, str(raw.get("name") or path.stem), raw))
    return out


def _same_as_source(current: Dict, source: Dict) -> bool:
    """运行期副本与源头是否一致（只比较影响合成的字段，且必须带 builtin 标记）"""
    return (
        current.get("name") == source.get("name")
        and current.get("builtin") is True
        and current.get("parts") == source.get("parts")
        and _norm_sketch(current.get("sketch")) == _norm_sketch(source.get("sketch"))
    )


def ensure_builtins(character_name: Optional[str] = None) -> int:
    """确保内置预设的运行期副本存在且正确（缺失 / 损坏 / 被改动 → 从源头写回）。

    返回本次写回的预设数量；调用成本极低（几个小 JSON 的读+比对）。
    """
    healed = 0
    for char, name, source in _builtin_sources(character_name):
        dst = preset_file(char, name)
        current = _read_json(dst) if dst.is_file() else None
        if current is not None and _same_as_source(current, source):
            continue
        try:
            _write_json(dst, source)
            healed += 1
            log("info", f"[preset] 已（重新）写入内置预设 {char}/{name}")
        except OSError as e:
            log("warning", f"[preset] 写入内置预设失败 {char}/{name}: {e}")
    return healed


def is_builtin(character_name: str, preset_name: str) -> bool:
    """该名字是否属于内置预设（按源头判定；运行期文件被删也依然为真）"""
    return any(name == preset_name for _, name, _ in _builtin_sources(character_name))


def load_presets(character_name: str) -> Dict[str, Dict]:
    """读取角色的全部预设 {预设名: 预设数据}；目录缺失时返回 {}

    读取前先确保内置预设已镜像 / 自愈，所以「Default」永远存在且内容完整。
    """
    try:
        ensure_builtins(character_name)
    except Exception as e:      # 自愈失败不影响正常读取
        log("warning", f"[preset] 内置预设自愈失败 {character_name}: {e}")
    folder = preset_dir(character_name)
    if not folder.is_dir():
        return {}
    presets: Dict[str, Dict] = {}
    for path in sorted(folder.glob("*.json")):
        raw = _read_json(path)
        if raw is None:
            log("warning", f"[preset] 读取预设失败（已跳过）: {path.name}")
            continue
        presets[str(raw.get("name") or path.stem)] = raw
    return presets


def list_presets(character_name: str) -> List[Dict]:
    """列出角色的预设：内置优先，其余按名称；每项含 name / parts / sketch / updated / builtin"""
    presets = load_presets(character_name)
    result: List[Dict] = []
    for name, preset in sorted(
        presets.items(), key=lambda kv: (not bool(kv[1].get("builtin")), kv[0])
    ):
        if not isinstance(preset, dict):
            continue
        result.append({
            "name": name,
            "parts": preset.get("parts") or [],
            "sketch": _norm_sketch(preset.get("sketch")),
            "updated": preset.get("updated") or "",
            "builtin": bool(preset.get("builtin")),
        })
    return result


def save_preset(
    character_name: str,
    preset_name: str,
    parts: Optional[List[Dict]],
    sketch: Optional[Dict] = None,
) -> Dict:
    """写入 / 覆盖一个预设，返回保存后的预设数据（含 name）。

    Args:
        character_name: 角色名
        preset_name:    预设名（空名抛 ValueError）
        parts:          [{"name": 部件名, "sorting_order": int}, ...]
        sketch:         {"text": str, "size": int, "align": left/center/right}
    """
    name = validate_preset_name(preset_name)

    # 内置预设名受保护：不允许覆盖 / 同名新建（按源头判定，副本被删也拒绝）
    path = preset_file(character_name, name)
    existing = _read_json(path) if path.is_file() else None
    if is_builtin(character_name, name) or (existing or {}).get("builtin"):
        raise BuiltinPresetError(name)
    # 与其他预设落成同一文件（大小写/非法字符撞名）时拒绝，避免静默改名或误覆盖
    conflict = find_name_conflict(character_name, name)
    if conflict:
        raise PresetNameError("conflict")

    entry: Dict[str, Any] = {
        "character_name": character_name,
        "name": name,
        "builtin": False,
        "parts": [
            {"name": str(p.get("name", "")), "sorting_order": _to_int(p.get("sorting_order", 0))}
            for p in (parts or [])
            if p.get("name")
        ],
        "sketch": _norm_sketch(sketch),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_json(path, entry)
    return entry


def delete_preset(character_name: str, preset_name: str) -> bool:
    """删除一个预设文件；内置预设抛 BuiltinPresetError；不存在返回 False

    （角色目录空了则一并移除）
    """
    path = preset_file(character_name, preset_name)
    existing = _read_json(path) if path.is_file() else None
    if is_builtin(character_name, preset_name) or (existing or {}).get("builtin"):
        raise BuiltinPresetError(preset_name)
    if existing is None and not path.is_file():
        return False
    path.unlink()
    folder = preset_dir(character_name)
    try:
        if not any(folder.iterdir()):
            folder.rmdir()
    except OSError:
        pass
    return True


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Dict) -> None:
    """原子写入预设 JSON（先写临时文件再替换，避免中断留下半截 JSON）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _norm_sketch(sketch: Optional[Dict]) -> Dict:
    """规范化素描本参数（非法值回退默认：无文字 / 56 / center）"""
    sk = sketch if isinstance(sketch, dict) else {}
    size = _to_int(sk.get("size", 56))
    size = max(_SKETCH_SIZE_MIN, min(_SKETCH_SIZE_MAX, size))
    align = str(sk.get("align") or "center").lower()
    return {
        "text": str(sk.get("text") or ""),
        "size": size,
        "align": align if align in _ALIGNS else "center",
    }


def _to_int(v: object) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0

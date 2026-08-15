# -*- coding: utf-8 -*-
"""生成每个角色的 mask_mapping.json

从游戏 bundle 提取真实数据（材质 → 混合方式 + stencil 遮罩分组），
与 temp/<角色>/character_data.json 的部件清单交叉，
为每个角色生成 mask_mapping.json（放在同一文件夹）。

用法:
    python src/generate_mask_mapping.py [temp_dir] [characters_dir] [--dry]

默认:
    temp_dir      = <项目根>/temp
    characters_dir = E:\\steam\\steamapps\\common\\manosaba_game\\
                     manosaba_Data\\StreamingAssets\\aa\\StandaloneWindows64\\
                     naninovel-characters_assets_naninovel\\characters
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import UnityPy

DEFAULT_CHARS_DIR = (
    Path(r"E:\steam\steamapps\common\manosaba_game")
    / "manosaba_Data"
    / "StreamingAssets"
    / "aa"
    / "StandaloneWindows64"
    / "naninovel-characters_assets_naninovel"
    / "characters"
)


# ---------------------------------------------------------------------------
# 材质解析
# ---------------------------------------------------------------------------
def parse_material(mat_name: str):
    """解析材质名 -> (blend_mode, role, stencil_ref)

    blend_mode: normal / multiply / softlight / overlay
    role:       'mask'（写入 stencil，定义裁剪区域）
                'masked'（读取 stencil，被裁剪进区域）
                'none'（不参与遮罩）
    """
    base = mat_name.split("#")[0]
    if "Multiply" in base:
        blend = "multiply"
    elif "Softlight" in base:
        blend = "softlight"
    elif "Overlay" in base:
        blend = "overlay"
    elif "Default" in base:
        blend = "normal"
    else:
        blend = base.strip() or "normal"

    role = "none"
    ref = None
    if "#" in mat_name:
        for seg in mat_name.split("#")[1:]:
            m = re.match(r"^(Mask|Masked)_Ref(\d+)", seg.strip())
            if m:
                role = "mask" if m.group(1) == "Mask" else "masked"
                ref = int(m.group(2))
    return blend, role, ref


def part_materials_from_env(env):
    """从已加载的 UnityPy env 读取 {部件名: {material, blend_mode, role, ref}}

    供提取流程复用已加载的 env（避免重复解析 bundle）；独立 CLI 走 load_bundle_part_materials。
    """
    # GameObject: path_id -> name
    go_names = {}
    for obj in env.objects:
        if obj.type.name != "GameObject":
            continue
        try:
            data = obj.read()
            go_names[obj.path_id] = getattr(data, "m_Name", f"GO_{obj.path_id}")
        except Exception:
            pass

    # Material: path_id -> name
    mat_names = {}
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        try:
            data = obj.read()
            mat_names[obj.path_id] = getattr(data, "m_Name", "")
        except Exception:
            pass

    # SpriteRenderer -> (go_name, mat_name) -> 解析
    part_materials = {}
    for obj in env.objects:
        if obj.type.name != "SpriteRenderer":
            continue
        try:
            data = obj.read()
            go_ref = getattr(data, "m_GameObject", None)
            go_id = getattr(go_ref, "m_PathID", 0)
            mat_ref = getattr(data, "m_Materials", None)
            mat_id = None
            if mat_ref and len(mat_ref) > 0:
                mat_id = getattr(mat_ref[0], "m_PathID", None)
            go_name = go_names.get(go_id)
            if go_name is None:
                continue
            mat_name = mat_names.get(mat_id, "")
            blend, role, ref = parse_material(mat_name)
            part_materials[go_name] = {
                "material": mat_name,
                "blend_mode": blend,
                "role": role,
                "ref": ref,
            }
        except Exception:
            continue
    return part_materials


def load_bundle_part_materials(bundle_path: Path):
    """加载 bundle，返回 {部件名: {material, blend_mode, role, ref}}"""
    env = UnityPy.load(str(bundle_path))
    try:
        return part_materials_from_env(env)
    finally:
        try:
            env.files.clear()
        except Exception:
            pass


def build_mask_mapping(char_data: dict, part_materials: dict) -> dict:
    """由 character_data 与 bundle 材质信息生成 mask_mapping 结构

    返回:
        {
            "character_name": str,
            "mask_mapping":  {
                # 普通部件（role: mask=定义裁剪区域 / none=不受遮罩）
                "<部件>": {"blend_mode": str, "role": str, "stencil_ref": int|None,
                           "mask_parts": [关联的 ClippingMask 部件]},
            },
            "clipping_masks": {
                # 被裁剪的叠加层（ClippingMask_*，role=masked）
                "<部件>": {"blend_mode": str, "role": "masked", "stencil_ref": int},
            },
        }
    """
    td_parts = char_data.get("transform_data", [])
    td_names = {p["name"] for p in td_parts}

    # 1) 收集遮罩组: stencil_ref -> 被裁剪的 ClippingMask 部件（仅统计部件清单中存在的）
    masked_by_ref = {}  # ref -> [part_name]
    for name, info in part_materials.items():
        if name not in td_names:
            continue
        if info["role"] == "masked" and info["ref"] is not None:
            masked_by_ref.setdefault(info["ref"], []).append(name)

    # 2) 拆分: 普通部件（role=mask/none）与 ClippingMask 部件（role=masked）
    mask_mapping = {}
    clipping_masks = {}
    for p in td_parts:
        name = p["name"]
        info = part_materials.get(name)
        if info is None:
            # character_data 有但 bundle 无对应 SR（兜底）
            info = {"blend_mode": "normal", "role": "none", "ref": None}
        blend, role, ref = info["blend_mode"], info["role"], info["ref"]
        entry = {"blend_mode": blend, "role": role, "stencil_ref": ref}
        if role == "masked":
            clipping_masks[name] = entry
        else:
            mask_parts = (
                sorted(masked_by_ref.get(ref, []))
                if role == "mask" and ref is not None
                else []
            )
            entry["mask_parts"] = mask_parts
            mask_mapping[name] = entry

    return {
        "character_name": char_data.get("character_name", ""),
        "mask_mapping": mask_mapping,
        "clipping_masks": clipping_masks,
    }


def build_mask_mapping_from_env(env, char_data: dict) -> dict:
    """从已加载的 UnityPy env 直接构建 mask_mapping（提取流程复用 env，避免重复加载 bundle）"""
    return build_mask_mapping(char_data, part_materials_from_env(env))


def generate_for_character(temp_dir: Path, chars_dir: Path, name: str) -> dict:
    """为单个角色生成 mask_mapping.json，返回诊断信息"""
    char_dir = temp_dir / name
    json_path = char_dir / "character_data.json"
    if not json_path.exists():
        return {"name": name, "status": "skip", "reason": "no character_data.json"}

    bundle_path = chars_dir / f"{name}.bundle"
    if not bundle_path.exists():
        return {"name": name, "status": "skip", "reason": "no bundle"}

    char_data = json.loads(json_path.read_text(encoding="utf-8"))
    part_materials = load_bundle_part_materials(bundle_path)

    result = build_mask_mapping(char_data, part_materials)

    out_path = char_dir / "mask_mapping.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 诊断统计
    td_names = [p["name"] for p in char_data.get("transform_data", [])]
    missing = [n for n in td_names if n not in part_materials]
    clippers = [n for n, i in part_materials.items() if i["role"] == "masked"]
    unparsed = [n for n, i in part_materials.items() if i["role"] == "none"]
    return {
        "name": name,
        "status": "ok",
        "parts": len(td_names),
        "materials": len(part_materials),
        "missing_in_bundle": missing,
        "clipping_mask_parts": clippers,
        "no_mask_parts": unparsed,
        "out": str(out_path),
    }


def main():
    parser = argparse.ArgumentParser(description="生成角色 mask_mapping.json")
    parser.add_argument("temp_dir", nargs="?", default=str(BASE / "temp"))
    parser.add_argument("characters_dir", nargs="?", default=str(DEFAULT_CHARS_DIR))
    parser.add_argument("--dry", action="store_true", help="只诊断，不写文件")
    args = parser.parse_args()

    temp_dir = Path(args.temp_dir)
    chars_dir = Path(args.characters_dir)
    if not chars_dir.exists():
        print(f"[ERROR] characters 目录不存在: {chars_dir}")
        sys.exit(1)

    report = []
    for char_dir in sorted(temp_dir.iterdir()):
        if not char_dir.is_dir():
            continue
        diag = generate_for_character(temp_dir, chars_dir, char_dir.name)
        report.append(diag)

    # 汇总写到 UTF-8 文件（控制台是 GBK）
    out = []
    for d in report:
        if d["status"] == "ok":
            out.append(
                f"[OK] {d['name']}: parts={d['parts']} materials={d['materials']} "
                f"clippers={d['clipping_mask_parts']} missing={d['missing_in_bundle']}"
            )
        else:
            out.append(f"[SKIP] {d['name']}: {d.get('reason')}")
    report_path = BASE / "temp" / "_mask_mapping_report.txt"
    report_path.write_text("\n".join(out), encoding="utf-8")
    print("report:", report_path)


if __name__ == "__main__":
    main()

"""
公共版本信息 —— exe / 安装器版本信息的**单一数据源**

使用方：
  - scripts/build_electron_backend.py → backend.exe 的版本信息（make_version_file）
  - scripts/build_electron.py         → electron/package.json 的 author（安装器 CompanyName 来源）
  - electron/electron-builder.yml     → copyright 需与本文件 APP_COPYRIGHT 保持一致

个人业余开发者无公司时，可将 APP_COMPANY 填为自己的昵称 / GitHub 用户名。
"""

import re
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# ── exe 版本信息（可自行修改）──────────────────────
# 写入 exe 的详细信息（右键 exe → 属性 → 详细信息），可降低杀软误报。
# 个人业余开发者无公司时，可将 APP_COMPANY 填为自己的昵称 / GitHub 用户名。
# 注：APP_COMPANY 用全角括号 —— npm 的 person 解析器会把 ASCII 圆括号内容当 URL 剥离，全角可保留完整显示。
APP_COMPANY = "paliku520（云野风云）"                                              # 公司/开发者名称
APP_PRODUCT_NAME = "Manosaba Character Extracter"                                # 产品名称
APP_DESCRIPTION = "Manosaba 角色立绘提取与合成工具"                                  # 文件说明
APP_COPYRIGHT = "Copyright (c) 2026 paliku520. Licensed under GPL-3.0."          # 版权信息


def make_version_file(
    name: str,
    company: Optional[str] = None,
    product_name: Optional[str] = None,
    description: Optional[str] = None,
    copyright_: Optional[str] = None,
) -> Path:
    """生成 PyInstaller 版本信息文件（提供 exe 文件版本/产品名称等，降低杀软误报）。

    版本号从 src/version.py 的 __version__ 读取（单一数据源），自动转成 4 段。
    版本信息字段优先取传入参数，未提供时回退到本模块顶部 APP_* 常量。
    """
    # 传入参数优先，否则使用顶部常量
    company = company or APP_COMPANY
    product_name = product_name or APP_PRODUCT_NAME
    description = description or APP_DESCRIPTION
    copyright_ = copyright_ or APP_COPYRIGHT

    sys.path.insert(0, str(PROJECT_ROOT))
    from src.version import __version__

    # 版本号可能带后缀（如 v1.2.0-prewiew-1、v1.2.0-hotfix-2），只取前导数字段作为 4 段版本
    m = re.match(r"(\d+(?:\.\d+)*)", __version__)
    ver_digits = m.group(1) if m else "0"
    parts = ver_digits.split(".")
    while len(parts) < 4:
        parts.append("0")
    ver = tuple(int(p) for p in parts[:4])
    ver_str = ".".join(str(v) for v in ver)
    # 属性中显示带 v 的完整版本号（如 v1.2.0-prewiew-1）；FixedFileInfo 仍用 4 段数字供系统比较
    display_ver = f"v{__version__}"

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({ver[0]}, {ver[1]}, {ver[2]}, {ver[3]}),
    prodvers=({ver[0]}, {ver[1]}, {ver[2]}, {ver[3]}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'{company}'),
           StringStruct(u'FileDescription', u'{description}'),
           StringStruct(u'FileVersion', u'{display_ver}'),
           StringStruct(u'InternalName', u'{name}'),
           StringStruct(u'LegalCopyright', u'{copyright_}'),
           StringStruct(u'OriginalFilename', u'{name}.exe'),
           StringStruct(u'ProductName', u'{product_name}'),
           StringStruct(u'ProductVersion', u'{display_ver}')]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    vf = PROJECT_ROOT / "build" / "version_info.txt"
    vf.parent.mkdir(parents=True, exist_ok=True)
    vf.write_text(content, encoding="utf-8")
    print(f"[INFO] 已生成版本信息文件: {vf} (v{ver_str})")
    return vf

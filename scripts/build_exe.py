"""
打包脚本 — 使用 PyInstaller 将项目封装为 exe（保留控制台）

使用方法:
    python scripts\build_exe.py                          # 默认 onedir 模式
    python scripts\build_exe.py --onefile                # 打包为单个 exe
    python scripts\build_exe.py --name "MyApp"           # 自定义名称
    python scripts\build_exe.py --icon "assets/icon.ico"   # 自定义图标
    python scripts\build_exe.py -h                       # 查看完整帮助

输出目录: dist/
  - onedir 模式: dist\\名称\\名称.exe + _internal\\ 文件夹
  - onefile 模式: dist\\名称.exe

注意:
    - 默认使用 --onedir 模式，启动速度快，输出是一个文件夹
    - 图标文件需为 .ico 格式（可用在线工具将 png 转为 ico）
    - UnityPy 等依赖通过 --collect-all 确保完整打包
"""

import os
import sys
from pathlib import Path
from typing import Optional

# 脚本在 scripts/ 子目录中，项目根目录在其父目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# ── exe 版本信息（可自行修改）──────────────────────
# 写入 exe 的详细信息（右键 exe → 属性 → 详细信息），可降低杀软误报。
# 个人业余开发者无公司时，可将 APP_COMPANY 填为自己的昵称 / GitHub 用户名。
APP_COMPANY = "paliku520(云野风云)"                                               # 公司/开发者名称
APP_PRODUCT_NAME = "Manosaba Character Extractor"                                # 产品名称
APP_DESCRIPTION = "Manosaba 角色立绘提取与合成工具"                                  # 文件说明
APP_COPYRIGHT = "Copyright (c) 2026 paliku520. Licensed under GPL-3.0."          # 版权信息


# ──────────────────────────────────────────────
# 1. 运行 PyInstaller
# ──────────────────────────────────────────────

def make_version_file(
    name: str,
    company: Optional[str] = None,
    product_name: Optional[str] = None,
    description: Optional[str] = None,
    copyright_: Optional[str] = None,
) -> Path:
    """生成 PyInstaller 版本信息文件（提供 exe 文件版本/产品名称等，降低杀软误报）。

    版本号从 src/version.py 的 __version__ 读取（单一数据源），自动转成 4 段。
    版本信息字段优先取命令行参数，未提供时回退到本文件顶部 APP_* 常量。
    """
    # 命令行参数优先，否则使用顶部常量
    company = company or APP_COMPANY
    product_name = product_name or APP_PRODUCT_NAME
    description = description or APP_DESCRIPTION
    copyright_ = copyright_ or APP_COPYRIGHT

    sys.path.insert(0, str(PROJECT_ROOT))
    from src.version import __version__

    parts = __version__.split(".")
    while len(parts) < 4:
        parts.append("0")
    ver = tuple(int(p) for p in parts[:4])
    ver_str = ".".join(str(v) for v in ver)
    # 属性中显示带 v 的版本号（如 v1.2.0）；FixedFileInfo 仍用 4 段数字供系统比较
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


def run_pyinstaller(
    onefile: bool = False,
    name: str = "ManosabaExtracter",
    icon: str = "assets/icon.ico",
    console: bool = True,
    company: Optional[str] = None,
    product_name: Optional[str] = None,
    description: Optional[str] = None,
    copyright_: Optional[str] = None,
):
    """使用命令行参数直接调用 PyInstaller 打包"""
    import PyInstaller.__main__

    print("=" * 60)
    print("  开始打包...")
    print("=" * 60)

    args = [
        str(PROJECT_ROOT / "run.py"),
        "--onedir" if not onefile else "--onefile",
        "--console" if console else "--windowed",  # 保留 / 不保留控制台窗口
        "--clean",                      # 清理缓存
        "--noconfirm",                  # 覆盖输出目录
        "--name", name,                 # 输出文件名
        "--distpath", str(PROJECT_ROOT / "dist"),   # 强制输出到项目 dist/
        "--workpath", str(PROJECT_ROOT / "build"),  # 构建缓存放在项目 build/
        "--collect-all", "UnityPy",     # 收集 UnityPy 所有子模块和数据
        "--collect-all", "fmod_toolkit", # 收集 fmod_toolkit DLL（UnityPy 依赖）
        "--collect-all", "archspec",      # 收集 archspec JSON 数据文件
        "--version-file", str(make_version_file(name, company, product_name, description, copyright_)),  # exe 版本信息（文件版本/产品名称等，降低杀软误报）
    ]

    # 处理图标
    icon_path = Path(icon)
    if not icon_path.is_absolute():
        icon_path = PROJECT_ROOT / icon_path
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
        # 将图标文件也作为数据打包，供窗口使用
        args.extend(["--add-data", f"{icon_path};."])
        print(f"[INFO] 使用图标: {icon_path}")
    else:
        print(f"[WARN] 图标文件不存在: {icon_path}，跳过")

    # 打包前端资源 webui/（PyWebView 前端页面，PyInstaller 冻结时从 _MEIPASS 读取）
    webui_dir = PROJECT_ROOT / "webui"
    if webui_dir.exists():
        args.extend(["--add-data", f"{webui_dir};webui"])
        print(f"[INFO] 打包前端资源: {webui_dir}")
    else:
        print(f"[WARN] 前端资源目录不存在: {webui_dir}，跳过")

    PyInstaller.__main__.run(args)

    print("=" * 60)
    print("  打包完成！")
    print("=" * 60)


# ──────────────────────────────────────────────
# 2. 验证打包结果
# ──────────────────────────────────────────────

def verify_build(name: str, onefile: bool):
    """检查 exe 是否生成成功"""
    dist_dir = PROJECT_ROOT / "dist"
    if onefile:
        exe_path = dist_dir / f"{name}.exe"
    else:
        exe_path = dist_dir / name / f"{name}.exe"

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[OK] 可执行文件: {exe_path}")
        print(f"[OK] 文件大小: {size_mb:.2f} MB")
        return True
    else:
        print(f"[!] 未找到可执行文件: {exe_path}")
        return False


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def clean_dir(path: Path, label: str):
    """删除指定目录并打印日志"""
    if path.exists() and path.is_dir():
        import shutil
        shutil.rmtree(path)
        print(f"[OK] 已清除 {label}: {path}")
    else:
        print(f"[INFO] {label} 目录不存在，跳过: {path}")


def main():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║  Manosaba-character-extracter 打包   ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    import argparse

    class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
        """固定帮助宽度，避免终端过窄导致帮助信息折行错乱"""
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40, width=100)

    parser = argparse.ArgumentParser(
        prog="build_exe.py",
        usage="%(prog)s [options]",
        description="将项目打包为 exe（PyInstaller）",
        epilog=(
            "示例:\n"
            "  python scripts\\build_exe.py\n"
            "  python scripts\\build_exe.py --onefile --name MyApp --icon assets/icon.ico\n"
            "\n"
            "输出目录: dist/\n"
            "  onedir  -> dist\\名称\\名称.exe + _internal\\\n"
            "  onefile -> dist\\名称.exe\n"
        ),
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("--onefile", action="store_true",
                        help="打包为单个 exe（适合分发）")
    parser.add_argument("--name", type=str, default="ManosabaExtracter",
                        help="输出文件名（不含 .exe）")
    parser.add_argument("--icon", "--i", type=str, default="assets/icon.ico",
                        help="图标路径（.ico）")
    parser.add_argument("--company", "--c", type=str, default=None,
                        help="公司/开发者名称（默认用顶部 APP_COMPANY）")
    parser.add_argument("--product", "--p", type=str, default=None,
                        help="产品名称（默认用顶部 APP_PRODUCT_NAME）")
    parser.add_argument("--description", type=str, default=None,
                        help="文件说明（默认用顶部 APP_DESCRIPTION）")
    parser.add_argument("--copyright", type=str, default=None,
                        help="版权信息（默认用顶部 APP_COPYRIGHT）")
    def _parse_bool(s: str) -> bool:
        v = str(s).strip().lower()
        if v in ("true", "1", "yes", "y", "on"):
            return True
        if v in ("false", "0", "no", "n", "off"):
            return False
        raise argparse.ArgumentTypeError(f"无效的布尔值: {s}（请用 true/false）")

    parser.add_argument(
        "--console", type=_parse_bool, nargs="?", const=True, default=True,
        metavar="BOOL",
        help="是否保留控制台窗口（true/false，默认 true）",
    )
    args = parser.parse_args()

    mode = "onefile" if args.onefile else "onedir"
    console_txt = "保留控制台" if args.console else "不保留控制台(GUI)"
    print(f"[INFO] 打包模式: --{mode}")
    print(f"[INFO] 输出名称: {args.name}")
    print(f"[INFO] 控制台: {console_txt}")
    if args.icon:
        print(f"[INFO] 自定义图标: {args.icon}")
    print()

    # ── 确认与清理 ──
    print("[WARNING] 该操作会覆盖原有的 exe 程序")
    try:
        reply = input("[?] 是否继续? (Y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        reply = "n"
    if reply and reply not in ("y", "yes", ""):
        print("[INFO] 已取消打包")
        return
    print()
    clean_dir(PROJECT_ROOT / "dist", "dist")
    clean_dir(PROJECT_ROOT / "build", "build")
    print()

    # 检查 PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[!] 未安装 PyInstaller，正在安装...")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"]
        )
        print("[OK] PyInstaller 安装完成")

    run_pyinstaller(
        onefile=args.onefile,
        name=args.name,
        icon=args.icon,
        console=args.console,
        company=args.company,
        product_name=args.product,
        description=args.description,
        copyright_=args.copyright,
    )
    verify_build(name=args.name, onefile=args.onefile)

    if args.onefile:
        exe_display = f"dist\\{args.name}.exe"
    else:
        exe_display = f"dist\\{args.name}\\{args.name}.exe"

    print()
    print("==============================================================")
    print(" 打包完成！")
    print(f" 输出目录: dist\\")
    print(f" 可执行文件: {exe_display}")
    print("==============================================================")
    print()


if __name__ == "__main__":
    main()

"""
打包 Electron 后端子进程（backend.py → PyInstaller onedir）

用法:
    python scripts\\build_electron_backend.py

输出: dist/backend/backend.exe + _internal/ 文件夹
      （随后由 electron-builder 作为 extraResources 放进 resources/backend/）

注意:
    - 排除 webview / pythonnet（clr）：Electron 模式后端不需要，避免打包体积与坑
    - UnityPy 等依赖通过 --collect-all 确保完整打包
    - 不打包 webui/（前端由 Electron 负责打包）
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_pywebview import make_version_file  # noqa: E402  复用 exe 版本信息生成

# MCE 字符画（与 electron/main.js 的 MCE_BANNER 一致）
MCE_BANNER = """███╗   ███╗ ██████╗███████╗
████╗ ████║██╔════╝██╔════╝
██╔████╔██║██║     █████╗  
██║╚██╔╝██║██║     ██╔══╝  
██║ ╚═╝ ██║╚██████╗███████╗
╚═╝     ╚═╝ ╚═════╝╚══════╝"""


def run_pyinstaller(
    company: Optional[str] = None,
    product_name: Optional[str] = None,
    description: Optional[str] = None,
    copyright_: Optional[str] = None,
):
    """使用命令行参数直接调用 PyInstaller 打包 backend"""
    import PyInstaller.__main__

    print(MCE_BANNER)
    print("=" * 60)
    print("  开始打包 Electron 后端 (backend.py)...")
    print("=" * 60)

    vf = make_version_file(
        "backend",
        company=company,
        product_name=product_name or "Manosaba Character Extracter Backend",
        description=description or "Manosaba 角色立绘提取工具 - Python 后端子进程",
        copyright_=copyright_,
    )

    args = [
        str(PROJECT_ROOT / "backend.py"),
        "--onedir",
        "--console",          # 保留 stdin/stdout（Electron 通过管道桥接，windowsHide 隐藏窗口）
        "--clean",
        "--noconfirm",
        "--name", "backend",
        "--distpath", str(PROJECT_ROOT / "dist"),             # 统一输出到项目根 dist/
        "--workpath", str(PROJECT_ROOT / "build"),
        "--collect-all", "UnityPy",      # 收集 UnityPy 所有子模块和数据
        "--collect-all", "fmod_toolkit", # 收集 fmod_toolkit DLL（UnityPy 依赖）
        "--collect-all", "archspec",     # 收集 archspec JSON 数据文件
        # 排除 pywebview / pythonnet（Electron 模式不需要）
        "--exclude-module", "webview",
        "--exclude-module", "clr",
        "--exclude-module", "pythonnet",
        "--exclude-module", "System",
        "--version-file", str(vf),
    ]

    icon = PROJECT_ROOT / "assets" / "icon.ico"
    if icon.exists():
        args += ["--icon", str(icon)]
        print(f"[INFO] 使用图标: {icon}")
    else:
        print(f"[WARN] 图标文件不存在: {icon}，跳过")

    PyInstaller.__main__.run(args)

    exe = PROJECT_ROOT / "dist" / "backend" / "backend.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print("=" * 60)
        print(f"  后端打包完成: {exe} ({size_mb:.2f} MB)")
        print("=" * 60)
    else:
        print("[!] 未找到 backend.exe，打包可能失败")


if __name__ == "__main__":
    import argparse

    class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
        """固定帮助宽度，避免终端过窄导致帮助信息折行错乱"""
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40, width=100)

    parser = argparse.ArgumentParser(
        prog="build_electron_backend.py",
        description="打包 Electron 后端子进程（backend.py → PyInstaller onedir）",
        epilog=(
            "示例:\n"
            "  python scripts\\build_electron_backend.py\n"
            "  python scripts\\build_electron_backend.py --product \"My Product\" --description \"...\"\n"
        ),
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("--company", "--c", type=str, default=None,
                        help="公司/开发者名称（默认用 build_pywebview 顶部 APP_COMPANY）")
    parser.add_argument("--product", "--p", type=str, default=None,
                        help="产品名称（默认 'Manosaba Character Extracter Backend'）")
    parser.add_argument("--description", type=str, default=None,
                        help="文件说明（默认 'Manosaba 角色立绘提取工具 - Python 后端子进程'）")
    parser.add_argument("--copyright", type=str, default=None,
                        help="版权信息（默认用 build_pywebview 顶部 APP_COPYRIGHT）")
    args = parser.parse_args()

    run_pyinstaller(
        company=args.company,
        product_name=args.product,
        description=args.description,
        copyright_=args.copyright,
    )

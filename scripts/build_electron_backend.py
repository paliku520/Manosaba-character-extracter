"""
打包 Electron 后端子进程（backend.py → PyInstaller onedir）

用法:
    python scripts\\build_electron_backend.py

输出: dist/backend/backend.exe + _internal/ 文件夹
      （随后由 electron-builder 作为 extraResources 放进 resources/backend/）

注意:
    - run.py 为纯业务模块（不导入任何 GUI 框架）；下列 --exclude-module 仅作防御，
      防止间接依赖意外把 pywebview / pythonnet 拉进包体
    - UnityPy 等依赖通过 --collect-all 确保完整打包
    - 不打包 webui/（前端由 Electron 负责打包）
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.version_info import make_version_file  # noqa: E402  版本信息单一数据源（scripts/version_info.py）

# MCE 字符画（与 electron/main.js 的 MCE_BANNER 一致）
MCE_BANNER = """███╗   ███╗ ██████╗███████╗
████╗ ████║██╔════╝██╔════╝
██╔████╔██║██║     █████╗  
██║╚██╔╝██║██║     ██╔══╝  
██║ ╚═╝ ██║╚██████╗███████╗
╚═╝     ╚═╝ ╚═════╝╚══════╝"""


def _bundle_root() -> Path:
    """PyInstaller onedir 产物中随包资源所在目录（6.x 在 _internal/，5.x 与 exe 同级）"""
    base = PROJECT_ROOT / "dist" / "backend"
    internal = base / "_internal"
    return internal if internal.is_dir() else base


def count_builtin_sources() -> int:
    """仓库内置预设源头文件数（builtin/presets/<角色>/<名称>.json）"""
    src = PROJECT_ROOT / "builtin" / "presets"
    return len(list(src.glob("*/*.json"))) if src.is_dir() else 0


def verify_bundled_resources() -> bool:
    """校验 i18n / 内置预设是否随包，且落位与运行时读取路径一致。

    这类问题只会在打包后暴露（开发版直读仓库目录），所以构建时就断言。
    """
    root = _bundle_root()
    ok = True

    i18n = root / "i18n" / "common" / "zh_CN.yaml"
    if i18n.is_file():
        print(f"[OK] 已打包翻译: {i18n.relative_to(root)}")
    else:
        print(f"[!] 缺少翻译文件: {i18n}")
        ok = False

    # 必须落在 builtin_presets/<角色>/<名称>.json（src/preset_store.py 的 builtin_dir() 读取路径）
    builtin = root / "builtin_presets"
    files = sorted(builtin.glob("*/*.json")) if builtin.is_dir() else []
    if files:
        chars = {p.parent.name for p in files}
        print(f"[OK] 已打包内置预设: {len(files)} 个文件 / {len(chars)} 个角色 → {builtin.relative_to(root)}")
        src_count = count_builtin_sources()
        if src_count and len(files) != src_count:
            print(f"[WARN] 内置预设数量不一致: 仓库 {src_count} / 包内 {len(files)}")
    else:
        print(f"[!] 内置预设未随包（应为 {builtin}/<角色>/<名称>.json）")
        if (builtin / "presets").is_dir():
            print("    → 包内多出一层 presets/：--add-data 的源应写 builtin/presets（PyInstaller 拷贝的是源目录的内容）")
        ok = False

    return ok


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
        # 打包翻译文件 i18n/（后端从 _MEIPASS 读取）
        "--add-data", f"{PROJECT_ROOT / 'i18n'};i18n",
        # 打包内置预设源头：注意源必须写到 builtin/presets（PyInstaller 拷贝的是"源目录的内容"），
        # 否则包里会多出一层 builtin_presets/presets/，而运行时读的是 _MEIPASS/builtin_presets/<角色>/<名称>.json
        # → 打包版看不到任何内置预设（启动时也就无法镜像 / 自愈到 data/presets）。
        "--add-data", f"{PROJECT_ROOT / 'builtin' / 'presets'};builtin_presets",
        # 防御性排除：业务代码已不导入这些模块（GUI 全部由 Electron 承担），
        # 此处仅防止间接依赖把它们带进包体
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

    builtin_count = count_builtin_sources()
    if builtin_count:
        print(f"[INFO] 内置预设源头: {builtin_count} 个（builtin/presets/<角色>/<名称>.json）")
    else:
        print("[WARN] 未找到内置预设源头 builtin/presets/*/*.json —— 打包版将没有内置预设")

    PyInstaller.__main__.run(args)

    exe = PROJECT_ROOT / "dist" / "backend" / "backend.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print("=" * 60)
        print(f"  后端打包完成: {exe} ({size_mb:.2f} MB)")
        print("=" * 60)
    else:
        print("[!] 未找到 backend.exe，打包可能失败")

    # 随包资源校验：缺了就直接失败（否则要等用户装完包才发现内置预设不见了）
    print("-" * 60)
    if not verify_bundled_resources():
        print("  随包资源校验失败，已中断打包")
        print("=" * 60)
        sys.exit(1)
    print("=" * 60)


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
                        help="公司/开发者名称（默认用 scripts/version_info.py 顶部 APP_COMPANY）")
    parser.add_argument("--product", "--p", type=str, default=None,
                        help="产品名称（默认 'Manosaba Character Extracter Backend'）")
    parser.add_argument("--description", type=str, default=None,
                        help="文件说明（默认 'Manosaba 角色立绘提取工具 - Python 后端子进程'）")
    parser.add_argument("--copyright", type=str, default=None,
                        help="版权信息（默认用 scripts/version_info.py 顶部 APP_COPYRIGHT）")
    args = parser.parse_args()

    run_pyinstaller(
        company=args.company,
        product_name=args.product,
        description=args.description,
        copyright_=args.copyright,
    )

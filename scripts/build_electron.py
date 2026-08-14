"""
打包脚本 — 一键打包 Electron 应用全套：

  1. Electron 后端（backend.py → PyInstaller onedir → dist/backend/backend.exe）
     供主进程作为 resources/backend 的 extraResources 使用
  2. Electron 应用（electron-builder → dist/ 下绿色版 zip + 安装版 Setup.exe）
     依赖第 1 步的 dist/backend 作为 extraResources

子脚本逻辑复用：
  - 后端: scripts/build_electron_backend.py 的 run_pyinstaller()
  - 应用: 直接调用 electron/node_modules/electron-builder 的 cli.js，
    --projectDir 指向 electron/（配置读取 electron/electron-builder.yml）

用法:
    python scripts\\build_electron.py                # 后端 + 绿色版 + 安装版
    python scripts\\build_electron.py --backend-only # 只打 Electron 后端
    python scripts\\build_electron.py --app-only     # 只打 Electron 应用（绿色版+安装版，需 dist/backend 已存在）
    python scripts\\build_electron.py --zip-only     # 只打绿色版 zip（需 dist/backend 已存在）
    python scripts\\build_electron.py --installer-only  # 只打安装版 Setup.exe（需 dist/backend 已存在）
    python scripts\\build_electron.py --no-clean     # 跳过清理构建缓存
    python scripts\\build_electron.py --clean-dist   # 额外清理本次构建的 dist 输出目录
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_electron_backend import run_pyinstaller as build_backend  # noqa: E402

ELECTRON_DIR = PROJECT_ROOT / "electron"
ELECTRON_BUILDER_CLI = ELECTRON_DIR / "node_modules" / "electron-builder" / "out" / "cli" / "cli.js"

# MCE 字符画（与 electron/main.js 的 MCE_BANNER 一致）
MCE_BANNER = """███╗   ███╗ ██████╗███████╗
████╗ ████║██╔════╝██╔════╝
██╔████╔██║██║     █████╗  
██║╚██╔╝██║██║     ██╔══╝  
██║ ╚═╝ ██║╚██████╗███████╗
╚═╝     ╚═╝ ╚═════╝╚══════╝"""


def clean_dir(path: Path, label: str) -> None:
    """删除指定目录并打印日志"""
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
        print(f"[OK] 已清除 {label}: {path}")
    else:
        print(f"[INFO] {label} 目录不存在，跳过: {path}")


def run_electron_app(target: str = "") -> bool:
    """调用 electron-builder 打包 Electron 应用。

    target: ""=按配置全部（zip+nsis）、"zip"=仅绿色版、"nsis"=仅安装版
    """
    node = shutil.which("node")
    if not node:
        print("[!] 未找到 node，无法执行 electron-builder。请安装 Node.js（或确认 PATH）")
        return False
    cfg = ELECTRON_DIR / "electron-builder.yml"
    if not ELECTRON_BUILDER_CLI.exists():
        print(f"[!] electron-builder 未安装：缺少 {ELECTRON_BUILDER_CLI}")
        print("    请在 electron 目录执行: npm install --save-dev electron-builder")
        return False
    if not cfg.exists():
        print(f"[!] electron-builder 配置缺失：{cfg}")
        return False
    targets_txt = {"zip": "绿色版 zip", "nsis": "安装版 Setup.exe"}.get(target, "绿色版 zip + 安装版 Setup.exe")
    print("=" * 60)
    print(f"  打包 Electron 应用（{targets_txt}）...")
    print("=" * 60)
    cmd = [node, str(ELECTRON_BUILDER_CLI), "--win"]
    if target:
        cmd.append(target)
    cmd += ["-c", str(cfg), "--projectDir", str(ELECTRON_DIR)]
    subprocess.check_call(cmd, cwd=str(ELECTRON_DIR))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="build_electron.py",
        description="一键打包 Electron 应用（后端 + 绿色版 zip + 安装版 Setup.exe）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python scripts\\build_electron.py\n"
            "  python scripts\\build_electron.py --backend-only\n"
            "  python scripts\\build_electron.py --app-only\n"
            "  python scripts\\build_electron.py --zip-only\n"
            "  python scripts\\build_electron.py --installer-only\n"
        ),
    )
    parser.add_argument("--backend-only", action="store_true",
                        help="只打 Electron 后端（不做 electron-builder）")
    parser.add_argument("--app-only", action="store_true",
                        help="只打 Electron 应用（绿色版+安装版，需 dist/backend 已存在）")
    parser.add_argument("--zip-only", action="store_true",
                        help="只打绿色版 zip（需 dist/backend 已存在）")
    parser.add_argument("--installer-only", action="store_true",
                        help="只打安装版 Setup.exe（需 dist/backend 已存在）")
    parser.add_argument("--no-clean", action="store_true",
                        help="跳过清理构建缓存")
    parser.add_argument("--clean-dist", action="store_true",
                        help="额外清理本次构建的 dist 输出目录（保留其他产物）")
    parser.add_argument("--company", "--c", type=str, default=None,
                        help="公司/开发者名称（透传给后端 exe 版本信息，默认用顶部 APP_COMPANY）")
    parser.add_argument("--product", "--p", type=str, default=None,
                        help="产品名称（透传给后端 exe 版本信息，默认 Manosaba Character Extracter Backend）")
    parser.add_argument("--description", type=str, default=None,
                        help="文件说明（透传给后端 exe 版本信息）")
    parser.add_argument("--copyright", type=str, default=None,
                        help="版权信息（透传给后端 exe 版本信息，默认用顶部 APP_COPYRIGHT）")
    args = parser.parse_args()

    only_flags = [args.app_only, args.backend_only, args.zip_only, args.installer_only]
    if sum(1 for f in only_flags if f) > 1:
        parser.error("--app-only / --backend-only / --zip-only / --installer-only 只能同时指定一个")

    print(MCE_BANNER)
    print("=" * 60)
    print("  Manosaba Character Extracter (MCE) - Electron 打包")
    print("=" * 60)
    if args.backend_only:
        print("[模式] 仅打包 Electron 后端")
    elif args.app_only:
        print("[模式] 仅打包 Electron 应用（绿色版+安装版）")
    elif args.zip_only:
        print("[模式] 仅打包 Electron 应用（绿色版 zip）")
    elif args.installer_only:
        print("[模式] 仅打包 Electron 应用（安装版 Setup.exe）")
    else:
        print("[模式] Electron 后端 + 应用（绿色版/安装包）")

    # ── 清理 ──
    if not args.no_clean:
        clean_dir(PROJECT_ROOT / "build", "build 构建缓存")
        if args.clean_dist:
            clean_dir(PROJECT_ROOT / "dist" / "backend", "dist/backend")

    ok = True

    # ── 1. Electron 后端 ──
    if not args.app_only:
        build_backend(
            company=args.company,
            product_name=args.product,
            description=args.description,
            copyright_=args.copyright,
        )

    # ── 2. Electron 应用（绿色版 zip + 安装版 Setup.exe）──
    run_app = not args.backend_only
    target = "zip" if args.zip_only else ("nsis" if args.installer_only else "")
    if run_app and not run_electron_app(target):
        ok = False

    # ── 结果确认 ──
    print("=" * 60)
    print("  打包完成！产物：")
    if not args.app_only:
        backend_exe = PROJECT_ROOT / "dist" / "backend" / "backend.exe"
        if backend_exe.exists():
            print(f"    [OK] Electron 后端: {backend_exe}")
        else:
            print(f"    [!] Electron 后端未生成: {backend_exe}")
            ok = False
    if run_app:
        if not args.installer_only:
            zips = list((PROJECT_ROOT / "dist").glob("MCE-*-win.zip"))
            if zips:
                print(f"    [OK] 绿色版 zip: {zips[-1]}")
            else:
                print("    [!] 绿色版 zip 未生成")
                ok = False
        if not args.zip_only:
            setups = list((PROJECT_ROOT / "dist").glob("MCE-Setup-*.exe"))
            if setups:
                print(f"    [OK] 安装版: {setups[-1]}")
            else:
                print("    [!] 安装版 Setup.exe 未生成")
                ok = False
    print("=" * 60)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

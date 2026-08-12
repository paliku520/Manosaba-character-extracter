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

# 脚本在 scripts/ 子目录中，项目根目录在其父目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# ──────────────────────────────────────────────
# 1. 运行 PyInstaller
# ──────────────────────────────────────────────

def run_pyinstaller(onefile: bool = False, name: str = "ManosabaExtracter", icon: str = "assets/icon.ico"):
    """使用命令行参数直接调用 PyInstaller 打包"""
    import PyInstaller.__main__

    print("=" * 60)
    print("  开始打包...")
    print("=" * 60)

    args = [
        str(PROJECT_ROOT / "run.py"),
        "--onedir" if not onefile else "--onefile",
        "--console",                    # 保留控制台窗口
        "--clean",                      # 清理缓存
        "--noconfirm",                  # 覆盖输出目录
        "--name", name,                 # 输出文件名
        "--distpath", str(PROJECT_ROOT / "dist"),   # 强制输出到项目 dist/
        "--workpath", str(PROJECT_ROOT / "build"),  # 构建缓存放在项目 build/
        "--collect-all", "UnityPy",     # 收集 UnityPy 所有子模块和数据
        "--collect-all", "fmod_toolkit", # 收集 fmod_toolkit DLL（UnityPy 依赖）
        "--collect-all", "archspec",      # 收集 archspec JSON 数据文件
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

    parser = argparse.ArgumentParser(
        description="使用 PyInstaller 将项目打包为 exe（保留控制台）",
        epilog=(
            "示例:\n"
            "  python scripts\\build_exe.py\n"
            "  python scripts\\build_exe.py --onefile --name MyApp --icon assets/icon.ico\n"
            "\n"
            "输出目录: dist/\n"
            "  onedir  -> dist\\名称\\名称.exe + _internal\\\n"
            "  onefile -> dist\\名称.exe\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--onefile", action="store_true",
        help="打包为单个 exe（启动较慢，但只有一个文件，适合分发）"
    )
    parser.add_argument(
        "--name", type=str, default="ManosabaExtracter",
        help="输出文件名，不含 .exe（默认: ManosabaExtracter）"
    )
    parser.add_argument(
        "--icon", "--i", type=str, default="assets/icon.ico",
        help="图标文件路径（.ico 格式，相对或绝对路径均可）"
    )
    args = parser.parse_args()

    mode = "onefile" if args.onefile else "onedir"
    print(f"[INFO] 打包模式: --{mode}")
    print(f"[INFO] 输出名称: {args.name}")
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

    run_pyinstaller(onefile=args.onefile, name=args.name, icon=args.icon)
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

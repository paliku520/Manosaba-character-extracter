"""魔法少女の魔女审判 - Bundle 文件加载器

加载游戏目录中的所有 bundle 文件，自动查找 characters 目录。"""
import json
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional

import UnityPy

from src.tools import log

# 常见 Unity/纳诺精灵 路径模式（快速查找，避免递归）
COMMON_PATTERNS = [
    "manosaba_Data/StreamingAssets/aa/StandaloneWindows64/naninovel-characters_assets_naninovel/characters",
    "manosaba_Data/StreamingAssets/aa/StandaloneWindows64/naninovel-characters_assets_naninovel",
    "manosaba_Data/StreamingAssets/aa/StandaloneWindows64",
    "manosaba_Data/StreamingAssets",
    "StreamingAssets",
]

# 需要跳过的目录名
SKIP_DIRS = frozenset({"node_modules", "__pycache__", ".git", ".svn", ".idea"})


class BundleLoader:
    """Bundle 文件加载器，带路径记忆功能"""

    def __init__(self, app_name: str = "bundle_loader"):
        self.app_name = app_name
        self.config_file = Path.home() / f".{app_name}_config.json"
        self.last_path = self._load_last_path()
        self.bundles: dict[str, str] = {}

    # ── 路径记忆 ──────────────────────────────────────────

    def _load_last_path(self) -> str:
        """加载上次使用的路径"""
        try:
            if self.config_file.exists():
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                path = data.get("last_path", "")
                if path and Path(path).exists():
                    return path
        except Exception:
            pass
        return str(Path.home())

    def _save_last_path(self, path: str) -> None:
        """保存上次使用的路径"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(
                json.dumps({"last_path": path}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            log("warning", f"保存路径记忆失败: {e}")

    # ── 目录选择 ──────────────────────────────────────────

    def select_directory(self, title: str = "选择游戏目录") -> str | None:
        """弹出文件夹选择对话框"""
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        dir_path = filedialog.askdirectory(title=title, initialdir=self.last_path)
        root.destroy()

        if dir_path:
            self.last_path = dir_path
            self._save_last_path(dir_path)
            return dir_path
        return None

    # ── 查找 characters 目录 ──────────────────────────────

    def find_characters_dir(self, game_root: Path) -> Path | None:
        """在游戏目录中查找 characters 目录（先查常见模式，再递归搜索）"""
        # 1. 先试常见模式
        result = self._search_common_patterns(game_root)
        if result is not None:
            return result

        # 2. 常见模式未命中 → 递归搜索
        log("info", "常见路径未命中，开始递归搜索 characters 目录...")
        return self._search_dir_recursive(game_root, "characters", max_depth=8)

    @staticmethod
    def _search_common_patterns(game_root: Path) -> Path | None:
        """在常见路径模式中查找 characters 目录"""
        for pattern in COMMON_PATTERNS:
            target = game_root / pattern
            if not target.exists():
                continue

            # 精确命中
            if target.name == "characters":
                log("info", f"通过常见路径找到: {target}")
                return target

            # 遍历子目录查找 characters
            for sub in target.iterdir():
                if not sub.is_dir():
                    continue
                if sub.name == "characters":
                    log("info", f"通过常见路径子目录找到: {sub}")
                    return sub
                if "characters" in sub.name.lower():
                    for sub_sub in sub.iterdir():
                        if sub_sub.is_dir() and sub_sub.name == "characters":
                            log("info", f"通过常见路径深层找到: {sub_sub}")
                            return sub_sub
        return None

    @staticmethod
    def _search_dir_recursive(
        root: Path, target_name: str, max_depth: int = 8
    ) -> Path | None:
        """递归搜索指定名称的目录，限制最大深度"""
        # 使用 Path.rglob 替代 os.walk（更 Pythonic）
        # 注意: rglob 不直接支持深度限制，所以我们手动控制
        root_length = len(root.parts)
        for entry in root.rglob("*"):
            if not entry.is_dir():
                continue
            # 跳过隐藏目录和无关目录
            if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                continue
            # 检查深度
            depth = len(entry.parts) - root_length
            if depth > max_depth:
                continue
            if entry.name == target_name:
                return entry
        return None

    # ── Bundle 加载 ───────────────────────────────────────

    @staticmethod
    def load_bundle(bundle_path: Path) -> bool:
        """加载单个 bundle 文件，验证是否包含精灵"""
        try:
            env = UnityPy.load(str(bundle_path))
            return any(obj.type.name == "Sprite" for obj in env.objects)
        except Exception as e:
            log("error", f"加载失败 {bundle_path.name}: {e}")
            return False

    # ── 主流程 ────────────────────────────────────────────

    def load_from_directory(self, directory: str) -> dict:
        """
        从指定目录加载所有 bundle

        Args:
            directory: 游戏根目录或 characters 目录路径

        Returns:
            {"success": bool, "bundles": {角色名: 路径}, "count": int, "errors": [错误信息]}
        """
        result: dict = {
            "success": False,
            "bundles": {},
            "count": 0,
            "errors": [],
        }

        root_path = Path(directory)
        if not root_path.exists():
            result["errors"].append(f"路径不存在: {directory}")
            return result

        # 判断是游戏根目录还是 characters 目录
        characters_dir = self._resolve_characters_dir(root_path, result)
        if characters_dir is None:
            return result

        log("info", f"找到 characters 目录: {characters_dir}")

        # 搜索所有 bundle 文件
        bundle_files = sorted(characters_dir.glob("*.bundle"))
        if not bundle_files:
            result["errors"].append(f"未找到 bundle 文件: {characters_dir}")
            return result

        log("info", f"找到 {len(bundle_files)} 个 bundle 文件")

        # 加载每个 bundle
        for bundle_path in bundle_files:
            name = bundle_path.stem
            if self.load_bundle(bundle_path):
                result["bundles"][name] = str(bundle_path)
                result["count"] += 1
                log("info", f"加载角色成功: {name}")
            else:
                log("warning", f"跳过角色: {name} (未找到精灵资源)")

        if result["count"] > 0:
            result["success"] = True
            self.bundles = result["bundles"]
            log("info", f"成功加载 {result['count']} 个角色")
        else:
            result["errors"].append("没有成功加载任何 bundle")

        return result

    def _resolve_characters_dir(
        self, root_path: Path, result: dict
    ) -> Path | None:
        """解析 characters 目录路径"""
        if root_path.name == "characters":
            return root_path
        if (root_path / "characters").exists():
            return root_path / "characters"

        characters_dir = self.find_characters_dir(root_path)
        if characters_dir is None:
            result["errors"].append(f"未找到 characters 目录: {root_path}")
        return characters_dir

    def load_with_gui(self) -> dict:
        """使用 GUI 选择目录并加载"""
        dir_path = self.select_directory("选择游戏根目录或 characters 目录")
        if not dir_path:
            log("warning", "用户取消了选择")
            return {"success": False, "bundles": {}, "count": 0, "errors": ["用户取消"]}

        return self.load_from_directory(dir_path)

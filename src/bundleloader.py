"""魔法少女の魔女审判 - Bundle 文件加载器

加载游戏目录中的所有 bundle 文件，自动查找 characters 目录。"""
import json
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional

import UnityPy

from src.tools import log
from src.i18n import _

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
            log("warning", _("log.saved_path_failed", e=e))

    # ── 目录选择 ──────────────────────────────────────────

    def select_directory(self, title: str = "") -> str | None:
        """弹出文件夹选择对话框"""
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        dir_path = filedialog.askdirectory(title=title or _("dir.select_title"), initialdir=self.last_path)
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
        log("info", _("log.recursive_search"))
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
                log("info", _("log.found_common", path=target))
                return target

            # 遍历子目录查找 characters
            for sub in target.iterdir():
                if not sub.is_dir():
                    continue
                if sub.name == "characters":
                    log("info", _("log.found_sub", path=sub))
                    return sub
                if "characters" in sub.name.lower():
                    for sub_sub in sub.iterdir():
                        if sub_sub.is_dir() and sub_sub.name == "characters":
                            log("info", _("log.found_deep", path=sub_sub))
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
            log("error", _("log.load_failed", name=bundle_path.name, e=e))
            return False

    # ── 主流程 ────────────────────────────────────────────

    def load_from_directory(self, directory: str, progress_callback=None) -> dict:
        """
        从指定目录加载所有 bundle

        Args:
            directory: 游戏根目录或 characters 目录路径
            progress_callback: 可选进度回调 fn(current, total)

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
            result["errors"].append(_("dialog.bundle_not_found", path=directory))
            return result

        # 判断是游戏根目录还是 characters 目录
        characters_dir = self._resolve_characters_dir(root_path, result)
        if characters_dir is None:
            return result

        log("info", _("log.characters_dir_found", path=characters_dir))

        # 搜索所有 bundle 文件
        bundle_files = sorted(characters_dir.glob("*.bundle"))
        if not bundle_files:
            result["errors"].append(_("dialog.no_bundle_files", path=characters_dir))
            return result

        log("info", _("log.bundle_files_found", count=len(bundle_files)))

        # 加载每个 bundle
        total = len(bundle_files)
        for i, bundle_path in enumerate(bundle_files):
            name = bundle_path.stem
            if self.load_bundle(bundle_path):
                result["bundles"][name] = str(bundle_path)
                result["count"] += 1
                log("info", _("log.loaded_char", name=name))
            else:
                log("warning", _("log.skipped_char", name=name))
            if progress_callback:
                progress_callback(i + 1, total)

        if result["count"] > 0:
            result["success"] = True
            self.bundles = result["bundles"]
            log("info", _("log.loaded_all", count=result['count']))
        else:
            result["errors"].append(_("dialog.no_bundle_loaded"))

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
            result["errors"].append(_("dialog.characters_not_found", path=root_path))
        return characters_dir

    def load_with_gui(self) -> dict:
        """使用 GUI 选择目录并加载"""
        dir_path = self.select_directory(_("dir.select_title"))
        if not dir_path:
            log("warning", _("log.user_cancelled"))
            return {"success": False, "bundles": {}, "count": 0, "errors": [_("dialog.user_cancelled")]}

        return self.load_from_directory(dir_path)

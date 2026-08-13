"""魔法少女の魔女审判 - Bundle 文件加载器

加载游戏目录中的所有 bundle 文件，自动查找 characters 目录。"""
import gc
from pathlib import Path
from typing import Optional

import UnityPy

from src.logtools import log
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


class _SearchCancelled(Exception):
    """内部异常：目录查找被新的查找打断（取消）"""


class BundleLoader:
    """Bundle 文件加载器，带路径记忆功能"""

    def __init__(self, app_name: str = "bundle_loader"):
        self.app_name = app_name
        self.last_path = self._load_last_path()
        self.bundles: dict[str, str] = {}

    # ── 路径记忆 ──────────────────────────────────────────

    def _load_last_path(self) -> str:
        """加载上次使用的路径（从程序根目录 settings.json 读取）"""
        from src.settings import get_last_directory
        return get_last_directory(str(Path.home())) or str(Path.home())

    def _save_last_path(self, path: str) -> None:
        """保存上次使用的路径（写入 settings.json，与 GUI 层共用）"""
        try:
            from src.settings import save_settings
            save_settings(last_directory=path)
        except Exception as e:
            log("warning", _("log.saved_path_failed", e=e))

    # ── 查找 characters 目录 ──────────────────────────────

    def find_characters_dir(self, game_root: Path, cancel_check=None) -> Path | None:
        """在游戏目录中查找 characters 目录（先查常见模式，再递归搜索）"""
        # 1. 先试常见模式
        result = self._search_common_patterns(game_root)
        if result is not None:
            return result

        # 2. 向上回退匹配（用户可能选择了游戏目录下的子目录）
        for ancestor in game_root.parents:
            result = self._search_common_patterns(ancestor)
            if result is not None:
                log("info", _("log.found_common", path=result))
                return result

        # 3. 递归搜索（有限深度 + 剪枝）
        log("info", _("log.recursive_search"))
        return self._search_dir_recursive(
            game_root, "characters", max_depth=8, cancel_check=cancel_check
        )

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
        root: Path, target_name: str, max_depth: int = 8, cancel_check=None
    ) -> Path | None:
        """递归搜索指定名称的目录，限制最大深度并剪枝；cancel_check() 返回 True 时取消"""
        # 迭代式深度优先（DFS），跳过隐藏 / 无关目录（避免遍历大型无关目录导致卡顿）
        stack = [(root, 0)]
        while stack:
            if cancel_check and cancel_check():
                raise _SearchCancelled()
            current, depth = stack.pop()
            try:
                children = sorted(
                    (p for p in current.iterdir() if p.is_dir()),
                    key=lambda p: p.name,
                )
            except OSError:
                continue
            for child in children:
                if child.name == target_name:
                    return child
                if child.name.startswith(".") or child.name in SKIP_DIRS:
                    continue
                if depth + 1 < max_depth:
                    stack.append((child, depth + 1))
        return None

    # ── Bundle 加载 ───────────────────────────────────────

    @staticmethod
    def load_bundle(bundle_path: Path) -> tuple[bool, bool]:
        """加载单个 bundle 文件，验证是否包含精灵/组件数据；用后立即释放 UnityPy 环境（防内存累积）

        Returns:
            (has_sprite, has_components) 是否含精灵 / 是否含 SpriteRenderer 组件
        """
        env = None
        try:
            env = UnityPy.load(str(bundle_path))
            has_sprite = False
            has_components = False
            for obj in env.objects:
                t = obj.type.name
                if t == "Sprite":
                    has_sprite = True
                elif t == "SpriteRenderer":
                    has_components = True
                if has_sprite and has_components:
                    break
            return (has_sprite, has_components)
        except Exception as e:
            log("error", _("log.load_failed", name=bundle_path.name, e=e))
            return (False, False)
        finally:
            # 释放 UnityPy 环境（大对象）：清空已解析文件并断开引用
            if env is not None:
                try:
                    env.files.clear()
                except Exception:
                    pass
                env = None

    # ── 主流程 ────────────────────────────────────────────

    def load_from_directory(
        self, directory: str, progress_callback=None, cancel_check=None
    ) -> dict:
        """
        从指定目录加载所有 bundle

        Args:
            directory: 游戏根目录或 characters 目录路径
            progress_callback: 可选进度回调 fn(current, total)
            cancel_check: 可选取消检查 fn() -> bool；返回 True 时中止本次查找

        Returns:
            {"success": bool, "bundles": {角色名: 路径}, "count": int, "errors": [错误信息], "cancelled": bool}
        """
        result: dict = {
            "success": False,
            "bundles": {},
            "count": 0,
            "errors": [],
            "cancelled": False,
            "components": {},   # {角色名: 是否含组件数据}
        }

        root_path = Path(directory)
        if not root_path.exists():
            result["errors"].append(_("dialog.bundle_not_found", path=directory))
            return result

        # 判断是游戏根目录还是 characters 目录
        try:
            characters_dir = self._resolve_characters_dir(root_path, result, cancel_check)
        except _SearchCancelled:
            result["cancelled"] = True
            return result
        if characters_dir is None:
            return result

        log("info", _("log.characters_dir_found", path=characters_dir))

        # 搜索所有 bundle 文件
        bundle_files = sorted(characters_dir.glob("*.bundle"))
        if not bundle_files:
            result["errors"].append(_("dialog.no_bundle_files", path=characters_dir))
            return result

        log("info", _("log.bundle_files_found", count=len(bundle_files)))

        # 加载每个 bundle（每 GC_INTERVAL 个强制回收一次，避免 UnityPy 对象内存累积）
        GC_INTERVAL = 5
        total = len(bundle_files)
        for i, bundle_path in enumerate(bundle_files):
            if cancel_check and cancel_check():
                result["cancelled"] = True
                return result
            name = bundle_path.stem
            has_sprite, has_components = self.load_bundle(bundle_path)
            if has_sprite:
                result["bundles"][name] = str(bundle_path)
                result["components"][name] = has_components
                result["count"] += 1
                log("info", _("log.loaded_char", name=name))
            else:
                log("warning", _("log.skipped_char", name=name))
            if progress_callback:
                progress_callback(i + 1, total)
            if (i + 1) % GC_INTERVAL == 0:
                gc.collect()
        # 全部加载完成后再次回收，释放临时对象
        gc.collect()

        if result["count"] > 0:
            result["success"] = True
            self.bundles = result["bundles"]
            log("info", _("log.loaded_all", count=result['count']))
        else:
            result["errors"].append(_("dialog.no_bundle_loaded"))

        return result

    def _resolve_characters_dir(
        self, root_path: Path, result: dict, cancel_check=None
    ) -> Path | None:
        """解析 characters 目录路径"""
        if root_path.name == "characters":
            return root_path
        if (root_path / "characters").exists():
            return root_path / "characters"

        characters_dir = self.find_characters_dir(root_path, cancel_check)
        if characters_dir is None:
            result["errors"].append(_("dialog.characters_not_found", path=root_path))
        return characters_dir

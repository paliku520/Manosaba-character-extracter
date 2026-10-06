"""
名片（角色名牌）合成模块

素材与排版参数**全部解析自游戏 bundle**，不凭手感设定：

  - `general-sprites_assets_all.bundle` → Sprite `NamePlateBase`（601×289 菱形底板，
    即游戏内"空名片"本体；`NameUnderline` 已不再使用）
  - `naninovel-ui_assets_all.bundle`   → 名牌节点层级
    `WitchBookUI/.../Page_Profiles/LeftArea/AuthorPanel`
    ├─ AuthorBase  size=(601, 289)   apos=(0, 0)      anchor/pivot=(0.5, 0.5)  ← 引用 NamePlateBase
    └─ AuthorLabel size=(1000, 160)  apos=(287, 14)   anchor/pivot=(0.5, 0.5)  ← 名字文本
         TMP: m_fontSize=136, m_HorizontalAlignment=1(Left), m_VerticalAlignment=8192(Middle)

由上述数据推导出的权威排版参数：

  - 文本左边界 = 287 − 1000/2 = **−213**（相对底板中心，Unity 坐标，向右为正）
  - 文本垂直中心 = **+14**（相对底板中心，Unity 坐标，向上为正）
  - 基准字号 = **136**（TMP m_fontSize；底板菱形恰好容纳 136px 的字）

名字排版规则（游戏内为"姓氏 + 名字"，首字分别放大）：

    姓氏首字 → 大字号（落在菱形内）
    名字首字 → 中字号
    其余字   → 小字号
"""

import math
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from src.export_manager import safe_name, save_png
from src.logtools import log

# ---------------------------------------------------------------------------
# 权威排版参数（解析自游戏 bundle，改动前请先核对上表）
# ---------------------------------------------------------------------------

BASE_SPRITE_NAME = "NamePlateBase"

BASE_SPRITE_SIZE: Tuple[int, int] = (601, 289)   # AuthorBase RectTransform size
LABEL_FONT_SIZE: float = 136.0                   # AuthorLabel TMP m_fontSize
LABEL_SIZE: Tuple[float, float] = (1000.0, 160.0)
LABEL_ANCHORED_POS: Tuple[float, float] = (287.0, 14.0)  # 相对 AuthorBase 中心
LABEL_MARGIN_LEFT: float = LABEL_ANCHORED_POS[0] - LABEL_SIZE[0] / 2.0  # −213.0
LABEL_CENTER_Y: float = LABEL_ANCHORED_POS[1]                            # +14.0

# 文字过长时**加宽画布**（字号不变）：画布宽 = 文字起点 + 文字宽 + 右侧留白，
# 下限为底板自身宽度（名字短时输出尺寸不变）。
LABEL_RIGHT_PADDING: float = 16.0

# 字号层级（em 倍数，基准 = LABEL_FONT_SIZE）
DEFAULT_FONT_STEPS: Dict[str, float] = {
    "surname_head": 1.0,   # 姓氏首字 —— 大
    "given_head": 0.8,     # 名字首字 —— 中
    "rest": 0.6,           # 其余字   —— 小
}

# 素材文件名（素材统一存放在 webui/assets/nameplate/）
BASE_PNG_NAME = "NamePlateBase.png"

FONT_EXTS = (".ttf", ".otf", ".ttc", ".otc")

# 系统兜底字体（优先明朝体 / 宋体，贴近游戏字形）
SYSTEM_FONT_CANDIDATES = (
    "C:/Windows/Fonts/yumin.ttf",     # Yu Mincho（明朝体）
    "C:/Windows/Fonts/simsun.ttc",    # 宋体
    "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
    "C:/Windows/Fonts/arial.ttf",
)


class NameplateAssetsMissing(Exception):
    """底板素材尚未从游戏 bundle 提取"""


# ---------------------------------------------------------------------------
# 素材：定位游戏 bundle / 提取底板
# ---------------------------------------------------------------------------

# 游戏内名片素材所在 bundle 的常见文件名（Addressables 打包）
BUNDLE_PATTERNS = (
    "general-sprites*.bundle",
    "general-sprites_assets_all.bundle",
)

# 手动查找时的位置指引（相对 Steam 库文件夹）+ 目标文件名，仅用于提示文案
GAME_REL_HINT = r"steamapps\common\manosaba_game\manosaba_Data\StreamingAssets\aa\StandaloneWindows64"
BUNDLE_HINT_FILE = "general-sprites_assets_all.bundle"

# 游戏内字体 bundle（general-fonts-*.bundle → TsukushiMincho / SourceHanSerifSC ...）
FONT_BUNDLE_PATTERNS = (
    "general-fonts-*.bundle",
    "general-fonts_*.bundle",
)

# 素材实际所在目录名（Addressables 平台目录，游戏资源都在这里）
STANDALONE_DIR = "StandaloneWindows64"

# 游戏内 Addressables bundle 所在目录（相对搜索根目录，按优先级）
_COMMON_SUBDIRS = (
    STANDALONE_DIR,
    "manosaba_Data/StreamingAssets/aa/" + STANDALONE_DIR,
    "manosaba_Data/StreamingAssets/aa",
    "manosaba_Data/StreamingAssets",
    "StreamingAssets/aa/" + STANDALONE_DIR,
    "StreamingAssets/aa",
    "StreamingAssets",
)

# 递归兜底时跳过的目录（避免遍历大型无关目录）
_SKIP_DIRS = frozenset({
    "node_modules", "__pycache__", ".git", "logs", "temp", "output",
    "build", "dist", "resources", "plugins", "dotnet", "BepInEx",
})

# 默认向上回溯层数 / 向下递归深度
# 浅层探测（_probe_dirs）很快且已覆盖游戏的常见目录结构，递归只当"素材位于其它层级"时的保险；
# 它是查找里最贵的一步（在大目录上枚举一次就要数秒），所以故意压得很浅：
#   _DEFAULT_DOWN_DEPTH = 2  → 只查 root 自身 + 它的直接子目录
#   _RECURSE_ROOTS = 3       → 只对最接近起点的 3 个根递归，更远的祖先（盘根、Steam 库…）只浅层探测
_DEFAULT_UP_LEVELS = 6
_DEFAULT_DOWN_DEPTH = 2
_RECURSE_ROOTS = 3


def _probe_dirs(root: Path) -> List[Path]:
    """root 下值得先探测的目录（root 自身 → StandaloneWindows64 → 常见 Addressables 路径）"""
    dirs: List[Path] = []
    for cand in (root, *(root / rel for rel in _COMMON_SUBDIRS)):
        if cand.is_dir() and cand not in dirs:
            dirs.append(cand)
    return dirs


def _glob_in(root: Path, patterns: Sequence[str]) -> Optional[Path]:
    """在 root 内按给定文件名模式找第一个匹配（不递归）"""
    for pat in patterns:
        hits = sorted(root.glob(pat))
        if hits:
            return hits[0]
    return None


class NameplateSearchCancelled(Exception):
    """查找被用户中止（前端点「停止查找」时抛出，用于与“没找到”区分）"""


def _check_cancel(should_cancel: Optional[Callable[[], bool]]) -> None:
    """用户已请求中止时抛 NameplateSearchCancelled"""
    if should_cancel is not None and should_cancel():
        raise NameplateSearchCancelled()


def _recursive_find(
    root: Path,
    patterns: Sequence[str],
    max_depth: int,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Optional[Path]:
    """有限深度递归查找（跳过无关目录）；深度优先，先在浅层找 StandaloneWindows64"""
    stack: List[Tuple[Path, int]] = [(root, 0)]
    while stack:
        _check_cancel(should_cancel)
        cur, depth = stack.pop()
        hit = _glob_in(cur, patterns)
        if hit:
            return hit
        if depth + 1 >= max_depth:
            continue
        try:
            children = sorted(cur.iterdir())
        except OSError:
            continue
        # 先压入非 StandaloneWindows64 目录，后压入它 → 出栈时优先遍历 StandaloneWindows64
        for child in children:
            if not child.is_dir() or child.name.startswith(".") or child.name in _SKIP_DIRS:
                continue
            stack.append((child, depth + 1))
    return None


def _search_roots(start: Path, up_levels: int) -> List[Path]:
    """搜索根目录链：起点自身 + 逐级向上的父目录（去掉重复/盘符根之外的无效项）"""
    start = Path(start)
    roots: List[Path] = []
    chain = [start, *list(start.parents)[:max(0, up_levels)]]
    for r in chain:
        if r not in roots and r.is_dir():
            roots.append(r)
    return roots


def find_sprites_bundle(
    start: Path,
    up_levels: int = _DEFAULT_UP_LEVELS,
    down_depth: int = _DEFAULT_DOWN_DEPTH,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Tuple[Optional[Path], List[str]]:
    """从 start（通常是 settings.json 的 last_directory）查找名片素材 bundle。

    策略（先快后慢）：
      1. 起点是 .bundle 文件 → 直接用它
      2. 每个搜索根（起点 + 向上各级父目录）内：先探测根自身 / StandaloneWindows64 /
         常见 Addressables 路径（不递归，快）
      3. 仍未命中 → 只对**最接近起点的 `_RECURSE_ROOTS` 个根**做有限深度递归
         （深度 `down_depth=2`），更远的祖先目录不递归（否则会在盘根 / Steam 库
         这类大目录里扫很久，而素材几乎不会是那个深度）

    should_cancel: 可选中止回调（返回 True 时抛 NameplateSearchCancelled），
                   在递归兜底阶段每步检查 —— 这一步最慢，也是用户最可能想中止的时候。

    Returns:
        (命中的 bundle 路径或 None, 实际搜索过的根目录字符串列表[用于提示])
    """
    start = Path(start)
    if start.is_file():
        return (start if start.suffix.lower() == ".bundle" else None), [str(start.parent)]

    roots = _search_roots(start, up_levels)
    searched = [str(r) for r in roots]

    for root in roots:
        _check_cancel(should_cancel)
        for d in _probe_dirs(root):
            hit = _glob_in(d, BUNDLE_PATTERNS)
            if hit:
                return hit, searched

    for root in roots[:_RECURSE_ROOTS]:
        _check_cancel(should_cancel)
        hit = _recursive_find(root, BUNDLE_PATTERNS, down_depth, should_cancel)
        if hit:
            return hit, searched

    return None, searched


def find_font_bundles(
    start: Path,
    up_levels: int = _DEFAULT_UP_LEVELS,
    down_depth: int = _DEFAULT_DOWN_DEPTH,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[Path]:
    """查找游戏字体 bundle（general-fonts-*.bundle）；搜索策略与深度限制同 find_sprites_bundle"""
    start = Path(start)
    if not start.is_dir():
        return []
    roots = _search_roots(start, up_levels)
    found: List[Path] = []
    for root in roots:
        _check_cancel(should_cancel)
        for d in _probe_dirs(root):
            for pat in FONT_BUNDLE_PATTERNS:
                for hit in sorted(d.glob(pat)):
                    if hit not in found:
                        found.append(hit)
            if found:
                return found
    for root in roots[:_RECURSE_ROOTS]:
        _check_cancel(should_cancel)
        hit = _recursive_find(root, FONT_BUNDLE_PATTERNS, down_depth, should_cancel)
        if hit:
            # 同目录下的其它字体 bundle 一并取用
            for pat in FONT_BUNDLE_PATTERNS:
                for h in sorted(hit.parent.glob(pat)):
                    if h not in found:
                        found.append(h)
            return found
    return found


def extract_font_assets(bundle_paths: Sequence[Path], dest_dir: Path) -> List[Dict]:
    """从字体 bundle 中提取字体文件（otf/ttf）到 dest_dir（已存在的同名文件跳过）

    Returns:
        [{"name": 字体名, "path": 目标路径, "size": 字节数}, ...]
    """
    import UnityPy

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Dict] = []

    for bundle_path in bundle_paths:
        bundle_path = Path(bundle_path)
        if not bundle_path.exists():
            continue
        env = None
        try:
            env = UnityPy.load(str(bundle_path))
            for obj in env.objects:
                if obj.type.name != "Font":
                    continue
                try:
                    data = obj.read()
                    raw = getattr(data, "m_FontData", None)
                    if not raw:
                        continue
                    blob = bytes(bytearray(raw))
                except Exception as e:
                    log("warning", f"[nameplate] 字体读取失败 {bundle_path.name}: {e}")
                    continue
                name = getattr(data, "m_Name", "") or "font"
                head = blob[:4]
                ext = ".otf" if head == b"OTTO" else (".ttf" if head in (b"\x00\x01\x00\x00", b"true") else ".ttf")
                out_path = dest_dir / f"{name}{ext}"
                if out_path.exists():
                    continue
                try:
                    out_path.write_bytes(blob)
                except Exception as e:
                    log("warning", f"[nameplate] 字体写入失败 {out_path}: {e}")
                    continue
                saved.append({"name": name, "path": str(out_path), "size": len(blob)})
                log("info", f"[nameplate] 已提取字体 {name} ({len(blob) / 1024:.0f}KB) → {out_path}")
        except Exception as e:
            log("warning", f"[nameplate] 解析字体 bundle 失败 {bundle_path.name}: {e}")
        finally:
            if env is not None:
                try:
                    env.files.clear()
                except Exception:
                    pass
    return saved


def extract_base_assets(bundle_path: Path, dest_dir: Optional[Path] = None) -> Dict:
    """从 bundle 中提取名片底板（Sprite `NamePlateBase`）并保存为 PNG。

    Args:
        bundle_path: general-sprites*.bundle
        dest_dir:    保存目录；为 None 时自动选可写目录（优先 webui/assets/nameplate）

    Returns:
        {"base": 路径, "size": [w, h], "dir": 实际目录}
    """
    import UnityPy

    bundle_path = Path(bundle_path)
    dest_dir = Path(dest_dir) if dest_dir is not None else nameplate_dir(writable=True)

    base_path: Optional[Path] = None
    size: Optional[List[int]] = None

    env = None
    try:
        env = UnityPy.load(str(bundle_path))
        for obj in env.objects:
            if obj.type.name != "Sprite":
                continue
            try:
                data = obj.read()
            except Exception:
                continue
            if getattr(data, "m_Name", "") != BASE_SPRITE_NAME:
                continue
            img = getattr(data, "image", None)
            if img is None:
                continue
            base_path = save_png(img, dest_dir, Path(BASE_PNG_NAME).stem, overwrite=True)
            size = [img.size[0], img.size[1]]
            log("info", f"[nameplate] 已提取底板 {BASE_SPRITE_NAME} ({img.size[0]}x{img.size[1]}) → {base_path}")
            break
    finally:
        if env is not None:
            try:
                env.files.clear()
            except Exception:
                pass

    if base_path is None:
        raise NameplateAssetsMissing(f"bundle 中未找到精灵 {BASE_SPRITE_NAME}: {bundle_path}")

    return {
        "base": str(base_path),
        "size": size or list(BASE_SPRITE_SIZE),
        "dir": str(dest_dir),
    }


# ---------------------------------------------------------------------------
# 字体
# ---------------------------------------------------------------------------

def list_fonts(font_dir: Path) -> List[Dict]:
    """列出字体目录中可用字体（文件名即显示名）"""
    font_dir = Path(font_dir)
    if not font_dir.is_dir():
        return []
    items = []
    for p in sorted(font_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in FONT_EXTS:
            items.append({"name": p.stem, "file": p.name, "path": str(p)})
    return items


def list_fonts_all() -> List[Dict]:
    """合并所有候选字体目录（见 fonts_dirs）的字体，按名称排序、按文件名去重（先出现的优先）"""
    seen = set()
    items: List[Dict] = []
    for d in fonts_dirs():
        for item in list_fonts(d):
            key = item["file"].lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return sorted(items, key=lambda i: i["name"].lower())


def webui_assets_dir() -> Path:
    """`webui/assets` 目录 —— 本工具所有静态素材（字体、名片底板…）的统一存放处。

    注意：名片素材（底板 + 游戏原版字体）版权受限，不随发行包分发，由运行时提取到此处；
    程序自带的 UI 字体（见 webui/css/theme.css 的 @font-face）仍随包分发。

    定位顺序（命中即返回，均不存在时返回开发态路径）：
      1. 打包态：<exe 目录>/../webui/assets（Electron: resources/backend → resources/webui）
      2. 打包态：<exe 目录>/webui/assets
      3. 开发态：<仓库根>/webui/assets
    """
    candidates: List[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir.parent / "webui" / "assets")
        candidates.append(exe_dir / "webui" / "assets")
    candidates.append(Path(__file__).resolve().parent.parent / "webui" / "assets")
    for cand in candidates:
        if cand.is_dir():
            return cand
    return candidates[-1]


def fonts_dir(writable: bool = False) -> Path:
    """返回名片字体目录。

    writable=True 时返回**第一个真正可写**的候选（写探针实测，同 nameplate_dir）：
    绿色版写入 `webui/assets/fonts`（与 UI 字体同处），安装到 Program Files 等只读目录时
    回退 `data/nameplate/fonts` —— 发行包不再内置名片素材，字体必须靠运行时提取，
    故这条回退链是安装版可用的关键。
    """
    dirs = fonts_dirs()
    if not writable:
        return dirs[0]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".mce_write_probe"
            probe.write_bytes(b"")
            probe.unlink()
            return d
        except Exception:
            continue
    return dirs[-1]


def fonts_dirs() -> List[Path]:
    """名片字体目录候选（按优先级）：

      1. `webui/assets/fonts`   —— 与前端 @font-face 共用（程序自带 UI 字体 + 运行时提取的游戏字体）
      2. `data/nameplate/fonts` —— 安装到只读目录（Program Files 等）时的可写兜底

    名字重复时以先出现的为准（见 `list_fonts_all`）。
    注意：前端 @font-face 用的 woff2 无法被 PIL 使用，故只认 ttf/otf/ttc。
    """
    dirs = [webui_assets_dir() / "fonts"]
    try:
        from src.settings import get_nameplate_dir
        fallback = get_nameplate_dir() / "fonts"
        if fallback not in dirs:
            dirs.append(fallback)
    except Exception:
        pass
    return dirs


def nameplate_dirs() -> List[Path]:
    """名片底板素材目录候选（按优先级）：

      1. `webui/assets/nameplate` —— 与字体等素材统一存放（**不随发行包分发**，由运行时从游戏目录提取）
      2. `data/nameplate`        —— 安装到只读目录（Program Files 等）时的可写兜底
    """
    dirs = [webui_assets_dir() / "nameplate"]
    try:
        from src.settings import get_nameplate_dir
        fallback = get_nameplate_dir()
        if fallback not in dirs:
            dirs.append(fallback)
    except Exception:
        pass
    return dirs


def nameplate_dir(writable: bool = False) -> Path:
    """返回名片底板素材目录。

    writable=True 时返回**第一个真正可写**的候选（用写探针实测，因为 Windows 上
    os.access 不反映 ACL，打包安装到 Program Files 时 webui/assets 可能只读）。
    """
    dirs = nameplate_dirs()
    if not writable:
        return dirs[0]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".mce_write_probe"
            probe.write_bytes(b"")
            probe.unlink()
            return d
        except Exception:
            continue
    return dirs[-1]


def system_font_path() -> Optional[str]:
    """返回系统兜底字体路径（找不到返回 None）"""
    for cand in SYSTEM_FONT_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def _hex_to_rgba(color: str, default: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int, int, int]:
    """#RRGGBB / #RRGGBBAA / #RGB → RGBA 元组"""
    if not color:
        return default
    s = str(color).strip().lstrip("#")
    try:
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
        if len(s) == 8:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
    except ValueError:
        pass
    return default


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def split_name(name: str) -> List[Tuple[str, str]]:
    """把「姓氏」「名字」拆成带字号层级的字符段

    Returns:
        [(文字, 层级)]，层级 ∈ {surname_head, given_head, rest}
    """
    segs: List[Tuple[str, str]] = []
    surname = (name or "").strip()
    if surname:
        segs.append((surname[0], "surname_head"))
        if len(surname) > 1:
            segs.append((surname[1:], "rest"))
    return segs


class NameplateRenderer:
    """按游戏内排版规则合成名片。

    底板 1:1 使用游戏素材；文字左边界 / 垂直中心 / 基准字号均取自解析出的
    AuthorLabel 节点参数，因此合成结果与游戏内名牌一致。
    """

    def __init__(self, base_png: Path):
        self._base_path = Path(base_png)
        if not self._base_path.exists():
            raise NameplateAssetsMissing(str(self._base_path))
        with Image.open(self._base_path) as im:
            self.base = im.convert("RGBA")

    # ── 资源 ─────────────────────────────────────────────

    @staticmethod
    def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
        candidates = [font_path, system_font_path()]
        for cand in candidates:
            if not cand:
                continue
            try:
                return ImageFont.truetype(str(cand), max(1, int(size)))
            except Exception:
                continue
        return ImageFont.load_default()  # type: ignore[return-value]

    # ── 合成 ─────────────────────────────────────────────

    def render(
        self,
        surname: str = "",
        given: str = "",
        font_path: Optional[str] = None,
        scale: float = 1.0,
        color: str = "#FFFFFF",
        head_color: Optional[str] = None,
        steps: Optional[Dict[str, float]] = None,
    ) -> Image.Image:
        """渲染名片（画布固定为底板尺寸 601×289，不提供背景/缩放/偏移）。

        Args:
            surname/given: 姓氏 / 名字（首字分别使用大 / 中字号）
            font_path:     字体文件路径（None → 系统兜底字体）
            scale:         字号整体缩放（1.0 = 游戏原始字号 136）
            color:         其余文字颜色
            head_color:    姓氏首字颜色（None → 与 color 相同）
            steps:         字号层级 em 倍数，默认 DEFAULT_FONT_STEPS

        Returns:
            PIL Image (RGBA)
        """
        steps = {**DEFAULT_FONT_STEPS, **(steps or {})}
        base = self.base

        # ── 文字排布（对齐 AuthorLabel 节点参数）──
        # 姓氏首字 → 大；名字首字 → 中；其余 → 小
        segs: List[Tuple[str, str]] = list(split_name(surname))
        segs += [
            (txt, "given_head" if lvl == "surname_head" else lvl)
            for txt, lvl in split_name(given)
        ]

        # ── 画布宽度：底板宽 与「文字起点 + 文字宽 + 右侧留白」取大者 ──
        # 名字过长时只把画布向右加长，字号不变（底板始终贴在画布左上角）
        text_left = base.width / 2.0 + LABEL_MARGIN_LEFT
        text_w = self._measure_text(segs, font_path=font_path, scale=scale, steps=steps) if segs else 0.0
        canvas_w = max(base.width, int(math.ceil(text_left + text_w + LABEL_RIGHT_PADDING)))
        canvas = Image.new("RGBA", (canvas_w, base.height), (0, 0, 0, 0))
        canvas.alpha_composite(base, (0, 0))

        if segs:
            self._draw_text(
                canvas, segs, font_path=font_path, scale=scale,
                color=color, head_color=head_color, steps=steps,
            )

        return canvas

    def _build_fonts(
        self,
        font_path: Optional[str],
        scale: float,
        steps: Dict[str, float],
    ) -> Dict[str, object]:
        """按字号层级建立字体对象（不随文字长度变化）"""
        out: Dict[str, object] = {}
        for lvl, ratio in steps.items():
            size = max(1, int(round(LABEL_FONT_SIZE * float(ratio) * float(scale))))
            out[lvl] = self._load_font(font_path, size)
        return out

    def _measure_text(
        self,
        segs: List[Tuple[str, str]],
        font_path: Optional[str],
        scale: float,
        steps: Dict[str, float],
    ) -> float:
        """测量名字的总宽度（用于决定画布需要加长多少）"""
        fonts = self._build_fonts(font_path, scale, steps)
        total = 0.0
        for text, level in segs:
            f = fonts.get(level) or fonts.get("rest")
            if f is None:
                continue
            for ch in text:
                if ch != "\n":
                    total += f.getlength(ch)   # type: ignore[attr-defined]
        return total

    def _draw_text(
        self,
        canvas: Image.Image,
        segs: List[Tuple[str, str]],
        font_path: Optional[str],
        scale: float,
        color: str,
        head_color: Optional[str],
        steps: Dict[str, float],
    ) -> None:
        """逐字绘制名字（左对齐 + 行盒垂直居中，等价 TMP 的 Left/Middle）。

        字号固定不变；文字过长时由调用方（render）加宽画布来容纳。
        """
        base_w, base_h = self.base.size
        plate_cx = base_w / 2.0
        plate_cy = base_h / 2.0

        fonts = self._build_fonts(font_path, scale, steps)
        metrics = {lvl: f.getmetrics() for lvl, f in fonts.items()}  # type: ignore[attr-defined]
        max_ascent = max(a for a, _ in metrics.values())
        max_descent = max(d for _, d in metrics.values())

        rest_rgba = _hex_to_rgba(color)
        head_rgba = _hex_to_rgba(head_color) if head_color else rest_rgba

        draw = ImageDraw.Draw(canvas)
        x = plate_cx + LABEL_MARGIN_LEFT
        # Unity y 向上 → PIL y 向下；行盒（最大字号）垂直中心对齐 LABEL_CENTER_Y
        center_y = plate_cy - LABEL_CENTER_Y
        baseline = center_y + (max_ascent - max_descent) / 2.0

        for text, level in segs:
            font = fonts.get(level) or fonts.get("rest")
            if font is None:
                continue
            fill = head_rgba if level == "surname_head" else rest_rgba
            for ch in text:
                if ch == "\n":
                    continue
                draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
                x += font.getlength(ch)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def render_nameplate(
    base_png: Path,
    surname: str,
    given: str,
    **kwargs,
) -> Image.Image:
    """一次性渲染（内部创建 renderer；批量渲染请复用 NameplateRenderer）"""
    return NameplateRenderer(base_png).render(surname=surname, given=given, **kwargs)


def safe_file_stem(text: str, fallback: str = "nameplate") -> str:
    """把文字转成安全的文件名片段（复用导出模块的统一命名规则）"""
    raw = str(text or "").strip().strip(".")
    return safe_name(raw) if raw else fallback

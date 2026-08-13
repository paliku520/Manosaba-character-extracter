"""
更新检查模块 — 通过 GitHub Releases API 检查最新版本

依赖: 仅使用 Python 标准库（urllib），无需额外安装包。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 项目的 GitHub 仓库（owner/repo）
GITHUB_REPO = "paliku520/Manosaba-character-extracter"

# GitHub Releases API（latest release）
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# 网络请求超时（秒）
REQUEST_TIMEOUT = 10


@dataclass
class UpdateInfo:
    """可用的更新信息"""
    latest_version: str   # 最新版本号（如 "1.1.0"）
    release_url: str      # 发布页面地址
    notes: str            # 发布说明摘要


def _normalize_version(tag: str) -> str:
    """规范化版本号，去掉常见前缀（如 v1.0.0 -> 1.0.0）"""
    tag = tag.strip()
    if tag[:1].lower() == "v":
        tag = tag[1:]
    return tag


def _parse_version(version: str) -> Optional[tuple]:
    """将版本号解析为可比较的元组；兼容 prewiew-n / hotfix-n 等后缀。

    返回 (主版本, 发布级别, 发布编号)，发布级别：
      2 = hotfix（同一主版本下最高）
      1 = 正式版（无后缀）
      0 = prewiew（预发布，最低）
    发布编号为同级内的序号（如 hotfix-2 的 2、prewiew-1 的 1），无后缀时为 0。
    如：
      1.2.3            -> ((1, 2, 3), 1, 0)
      1.2.3-prewiew-1  -> ((1, 2, 3), 0, 1)
      1.2.3-hotfix-2   -> ((1, 2, 3), 2, 2)
    解析失败返回 None。
    """
    m = re.match(r"(\d+(?:\.\d+)*)", version)
    if not m:
        return None
    main = tuple(int(n) for n in m.group(1).split("."))
    lower = version.lower()
    if "hotfix" in lower:
        level = 2
    elif any(k in lower for k in ("prewiew", "pre-view", "pre", "rc", "beta", "alpha")):
        level = 0
    else:
        level = 1
    nums = re.findall(r"\d+", version)
    seq = int(nums[-1]) if level != 1 and len(nums) > 1 else 0
    return (main, level, seq)


def _is_newer(latest: str, current: str) -> bool:
    """判断 latest 是否比 current 更新（版本号无法解析时返回 False，保守处理）"""
    lv = _parse_version(latest)
    cv = _parse_version(current)
    if lv is None or cv is None:
        return False
    lm, ll, lh = lv
    cm, cl, ch = cv
    if lm != cm:
        return lm > cm
    # 主版本相同：hotfix(2) > 正式版(1) > prewiew(0)
    if ll != cl:
        return ll > cl
    # 发布级别相同：hotfix 编号较大的更新
    return lh > ch


def check_for_update(
    current_version: str,
    timeout: int = REQUEST_TIMEOUT,
) -> Optional[UpdateInfo]:
    """
    检查 GitHub 上是否有新版本。

    参数:
        current_version: 当前程序版本号（如 "1.0.0"）
        timeout: 网络请求超时秒数

    返回:
        UpdateInfo — 检测到新版本时返回更新信息
        None      — 已是最新版本

    异常:
        URLError / HTTPError / ValueError — 网络错误或响应异常，由调用方处理
    """
    req = Request(
        RELEASES_API_URL,
        headers={
            "User-Agent": f"Manosaba-character-extracter/{current_version}",
            "Accept": "application/vnd.github+json",
        },
    )

    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "")
    latest = _normalize_version(tag)
    if not latest:
        return None

    if not _is_newer(latest, current_version):
        return None

    return UpdateInfo(
        latest_version=latest,
        release_url=data.get("html_url")
        or f"https://github.com/{GITHUB_REPO}/releases/latest",
        notes=(data.get("body") or "").strip(),
    )

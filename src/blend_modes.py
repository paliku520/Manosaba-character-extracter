# -*- coding: utf-8 -*-
"""混合方式（blend mode）实现 — 纯 Pillow，无 numpy 依赖

支持 normal / multiply / screen / overlay / softlight。
语义对齐游戏材质基名（Naninovel Extender 系列 shader）：
    Default    -> normal
    Multiply   -> multiply
    Screen     -> screen
    Overlay    -> overlay
    Softlight  -> softlight

公式（W3C Compositing and Blending，8-bit 近似）：
    结果颜色 = (1 - αs)·Cb + αs·B(Cb, Cs)          # 颜色按源 alpha 混合
    结果 alpha = αs + αb·(1 - αs)                   # ImageChops.screen 等价
其中 B(Cb, Cs) 为对应混合函数，Cb=底色 / Cs=源色。
"""
import math
from typing import Callable

from PIL import Image, ImageChops


# point() 的类型化辅助函数（具名函数带 int 注解，避免 Pylance 匹配到
# Callable[[ImagePointTransform], ...] 重载导致 lambda 参数类型推断错误）
_pt = Callable[[int], int]


def _pt_mul2(v: int) -> int:
    """2·v（越界由 PIL point 自动 clamp 到 0..255）"""
    return 2 * v


def _pt_255_minus_2v(v: int) -> int:
    """255 - 2·v"""
    return 255 - 2 * v


def _pt_mask_le128(v: int) -> int:
    """v <= 128 时为 255，否则 0"""
    return 255 if v <= 128 else 0


def _pt_2v_minus_255(v: int) -> int:
    """2·v - 255"""
    return 2 * v - 255


def _pt_sqrt_scale(v: int) -> int:
    """255·sqrt(v/255)"""
    return int(255 * math.sqrt(v / 255.0))


def _pt_mask_gt128(v: int) -> int:
    """v > 128 时为 255，否则 0"""
    return 255 if v > 128 else 0


def blend_over(canvas: Image.Image, top: Image.Image,
               place_x: int, place_y: int, blend_mode: str = "normal") -> None:
    """将 top(RGBA) 以 blend_mode 混合到 canvas(RGBA) 的 (place_x, place_y) 处（原地修改）。

    blend_mode 支持: normal / multiply / screen / overlay / softlight。
    超出画布范围自动裁剪；normal 退化为 alpha_composite（与旧行为一致）。
    """
    if not blend_mode or blend_mode == "normal":
        canvas.alpha_composite(top, dest=(place_x, place_y))
        return

    W, H = canvas.size
    sx, sy = top.size
    l = max(place_x, 0)
    t = max(place_y, 0)
    r = min(place_x + sx, W)
    b = min(place_y + sy, H)
    if l >= r or t >= b:
        return

    base = canvas.crop((l, t, r, b)).convert("RGBA")
    top_c = top.crop((l - place_x, t - place_y, r - place_x, b - place_y)).convert("RGBA")
    out = _blend_region(base, top_c, blend_mode)
    canvas.paste(out, (l, t))


def _blend_region(base: Image.Image, top: Image.Image, mode: str) -> Image.Image:
    """对 base/top（等尺寸 RGBA）应用混合，返回 RGBA"""
    base_rgb = base.convert("RGB")
    top_rgb = top.convert("RGB")
    b_rgb = _blend_rgb(base_rgb, top_rgb, mode)
    # 颜色按源 alpha 混合: out = (1-αs)·Cb + αs·B
    # 注意 Image.composite(im1, im2, mask): mask=255 取 im1，mask=0 取 im2
    # → 源不透明(αs=255)处取混合色 b_rgb，透明处保留底色 base_rgb
    out_rgb = Image.composite(b_rgb, base_rgb, top.getchannel("A"))
    # alpha 合成: αs + αb·(1-αs) == screen(αb, αs)
    out_a = ImageChops.screen(base.getchannel("A"), top.getchannel("A"))
    return Image.merge("RGBA", (*out_rgb.split(), out_a))


def _blend_rgb(base: Image.Image, top: Image.Image, mode: str) -> Image.Image:
    """B(Cb, Cs) 混合函数，对两个等尺寸 RGB 图像逐通道计算，返回 RGB"""
    if mode == "multiply":
        return ImageChops.multiply(base, top)
    if mode == "screen":
        return ImageChops.screen(base, top)
    if mode == "overlay":
        return _overlay(base, top)
    if mode == "softlight":
        return _softlight(base, top)
    return top


# ---------------------------------------------------------------------------
# overlay（以底色为基准的分段混合）
#   Cb <= 0.5: 2·Cb·Cs
#   Cb >  0.5: 1 - 2·(1-Cb)·(1-Cs)
# ---------------------------------------------------------------------------
def _overlay(base: Image.Image, top: Image.Image) -> Image.Image:
    chans = []
    for cb, cs in zip(base.split(), top.split()):
        # multiply(cb,cs) = cb·cs/255（0..255）; 2·Cb·Cs·255 = 2·P
        lo = ImageChops.multiply(cb, cs).point(_pt_mul2)
        # multiply(inv_cb,inv_cs) = (255-cb)(255-cs)/255 = (1-Cb)(1-Cs)·255; hi = 255 - 2·M
        hi = ImageChops.multiply(ImageChops.invert(cb), ImageChops.invert(cs)).point(
            _pt_255_minus_2v
        )
        mask = cb.point(_pt_mask_le128)
        chans.append(Image.composite(lo, hi, mask))
    return Image.merge("RGB", chans)


# ---------------------------------------------------------------------------
# softlight（W3C soft light）
#   Cs <= 0.5: Cb - (1-2·Cs)·Cb·(1-Cb)
#   Cs >  0.5: Cb + (2·Cs-1)·(D(Cb)-Cb)，D(Cb)≈sqrt(Cb)
# ---------------------------------------------------------------------------
def _softlight(base: Image.Image, top: Image.Image) -> Image.Image:
    chans = []
    for cb, cs in zip(base.split(), top.split()):
        chans.append(_softlight_channel(cb, cs))
    return Image.merge("RGB", chans)


def _softlight_channel(cb: Image.Image, cs: Image.Image) -> Image.Image:
    # ---- 低分支 (cs <= 0.5): out = cb·(1 - (1-2cs)·(1-cb)) ----
    a_low = cs.point(_pt_255_minus_2v)                      # (1-2cs)*255
    t = ImageChops.multiply(a_low, ImageChops.invert(cb))   # (1-2cs)(1-cb)*255 近似
    out_low = ImageChops.multiply(cb, ImageChops.invert(t))

    # ---- 高分支 (cs > 0.5): out = cb + (2cs-1)·(sqrt(cb)-cb) ----
    a_high = cs.point(_pt_2v_minus_255)                     # (2cs-1)*255
    d = cb.point(_pt_sqrt_scale)                            # sqrt(cb)*255
    diff = ImageChops.subtract(d, cb)                       # D - Cb
    prod = ImageChops.multiply(a_high, diff)                # (2cs-1)(D-cb) 近似
    out_high = ImageChops.add(cb, prod)

    mask = cs.point(_pt_mask_gt128)
    return Image.composite(out_high, out_low, mask)

"""Color utilities for accessibility-safe text/background contrast."""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
_RGBA_RE = re.compile(
    r"^rgba?\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})(?:\s*,\s*([0-9]*\.?[0-9]+))?\s*\)$"
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_hex(color: str) -> tuple[int, int, int]:
    match = _HEX_RE.match(color)
    if not match:
        raise ValueError(f"Unsupported hex color: {color}")
    value = match.group(1)
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _parse_rgba(color: str) -> tuple[int, int, int, float]:
    match = _RGBA_RE.match(color)
    if not match:
        raise ValueError(f"Unsupported rgb/rgba color: {color}")
    r = max(0, min(255, int(match.group(1))))
    g = max(0, min(255, int(match.group(2))))
    b = max(0, min(255, int(match.group(3))))
    a = 1.0 if match.group(4) is None else _clamp01(float(match.group(4)))
    return r, g, b, a


def _composite(
    fg: tuple[int, int, int, float], bg: tuple[int, int, int]
) -> tuple[int, int, int]:
    r, g, b, a = fg
    br, bgc, bb = bg
    out_r = round((a * r) + ((1.0 - a) * br))
    out_g = round((a * g) + ((1.0 - a) * bgc))
    out_b = round((a * b) + ((1.0 - a) * bb))
    return out_r, out_g, out_b


def _to_rgb(color: str, under_bg: str = "#FFFFFF") -> tuple[int, int, int]:
    color = color.strip()
    if color.startswith("#"):
        return _parse_hex(color)
    if color.startswith("rgb"):
        r, g, b, a = _parse_rgba(color)
        if a >= 1.0:
            return r, g, b
        return _composite((r, g, b, a), _parse_hex(under_bg))
    raise ValueError(f"Unsupported color format: {color}")


def _channel_linear(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str, under_bg: str = "#FFFFFF") -> float:
    r, g, b = _to_rgb(color, under_bg)
    rs, gs, bs = (r / 255.0), (g / 255.0), (b / 255.0)
    return (
        0.2126 * _channel_linear(rs)
        + 0.7152 * _channel_linear(gs)
        + 0.0722 * _channel_linear(bs)
    )


def contrast_ratio(
    fg_color: str, bg_color: str, fg_under_bg: str = "#FFFFFF", bg_under_bg: str = "#FFFFFF"
) -> float:
    l1 = relative_luminance(fg_color, fg_under_bg)
    l2 = relative_luminance(bg_color, bg_under_bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def readable_text_on(
    bg_color: str, dark_text: str = "#111111", light_text: str = "#FFFFFF"
) -> str:
    dark_ratio = contrast_ratio(dark_text, bg_color)
    light_ratio = contrast_ratio(light_text, bg_color)
    return dark_text if dark_ratio >= light_ratio else light_text

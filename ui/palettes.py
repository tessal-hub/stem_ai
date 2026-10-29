"""
ui/palettes.py — Định nghĩa bảng màu cao cấp cho ứng dụng.

Cung cấp các lớp dữ liệu Palette và bộ màu chuẩn: Sáng (Light - M3 Dynamic Tonal).
Tuân thủ chuẩn thiết kế Material You (Material Design 3).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Lớp lưu trữ các giá trị màu sắc và hiệu ứng thị giác."""

    PRIMARY: str           # Màu chủ đạo
    PRIMARY_LIGHT: str     # Màu chủ đạo nhạt
    PRIMARY_DARK: str      # Màu chủ đạo đậm

    SURFACE_PRIMARY: str   # Nền thẻ (Trắng)
    SURFACE_SECONDARY: str  # Nền chính của ứng dụng (Canvas)
    SURFACE_TERTIARY: str  # Nền lớp thứ 3 (Input)

    TEXT_PRIMARY: str      # Chữ chính
    TEXT_SECONDARY: str    # Chữ phụ
    TEXT_TERTIARY: str     # Chữ mờ

    BORDER: str            # Viền chuẩn
    BORDER_LIGHT: str      # Viền mờ

    STATUS_SUCCESS: str    # Trạng thái thành công
    STATUS_WARNING: str    # Trạng thái cảnh báo
    STATUS_ERROR: str      # Trạng thái lỗi
    STATUS_SUCCESS_TEXT: str
    STATUS_ERROR_TEXT: str
    STATUS_WARNING_TEXT: str

    HOVER_BG: str          # Nền khi di chuột
    TERM_BG: str           # Nền terminal
    TERM_FG: str           # Chữ terminal

    GLASS_BG: str          # Nền hiệu ứng kính
    GLASS_BG_STRONG: str   # Nền kính đậm
    GLASS_EDGE: str        # Viền kính

    SHADOW_COLOR: str      # Màu đổ bóng


# ── Bảng màu Material You (M3 Dynamic Tonal Palette) ──────────────────────────
LIGHT_PALETTE = Palette(
    PRIMARY="#4E58A9",           # M3 Baseline Tech Indigo / Primary (5.7:1 on white)
    PRIMARY_LIGHT="#DFE0FF",     # M3 Primary Container (soft tonal lavender)
    PRIMARY_DARK="#38428B",      # M3 Primary Pressed / Active

    SURFACE_PRIMARY="#FFFFFF",   # M3 Surface Container Lowest (Cards / Panes)
    SURFACE_SECONDARY="#FAF8FD", # M3 Surface Canvas (ambient tinted background)
    SURFACE_TERTIARY="#EFEBF4",  # M3 Surface Container (inputs, sunk tracks)

    TEXT_PRIMARY="#1B1B21",      # M3 On-Surface (Ink, 16.2:1 contrast)
    TEXT_SECONDARY="#46464F",    # M3 On-Surface Variant (Body, 8.5:1 contrast)
    TEXT_TERTIARY="#71717A",     # M3 Outline / Muted Hint (4.83:1 on white, WCAG AA compliant)

    BORDER="#E3DFE8",            # M3 Surface Container Highest / divider
    BORDER_LIGHT="#CAC4D0",      # M3 Outline Variant

    STATUS_SUCCESS="#1A6C39",    # M3 Forest Green
    STATUS_WARNING="#875200",    # M3 Warm Amber
    STATUS_ERROR="#BA1A1A",      # M3 Error Red
    STATUS_SUCCESS_TEXT="#FFFFFF",
    STATUS_ERROR_TEXT="#FFFFFF",
    STATUS_WARNING_TEXT="#FFFFFF",

    HOVER_BG="rgba(78, 88, 169, 0.08)",  # M3 Primary 8% State Layer
    TERM_BG="#191C20",           # M3 Dark Surface Container
    TERM_FG="#E1E2E8",           # M3 Dark On-Surface

    GLASS_BG="rgba(250, 248, 253, 0.90)",
    GLASS_BG_STRONG="rgba(250, 248, 253, 0.98)",
    GLASS_EDGE="#E3DFE8",

    SHADOW_COLOR="rgba(27, 27, 33, 0.06)"
)


DARK_PALETTE = Palette(
    PRIMARY="#BEC2FF",           # M3 Tech Indigo 80 (high contrast on dark)
    PRIMARY_LIGHT="#373F8F",     # M3 Dark Primary Container (deep tonal indigo)
    PRIMARY_DARK="#DFE0FF",      # M3 Dark On-Primary Container / Light accent

    SURFACE_PRIMARY="#1A1B21",   # M3 Dark Surface Container Low (Cards / Panes)
    SURFACE_SECONDARY="#121318", # M3 Dark Surface Canvas (ambient tinted dark background)
    SURFACE_TERTIARY="#24252C",  # M3 Dark Surface Container (inputs, sunk tracks)

    TEXT_PRIMARY="#E2E2E9",      # M3 Dark On-Surface (Ink Dark, 12.75:1 contrast on #1A1B21)
    TEXT_SECONDARY="#C6C5D0",    # M3 Dark On-Surface Variant (Body, 9.6:1 contrast)
    TEXT_TERTIARY="#90909A",     # M3 Dark Outline / Muted (5.15:1 contrast, WCAG AA compliant)

    BORDER="#33343B",            # M3 Dark Surface Container Highest / divider
    BORDER_LIGHT="#46464F",      # M3 Dark Outline Variant

    STATUS_SUCCESS="#81D691",    # M3 Forest Green Light
    STATUS_WARNING="#FFB870",    # M3 Warm Amber Light
    STATUS_ERROR="#FFB4AB",      # M3 Error Red Light
    STATUS_SUCCESS_TEXT="#003916", # High contrast on #81D691 (7.29:1)
    STATUS_ERROR_TEXT="#690005",   # High contrast on #FFB4AB (6.93:1)
    STATUS_WARNING_TEXT="#4A2800", # High contrast on #FFB870 (7.44:1)

    HOVER_BG="rgba(190, 194, 255, 0.08)", # M3 Primary 8% State Layer on Dark
    TERM_BG="#0D0E13",           # M3 Darkest Surface
    TERM_FG="#E2E2E9",           # M3 Dark On-Surface (15.1:1 on #0D0E13)

    GLASS_BG="rgba(26, 27, 33, 0.90)",
    GLASS_BG_STRONG="rgba(26, 27, 33, 0.98)",
    GLASS_EDGE="#33343B",

    SHADOW_COLOR="rgba(0, 0, 0, 0.35)"
)


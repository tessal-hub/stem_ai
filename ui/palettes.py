"""
ui/palettes.py — Định nghĩa bảng màu cao cấp cho ứng dụng.

Cung cấp các lớp dữ liệu Palette và hai bộ màu mặc định: Sáng (Light) và Tối (Dark).
Tuân thủ chuẩn thiết kế Vanguard Editorial Luxury.
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


# ── Bảng màu Bench Restrained (Light) — aligned to DESIGN.md / ml_lab lab_style ─────
LIGHT_PALETTE = Palette(
    PRIMARY="#0668d1",           # Calibrated Blue 5.37:1 on white (DESIGN.md)
    PRIMARY_LIGHT="rgba(10, 122, 255, 0.07)",  # ACCENT_TINT
    PRIMARY_DARK="#0557b0",      # Hover — 7.01:1

    SURFACE_PRIMARY="#FFFFFF",   # Card / pane
    SURFACE_SECONDARY="#f6f7f9",  # App canvas BG_APP
    SURFACE_TERTIARY="#f1f5f9",  # Sunk / input track

    TEXT_PRIMARY="#0f172a",      # Ink
    TEXT_SECONDARY="#334155",    # Body 10.35:1 — readable
    TEXT_TERTIARY="#5b6b7f",     # Muted 5.45:1 — meets AA for hints

    BORDER="rgba(15, 23, 42, 0.08)",   # BORDER derived from ink
    BORDER_LIGHT="rgba(15, 23, 42, 0.05)",

    STATUS_SUCCESS="#1e7a46",
    STATUS_WARNING="#b45309",
    STATUS_ERROR="#dc2626",
    STATUS_SUCCESS_TEXT="#FFFFFF",
    STATUS_ERROR_TEXT="#FFFFFF",
    STATUS_WARNING_TEXT="#FFFFFF",

    HOVER_BG="rgba(10, 122, 255, 0.07)",
    TERM_BG="#16181d",
    TERM_FG="#d7dde6",

    GLASS_BG="rgba(255, 255, 255, 0.8)",
    GLASS_BG_STRONG="rgba(255, 255, 255, 0.95)",
    GLASS_EDGE="rgba(15, 23, 42, 0.08)",

    SHADOW_COLOR="transparent"
)


# Dark mode intentionally disabled per project spec: alias to LIGHT_PALETTE
DARK_PALETTE = LIGHT_PALETTE


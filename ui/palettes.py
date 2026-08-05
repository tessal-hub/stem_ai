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


# ── Bảng màu Claude Aesthetic (Light) ───────────────────────────────────────
LIGHT_PALETTE = Palette(
    PRIMARY="#9BB8D7",           # Soft Pastel Blue (Muted)
    PRIMARY_LIGHT="#C9DDF0",     # Very Light Blue
    PRIMARY_DARK="#7395B8",      # Deeper Muted Blue

    SURFACE_PRIMARY="#FFFFFF",   # Nền thẻ (Raised)
    SURFACE_SECONDARY="#FBF9F6",  # Nền chính của ứng dụng
    SURFACE_TERTIARY="#F3F0E9",  # Nền lớp ngoài/Input

    TEXT_PRIMARY="#1D1D1D",      # Darker grey for readability
    TEXT_SECONDARY="#6B6B6B",
    TEXT_TERTIARY="#9C9C9C",

    BORDER="rgba(0, 0, 0, 0.08)",
    BORDER_LIGHT="rgba(0, 0, 0, 0.04)",

    STATUS_SUCCESS="#10B981",
    STATUS_WARNING="#F59E0B",
    STATUS_ERROR="#EF4444",
    STATUS_SUCCESS_TEXT="#FFFFFF",
    STATUS_ERROR_TEXT="#FFFFFF",
    STATUS_WARNING_TEXT="#FFFFFF",

    HOVER_BG="rgba(115, 149, 184, 0.08)",  # Subtle blue tint for hover
    TERM_BG="#FFFFFF",
    TERM_FG="#1D1D1D",

    GLASS_BG="rgba(255, 255, 255, 0.8)",
    GLASS_BG_STRONG="rgba(255, 255, 255, 0.95)",
    GLASS_EDGE="rgba(0, 0, 0, 0.08)",

    SHADOW_COLOR="rgba(0, 0, 0, 0.04)"
)


# ── Bảng màu Obsidian Dark Palette (Apple Dark Theme) ──────────────────────
DARK_PALETTE = Palette(
    PRIMARY="#0A84FF",           # Apple System Blue (Dark)
    PRIMARY_LIGHT="rgba(10, 132, 255, 0.25)",
    PRIMARY_DARK="#0066CC",

    SURFACE_PRIMARY="#242426",   # Brighter raised card
    SURFACE_SECONDARY="#0A0A0C", # Nền chính ứng dụng
    SURFACE_TERTIARY="#333336",  # Nền input / inner frame

    TEXT_PRIMARY="#FFFFFF",      
    TEXT_SECONDARY="#E0E0E6",    # Brighter secondary text
    TEXT_TERTIARY="#A1A1A6",     # Brighter tertiary text

    BORDER="rgba(255, 255, 255, 0.22)",
    BORDER_LIGHT="rgba(255, 255, 255, 0.15)",

    STATUS_SUCCESS="#30D158",
    STATUS_WARNING="#FF9F0A",
    STATUS_ERROR="#FF453A",
    STATUS_SUCCESS_TEXT="#FFFFFF",
    STATUS_ERROR_TEXT="#FFFFFF",
    STATUS_WARNING_TEXT="#FFFFFF",

    HOVER_BG="rgba(10, 132, 255, 0.22)",
    TERM_BG="#0B0B0C",
    TERM_FG="#F2F2F7",

    GLASS_BG="rgba(28, 28, 30, 0.85)",
    GLASS_BG_STRONG="rgba(28, 28, 30, 0.95)",
    GLASS_EDGE="rgba(255, 255, 255, 0.16)",

    SHADOW_COLOR="rgba(0, 0, 0, 0.60)"
)

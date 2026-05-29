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
    SURFACE_SECONDARY: str # Nền chính của ứng dụng (Canvas)
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
    PRIMARY="#1C1C1E",           # Monochrome accent
    PRIMARY_LIGHT="#3A3A3C",
    PRIMARY_DARK="#000000",

    SURFACE_PRIMARY="#FFFFFF",   # Nền thẻ
    SURFACE_SECONDARY="#F5F5F7", # Nền chính của ứng dụng
    SURFACE_TERTIARY="#F5F5F7",  # Nền lớp ngoài/Input

    TEXT_PRIMARY="#1C1C1E",
    TEXT_SECONDARY="#636366",
    TEXT_TERTIARY="#8E8E93",

    BORDER="rgba(0, 0, 0, 0.12)",
    BORDER_LIGHT="rgba(0, 0, 0, 0.08)",

    STATUS_SUCCESS="#10B981",
    STATUS_WARNING="#F59E0B",
    STATUS_ERROR="#EF4444",
    STATUS_SUCCESS_TEXT="#FFFFFF",
    STATUS_ERROR_TEXT="#FFFFFF",
    STATUS_WARNING_TEXT="#FFFFFF",

    HOVER_BG="rgba(0, 0, 0, 0.04)",
    TERM_BG="#FFFFFF",
    TERM_FG="#1C1C1E",

    GLASS_BG="rgba(255, 255, 255, 0.8)",
    GLASS_BG_STRONG="rgba(255, 255, 255, 0.95)",
    GLASS_EDGE="rgba(0, 0, 0, 0.08)",

    SHADOW_COLOR="rgba(0, 0, 0, 0.04)"
)


# ── Dark palette được bỏ qua (mapping về Light để tránh nhầm lẫn) ──────────────
DARK_PALETTE = LIGHT_PALETTE

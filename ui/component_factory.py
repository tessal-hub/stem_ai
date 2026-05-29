"""
ui/component_factory.py — Factory tạo widget UI thống nhất.

Cung cấp các hàm khởi tạo widget tuân thủ bảng màu Vanguard Palette,
giúp duy trì tính nhất quán của giao diện và hỗ trợ chuyển đổi theme động.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logic.theme_manager import theme_manager
from ui.asset_utils import resolve_asset_path
from ui.color_utils import readable_text_on
from ui.tokens import (
    APP_FONT_STACK,
    BADGE_RADIUS,
    BTN_H,
    BTN_RADIUS,
    CARD_BEZEL,
    INPUT_RADIUS,
    SETTINGS_BTN_H,
    SETTINGS_INPUT_H,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XS,
    TITLE_FONT_STACK,
)


def _p():
    """Hàm helper lấy palette hiện tại."""
    return theme_manager.get_palette()


class IconButton(QToolButton):
    """Nút bấm chỉ chứa icon SVG, tối ưu cho toolbar và các nút điều khiển nhỏ."""

    def __init__(self, icon_path: str, height: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(height, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(QIcon(resolve_asset_path(icon_path)))
        self.setIconSize(QSize(int(height * 0.6), int(height * 0.6)))
        self.setProperty("type", "icon")


# ── Card & Frame Factories ───────────────────────────────────────────────────

def make_card(
    margins: tuple[int, int, int, int] = (SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD),
    spacing: int = SPACING_SM,
) -> tuple[QFrame, QVBoxLayout]:
    """Tạo một thẻ (Card) tiêu chuẩn đồng bộ với theme."""
    card = QFrame()
    card.setObjectName("Card")
    
    layout = QVBoxLayout(card)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return card, layout


def make_card_frame() -> QFrame:
    """Tạo khung viền Card đơn giản."""
    palette = _p()
    frame = QFrame()
    frame.setObjectName("CardFrame") # Cho phép theme.py style
    return frame


# ── Button Factories ─────────────────────────────────────────────────────────

def make_button(label: str, type_: str = "", height: int = BTN_H) -> QPushButton:
    """Tạo một nút bấm cơ bản."""
    btn = QPushButton(label)
    btn.setFixedHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if type_:
        btn.setProperty("type", type_)
    return btn


def make_primary_button(label: str, height: int = BTN_H) -> QPushButton:
    """Tạo nút bấm chính (Primary) với màu chủ đạo."""
    return make_button(label, "primary", height)


def make_outline_button(label: str, height: int = BTN_H) -> QPushButton:
    """Tạo nút bấm dạng viền (Outline)."""
    return make_button(label, "outline", height)


# ── Label & Utility Factories ────────────────────────────────────────────────

def make_section_label(text: str, accent: bool = True) -> QLabel:
    """Tạo nhãn tiêu đề cho một phân đoạn UI."""
    lbl = QLabel(text)
    lbl.setProperty("type", "section_title")
    if accent:
        lbl.setProperty("status", "accent")
    return lbl


def make_hint(text: str, color: str | None = None) -> QLabel:
    """Tạo nhãn gợi ý (Hint) với font chữ nhỏ và nghiêng."""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setProperty("type", "settings_hint")
    if color:
        lbl.setStyleSheet(f"color: {color};")
    return lbl


def make_checkbox(label: str, checked: bool = False) -> QCheckBox:
    """Tạo checkbox tùy chỉnh giao diện."""
    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    return chk


def make_empty_state_card(
    title: str = "No data to evaluate yet",
    body: str = "",
) -> tuple[QFrame, QVBoxLayout]:
    """Tạo một thẻ hiển thị trạng thái trống (Empty State)."""
    card, layout = make_card()
    card.setMinimumHeight(220)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(10)
    
    icon = QLabel("📊")
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setProperty("type", "empty_state_icon")
    
    lbl_title = QLabel(title)
    lbl_title.setProperty("type", "state_empty_title")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    layout.addWidget(icon)
    layout.addWidget(lbl_title)
    
    if body:
        lbl_body = QLabel(body)
        lbl_body.setWordWrap(True)
        lbl_body.setProperty("type", "state_empty_body")
        lbl_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_body)
    return card, layout


def make_error_state_card(title: str, body: str) -> tuple[QFrame, QVBoxLayout]:
    """Tạo một thẻ hiển thị trạng thái lỗi (Error State)."""
    card, layout = make_card()
    layout.setSpacing(8)
    lbl_title = QLabel(title)
    lbl_title.setProperty("type", "state_empty_title")
    lbl_title.setProperty("status", "error")
    
    lbl_body = QLabel(body)
    lbl_body.setWordWrap(True)
    lbl_body.setProperty("type", "state_empty_body")
    
    layout.addWidget(lbl_title)
    layout.addWidget(lbl_body)
    return card, layout


def make_card_name_label(name: str) -> QLabel:
    """Tạo nhãn tên cho thẻ danh sách."""
    lbl = QLabel(name)
    lbl.setProperty("type", "record_current_spell")
    return lbl


def make_card_count_label(count: int) -> QLabel:
    """Tạo nhãn số lượng cho thẻ danh sách."""
    lbl = QLabel(f"{count} samples")
    lbl.setProperty("type", "statistics_meta_label")
    return lbl


def make_rarity_badge_statistics(label: str, color: str) -> QLabel:
    """Tạo huy hiệu (Badge) độ hiếm cho trang thống kê."""
    lbl = QLabel(label)
    palette = _p()
    text_color = readable_text_on(color, dark_text=palette.TEXT_PRIMARY, light_text="#FFFFFF")
    lbl.setStyleSheet(f"""
        background-color: {color}; color: {text_color};
        border-radius: {BADGE_RADIUS}; padding: 4px 12px;
        font-weight: 800; font-size: 10px; font-family: {APP_FONT_STACK};
    """)
    return lbl


def make_rarity_badge_wand(label: str, color: str) -> QLabel:
    """Tạo huy hiệu (Badge) độ hiếm cho trang Wand."""
    # Tương tự như statistics nhưng có thể tinh chỉnh kích thước nếu cần
    return make_rarity_badge_statistics(label, color)

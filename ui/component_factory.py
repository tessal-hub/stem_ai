"""
ui/component_factory.py — Factory tạo widget UI thống nhất.

Cung cấp các hàm khởi tạo widget tuân thủ bảng màu Material You (M3),
giúp duy trì tính nhất quán của giao diện và hỗ trợ chuyển đổi theme động.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QCheckBox, QFrame, QLabel, QPushButton,
                             QToolButton, QVBoxLayout, QWidget)

from logic.theme_manager import theme_manager
from ui.asset_utils import resolve_asset_path
from ui.color_utils import readable_text_on
from ui.tokens import (APP_FONT_STACK, BADGE_RADIUS, BTN_H, SPACING_MD,
                       SPACING_SM)


def _p():
    """Hàm helper lấy palette hiện tại."""
    return theme_manager.get_palette()


class IconButton(QToolButton):
    """Nút bấm chỉ chứa icon SVG, tối ưu cho toolbar và các nút điều khiển nhỏ."""

    def __init__(
        self,
        icon_path: str,
        height: int = 36,
        tooltip: str = "",
        accessible_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(height, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(QIcon(resolve_asset_path(icon_path)))
        self.setIconSize(QSize(int(height * 0.6), int(height * 0.6)))
        self.setProperty("type", "icon")
        if tooltip:
            self.setToolTip(tooltip)
        acc_name = accessible_name or tooltip or icon_path.split("/")[-1].replace(".svg", "").replace("_", " ")
        self.setAccessibleName(acc_name)
        self.setAccessibleDescription(tooltip or acc_name)


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


# ── Button Factories ─────────────────────────────────────────────────────────

def make_button(
    label: str,
    type_: str = "",
    height: int = BTN_H,
    tooltip: str = "",
) -> QPushButton:
    """Tạo một nút bấm cơ bản kèm hỗ trợ Accessibility."""
    btn = QPushButton(label)
    btn.setFixedHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if type_:
        btn.setProperty("type", type_)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setAccessibleName(label)
    return btn


def make_primary_button(label: str, height: int = BTN_H, tooltip: str = "") -> QPushButton:
    """Tạo nút bấm chính (Primary) với màu chủ đạo."""
    return make_button(label, "primary", height, tooltip=tooltip)


def make_outline_button(label: str, height: int = BTN_H, tooltip: str = "") -> QPushButton:
    """Tạo nút bấm dạng viền (Outline)."""
    return make_button(label, "outline", height, tooltip=tooltip)


# ── Label & Utility Factories ────────────────────────────────────────────────

def make_section_label(text: str, accent: bool = False) -> QLabel:
    """Tạo nhãn tiêu đề cho một phân đoạn UI (M3 On-Surface INK theo chuẩn, accent=True khi cần)."""
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
    flat: bool = False,
    icon_path: str = "assets/icon/statistic.svg",
) -> tuple[QFrame, QVBoxLayout]:
    """Tạo một thẻ hiển thị trạng thái trống (Empty State) theo Material You."""
    if flat:
        card = QFrame()
        card.setObjectName("EmptyStateFlat")
        card.setStyleSheet("QFrame#EmptyStateFlat { background: transparent; border: none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
    else:
        card, layout = make_card()
    card.setMinimumHeight(160)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(10)

    # Material You M3 tonal icon squircle
    palette = _p()
    icon_container = QLabel()
    icon_container.setFixedSize(44, 44)
    icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_container.setStyleSheet(f"""
        background-color: {palette.SURFACE_TERTIARY};
        border: 1px solid {palette.BORDER};
        border-radius: 14px;
    """)

    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtGui import QPixmap, QPainter, QColor
    renderer = QSvgRenderer(resolve_asset_path(icon_path))
    pix = QPixmap(48, 48)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pix.rect(), QColor(palette.TEXT_SECONDARY))
    painter.end()

    scaled_pix = pix.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    icon_container.setPixmap(scaled_pix)

    lbl_title = QLabel(title)
    lbl_title.setProperty("type", "state_empty_title")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(icon_container, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_title)

    if body:
        lbl_body = QLabel(body)
        lbl_body.setWordWrap(True)
        lbl_body.setProperty("type", "state_empty_body")
        lbl_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_body)
    return card, layout


def make_rarity_badge_statistics(label: str, color: str, text_color: str | None = None) -> QLabel:
    """Tạo huy hiệu (Badge) độ hiếm theo chuẩn Material You M3."""
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    palette = _p()
    if not text_color:
        text_color = readable_text_on(color, dark_text=palette.TEXT_PRIMARY, light_text="#FFFFFF")
    lbl.setStyleSheet(f"""
        background-color: {color}; color: {text_color};
        border-radius: 11px; padding: 3px 10px;
        min-width: 68px;
        font-weight: 700; font-size: 11px; font-family: {APP_FONT_STACK};
    """)
    return lbl


def make_rarity_badge_wand(label: str, color: str, text_color: str | None = None) -> QLabel:
    """Tạo huy hiệu (Badge) độ hiếm cho trang Wand."""
    return make_rarity_badge_statistics(label, color, text_color=text_color)

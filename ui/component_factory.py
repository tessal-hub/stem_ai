"""
Factory tạo widget UI thống nhất — Theme aware via Vanguard Palette.
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ui.mac_material import apply_soft_shadow
from logic.theme_manager import theme_manager

from ui.tokens import (
    # Sizes
    BTN_H,
    SETTINGS_BTN_H,
    SETTINGS_INPUT_H,
    LABEL_W,
    RECORD_GRAPH_MIN_H,
    TITLE_FONT_STACK,
    APP_FONT_STACK,
)
from ui.modern_layout import (
    MARGIN_COMFORTABLE,
    SPACING_XS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
)

def p(): return theme_manager.get_palette()

# ────────────────────────────────────────────────────────────────────────────
# CARD & FRAME FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_card(
    margins: tuple[int, int, int, int] = (SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD),
    spacing: int = SPACING_SM,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a high-end 'Double-Bezel' styled card."""
    palette = p()
    outer = QFrame()
    outer.setObjectName("VanguardCardOuter")
    outer.setStyleSheet(f"""
        #VanguardCardOuter {{
            background-color: {palette.SURFACE_TERTIARY};
            border: 1px solid {palette.BORDER};
            border-radius: 20px;
        }}
    """)
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(6, 6, 6, 6) 
    
    inner = QFrame()
    inner.setObjectName("VanguardCardInner")
    inner.setStyleSheet(f"""
        #VanguardCardInner {{
            background-color: {palette.SURFACE_PRIMARY};
            border: none;
            border-radius: 14px;
        }}
    """)
    apply_soft_shadow(inner, blur_radius=16, y_offset=3, color=palette.SHADOW_COLOR)
    
    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(*margins)
    inner_layout.setSpacing(spacing)
    outer_layout.addWidget(inner)
    return outer, inner_layout

def make_card_frame() -> QFrame:
    """Legacy alias for creating a standalone Vanguard card frame."""
    palette = p()
    frame = QFrame()
    frame.setObjectName("VanguardCardOuter")
    frame.setStyleSheet(f"""
        #VanguardCardOuter {{
            background-color: {palette.SURFACE_TERTIARY};
            border: 1px solid {palette.BORDER};
            border-radius: 20px;
        }}
    """)
    return frame

# ────────────────────────────────────────────────────────────────────────────
# BUTTON FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_button(label: str, style: str = "", height: int = BTN_H) -> QPushButton:
    btn = QPushButton(label)
    btn.setFixedHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if style:
        btn.setStyleSheet(style)
    return btn

def make_primary_button(label: str, height: int = BTN_H) -> QPushButton:
    palette = p()
    btn = make_button(label, height=height)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {palette.PRIMARY};
            color: {palette.SURFACE_PRIMARY};
            border: none;
            border-radius: {height//2}px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            padding: 0 20px;
        }}
        QPushButton:hover {{ background-color: {palette.PRIMARY_LIGHT}; }}
    """)
    return btn

def make_outline_button(label: str, height: int = BTN_H) -> QPushButton:
    palette = p()
    btn = make_button(label, height=height)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            color: {palette.TEXT_PRIMARY};
            border: 1px solid {palette.BORDER};
            border-radius: {height//2}px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            padding: 0 20px;
        }}
        QPushButton:hover {{ background-color: {palette.HOVER_BG}; border-color: {palette.TEXT_PRIMARY}; }}
    """)
    return btn

# ────────────────────────────────────────────────────────────────────────────
# LABEL FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_section_label(text: str, accent: bool = True) -> QLabel:
    palette = p()
    lbl = QLabel(text)
    color = palette.PRIMARY if accent else palette.TEXT_PRIMARY
    lbl.setStyleSheet(f"""
        font-family: {TITLE_FONT_STACK};
        color: {color};
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    """)
    return lbl

def make_empty_state_card(title: str, message: str) -> tuple[QFrame, QVBoxLayout]:
    palette = p()
    frame, layout = make_card(margins=(32, 32, 32, 32))
    
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 18px; font-weight: 700;")
    
    body_lbl = QLabel(message)
    body_lbl.setWordWrap(True)
    body_lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 13px; line-height: 1.5;")
    
    layout.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(body_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
    return frame, layout

def make_graph_placeholder() -> QLabel:
    palette = p()
    lbl = QLabel("FOCAL STUDY AREA")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        background-color: {palette.SURFACE_TERTIARY};
        color: {palette.TEXT_TERTIARY};
        border: 1px dashed {palette.BORDER};
        border-radius: 12px;
        font-weight: 800;
        font-size: 10px;
        letter-spacing: 0.2em;
    """)
    lbl.setMinimumHeight(400)
    return lbl

def make_rarity_badge_statistics(label: str, color: str) -> QLabel:
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        background-color: {color};
        color: #FFFFFF;
        border-radius: 10px;
        padding: 2px 10px;
        font-weight: 900;
        font-size: 9px;
        letter-spacing: 0.05em;
    """)
    return lbl

def make_rarity_badge_wand(label: str, color: str) -> QLabel:
    return make_rarity_badge_statistics(label, color)

def make_checkbox(text: str, checked: bool = False) -> QCheckBox:
    palette = p()
    cb = QCheckBox(text)
    cb.setChecked(checked)
    cb.setStyleSheet(f"""
        QCheckBox {{ color: {palette.TEXT_PRIMARY}; font-size: 11px; font-weight: 600; spacing: 8px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {palette.BORDER}; }}
        QCheckBox::indicator:checked {{ background-color: {palette.PRIMARY}; border: none; image: none; }}
    """)
    return cb

def make_hint(text: str, color: str = "") -> QLabel:
    palette = p()
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    c = color if color else palette.TEXT_TERTIARY
    lbl.setStyleSheet(f"color: {c}; font-size: 11px; font-weight: 500; line-height: 1.4;")
    return lbl

def make_card_name_label(name: str) -> QLabel:
    palette = p()
    lbl = QLabel(name)
    lbl.setStyleSheet(f"font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 14px; font-weight: 700;")
    return lbl

def make_card_count_label(count: int) -> QLabel:
    palette = p()
    lbl = QLabel(str(count))
    lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 11px; font-weight: 800; text-transform: uppercase;")
    return lbl

def make_error_state_card(title: str, message: str) -> tuple[QFrame, QVBoxLayout]:
    palette = p()
    frame, layout = make_card(margins=(24, 24, 24, 24))
    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(f"color: {palette.STATUS_ERROR}; font-weight: 800; font-size: 13px; text-transform: uppercase;")
    lbl_msg = QLabel(message)
    lbl_msg.setWordWrap(True)
    lbl_msg.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 12px;")
    layout.addWidget(lbl_title)
    layout.addWidget(lbl_msg)
    return frame, layout

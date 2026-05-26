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
from ui.color_utils import readable_text_on

from ui.tokens import (
    # Sizes
    BTN_H,
    SETTINGS_BTN_H,
    SETTINGS_INPUT_H,
    LABEL_W,
    RECORD_GRAPH_MIN_H,
    TITLE_FONT_STACK,
    APP_FONT_STACK,
    CARD_RADIUS,
    BTN_RADIUS,
    INPUT_RADIUS,
    BADGE_RADIUS,
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
    spacing: int = SPACING_MD,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a high-end 'Double-Bezel' styled card with generous padding."""
    palette = p()
    outer = QFrame()
    outer.setObjectName("VanguardCardOuter")
    outer.setStyleSheet(f"""
        #VanguardCardOuter {{
            background-color: {palette.SURFACE_TERTIARY};
            border: 1px solid {palette.BORDER};
            border-radius: {CARD_RADIUS};
        }}
    """)
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(8, 8, 8, 8) 
    
    inner = QFrame()
    inner.setObjectName("VanguardCardInner")
    inner.setStyleSheet(f"""
        #VanguardCardInner {{
            background-color: {palette.SURFACE_PRIMARY};
            border: none;
            border-radius: calc({CARD_RADIUS} - 4px);
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
            border-radius: {CARD_RADIUS};
        }}
    """)
    return frame

# ────────────────────────────────────────────────────────────────────────────
# BUTTON FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_button(label: str, style: str = "", height: int = BTN_H) -> QPushButton:
    btn = QPushButton(label)
    btn.setMinimumHeight(height)
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
            border-radius: {BTN_RADIUS};
            font-family: {APP_FONT_STACK};
            font-size: 13px;
            font-weight: 600;
            padding: 0 24px;
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
            border-radius: {BTN_RADIUS};
            font-family: {APP_FONT_STACK};
            font-size: 13px;
            font-weight: 600;
            padding: 0 24px;
        }}
        QPushButton:hover {{ background-color: {palette.HOVER_BG}; border-color: {palette.PRIMARY}; }}
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
        font-size: 14px;
    """)
    return lbl

def make_empty_state_card(title: str, message: str) -> tuple[QFrame, QVBoxLayout]:
    palette = p()
    frame, layout = make_card(margins=(32, 32, 32, 32))
    
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 18px; font-weight: 700;")
    
    body_lbl = QLabel(message)
    body_lbl.setWordWrap(True)
    body_lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 13px; line-height: 1.5; font-family: {APP_FONT_STACK};")
    
    layout.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(body_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
    return frame, layout

def make_card_name_label(name: str) -> QLabel:
    palette = p()
    lbl = QLabel(name)
    lbl.setStyleSheet(f"color: {palette.TEXT_PRIMARY}; font-size: 15px; font-weight: 600; font-family: {APP_FONT_STACK};")
    return lbl

def make_card_count_label(count: int) -> QLabel:
    palette = p()
    lbl = QLabel(f"{count} samples")
    lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 12px; font-family: {APP_FONT_STACK};")
    return lbl

def make_error_state_card(title: str, message: str) -> tuple[QFrame, QVBoxLayout]:
    palette = p()
    frame, layout = make_card(margins=(32, 32, 32, 32))
    
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"color: {palette.STATUS_ERROR_TEXT}; font-size: 18px; font-weight: 700; font-family: {TITLE_FONT_STACK};")
    
    body_lbl = QLabel(message)
    body_lbl.setWordWrap(True)
    body_lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY}; font-size: 13px; line-height: 1.5; font-family: {APP_FONT_STACK};")
    
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
        border-radius: {CARD_RADIUS};
        font-family: {APP_FONT_STACK};
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.1em;
    """)
    lbl.setMinimumHeight(400)
    return lbl

def make_rarity_badge_wand(label: str, color: str) -> QLabel:
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_color = readable_text_on(color, dark_text="#111111", light_text="#FFFFFF")
    lbl.setStyleSheet(f"""
        background-color: {color};
        color: {text_color};
        border-radius: {BADGE_RADIUS};
        padding: 4px 12px;
        font-family: {APP_FONT_STACK};
        font-weight: 700;
        font-size: 9px;
    """)
    return lbl

def make_rarity_badge_statistics(label: str, color: str) -> QLabel:
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_color = readable_text_on(color, dark_text="#111111", light_text="#FFFFFF")
    lbl.setStyleSheet(f"""
        background-color: {color};
        color: {text_color};
        border-radius: {BADGE_RADIUS};
        padding: 4px 14px;
        font-family: {APP_FONT_STACK};
        font-weight: 700;
        font-size: 10px;
    """)
    return lbl

def make_checkbox(label: str, checked: bool = False) -> QCheckBox:
    palette = p()
    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    chk.setStyleSheet(f"""
        QCheckBox {{
            color: {palette.TEXT_PRIMARY};
            font-family: {APP_FONT_STACK};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {palette.BORDER};
            background-color: {palette.SURFACE_TERTIARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {palette.PRIMARY};
            border-color: {palette.PRIMARY};
        }}
        QCheckBox::indicator:hover {{
            border-color: {palette.PRIMARY};
        }}
    """)
    return chk

def make_hint(text: str, color: str | None = None) -> QLabel:
    palette = p()
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    text_color = color if color else palette.TEXT_TERTIARY
    lbl.setStyleSheet(f"""
        color: {text_color};
        font-size: 12px;
        line-height: 1.4;
        font-style: italic;
        font-family: {APP_FONT_STACK};
    """)
    return lbl

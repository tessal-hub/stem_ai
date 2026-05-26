"""
Modern, professional theme system with Light/Dark mode support.
"""

from PyQt6.QtWidgets import QFrame, QWidget, QApplication
from ui.palettes import LIGHT_PALETTE, DARK_PALETTE, Palette
from logic.theme_manager import theme_manager
from ui.color_utils import readable_text_on
from ui.tokens import (
    APP_FONT_STACK,
    TITLE_FONT_STACK,
    MONO_FONT_STACK,
    CARD_RADIUS,
    BTN_RADIUS,
    INPUT_RADIUS,
)

def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Generate comprehensive modern QSS stylesheet based on selected theme.
    Force focus outline removal and high contrast.
    """
    p = DARK_PALETTE if theme_name == "dark" else LIGHT_PALETTE
    on_primary = readable_text_on(p.PRIMARY, dark_text=p.SURFACE_PRIMARY, light_text="#FFFFFF")
    
    # Base stylesheet - KILL OUTLINES GLOBALLY
    qss = f"""
* {{
    outline: none;
}}

QWidget {{
    font-family: {APP_FONT_STACK};
}}

QWidget#MainBox {{
    background-color: {p.SURFACE_PRIMARY};
    color: {p.TEXT_PRIMARY};
}}

QMainWindow {{
    background-color: {p.SURFACE_PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CARDS & CONTAINERS
   ═══════════════════════════════════════════════════════════════════════════ */

QFrame#CardFrame, QWidget#Card, #HomeViewerCard, #HomeRightSection, #CardFrameElevated, ClickableFrame, #VanguardCardOuter {{
    background-color: {p.SURFACE_TERTIARY};
    border: 1px solid {p.BORDER};
    border-radius: {CARD_RADIUS};
}}

#VanguardCardInner, #HomeViewerSurface {{
    background-color: {p.SURFACE_PRIMARY};
    border: none;
    border-radius: 12px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS - NO OUTLINES
   ═══════════════════════════════════════════════════════════════════════════ */

QPushButton {{
    background-color: {p.SURFACE_TERTIARY};
    color: {p.TEXT_PRIMARY};
    border: 1px solid {p.BORDER};
    border-radius: {BTN_RADIUS};
    padding: 8px 20px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {p.HOVER_BG};
    border-color: {p.PRIMARY};
}}

QPushButton:focus {{
    border: 2px solid {p.PRIMARY};
}}

QPushButton#btn_primary, QPushButton#btn_start, QPushButton#btn_record {{
    background-color: {p.PRIMARY};
    color: {on_primary};
    border: none;
}}

QPushButton#btn_stop, QPushButton#btn_danger {{
    background-color: {p.STATUS_ERROR};
    color: {p.STATUS_ERROR_TEXT};
    border: none;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUTS
   ═══════════════════════════════════════════════════════════════════════════ */

QLineEdit, QComboBox, QSpinBox {{
    background-color: {p.SURFACE_PRIMARY};
    color: {p.TEXT_PRIMARY};
    border: 1px solid {p.BORDER};
    border-radius: {INPUT_RADIUS};
    padding: 8px 12px;
}}

QLineEdit:focus, QComboBox:focus {{
    border: 2px solid {p.PRIMARY};
}}

QComboBox::drop-down {{ border: none; }}

QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item {{
    padding: 12px;
    border-radius: 8px;
    margin: 4px 8px;
    color: {p.TEXT_PRIMARY};
    background-color: {p.SURFACE_TERTIARY};
    border: 1px solid {p.BORDER};
}}

QListWidget::item:selected {{
    background-color: {p.PRIMARY};
    color: {p.SURFACE_PRIMARY};
    border: none;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   MAC SHELL
   ═══════════════════════════════════════════════════════════════════════════ */

QWidget#StemChrome {{
    background-color: {p.SURFACE_SECONDARY};
}}

QWidget#StemToolbar {{
    background-color: {p.SURFACE_PRIMARY};
    border-bottom: 1px solid {p.BORDER};
}}

QLabel#StemToolbarTitle {{
    font-family: {TITLE_FONT_STACK};
    color: {p.TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 700;
}}

QLabel#StemToolbarSubtitle {{
    color: {p.TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 500;
}}

QWidget#StemSidebar {{
    background-color: {p.SURFACE_TERTIARY};
    border-right: 1px solid {p.BORDER};
}}

QToolButton#StemNavBtn {{
    color: {p.TEXT_PRIMARY};
    background-color: transparent;
    border: none;
    border-radius: {BTN_RADIUS};
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 500;
    margin: 2px 8px;
}}

QToolButton#StemNavBtn:hover {{
    background-color: {p.HOVER_BG};
}}

QToolButton#StemNavBtn[active="true"] {{
    background-color: {p.PRIMARY};
    color: {p.SURFACE_PRIMARY};
    font-weight: 700;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SCROLLBARS - MODERN & VISIBLE
   ═══════════════════════════════════════════════════════════════════════════ */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {p.TEXT_TERTIARY};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p.PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TERMINAL
   ═══════════════════════════════════════════════════════════════════════════ */

QTextEdit, QPlainTextEdit {{
    background-color: {p.TERM_BG};
    color: {p.TERM_FG};
    border-radius: {INPUT_RADIUS};
    font-family: {MONO_FONT_STACK};
    font-size: 12px;
    padding: 12px;
    border: 1px solid {p.BORDER};
}}
"""
    return qss

def apply_modern_theme(widget_or_app, theme_name: str = "light") -> None:
    widget_or_app.setStyleSheet(get_modern_stylesheet(theme_name))

def apply_flat_widget_chrome(root_widget: QWidget) -> None:
    for frame in root_widget.findChildren(QFrame):
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setFrameShadow(QFrame.Shadow.Plain)
        frame.setLineWidth(0)

"""
Modern, professional theme system with Light/Dark mode support.
"""

from PyQt6.QtWidgets import QFrame, QWidget, QApplication
from ui.palettes import LIGHT_PALETTE, DARK_PALETTE, Palette
from logic.theme_manager import theme_manager
from ui.color_utils import readable_text_on

def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Generate comprehensive modern QSS stylesheet based on selected theme.
    """
    p = DARK_PALETTE if theme_name == "dark" else LIGHT_PALETTE
    on_primary = readable_text_on(p.PRIMARY, dark_text=p.SURFACE_PRIMARY, light_text="#FFFFFF")
    on_status_error = readable_text_on(p.STATUS_ERROR, dark_text=p.TEXT_PRIMARY, light_text="#FFFFFF")
    
    # Base stylesheet
    qss = f"""
QWidget#MainBox {{
    background-color: {p.SURFACE_PRIMARY};
    color: {p.TEXT_PRIMARY};
}}

QMainWindow {{
    background-color: {p.SURFACE_PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CARDS & CONTAINERS (Using Object Names)
   ═══════════════════════════════════════════════════════════════════════════ */

QFrame#CardFrame, QWidget#Card, #HomeViewerCard, #HomeRightSection, #CardFrameElevated, ClickableFrame {{
    background-color: {p.GLASS_BG};
    border: 1px solid {p.BORDER_LIGHT};
    border-radius: 20px;
}}

#HomeViewerSurface {{
    background-color: {p.GLASS_BG_STRONG};
    border: none;
    border-radius: 18px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════════════════════════════════════ */

QPushButton {{
    background-color: {p.GLASS_BG_STRONG};
    color: {p.TEXT_SECONDARY};
    border: 1px solid {p.GLASS_EDGE};
    border-radius: 12px;
    padding: 6px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {p.HOVER_BG};
    color: {p.PRIMARY};
}}

QPushButton#btn_primary, QPushButton#btn_start, QPushButton#btn_record {{
    background-color: {p.PRIMARY};
    color: {on_primary};
    border: none;
}}

QPushButton#btn_stop, QPushButton#btn_danger {{
    background-color: {p.STATUS_ERROR};
    color: {on_status_error};
    border: none;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUTS
   ═══════════════════════════════════════════════════════════════════════════ */

QLineEdit, QComboBox, QSpinBox {{
    background-color: {p.GLASS_BG_STRONG};
    color: {p.TEXT_PRIMARY};
    border: 1px solid {p.BORDER_LIGHT};
    border-radius: 8px;
    padding: 6px 12px;
}}

QComboBox::drop-down {{ border: none; }}

QListWidget {{
    background-color: {p.GLASS_BG_STRONG};
    border: none;
    border-radius: 16px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px;
    border-radius: 8px;
    margin: 2px 8px;
    color: {p.TEXT_PRIMARY};
}}

QListWidget::item:selected {{
    background-color: {p.HOVER_BG};
    color: {p.TEXT_PRIMARY};
    border-left: 4px solid {p.PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   MAC SHELL (sidebar / toolbar) — follows palette for dark mode
   ═══════════════════════════════════════════════════════════════════════════ */

QWidget#StemChrome {{
    background-color: {p.SURFACE_PRIMARY};
    border: none;
    border-radius: 14px;
}}

QWidget#StemToolbar {{
    background-color: {p.SURFACE_PRIMARY};
    border-bottom: 1px solid {p.BORDER_LIGHT};
}}

QLabel#StemToolbarTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 700;
}}

QLabel#StemToolbarSubtitle {{
    color: {p.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#StemNavHint {{
    color: {p.TEXT_TERTIARY};
    font-size: 11px;
    font-weight: 500;
}}

QWidget#StemSidebar {{
    background-color: {p.SURFACE_SECONDARY};
    border-right: 1px solid {p.BORDER_LIGHT};
}}

QLabel#StemNavSectionLabel {{
    color: {p.TEXT_TERTIARY};
    font-size: 11px;
    font-weight: 700;
}}

QLabel#StemBrandTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 800;
}}

QLabel#StemBrandSubtitle {{
    color: {p.TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 600;
}}

QToolButton#StemNavBtn {{
    color: {p.TEXT_SECONDARY};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
}}

QToolButton#StemNavBtn:hover {{
    background-color: {p.HOVER_BG};
    color: {p.PRIMARY};
    border: 1px solid {p.BORDER};
    border-radius: 14px;
}}

QToolButton#StemNavBtn[active="true"] {{
    background-color: {p.PRIMARY};
    color: {on_primary};
    border: 1px solid {p.PRIMARY};
    border-radius: 14px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SCROLLBARS
   ═══════════════════════════════════════════════════════════════════════════ */

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}

QScrollBar::handle:vertical {{
    background: {p.TEXT_TERTIARY};
    border-radius: 4px;
    min-height: 20px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TERMINAL
   ═══════════════════════════════════════════════════════════════════════════ */

QTextEdit, QPlainTextEdit {{
    background-color: {p.TERM_BG};
    color: {p.TERM_FG};
    border-radius: 12px;
    font-family: "Consolas", monospace;
    font-size: 11px;
    padding: 10px;
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

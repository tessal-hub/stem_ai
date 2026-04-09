"""
Modern, professional theme system for the STEM Spell Book application.

This module provides:
  - Comprehensive QSS stylesheets for all components
  - Modern color palette with professional accents
  - Enhanced visual hierarchy and depth
  - Smooth transitions and state interactions
  - Component-specific styling (buttons, cards, inputs, etc.)

The architecture pattern:
  1. Define semantic color variables and component styles
  2. Return complete QSS string ready for application via setStyleSheet()
  3. Support theme switching (light/dark) at runtime if needed

Usage:
  In main_window.py or app initialization:
  ```
  from theme import get_modern_stylesheet
  app.setStyleSheet(get_modern_stylesheet())
  ```
"""

from ui.tokens import (
    # Modern color palette
    PRIMARY_COLOR,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    SECONDARY_COLOR,
    SECONDARY_LIGHT,
    SECONDARY_DARK,
    SURFACE_PRIMARY,
    SURFACE_SECONDARY,
    SURFACE_TERTIARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    BORDER_COLOR,
    BORDER_LIGHT,
    STATUS_SUCCESS,
    STATUS_WARNING,
    STATUS_ERROR,
    SHADOW_LIGHT,
    SHADOW_MEDIUM,
    SHADOW_DARK,
    APP_FONT_STACK,
)


def get_modern_stylesheet() -> str:
    """
    Generate comprehensive modern QSS stylesheet.
    
    Returns:
        str: Complete QSS stylesheet for the entire application.
    """
    return f"""
/* ═══════════════════════════════════════════════════════════════════════════
   GLOBAL & BASE STYLES
   ═══════════════════════════════════════════════════════════════════════════ */

QWidget {{
    font-family: {APP_FONT_STACK};
    font-size: 13px;
}}

QMainWindow {{
    background-color: {SURFACE_PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS - Modern Variants
   ═══════════════════════════════════════════════════════════════════════════ */

/* PRIMARY BUTTON - Bold action button */
QPushButton#btn_primary, QPushButton#btn_start, QPushButton#btn_record {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#btn_primary:hover, QPushButton#btn_start:hover, QPushButton#btn_record:hover {{
    background-color: {PRIMARY_DARK};
}}

QPushButton#btn_primary:pressed, QPushButton#btn_start:pressed, QPushButton#btn_record:pressed {{
    background-color: {PRIMARY_DARK};
}}

QPushButton#btn_primary:disabled, QPushButton#btn_start:disabled, QPushButton#btn_record:disabled {{
    background-color: #d1d5db;
    color: #9ca3af;
}}

/* SECONDARY BUTTON - Default action button */
QPushButton#btn_secondary, QPushButton#btn_simulate {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#btn_secondary:hover, QPushButton#btn_simulate:hover {{
    background-color: {SURFACE_TERTIARY};
    border-color: {PRIMARY_COLOR};
    color: {PRIMARY_COLOR};
}}

QPushButton#btn_secondary:pressed, QPushButton#btn_simulate:pressed {{
    background-color: #f3f4f6;
    border-color: {PRIMARY_DARK};
}}

/* DANGER BUTTON - Destructive actions */
QPushButton#btn_stop, QPushButton#btn_danger {{
    background-color: {STATUS_ERROR};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#btn_stop:hover, QPushButton#btn_danger:hover {{
    background-color: #dc2626;
}}

QPushButton#btn_stop:pressed, QPushButton#btn_danger:pressed {{
    background-color: #991b1b;
}}

/* OUTLINE BUTTON - Secondary importance */
QPushButton#btn_outline {{
    background-color: transparent;
    color: {PRIMARY_COLOR};
    border: 1.5px solid {PRIMARY_COLOR};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#btn_outline:hover {{
    background-color: rgba(59, 130, 246, 0.08);
    border-color: {PRIMARY_DARK};
}}

QPushButton#btn_outline:pressed {{
    background-color: rgba(59, 130, 246, 0.12);
}}

/* SMALL/COMPACT BUTTONS */
QPushButton#btn_small {{
    min-height: 28px;
    max-height: 28px;
    padding: 4px 12px;
    font-size: 12px;
}}

/* FOCUS RINGS - Visible keyboard focus for all interactive controls */
QPushButton:focus {{
    outline: none;
    border: 2px solid {PRIMARY_COLOR};
}}

/* ICON BUTTON - Navigation, utilities */
QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    margin: 0px;
}}

QToolButton:hover {{
    background-color: rgba(59, 130, 246, 0.08);
}}

QToolButton:pressed {{
    background-color: rgba(59, 130, 246, 0.12);
}}

QToolButton:checked {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY_COLOR};
    border: 1px solid {PRIMARY_COLOR};
}}

QToolButton:focus {{
    outline: none;
    border: 2px solid {PRIMARY_COLOR};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUT FIELDS - Text, Combo, Spin
   ═══════════════════════════════════════════════════════════════════════════ */

QLineEdit, QPlainTextEdit {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY_COLOR};
}}

QLineEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {PRIMARY_COLOR};
    padding: 7px 11px;
    background-color: {SURFACE_PRIMARY};
}}

QLineEdit:disabled, QPlainTextEdit:disabled {{
    background-color: #f3f4f6;
    color: #9ca3af;
    border-color: #e5e7eb;
}}

QComboBox {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 32px;
    font-size: 13px;
}}

QComboBox:hover {{
    border-color: {PRIMARY_COLOR};
}}

QComboBox:focus {{
    border: 2px solid {PRIMARY_COLOR};
    padding: 5px 11px;
}}

QComboBox::drop-down {{
    border: none;
    width: 32px;
}}

QComboBox::down-arrow {{
    image: none;
    width: 0px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE_PRIMARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 0px;
    margin: 0px;
    selection-background-color: {PRIMARY_LIGHT};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    height: 32px;
    border: none;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {PRIMARY_LIGHT};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}

QSpinBox {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 4px;
    min-height: 32px;
}}

QSpinBox:focus {{
    border: 2px solid {PRIMARY_COLOR};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: transparent;
    border: none;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CHECKBOXES & RADIO BUTTONS
   ═══════════════════════════════════════════════════════════════════════════ */

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    background-color: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background-color: {SURFACE_SECONDARY};
    border: 1.5px solid {BORDER_COLOR};
    border-radius: 4px;
}}

QCheckBox::indicator:hover {{
    border-color: {PRIMARY_COLOR};
    background-color: {SURFACE_TERTIARY};
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
}}

QCheckBox::indicator:checked:focus {{
    border-color: {PRIMARY_DARK};
}}

QCheckBox::indicator:disabled {{
    background-color: #f3f4f6;
    border-color: #e5e7eb;
}}

QCheckBox::indicator:checked:disabled {{
    background-color: #d1d5db;
    border-color: #d1d5db;
}}

QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    background-color: {SURFACE_SECONDARY};
    border: 1.5px solid {BORDER_COLOR};
    border-radius: 9px;
}}

QRadioButton::indicator:hover {{
    border-color: {PRIMARY_COLOR};
    background-color: {SURFACE_TERTIARY};
}}

QRadioButton::indicator:checked {{
    background-color: {SURFACE_SECONDARY};
    border: 3px solid {PRIMARY_COLOR};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CARDS & FRAMES - Container Styling
   ═══════════════════════════════════════════════════════════════════════════ */

QFrame#CardFrame, QWidget#Card {{
    background-color: {SURFACE_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
}}

QFrame#CardFrame:hover {{
    border-color: {BORDER_LIGHT};
}}

/* Elevated card for emphasis */
QFrame#CardFrameElevated {{
    background-color: {SURFACE_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
}}

QFrame#CardFrameElevated:hover {{
    border-color: {PRIMARY_COLOR};
}}

/* Graph/Plot card - darker background */
QFrame#GraphCard {{
    background-color: #1a1a1f;
    border: 1px solid #3a3a40;
    border-radius: 10px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   LABELS & TEXT
   ═══════════════════════════════════════════════════════════════════════════ */

QLabel {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
}}

QLabel#TextMuted {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#TextSmall {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel#SectionTitle {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel#SectionSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

QLabel#StatusBadge {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY_COLOR};
    border: 1px solid {PRIMARY_COLOR};
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QLabel#StatusError {{
    background-color: rgba(239, 68, 68, 0.1);
    color: {STATUS_ERROR};
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QLabel#StatusSuccess {{
    background-color: rgba(16, 185, 129, 0.1);
    color: {STATUS_SUCCESS};
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   LISTS & TABLES
   ═══════════════════════════════════════════════════════════════════════════ */

QListWidget, QTableWidget {{
    background-color: {SURFACE_PRIMARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    gridline-color: {BORDER_LIGHT};
    outline: none;
}}

QListWidget::item, QTableWidget::item {{
    padding: 4px 12px;
    border-bottom: 1px solid {BORDER_LIGHT};
}}

QListWidget::item:hover, QTableWidget::item:hover {{
    background-color: {PRIMARY_LIGHT};
}}

QListWidget::item:selected, QTableWidget::item:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}

QHeaderView::section {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_PRIMARY};
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {BORDER_COLOR};
    font-weight: 600;
    font-size: 12px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   PROGRESS BARS
   ═══════════════════════════════════════════════════════════════════════════ */

QProgressBar {{
    background-color: {SURFACE_SECONDARY};
    color: transparent;
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
    text-align: right;
}}

QProgressBar::chunk {{
    background-color: {PRIMARY_COLOR};
    border-radius: 2px;
}}

QProgressBar:disabled {{
    background-color: #e5e7eb;
}}

QProgressBar:disabled::chunk {{
    background-color: #d1d5db;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SCROLLBARS - Modern style
   ═══════════════════════════════════════════════════════════════════════════ */

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_COLOR};
    border-radius: 4px;
    min-height: 20px;
    margin: 0px 0px 0px 0px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SECONDARY};
}}

QScrollBar::handle:vertical:pressed {{
    background-color: {TEXT_PRIMARY};
}}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER_COLOR};
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {TEXT_SECONDARY};
}}

QScrollBar::handle:horizontal:pressed {{
    background-color: {TEXT_PRIMARY};
}}

QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {{
    width: 0px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   DIALOGS & POPUPS
   ═══════════════════════════════════════════════════════════════════════════ */

QDialog {{
    background-color: {SURFACE_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
}}

QMessageBox {{
    background-color: {SURFACE_PRIMARY};
}}

QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TOOLTIPS
   ═══════════════════════════════════════════════════════════════════════════ */

QToolTip {{
    background-color: #1f2937;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TAB WIDGET
   ═══════════════════════════════════════════════════════════════════════════ */

QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {SURFACE_SECONDARY};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 12px;
}}

QTabBar::tab:hover {{
    background-color: {SURFACE_TERTIARY};
    color: {TEXT_PRIMARY};
}}

QTabBar::tab:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border-bottom: 2px solid {PRIMARY_DARK};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SPLITTERS
   ═══════════════════════════════════════════════════════════════════════════ */

QSplitter::handle {{
    background-color: {BORDER_LIGHT};
    border: none;
}}

QSplitter::handle:hover {{
    background-color: {BORDER_COLOR};
}}
"""


def apply_modern_theme(widget_or_app) -> None:
    """
    Apply modern theme to a widget or entire application.
    
    Args:
        widget_or_app: QWidget, QMainWindow, or QApplication instance
    """
    widget_or_app.setStyleSheet(get_modern_stylesheet())

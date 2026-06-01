"""
theme.py — Hệ thống quản lý giao diện (Theme) toàn cục.

Cung cấp các hàm tạo stylesheet (QSS) hiện đại, chỉ áp dụng Light Mode
và giữ giao diện đồng nhất cho toàn bộ ứng dụng.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QWidget

from ui.asset_utils import resolve_asset_path
from ui.tokens import (
    SURFACE_0, SURFACE_1, SURFACE_2,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_MUTED,
    PRIMARY_COLOR, PRIMARY_LIGHT, PRIMARY_DARK, ACCENT_TEXT,
    BORDER_COLOR, BORDER_LIGHT, BORDER_MID,
    STATUS_SUCCESS, STATUS_WARNING, STATUS_ERROR,
    FILL_PRIMARY, FILL_SECONDARY, FILL_TERTIARY,
    HOVER_BG, BG_DARK, TERM_BG, TERM_FG,
    APP_FONT_STACK, TITLE_FONT_STACK, MONO_FONT_STACK,
    RADIUS_XS, RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_XL, RADIUS_FULL
)


def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Tạo chuỗi stylesheet QSS dựa trên theme đã chọn.
    """
    _ = theme_name
    check_icon = resolve_asset_path("assets/icon/cooliocns SVG/Interface/Check.svg").replace("\\", "/")

    return f"""
        /* ── Base ── */
        QWidget {{ font-family: {APP_FONT_STACK}; color: {TEXT_PRIMARY}; }}
        QMainWindow, QWidget#MainBox, QWidget#StemChrome, QWidget#StemSidebar {{ background-color: {SURFACE_0}; }}
        QStackedWidget, QWidget#StemContentHost, QScrollArea, QAbstractScrollArea {{ background-color: transparent; border: none; }}
        
        /* ── Cards ── */
        QFrame#CardFrame, QFrame#VanguardCardOuter, QWidget#Card, #HomeViewerCard, #HomeRightSection, #CardFrameElevated, #VanguardCardInner, QFrame[type="statistics_card"], QWidget[type="statistics_card"], #HomeViewerSurface {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
        }}
        
        /* ── Buttons ── */
        QPushButton, QToolButton {{
            background-color: transparent;
            color: {TEXT_PRIMARY};
            border: none;
            border-radius: {RADIUS_SM}px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 13px;
        }}
        
        QPushButton[type="primary"], QPushButton[type="start"] {{
            background-color: {PRIMARY_COLOR};
            color: white;
            font-weight: 600;
        }}
        QPushButton[type="primary"]:hover, QPushButton[type="start"]:hover {{ background-color: {PRIMARY_DARK}; }}
        
        QPushButton[type="base"], QPushButton[type="back"] {{
            background-color: rgba(0, 122, 255, 0.10);
            color: {PRIMARY_COLOR};
            font-weight: 600;
        }}
        QPushButton[type="base"]:hover, QPushButton[type="back"]:hover {{ background-color: rgba(0, 122, 255, 0.18); }}
        
        QPushButton[type="stop"], QPushButton[type="danger"] {{
            background-color: rgba(255, 59, 48, 0.10);
            color: {STATUS_ERROR};
        }}
        QPushButton[type="stop"]:hover, QPushButton[type="danger"]:hover {{ background-color: {STATUS_ERROR}; color: white; }}
        
        QPushButton[type="outline"], QPushButton[type="snip"] {{
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
        }}
        QPushButton[type="outline"]:hover, QPushButton[type="snip"]:hover {{ background-color: {FILL_SECONDARY}; color: {TEXT_PRIMARY}; }}

        QPushButton:disabled {{
            background-color: {FILL_SECONDARY};
            color: {TEXT_TERTIARY};
            border: 1px solid {BORDER_COLOR};
        }}

        /* ── Inputs ── */
        QLineEdit, QComboBox, QSpinBox, QTimeEdit, QDateEdit {{
            background-color: {SURFACE_0};
            border: none;
            border-radius: {RADIUS_SM}px;
            padding: 8px 12px;
            color: {TEXT_PRIMARY};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 1.5px solid {PRIMARY_COLOR};
        }}
        
        /* ── Lists ── */
        QListWidget, QTableWidget, QTreeWidget {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
            outline: none;
            gridline-color: transparent;
        }}
        QListWidget::item {{
            min-height: 44px;
            border-radius: {RADIUS_MD}px;
            padding: 4px;
            color: {TEXT_PRIMARY};
        }}
        QListWidget::item:hover {{ background-color: {HOVER_BG}; }}
        QListWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY_COLOR}; font-weight: 600; }}
        
        /* ── Progress & Scroll ── */
        QProgressBar {{
            background-color: {FILL_TERTIARY};
            border: none;
            border-radius: {RADIUS_FULL}px;
            text-align: center;
        }}
        QProgressBar::chunk {{ background-color: {PRIMARY_COLOR}; border-radius: {RADIUS_FULL}px; }}
        
        QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {BORDER_COLOR}; min-height: 30px; border-radius: 3px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
        
        /* ── Terminal ── */
        QTextEdit, QPlainTextEdit {{
            background-color: {BG_DARK};
            color: {TERM_FG};
            border: none;
            border-radius: {RADIUS_LG}px;
            font-family: {MONO_FONT_STACK};
            padding: 12px;
        }}
        
        /* ── Dialog ── */
        QDialog {{ background-color: {SURFACE_0}; }}
        
        /* ── Checkbox & Radio ── */
        QCheckBox, QRadioButton {{ color: {TEXT_PRIMARY}; spacing: 8px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: {RADIUS_XS}px; border: 1px solid {BORDER_COLOR}; background-color: {SURFACE_1}; }}
        QCheckBox::indicator:checked {{ background-color: {PRIMARY_COLOR}; border-color: {PRIMARY_COLOR}; image: url("{check_icon}"); }}
        
        /* ── Typography & Specifics (Labels) ── */
        QLabel {{ color: {TEXT_PRIMARY}; font-weight: 400; }}
        QLabel[type="section_title"] {{ font-family: {TITLE_FONT_STACK}; font-size: 20px; font-weight: 700; }}
        QLabel[type="settings_section_label"] {{ font-size: 11px; font-weight: 700; color: {TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.5px; }}
        QLabel[type="status_label"] {{ font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: {RADIUS_FULL}px; }}
    """


def apply_modern_theme(widget_or_app, theme_name: str = "light") -> None:
    """
    Áp dụng theme hiện đại cho một widget hoặc toàn bộ ứng dụng.
    """
    widget_or_app.setStyleSheet(get_modern_stylesheet(theme_name))


def apply_flat_widget_chrome(root_widget: QWidget) -> None:
    """
    Loại bỏ khung viền mặc định của các widget con bên trong.
    """
    for frame in root_widget.findChildren(QFrame):
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setFrameShadow(QFrame.Shadow.Plain)
        frame.setLineWidth(0)

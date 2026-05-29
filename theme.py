"""
theme.py — Hệ thống quản lý giao diện (Theme) toàn cục.

Cung cấp các hàm tạo stylesheet (QSS) hiện đại, chỉ áp dụng Light Mode
và giữ giao diện đồng nhất cho toàn bộ ứng dụng.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QWidget

from ui.palettes import LIGHT_PALETTE, Palette
from ui.tokens import (
    APP_FONT_STACK,
    MONO_FONT_STACK,
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_INPUT,
    TITLE_FONT_STACK,
    COLOR_SURFACE_PRIMARY,
    COLOR_SURFACE_RAISED,
)
from ui.asset_utils import resolve_asset_path


def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Tạo chuỗi stylesheet QSS dựa trên theme đã chọn.
    """
    _ = theme_name
    palette = LIGHT_PALETTE
    on_primary = "#FFFFFF"
    on_error = "#FFFFFF"
    on_warning = "#FFFFFF"
    on_danger = "#FFFFFF"
    check_icon = resolve_asset_path("assets/icon/cooliocns SVG/Interface/Check.svg").replace("\\", "/")
    
    return f"""
        /* ── Cấu trúc chính ── */
        QWidget {{ font-family: {APP_FONT_STACK}; color: {palette.TEXT_PRIMARY}; }}
        QWidget#MainBox {{
            background-color: {COLOR_SURFACE_PRIMARY};
            color: {palette.TEXT_PRIMARY};
        }}
        QMainWindow {{ background-color: {COLOR_SURFACE_PRIMARY}; }}
        QStackedWidget {{ border: none; background: transparent; }}
        QScrollArea, QAbstractScrollArea {{ background-color: transparent; border: none; }}
        QWidget#StemChrome {{
            background-color: {COLOR_SURFACE_PRIMARY};
        }}
        QWidget#StemContentHost {{ background-color: transparent; }}

        /* ── Thẻ Card (Hợp nhất) ── */
        QFrame#VanguardCardOuter, QWidget#Card, #HomeViewerCard, #HomeRightSection, #CardFrameElevated, #VanguardCardInner, QFrame[type="statistics_card"], QWidget[type="statistics_card"], #HomeViewerSurface {{
            background-color: {COLOR_SURFACE_RAISED};
            border: 1px solid {palette.BORDER};
            border-radius: {RADIUS_CARD};
        }}
        QFrame[type="statistics_card"]:hover, QWidget[type="statistics_card"]:hover {{
            border-color: {palette.BORDER_LIGHT};
            background-color: {COLOR_SURFACE_PRIMARY};
        }}
        
        /* ── Text Labels ── */
        QLabel[type="statistics_card_name"] {{ font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 15px; font-weight: 700; }}
        QLabel[type="statistics_card_count"] {{ font-family: {APP_FONT_STACK}; color: {palette.TEXT_TERTIARY}; font-size: 12px; font-weight: 500; }}

        QLabel[type="settings_section_label"] {{
            font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_SECONDARY}; font-size: 11px; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase;
        }}
        QLabel[type="empty_state_icon"] {{ font-size: 38px; }}
        QLabel[type="empty_state_text"] {{ font-size: 14px; font-weight: 600; color: {palette.TEXT_SECONDARY}; }}
        QLabel[type="wand_flash_status"] {{ font-size: 11px; font-weight: 600; }}
        QLabel[type="dialog_title"] {{
            color: {palette.TEXT_PRIMARY}; font-size: 16px; font-weight: 700; font-family: {APP_FONT_STACK};
        }}
        QLabel[type="dialog_body"] {{
            color: {palette.TEXT_SECONDARY}; font-size: 13px; font-family: {APP_FONT_STACK};
        }}
        QLabel[type="section_title"] {{
            font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 20px; font-weight: 600;
        }}
        QLabel[type="section_subtitle"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_SECONDARY}; font-weight: 400; font-size: 13px;
        }}
        QLabel[type="state_empty_title"] {{
            font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 18px; font-weight: 600;
        }}
        QLabel[type="state_empty_body"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_SECONDARY}; font-size: 13px; line-height: 1.5;
        }}
        QLabel[type="record_field_label"], QLabel[type="settings_form_label"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;
        }}
        
        /* ── Trạng thái (Badges) ── */
        QLabel[type="status_label"] {{
            font-family: {APP_FONT_STACK}; font-weight: 700; font-size: 11px; letter-spacing: 0.06em; padding: 7px 14px; border-radius: 999px;
            background-color: {palette.SURFACE_TERTIARY}; border: 1px solid {palette.BORDER_LIGHT}; color: {palette.TEXT_PRIMARY};
        }}
        QLabel[status="success"] {{ color: {palette.STATUS_SUCCESS_TEXT}; background-color: {palette.STATUS_SUCCESS}; border: none; }}
        QLabel[status="error"], QLabel[status="danger"] {{ color: {palette.STATUS_ERROR_TEXT}; background-color: {palette.STATUS_ERROR}; border: none; }}
        QLabel[status="warning"] {{ color: {palette.STATUS_WARNING_TEXT}; background-color: {palette.STATUS_WARNING}; border: none; }}
        QLabel[status="accent"] {{ color: {palette.SURFACE_PRIMARY}; background-color: {palette.PRIMARY}; border: none; }}
        
        QLabel[type="record_current_spell"], QLabel[type="statistics_current_spell"] {{
            color: {palette.TEXT_PRIMARY}; font-family: {TITLE_FONT_STACK}; font-size: 18px; font-weight: 600;
        }}
        QLabel[type="record_metric_value"] {{
            color: {palette.TEXT_PRIMARY}; font-size: 24px; font-weight: 500; font-family: {APP_FONT_STACK};
        }}
        QLabel[type="statistics_info_label"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_SECONDARY}; font-size: 12px;
        }}
        QLabel[type="statistics_meta_label"], QLabel[type="wand_spell_count"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_TERTIARY}; font-size: 11px; font-weight: 600;
        }}
        QLabel[type="wand_list_title"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;
        }}
        QLabel[type="wand_spell_name"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 13px; font-weight: 500;
        }}
        QLabel[type="wand_empty_row"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_TERTIARY}; font-size: 11px; font-style: italic; padding: 12px;
        }}
        QLabel[type="settings_hint"] {{
            font-family: {APP_FONT_STACK}; color: {palette.TEXT_TERTIARY}; font-size: 11px;
        }}
        QLabel[type="gesture_card_title"] {{
            font-weight: 600; color: {palette.TEXT_PRIMARY};
        }}

        /* ── Nút bấm (Hợp nhất theo Claude) ── */
        QPushButton {{
            background-color: {palette.SURFACE_PRIMARY};
            color: {palette.TEXT_PRIMARY};
            border: 1px solid {palette.BORDER};
            border-radius: {RADIUS_BUTTON};
            padding: 8px 16px;
            font-weight: 500;
            font-family: {APP_FONT_STACK};
            font-size: 13px;
        }}
        QPushButton:hover {{ background-color: {palette.HOVER_BG}; }}
        
        QPushButton[type="primary"], QPushButton[type="start"] {{
            background-color: {palette.PRIMARY}; color: {on_primary}; border: none; padding: 8px 16px;
        }}
        QPushButton[type="primary"]:hover, QPushButton[type="start"]:hover {{ background-color: {palette.PRIMARY_LIGHT}; }}
        
        QPushButton[type="outline"] {{
            background-color: {COLOR_SURFACE_RAISED}; color: {palette.TEXT_PRIMARY}; border: 1px solid {palette.BORDER};
        }}
        
        QPushButton[type="base"], QPushButton[type="back"] {{
            font-size: 12px; padding: 6px 14px;
        }}
        
        QPushButton[type="stop"], QPushButton[type="danger"] {{
            background-color: {palette.STATUS_ERROR}; color: {on_error}; border: none;
        }}
        
        QPushButton[type="snip"] {{
            background-color: {palette.SURFACE_TERTIARY}; color: {palette.TEXT_PRIMARY}; border: 1px solid {palette.BORDER};
        }}
        
        QPushButton[type="danger_outline"] {{
            background-color: transparent; color: {palette.STATUS_ERROR}; border: 1px solid {palette.STATUS_ERROR};
        }}
        
        QPushButton[type="small"] {{
            font-size: 11px; padding: 4px 12px;
        }}
        QPushButton[status="success"] {{
            background-color: {palette.STATUS_SUCCESS}; color: {palette.STATUS_SUCCESS_TEXT}; border: none;
        }}

        /* ── Input và Danh sách ── */
        QLineEdit, QComboBox, QSpinBox, QTimeEdit, QDateEdit {{
            background-color: {palette.SURFACE_TERTIARY};
            color: {palette.TEXT_PRIMARY};
            border: 1px solid {palette.BORDER_LIGHT};
            border-radius: {RADIUS_INPUT};
            padding: 8px 12px;
            font-size: 13px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: {palette.PRIMARY}; background-color: {palette.SURFACE_PRIMARY};
        }}
        QComboBox::drop-down {{ border: none; }}
        QComboBox QAbstractItemView {{ background-color: {palette.SURFACE_PRIMARY}; border: 1px solid {palette.BORDER}; selection-background-color: {palette.HOVER_BG}; }}

        QListWidget, QTableWidget, QTreeWidget {{
            background-color: {COLOR_SURFACE_RAISED};
            border: 1px solid {palette.BORDER_LIGHT};
            border-radius: {RADIUS_CARD};
            outline: none;
            gridline-color: {palette.BORDER_LIGHT};
        }}
        QListWidget::item, QTableWidget::item {{ padding: 10px 12px; border-radius: 8px; margin: 2px 6px; color: {palette.TEXT_PRIMARY}; border: 1px solid transparent; font-size: 13px; }}
        QListWidget::item:hover, QTableWidget::item:hover {{ background-color: {palette.HOVER_BG}; border-color: transparent; }}
        QListWidget::item:selected, QTableWidget::item:selected {{ background-color: {palette.SURFACE_TERTIARY}; color: {palette.TEXT_PRIMARY}; font-weight: 500; border-color: {palette.BORDER_LIGHT}; }}
        QTableWidget QTableCornerButton::section {{ background-color: {palette.SURFACE_TERTIARY}; border: none; }}
        
        QListWidget[type="record_list"] {{ background-color: transparent; border: none; color: {palette.TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; }}
        QListWidget[type="record_list"]::item {{ background-color: {palette.SURFACE_PRIMARY}; border: 1px solid {palette.BORDER_LIGHT}; border-radius: 12px; margin-bottom: 6px; padding: 12px; }}
        QListWidget[type="record_list"]::item:selected {{ background-color: {palette.SURFACE_TERTIARY}; color: {palette.TEXT_PRIMARY}; border-color: {palette.BORDER_LIGHT}; }}

        QListWidget[type="wand_list"] {{
            background-color: {palette.SURFACE_PRIMARY}; border: 1px solid {palette.BORDER_LIGHT}; border-radius: 12px; padding: 6px;
        }}
        
        QHeaderView::section {{
            background-color: {palette.SURFACE_TERTIARY};
            color: {palette.TEXT_SECONDARY};
            padding: 8px 12px;
            border: none;
            border-bottom: 1px solid {palette.BORDER};
            font-weight: 500;
            font-size: 11px;
        }}

        /* ── Thanh cuộn tinh tế ── */
        QScrollBar:vertical {{
            border: none; background: transparent; width: 6px; margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {palette.BORDER}; min-height: 30px; border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {palette.TEXT_TERTIARY}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}

        /* ── MacShell (Sidebar & Toolbar) ── */
        QWidget#StemChrome {{ background-color: {COLOR_SURFACE_PRIMARY}; border: none; }}
        QWidget#StemToolbar {{ background-color: {COLOR_SURFACE_PRIMARY}; border-bottom: 1px solid {palette.BORDER_LIGHT}; }}
        QLabel#StemToolbarTitle {{ color: {palette.TEXT_PRIMARY}; font-size: 16px; font-weight: 600; }}
        QLabel#StemToolbarSubtitle {{ color: {palette.TEXT_SECONDARY}; font-size: 12px; }}
        QWidget#StemSidebar {{ background-color: {COLOR_SURFACE_PRIMARY}; border-right: 1px solid {palette.BORDER_LIGHT}; }}
        QLabel#StemBrandTitle {{ font-family: {TITLE_FONT_STACK}; color: {palette.TEXT_PRIMARY}; font-size: 14px; font-weight: 600; }}
        QLabel#StemBrandSubtitle {{ font-family: {APP_FONT_STACK}; font-size: 10px; font-weight: 500; color: {palette.TEXT_SECONDARY}; letter-spacing: 0.10em; }}
        QLabel#StemNavSectionLabel {{ font-family: {APP_FONT_STACK}; font-size: 11px; font-weight: 600; color: {palette.TEXT_TERTIARY}; margin-top: 18px; margin-bottom: 8px; text-transform: uppercase; }}
        QLabel[type="shell_nav_hint"] {{ font-family: {APP_FONT_STACK}; color: {palette.TEXT_TERTIARY}; font-size: 11px; font-style: italic; }}
        
        QToolButton#StemNavBtn, QToolButton {{
            color: {palette.TEXT_SECONDARY}; background-color: transparent;
            border: none; border-radius: 8px; padding: 10px 12px; font-size: 13px; font-weight: 500; text-align: left;
        }}
        QToolButton:hover, QToolButton#StemNavBtn:hover {{ background-color: {palette.HOVER_BG}; }}
        QToolButton#StemNavBtn[active="true"] {{ background: {palette.TEXT_PRIMARY}; color: {COLOR_SURFACE_PRIMARY}; }}
        
        QToolButton[type="icon"] {{
            background-color: {COLOR_SURFACE_RAISED};
            border: 1px solid {palette.BORDER_LIGHT};
            border-radius: 8px;
            padding: 4px;
        }}
        QToolButton[type="icon"]:hover {{ background-color: {palette.HOVER_BG}; border-color: {palette.BORDER}; }}
        QToolButton[type="icon"]:pressed {{ background-color: {palette.SURFACE_TERTIARY}; }}

        /* ── Terminal ── */
        QTextEdit, QPlainTextEdit {{
            background-color: {palette.TERM_BG};
            color: {palette.TERM_FG};
            border: 1px solid {palette.BORDER_LIGHT};
            border-radius: {RADIUS_CARD};
            font-family: {MONO_FONT_STACK};
            font-size: 12px;
            padding: 12px;
        }}
        
        /* ── Checkbox & ProgressBar ── */
        QCheckBox {{
            color: {palette.TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; font-size: 13px; spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px; height: 16px; border-radius: 4px; border: 1px solid {palette.BORDER}; background-color: {COLOR_SURFACE_RAISED};
        }}
        QCheckBox::indicator:checked {{
            background-color: {palette.PRIMARY}; border-color: {palette.PRIMARY}; image: url("{check_icon}");
        }}
        QCheckBox::indicator:hover {{ border-color: {palette.PRIMARY}; }}
        QProgressBar {{
            background-color: {palette.SURFACE_TERTIARY}; border: none; border-radius: 4px; text-align: center;
            color: {palette.TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; font-weight: 500;
        }}
        QProgressBar::chunk {{
            background-color: {palette.TEXT_PRIMARY}; border-radius: 4px;
        }}
        
        /* Error States */
        QLineEdit[invalid="true"] {{
            border: 1px solid {palette.STATUS_ERROR}; background-color: rgba(239, 68, 68, 0.05);
        }}

        /* Confirm Dialog */
        QDialog#ConfirmDialog {{
            background-color: {COLOR_SURFACE_RAISED}; border: 1px solid {palette.BORDER_LIGHT}; border-radius: {RADIUS_CARD};
        }}
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

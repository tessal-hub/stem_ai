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

    # ── Additional color tokens for enhanced UI ──
    SIDEBAR_BG = "#F7F5F2"          # Slightly warmer than SURFACE_0
    SIDEBAR_BORDER = "rgba(0, 0, 0, 0.06)"
    NAV_ACTIVE_BG = PRIMARY_COLOR
    NAV_ACTIVE_TEXT = "#FFFFFF"
    NAV_HOVER_BG = "rgba(155, 184, 215, 0.12)"
    TOOLBAR_BORDER = "rgba(0, 0, 0, 0.06)"
    CARD_SHADOW_BORDER = "rgba(0, 0, 0, 0.04)"
    STATUS_SUCCESS_BG = "rgba(16, 185, 129, 0.12)"
    STATUS_ERROR_BG = "rgba(239, 68, 68, 0.12)"
    STATUS_WARNING_BG = "rgba(245, 158, 11, 0.12)"
    STATUS_ACCENT_BG = "rgba(155, 184, 215, 0.15)"
    COMBO_ARROW = resolve_asset_path("assets/icon/cooliocns SVG/Arrow/Caret_Down_SM.svg").replace("\\", "/")

    return f"""
        /* ══════════════════════════════════════════════
           BASE & RESET
           ══════════════════════════════════════════════ */
        QWidget {{
            font-family: {APP_FONT_STACK};
            color: {TEXT_PRIMARY};
            font-size: 13px;
        }}
        QMainWindow, QWidget#MainBox, QWidget#StemChrome {{
            background-color: {SURFACE_0};
        }}
        QStackedWidget, QWidget#StemContentHost,
        QScrollArea, QAbstractScrollArea {{
            background-color: transparent;
            border: none;
        }}

        /* ══════════════════════════════════════════════
           SIDEBAR — Warm tinted panel with pill nav
           ══════════════════════════════════════════════ */
        QWidget#StemSidebar {{
            background-color: {SIDEBAR_BG};
            border-right: 1px solid {SIDEBAR_BORDER};
        }}
        /* Brand area */
        QLabel#StemBrandTitle {{
            font-family: {TITLE_FONT_STACK};
            font-size: 15px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            letter-spacing: 0.3px;
        }}
        QLabel#StemBrandSubtitle {{
            font-size: 11px;
            font-weight: 500;
            color: {TEXT_SECONDARY};
        }}
        /* Nav section header */
        QLabel#StemNavSectionLabel {{
            font-size: 10px;
            font-weight: 700;
            color: {TEXT_SECONDARY};
            text-transform: uppercase;
            letter-spacing: 1px;
            padding-left: 4px;
        }}
        /* Nav buttons — pill shape */
        QToolButton#StemNavBtn {{
            background-color: transparent;
            color: {TEXT_SECONDARY};
            border: none;
            border-radius: {RADIUS_SM}px;
            padding: 6px 16px;
            margin: 1px 12px;
            font-size: 13px;
            font-weight: 500;
            text-align: left;
        }}
        QToolButton#StemNavBtn:hover {{
            background-color: {NAV_HOVER_BG};
            color: {TEXT_PRIMARY};
        }}
        QToolButton#StemNavBtn[active="true"] {{
            background-color: {NAV_ACTIVE_BG};
            color: {NAV_ACTIVE_TEXT};
            font-weight: 600;
        }}
        /* Swipe hint at bottom of sidebar */
        QLabel[type="shell_nav_hint"] {{
            font-size: 10px;
            color: {TEXT_TERTIARY};
            padding: 8px;
        }}

        /* ══════════════════════════════════════════════
           TOOLBAR — Clean top bar with subtle separator
           ══════════════════════════════════════════════ */
        QFrame#StemToolbar {{
            background-color: {SURFACE_1};
            border-bottom: 1px solid {TOOLBAR_BORDER};
        }}
        QLabel#StemToolbarTitle {{
            font-family: {TITLE_FONT_STACK};
            font-size: 18px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        QLabel#StemToolbarSubtitle {{
            font-size: 12px;
            font-weight: 400;
            color: {TEXT_SECONDARY};
        }}

        /* ══════════════════════════════════════════════
           CARDS — White surface with soft border + depth
           ══════════════════════════════════════════════ */
        QFrame#CardFrame, QFrame#VanguardCardOuter, QWidget#Card,
        #HomeViewerCard, #HomeRightSection, #CardFrameElevated,
        #VanguardCardInner, QFrame[type="statistics_card"],
        QWidget[type="statistics_card"], #HomeViewerSurface,
        QFrame#ModernCard {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-bottom: 2px solid {CARD_SHADOW_BORDER};
            border-radius: {RADIUS_LG}px;
        }}

        /* ══════════════════════════════════════════════
           BUTTONS — Complete variant system
           ══════════════════════════════════════════════ */
        QPushButton, QToolButton {{
            background-color: transparent;
            color: {TEXT_PRIMARY};
            border: none;
            border-radius: {RADIUS_SM}px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 13px;
        }}

        /* Primary / Start */
        QPushButton[type="primary"], QPushButton[type="start"] {{
            background-color: {PRIMARY_COLOR};
            color: white;
            font-weight: 600;
        }}
        QPushButton[type="primary"]:hover, QPushButton[type="start"]:hover {{
            background-color: {PRIMARY_DARK};
        }}
        QPushButton[type="primary"]:pressed, QPushButton[type="start"]:pressed {{
            background-color: #5A8FBF;
        }}

        /* Base / Back */
        QPushButton[type="base"], QPushButton[type="back"] {{
            background-color: rgba(155, 184, 215, 0.12);
            color: {PRIMARY_COLOR};
            font-weight: 600;
        }}
        QPushButton[type="base"]:hover, QPushButton[type="back"]:hover {{
            background-color: rgba(155, 184, 215, 0.22);
        }}

        /* Stop / Danger (filled on hover) */
        QPushButton[type="stop"], QPushButton[type="danger"] {{
            background-color: {STATUS_ERROR_BG};
            color: {STATUS_ERROR};
            font-weight: 600;
        }}
        QPushButton[type="stop"]:hover, QPushButton[type="danger"]:hover {{
            background-color: {STATUS_ERROR};
            color: white;
        }}

        /* Danger outline (softer) */
        QPushButton[type="danger_outline"] {{
            background-color: transparent;
            color: {STATUS_ERROR};
            border: 1px solid rgba(239, 68, 68, 0.30);
            font-weight: 500;
        }}
        QPushButton[type="danger_outline"]:hover {{
            background-color: {STATUS_ERROR_BG};
            border-color: {STATUS_ERROR};
        }}

        /* Outline / Snip */
        QPushButton[type="outline"], QPushButton[type="snip"] {{
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
        }}
        QPushButton[type="outline"]:hover, QPushButton[type="snip"]:hover {{
            background-color: {FILL_SECONDARY};
            color: {TEXT_PRIMARY};
        }}

        /* Icon-only button */
        QToolButton[type="icon"] {{
            background-color: {FILL_TERTIARY};
            border-radius: {RADIUS_SM}px;
            padding: 4px;
        }}
        QToolButton[type="icon"]:hover {{
            background-color: {FILL_SECONDARY};
        }}

        QPushButton:disabled {{
            background-color: {SURFACE_0};
            color: {TEXT_TERTIARY};
            border: 1px solid {BORDER_LIGHT};
        }}

        /* ══════════════════════════════════════════════
           INPUTS — Refined form controls
           ══════════════════════════════════════════════ */
        QLineEdit, QSpinBox, QTimeEdit, QDateEdit {{
            background-color: {SURFACE_0};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_SM}px;
            padding: 8px 12px;
            color: {TEXT_PRIMARY};
            selection-background-color: {PRIMARY_LIGHT};
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border: 1.5px solid {PRIMARY_COLOR};
            background-color: {SURFACE_1};
        }}

        /* ComboBox — styled with custom arrow */
        QComboBox {{
            background-color: {SURFACE_0};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_SM}px;
            padding: 8px 28px 8px 12px;
            color: {TEXT_PRIMARY};
            min-height: 20px;
        }}
        QComboBox:hover {{
            border-color: {BORDER_MID};
        }}
        QComboBox:focus, QComboBox:on {{
            border: 1.5px solid {PRIMARY_COLOR};
            background-color: {SURFACE_1};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
            padding-right: 8px;
        }}
        QComboBox::down-arrow {{
            image: url("{COMBO_ARROW}");
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_SM}px;
            padding: 4px;
            outline: none;
            selection-background-color: {PRIMARY_LIGHT};
            selection-color: {PRIMARY_COLOR};
        }}

        /* ══════════════════════════════════════════════
           LISTS — Refined item styling
           ══════════════════════════════════════════════ */
        QListWidget, QTableWidget, QTreeWidget {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
            outline: none;
            gridline-color: transparent;
            padding: 4px;
        }}
        QListWidget::item {{
            min-height: 40px;
            border-radius: {RADIUS_SM}px;
            padding: 6px 12px;
            margin: 1px 2px;
            color: {TEXT_PRIMARY};
            font-size: 13px;
        }}
        QListWidget::item:hover {{
            background-color: {NAV_HOVER_BG};
        }}
        QListWidget::item:selected {{
            background-color: {PRIMARY_LIGHT};
            color: {PRIMARY_DARK};
            font-weight: 600;
        }}

        /* ══════════════════════════════════════════════
           PROGRESS BAR & SCROLLBARS
           ══════════════════════════════════════════════ */
        QProgressBar {{
            background-color: {FILL_TERTIARY};
            border: none;
            border-radius: 4px;
            text-align: center;
            font-size: 11px;
            color: {TEXT_SECONDARY};
            max-height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY_COLOR};
            border-radius: 4px;
        }}

        /* Vertical scrollbar */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 4px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(0, 0, 0, 0.10);
            min-height: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(0, 0, 0, 0.20);
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        /* Horizontal scrollbar */
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 6px;
            margin: 0px 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(0, 0, 0, 0.10);
            min-width: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: rgba(0, 0, 0, 0.20);
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* ══════════════════════════════════════════════
           TERMINAL — Dark surface with refined type
           ══════════════════════════════════════════════ */
        QTextEdit, QPlainTextEdit {{
            background-color: {BG_DARK};
            color: {TERM_FG};
            border: none;
            border-radius: {RADIUS_LG}px;
            font-family: {MONO_FONT_STACK};
            font-size: 12px;
            padding: 16px;
            selection-background-color: rgba(50, 215, 75, 0.20);
        }}

        /* ══════════════════════════════════════════════
           DIALOG
           ══════════════════════════════════════════════ */
        QDialog {{
            background-color: {SURFACE_0};
            border-radius: {RADIUS_LG}px;
        }}

        /* ══════════════════════════════════════════════
           CHECKBOX & RADIO — Polished indicators
           ══════════════════════════════════════════════ */
        QCheckBox, QRadioButton {{
            color: {TEXT_PRIMARY};
            spacing: 8px;
            font-size: 13px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {RADIUS_XS}px;
            border: 1.5px solid {BORDER_MID};
            background-color: {SURFACE_1};
        }}
        QCheckBox::indicator:hover {{
            border-color: {PRIMARY_COLOR};
        }}
        QCheckBox::indicator:checked {{
            background-color: {PRIMARY_COLOR};
            border-color: {PRIMARY_COLOR};
            image: url("{check_icon}");
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 1.5px solid {BORDER_MID};
            background-color: {SURFACE_1};
        }}
        QRadioButton::indicator:checked {{
            background-color: {PRIMARY_COLOR};
            border-color: {PRIMARY_COLOR};
        }}

        /* ══════════════════════════════════════════════
           TYPOGRAPHY — Full hierarchy
           ══════════════════════════════════════════════ */
        QLabel {{
            color: {TEXT_PRIMARY};
            font-weight: 400;
        }}
        /* Section title — large editorial */
        QLabel[type="section_title"] {{
            font-family: {TITLE_FONT_STACK};
            font-size: 20px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        QLabel[type="section_title"][status="accent"] {{
            color: {PRIMARY_DARK};
        }}
        /* Section subtitle */
        QLabel[type="section_subtitle"] {{
            font-size: 13px;
            font-weight: 400;
            color: {TEXT_SECONDARY};
            line-height: 1.5;
        }}
        /* Settings section header — caps eyebrow */
        QLabel[type="settings_section_label"] {{
            font-size: 10px;
            font-weight: 700;
            color: {TEXT_SECONDARY};
            text-transform: uppercase;
            letter-spacing: 1.2px;
        }}
        /* Status label — pill badges with semantic colors */
        QLabel[type="status_label"] {{
            font-size: 11px;
            font-weight: 600;
            padding: 5px 14px;
            border-radius: {RADIUS_FULL}px;
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
        }}
        QLabel[type="status_label"][status="success"] {{
            background-color: {STATUS_SUCCESS_BG};
            color: {STATUS_SUCCESS};
        }}
        QLabel[type="status_label"][status="error"] {{
            background-color: {STATUS_ERROR_BG};
            color: {STATUS_ERROR};
        }}
        QLabel[type="status_label"][status="warning"] {{
            background-color: {STATUS_WARNING_BG};
            color: {STATUS_WARNING};
        }}
        QLabel[type="status_label"][status="accent"] {{
            background-color: {STATUS_ACCENT_BG};
            color: {PRIMARY_DARK};
        }}
        /* Hint text */
        QLabel[type="settings_hint"] {{
            font-size: 11px;
            color: {TEXT_TERTIARY};
            line-height: 1.4;
        }}
        /* Record metric value */
        QLabel[type="record_metric_value"] {{
            font-family: {MONO_FONT_STACK};
            font-size: 22px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        /* Record field label */
        QLabel[type="record_field_label"] {{
            font-size: 12px;
            font-weight: 600;
            color: {TEXT_SECONDARY};
        }}
        /* Record current spell name */
        QLabel[type="record_current_spell"] {{
            font-family: {TITLE_FONT_STACK};
            font-size: 16px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        /* Statistics labels */
        QLabel[type="statistics_meta_label"] {{
            font-size: 12px;
            color: {TEXT_SECONDARY};
        }}
        /* Empty state */
        QLabel[type="state_empty_title"] {{
            font-size: 15px;
            font-weight: 600;
            color: {TEXT_SECONDARY};
        }}
        QLabel[type="state_empty_title"][status="error"] {{
            color: {STATUS_ERROR};
        }}
        QLabel[type="state_empty_body"] {{
            font-size: 12px;
            color: {TEXT_TERTIARY};
            line-height: 1.5;
        }}
        /* Empty state icon */
        QLabel[type="empty_state_icon"] {{
            font-size: 32px;
        }}

        /* ══════════════════════════════════════════════
           TOOLTIP
           ══════════════════════════════════════════════ */
        QToolTip {{
            background-color: {BG_DARK};
            color: #F0F0F0;
            border: none;
            border-radius: {RADIUS_XS}px;
            padding: 6px 10px;
            font-size: 12px;
            font-family: {APP_FONT_STACK};
        }}

        /* ══════════════════════════════════════════════
           TAB WIDGET (if used)
           ══════════════════════════════════════════════ */
        QTabWidget::pane {{
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
            background-color: {SURFACE_1};
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {TEXT_SECONDARY};
            padding: 8px 16px;
            border: none;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            color: {PRIMARY_COLOR};
            font-weight: 600;
            border-bottom: 2px solid {PRIMARY_COLOR};
        }}
        QTabBar::tab:hover {{
            color: {TEXT_PRIMARY};
        }}

        /* ══════════════════════════════════════════════
           GROUP BOX
           ══════════════════════════════════════════════ */
        QGroupBox {{
            font-weight: 600;
            font-size: 13px;
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
            margin-top: 12px;
            padding-top: 20px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {TEXT_SECONDARY};
        }}

        /* ══════════════════════════════════════════════
           ADDITIONAL WIDGET TYPES
           ══════════════════════════════════════════════ */
        /* Gesture card title */
        QLabel[type="gesture_card_title"] {{
            font-family: {TITLE_FONT_STACK};
            font-size: 15px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        /* Settings form label */
        QLabel[type="settings_form_label"] {{
            font-size: 13px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        }}
        /* Empty state text */
        QLabel[type="empty_state_text"] {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
        }}
        /* Dialog title & body */
        QLabel[type="dialog_title"] {{
            font-family: {TITLE_FONT_STACK};
            font-size: 17px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        QLabel[type="dialog_body"] {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
            line-height: 1.5;
        }}
        /* Small pill button (3D reset, etc.) */
        QPushButton[type="small"] {{
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
            font-size: 11px;
            padding: 4px 10px;
            border-radius: {RADIUS_SM}px;
        }}
        QPushButton[type="small"]:hover {{
            background-color: {FILL_SECONDARY};
            color: {TEXT_PRIMARY};
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

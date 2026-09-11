"""
theme.py — Hệ thống quản lý giao diện (Theme) toàn cục.

Cung cấp các hàm tạo stylesheet (QSS) hiện đại, chỉ áp dụng Light Mode
và giữ giao diện đồng nhất cho toàn bộ ứng dụng.
"""

from __future__ import annotations

import functools
from PyQt6.QtGui import QColor, QPalette
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


from ui.palettes import LIGHT_PALETTE, DARK_PALETTE, Palette


@functools.lru_cache(maxsize=4)
def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Tạo chuỗi stylesheet QSS dựa trên theme đã chọn ("light" hoặc "dark").
    """
    is_dark = str(theme_name).lower() == "dark"
    p: Palette = DARK_PALETTE if is_dark else LIGHT_PALETTE

    check_icon = resolve_asset_path("assets/icon/cooliocns SVG/Interface/Check.svg").replace("\\", "/")
    COMBO_ARROW = resolve_asset_path("assets/icon/cooliocns SVG/Arrow/Caret_Down_SM.svg").replace("\\", "/")

    # Token màu sắc động theo Palette chọn
    SURFACE_0 = p.SURFACE_SECONDARY
    SURFACE_1 = p.SURFACE_PRIMARY
    SURFACE_2 = p.SURFACE_TERTIARY
    TEXT_PRIMARY = p.TEXT_PRIMARY
    TEXT_SECONDARY = p.TEXT_SECONDARY
    TEXT_TERTIARY = p.TEXT_TERTIARY
    PRIMARY_COLOR = p.PRIMARY
    PRIMARY_LIGHT = p.PRIMARY_LIGHT
    PRIMARY_DARK = p.PRIMARY_DARK
    BORDER_COLOR = p.BORDER
    BORDER_LIGHT = p.BORDER_LIGHT
    BORDER_MID = p.BORDER

    if is_dark:
        SIDEBAR_BG = "#121214"
        SIDEBAR_BORDER = "rgba(255, 255, 255, 0.12)"
        NAV_ACTIVE_BG = p.PRIMARY
        NAV_ACTIVE_TEXT = "#FFFFFF"
        NAV_HOVER_BG = "rgba(10, 132, 255, 0.22)"
        TOOLBAR_BORDER = "rgba(255, 255, 255, 0.12)"
        CARD_SHADOW_BORDER = "rgba(0, 0, 0, 0.60)"
        STATUS_SUCCESS_BG = "rgba(48, 209, 88, 0.20)"
        STATUS_ERROR_BG = "rgba(255, 69, 58, 0.20)"
        STATUS_WARNING_BG = "rgba(255, 159, 10, 0.20)"
        STATUS_ACCENT_BG = "rgba(10, 132, 255, 0.22)"

        FILL_PRIMARY = "rgba(255, 255, 255, 0.18)"
        FILL_SECONDARY = "rgba(255, 255, 255, 0.14)"
        FILL_TERTIARY = "rgba(255, 255, 255, 0.08)"

        BTN_BASE_BG = "rgba(10, 132, 255, 0.22)"
        BTN_BASE_TEXT = "#0A84FF"
        BTN_OUTLINE_BG = "rgba(255, 255, 255, 0.10)"
        BTN_OUTLINE_TEXT = "#FFFFFF"

        INPUT_BG = "#2C2C2E"
        INPUT_BORDER = "rgba(255, 255, 255, 0.16)"

        COMBO_POPUP_BG = "#3A3A3C"
        COMBO_POPUP_TEXT = "#FFFFFF"
        COMBO_SEL_BG = "#0A84FF"
        COMBO_SEL_TEXT = "#FFFFFF"

        SCROLL_HANDLE = "rgba(255, 255, 255, 0.35)"
        SCROLL_HANDLE_HOVER = "rgba(255, 255, 255, 0.50)"
        ACCENT_TITLE_COLOR = PRIMARY_COLOR
        BG_DARK = "#16181d"

        # Interactive-state tokens — dark equivalents (never hard-code light values here)
        FOCUS_BORDER = "#f2f2f7"
        PRIMARY_PRESSED = "#0066CC"
        DISABLED_BG = "rgba(255, 255, 255, 0.08)"
        DISABLED_TEXT = "rgba(255, 255, 255, 0.45)"
        DISABLED_BORDER = "rgba(255, 255, 255, 0.16)"
        OUTLINE_BORDER = "rgba(255, 255, 255, 0.16)"
        ERROR_TEXT_ON_TINT = STATUS_ERROR
    else:
        SIDEBAR_BG = "#f6f7f9"
        SIDEBAR_BORDER = "#e4e9f0"
        NAV_ACTIVE_BG = PRIMARY_COLOR
        NAV_ACTIVE_TEXT = "#FFFFFF"
        NAV_HOVER_BG = "rgba(10, 122, 255, 0.07)"
        TOOLBAR_BORDER = "#e4e9f0"
        CARD_SHADOW_BORDER = "rgba(15, 23, 42, 0.04)"
        STATUS_SUCCESS_BG = "rgba(30, 122, 70, 0.09)"
        STATUS_ERROR_BG = "rgba(220, 38, 38, 0.08)"
        STATUS_WARNING_BG = "rgba(180, 83, 9, 0.10)"
        STATUS_ACCENT_BG = "rgba(10, 122, 255, 0.07)"

        FILL_PRIMARY = "#f1f5f9"
        FILL_SECONDARY = "rgba(15, 23, 42, 0.06)"
        FILL_TERTIARY = "rgba(15, 23, 42, 0.04)"

        BTN_BASE_BG = "rgba(10, 122, 255, 0.07)"
        BTN_BASE_TEXT = PRIMARY_COLOR
        BTN_OUTLINE_BG = "#ffffff"
        BTN_OUTLINE_TEXT = "#334155"

        INPUT_BG = SURFACE_1
        INPUT_BORDER = "#cdd6e1"

        COMBO_POPUP_BG = SURFACE_1
        COMBO_POPUP_TEXT = TEXT_PRIMARY
        COMBO_SEL_BG = "rgba(10, 122, 255, 0.14)"
        COMBO_SEL_TEXT = "#044a99"

        SCROLL_HANDLE = "rgba(15, 23, 42, 0.18)"
        SCROLL_HANDLE_HOVER = "rgba(15, 23, 42, 0.28)"
        ACCENT_TITLE_COLOR = PRIMARY_COLOR
        BG_DARK = "#16181d"

        # Interactive-state tokens — light equivalents
        FOCUS_BORDER = "#0f172a"
        PRIMARY_PRESSED = "#044a99"
        DISABLED_BG = "#f1f5f9"
        DISABLED_TEXT = "#8494a7"
        DISABLED_BORDER = "#e4e9f0"
        OUTLINE_BORDER = "#cdd6e1"
        # #dc2626 on the 8% error tint is 4.28:1 — one step darker for small text
        ERROR_TEXT_ON_TINT = "#b91c1c"

    return f"""
        /* ══════════════════════════════════════════════
           BASE & RESET
           ══════════════════════════════════════════════ */
        QWidget {{
            font-family: {APP_FONT_STACK};
            color: {TEXT_PRIMARY};
            font-size: 13px;
        }}
        QMainWindow, QWidget#MainBox, QWidget#StemChrome, QWidget#StemContentHost {{
            background-color: {SURFACE_0};
        }}
        QStackedWidget {{
            background-color: {SURFACE_0};
            border: none;
        }}
        QScrollArea, QAbstractScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}
        QFrame {{
            border: none;
            background: transparent;
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
            font-size: 11px;
            font-weight: 700;
            color: {TEXT_SECONDARY};
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
        QToolButton#StemNavBtn:focus {{
            border: 1.5px solid {FOCUS_BORDER};
            background-color: {NAV_HOVER_BG};
        }}
        QToolButton#StemNavBtn[active="true"] {{
            background-color: {NAV_ACTIVE_BG};
            color: {NAV_ACTIVE_TEXT};
            font-weight: 600;
        }}
        /* Swipe hint at bottom of sidebar */
        QLabel[type="shell_nav_hint"] {{
            font-size: 11px;
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
        QFrame#CardFrame, QFrame#VanguardCardOuter, QWidget#Card, QFrame#Card,
        #HomeViewerCard, #HomeRightSection, #CardFrameElevated, #HomeHeroCard,
        #HomeHistoryCard, #HomeLoadedCard,
        #VanguardCardInner, QFrame[type="statistics_card"],
        QWidget[type="statistics_card"], #HomeViewerSurface,
        QFrame#ModernCard {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-bottom: 2px solid {BORDER_LIGHT};
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

        /* Primary / Start — ink focus, calibrated blue only */
        QPushButton[type="primary"], QPushButton[type="start"] {{
            background-color: {PRIMARY_COLOR};
            color: white;
            font-weight: 700;
            border: 2px solid transparent;
        }}
        QPushButton[type="primary"]:hover, QPushButton[type="start"]:hover {{
            background-color: {PRIMARY_DARK};
        }}
        QPushButton[type="primary"]:pressed, QPushButton[type="start"]:pressed {{
            background-color: {PRIMARY_PRESSED};
        }}
        QPushButton[type="primary"]:focus, QPushButton[type="start"]:focus {{
            border-color: {FOCUS_BORDER};
        }}
        QPushButton[type="primary"]:disabled, QPushButton[type="start"]:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
        }}

        /* Base / Back — with focus ink */
        QPushButton[type="base"], QPushButton[type="back"] {{
            background-color: {BTN_BASE_BG};
            color: {BTN_BASE_TEXT};
            font-weight: 600;
            border: 1.5px solid transparent;
        }}
        QPushButton[type="base"]:hover, QPushButton[type="back"]:hover {{
            background-color: {NAV_HOVER_BG};
        }}
        QPushButton[type="base"]:focus, QPushButton[type="back"]:focus {{
            border-color: {FOCUS_BORDER};
            background-color: {NAV_HOVER_BG};
        }}

        /* Stop / Danger — focus ink */
        QPushButton[type="stop"], QPushButton[type="danger"] {{
            background-color: {STATUS_ERROR_BG};
            color: {STATUS_ERROR};
            font-weight: 600;
            border: 1.5px solid transparent;
        }}
        QPushButton[type="stop"]:hover, QPushButton[type="danger"]:hover {{
            background-color: {STATUS_ERROR};
            color: white;
        }}
        QPushButton[type="stop"]:focus, QPushButton[type="danger"]:focus {{
            border-color: {FOCUS_BORDER};
        }}

        /* Danger outline — focus ink */
        QPushButton[type="danger_outline"] {{
            background-color: transparent;
            color: {STATUS_ERROR};
            border: 1px solid rgba(220, 38, 38, 0.30);
            font-weight: 500;
        }}
        QPushButton[type="danger_outline"]:hover {{
            background-color: {STATUS_ERROR_BG};
            border-color: {STATUS_ERROR};
        }}
        QPushButton[type="danger_outline"]:focus {{
            border: 1.5px solid {FOCUS_BORDER};
            background-color: {STATUS_ERROR_BG};
        }}

        /* Outline / Snip — focus ink */
        QPushButton[type="outline"], QPushButton[type="snip"] {{
            background-color: {BTN_OUTLINE_BG};
            color: {BTN_OUTLINE_TEXT};
            border: 1px solid {OUTLINE_BORDER};
        }}
        QPushButton[type="outline"]:hover, QPushButton[type="snip"]:hover {{
            background-color: {FILL_PRIMARY};
            color: {TEXT_PRIMARY};
        }}
        QPushButton[type="outline"]:pressed, QPushButton[type="snip"]:pressed {{
            background-color: {FILL_SECONDARY};
        }}
        QPushButton[type="outline"]:focus, QPushButton[type="snip"]:focus {{
            border: 1.5px solid {FOCUS_BORDER};
        }}

        /* Icon-only — focus ink */
        QToolButton[type="icon"] {{
            background-color: {FILL_TERTIARY};
            border: 1.5px solid transparent;
            border-radius: {RADIUS_SM}px;
            padding: 4px;
        }}
        QToolButton[type="icon"]:hover {{
            background-color: {FILL_SECONDARY};
        }}
        QToolButton[type="icon"]:focus {{
            border-color: {FOCUS_BORDER};
            background-color: {FILL_SECONDARY};
        }}

        QPushButton:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
            border: 1px solid {DISABLED_BORDER};
        }}

        /* ══════════════════════════════════════════════
           INPUTS — Refined form controls
           ══════════════════════════════════════════════ */
        QLineEdit, QSpinBox, QTimeEdit, QDateEdit {{
            background-color: {INPUT_BG};
            border: 1px solid {INPUT_BORDER};
            border-radius: {RADIUS_SM}px;
            padding: 8px 12px;
            color: {TEXT_PRIMARY};
            selection-background-color: {PRIMARY_LIGHT};
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border: 1.5px solid {PRIMARY_COLOR};
            background-color: {SURFACE_1};
        }}
        QLineEdit:disabled, QSpinBox:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
            border-color: {DISABLED_BORDER};
        }}

        /* ComboBox — styled with custom arrow */
        QComboBox {{
            background-color: {INPUT_BG};
            border: 1px solid {INPUT_BORDER};
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
            background-color: {COMBO_POPUP_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_SM}px;
            padding: 4px;
            outline: none;
            selection-background-color: {COMBO_SEL_BG};
            selection-color: {COMBO_SEL_TEXT};
            color: {COMBO_POPUP_TEXT};
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
            background-color: {COMBO_SEL_BG};
            color: {COMBO_SEL_TEXT};
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
            background: {SCROLL_HANDLE};
            min-height: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {SCROLL_HANDLE_HOVER};
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
            background: {SCROLL_HANDLE};
            min-width: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {SCROLL_HANDLE_HOVER};
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
            color: {ACCENT_TITLE_COLOR};
        }}
        /* Section subtitle */
        QLabel[type="section_subtitle"] {{
            font-size: 13px;
            font-weight: 400;
            color: {TEXT_SECONDARY};
        }}
        /* Settings section header — caps group label (form legend, not decorative eyebrow) */
        QLabel[type="settings_section_label"] {{
            font-size: 11px;
            font-weight: 700;
            color: {TEXT_SECONDARY};
            letter-spacing: 1.2px;
        }}
        /* Status label — pill badges with semantic colors (padding dọc 7px cho dấu chồng VN) */
        QLabel[type="status_label"] {{
            font-size: 11px;
            font-weight: 600;
            padding: 7px 14px;
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
            color: {ERROR_TEXT_ON_TINT};
        }}
        QLabel[type="status_label"][status="warning"] {{
            background-color: {STATUS_WARNING_BG};
            color: {STATUS_WARNING};
        }}
        QLabel[type="status_label"][status="accent"] {{
            background-color: {STATUS_ACCENT_BG};
            color: {PRIMARY_DARK};
        }}
        /* Hint text — theme-aware (MUTED 5.45:1 light / #A1A1A6 dark) */
        QLabel[type="settings_hint"] {{
            font-size: 11px;
            font-weight: 500;
            color: {TEXT_TERTIARY};
        }}
        /* Record metric value */
        QLabel[type="record_metric_value"] {{
            font-family: {MONO_FONT_STACK};
            font-size: 13px;
            font-weight: 600;
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
        /* Empty state — titles strong, body muted but theme-aware */
        QLabel[type="state_empty_title"] {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        QLabel[type="state_empty_title"][status="error"] {{
            color: {STATUS_ERROR};
        }}
        QLabel[type="state_empty_body"] {{
            font-size: 12px;
            font-weight: 400;
            color: {TEXT_TERTIARY};
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
            border: 1px solid rgba(255, 255, 255, 0.12);
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
        }}
        /* Small pill — focus ink */
        QPushButton[type="small"] {{
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
            font-size: 11px;
            padding: 4px 10px;
            border: 1px solid transparent;
            border-radius: {RADIUS_SM}px;
        }}
        QPushButton[type="small"]:hover {{
            background-color: {FILL_SECONDARY};
            color: {TEXT_PRIMARY};
        }}
        QPushButton[type="small"]:focus {{
            border-color: {FOCUS_BORDER};
        }}

        /* ══════════════════════════════════════════════
           HOME PAGE — Refined & Fluid Dashboard Visuals
           ══════════════════════════════════════════════ */
        QFrame#HomeStatusBar {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_MD}px;
            padding: 2px 4px;
        }}
        QFrame#HomeHeroCard {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
        }}
        QLabel[type="hero_spell_name"] {{
            font-family: {TITLE_FONT_STACK};
            font-size: 38px;
            font-weight: 800;
            color: {TEXT_PRIMARY};
            letter-spacing: 1.5px;
            padding: 8px 0px;
        }}
        QLabel[type="hero_spell_name"][pulsing="true"] {{
            color: {PRIMARY_COLOR};
        }}
        QLabel[type="hero_confidence"] {{
            font-family: {MONO_FONT_STACK};
            font-size: 13px;
            font-weight: 700;
            padding: 5px 16px;
            border-radius: {RADIUS_FULL}px;
        }}
        QLabel[type="hero_confidence"][level="high"] {{
            background-color: {STATUS_SUCCESS_BG};
            color: {STATUS_SUCCESS};
            border: 1px solid rgba(16, 185, 129, 0.25);
        }}
        QLabel[type="hero_confidence"][level="moderate"] {{
            background-color: {STATUS_WARNING_BG};
            color: {STATUS_WARNING};
            border: 1px solid rgba(245, 158, 11, 0.25);
        }}
        QLabel[type="hero_confidence"][level="low"] {{
            background-color: {STATUS_ERROR_BG};
            color: {STATUS_ERROR};
            border: 1px solid rgba(239, 68, 68, 0.25);
        }}
        QLabel[type="hero_subtitle"] {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            color: {PRIMARY_COLOR};
        }}
        QProgressBar[type="hero_confidence_bar"] {{
            background-color: {FILL_TERTIARY};
            border: none;
            border-radius: 3px;
            max-height: 5px;
            min-height: 5px;
        }}
        QProgressBar[type="hero_confidence_bar"]::chunk {{
            background-color: {PRIMARY_COLOR};
            border-radius: 3px;
        }}
        /* Tip Card Container — flat tonal + full border, no side-stripe */
        QFrame#HomeTipCard {{
            background-color: {PRIMARY_LIGHT};
            border: 1px solid {PRIMARY_COLOR};
            border-radius: {RADIUS_MD}px;
        }}
        QLabel[type="tip_eyebrow"] {{
            font-size: 11px;
            font-weight: 800;
            color: {PRIMARY_COLOR};
            letter-spacing: 1.4px;
        }}
        QLabel[type="tip_text"] {{
            font-size: 15px;
            font-weight: 600;
            font-style: italic;
            color: {TEXT_PRIMARY};
        }}
        /* History & Loaded Cards */
        QFrame#HomeHistoryCard, QFrame#HomeLoadedCard {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
        }}
        QListWidget#HomeHistoryList {{
            background-color: {SURFACE_1};
            border: none;
            outline: none;
        }}
        QListWidget#HomeHistoryList::item {{
            background-color: transparent;
            border: none;
            padding: 0px;
            margin-bottom: 4px;
        }}
        QListWidget#HomeHistoryList::item:hover {{
            background-color: transparent;
        }}
        QFrame[type="history_item_row"] {{
            background-color: {SURFACE_0};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_MD}px;
            padding: 8px 12px;
        }}
        QFrame[type="history_item_row"]:hover {{
            background-color: {NAV_HOVER_BG};
            border-color: {PRIMARY_LIGHT};
        }}
        QFrame[type="loaded_spell_row"] {{
            background-color: {SURFACE_0};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_MD}px;
            padding: 8px 14px;
        }}
        QFrame[type="loaded_spell_row"]:hover {{
            background-color: {NAV_HOVER_BG};
            border-color: {PRIMARY_LIGHT};
        }}
    """


def apply_modern_theme(widget_or_app, theme_name: str = "light") -> None:
    """
    Áp dụng theme hiện đại cho một widget hoặc toàn bộ ứng dụng.
    """
    widget_or_app.setStyleSheet(get_modern_stylesheet(theme_name))
    # QSS không có selector cho placeholder text — đặt qua QPalette để đạt contrast
    # trên cả hai theme (mặc định của Qt quá nhạt trên nền tối).
    if hasattr(widget_or_app, "setPalette") and hasattr(widget_or_app, "palette"):
        is_dark = str(theme_name).lower() == "dark"
        pal = widget_or_app.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#a1a1a6" if is_dark else "#5b6b7f"))
        widget_or_app.setPalette(pal)


def apply_flat_widget_chrome(root_widget: QWidget) -> None:
    """No-op — frame removal is now handled by QSS in get_modern_stylesheet."""
    pass


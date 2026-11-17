"""
theme.py — Hệ thống quản lý giao diện (Theme) toàn cục.

Cung cấp các hàm tạo stylesheet (QSS) hiện đại, chỉ áp dụng Light Mode
và giữ giao diện đồng nhất cho toàn bộ ứng dụng.
"""

from __future__ import annotations

import functools
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QFrame

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


from ui.palettes import DARK_PALETTE, LIGHT_PALETTE, Palette


@functools.lru_cache(maxsize=4)
def get_modern_stylesheet(theme_name: str = "light") -> str:
    """
    Tạo QSS Material You (M3 Dynamic Tonal) cho Light Mode hoặc Dark Mode.
    """
    is_dark = (str(theme_name).lower() == "dark")
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

    if not is_dark:
        SIDEBAR_BG = "#F5F2FA"          # M3 Surface Container Low
        SIDEBAR_BORDER = "#E3DFE8"      # M3 Surface Container Highest
        NAV_ACTIVE_BG = "#DFE0FF"       # M3 Primary Container
        NAV_ACTIVE_TEXT = "#0A1365"     # M3 On-Primary Container (deep contrast indigo)
        NAV_HOVER_BG = "rgba(78, 88, 169, 0.08)"
        TOOLBAR_BORDER = "#E3DFE8"
        CARD_SHADOW_BORDER = "rgba(27, 27, 33, 0.04)"
        STATUS_SUCCESS_BG = "#A5F5B4"   # M3 Success Container
        STATUS_ERROR_BG = "#FFDAD6"     # M3 Error Container
        STATUS_WARNING_BG = "#FFDDB8"   # M3 Warning Container
        STATUS_ACCENT_BG = "#DFE0FF"
        STATUS_SUCCESS_TEXT_ON_TINT = "#005221"
        STATUS_WARNING_TEXT_ON_TINT = "#6B3D00"
        STATUS_ACCENT_TEXT_ON_TINT = "#0A1365"
        BORDER_SUCCESS_TINT = "rgba(26, 108, 57, 0.25)"
        BORDER_WARNING_TINT = "rgba(135, 82, 0, 0.25)"
        BORDER_ERROR_TINT = "rgba(186, 26, 26, 0.25)"

        FILL_PRIMARY = "#EFEBF4"        # M3 Surface Container
        FILL_SECONDARY = "rgba(78, 88, 169, 0.08)"
        FILL_TERTIARY = "rgba(78, 88, 169, 0.05)"

        BTN_PRIMARY_TEXT = "#FFFFFF"
        BTN_PRIMARY_HOVER = p.PRIMARY_DARK
        BTN_PRIMARY_PRESSED = "#38428B"
        BTN_BASE_BG = "#DFE0FF"
        BTN_BASE_TEXT = "#0A1365"
        BTN_OUTLINE_BG = "#FFFFFF"
        BTN_OUTLINE_TEXT = "#46464F"
        BTN_DANGER_HOVER_TEXT = "#FFFFFF"

        INPUT_BG = "#EFEBF4"
        INPUT_BORDER = "#C7C5D0"

        # M3 secondary container — list / combo / menu selection (baseline tonal)
        SEC_CONT_BG = "#E8DEF8"
        SEC_CONT_TEXT = "#1D192B"
        # M3 inverse surface — tooltips
        INVERSE_BG = "#313033"
        INVERSE_TEXT = "#F4EFF4"
        # M3 menu container — surface container
        MENU_BG = "#EFEBF4"

        COMBO_POPUP_BG = "#FFFFFF"
        COMBO_POPUP_TEXT = p.TEXT_PRIMARY
        COMBO_SEL_BG = SEC_CONT_BG
        COMBO_SEL_TEXT = SEC_CONT_TEXT

        SCROLL_HANDLE = "rgba(27, 27, 33, 0.20)"
        SCROLL_HANDLE_HOVER = "rgba(27, 27, 33, 0.35)"
        ACCENT_TITLE_COLOR = p.PRIMARY
        BG_DARK = "#191C20"

        # Interactive-state tokens — M3 state layers
        FOCUS_BORDER = "#4E58A9"
        PRIMARY_PRESSED = "#38428B"
        DISABLED_BG = "#EFEBF4"
        DISABLED_TEXT = "#767680"
        DISABLED_BORDER = "#E3DFE8"
        OUTLINE_BORDER = "#767680"
        ERROR_TEXT_ON_TINT = "#93000A"

    else:
        SIDEBAR_BG = "#1A1B21"          # M3 Dark Surface Container Low
        SIDEBAR_BORDER = "#33343B"      # M3 Dark Surface Container Highest
        NAV_ACTIVE_BG = "#373F8F"       # M3 Dark Primary Container
        NAV_ACTIVE_TEXT = "#DFE0FF"     # M3 Dark On-Primary Container (6.95:1 contrast)
        NAV_HOVER_BG = "rgba(190, 194, 255, 0.08)"
        TOOLBAR_BORDER = "#33343B"
        CARD_SHADOW_BORDER = "rgba(0, 0, 0, 0.30)"
        STATUS_SUCCESS_BG = "#005221"   # M3 Dark Success Container
        STATUS_ERROR_BG = "#690005"     # M3 Dark Error Container
        STATUS_WARNING_BG = "#4A2800"   # M3 Dark Warning Container
        STATUS_ACCENT_BG = "#373F8F"
        STATUS_SUCCESS_TEXT_ON_TINT = "#81D691"
        STATUS_WARNING_TEXT_ON_TINT = "#FFB870"
        STATUS_ACCENT_TEXT_ON_TINT = "#DFE0FF"
        BORDER_SUCCESS_TINT = "rgba(129, 214, 145, 0.25)"
        BORDER_WARNING_TINT = "rgba(255, 184, 112, 0.25)"
        BORDER_ERROR_TINT = "rgba(255, 180, 171, 0.25)"

        FILL_PRIMARY = "#24252C"        # M3 Dark Surface Container
        FILL_SECONDARY = "rgba(190, 194, 255, 0.08)"
        FILL_TERTIARY = "rgba(190, 194, 255, 0.05)"

        BTN_PRIMARY_TEXT = "#1B2678"    # M3 Dark On-Primary (8.0:1 on #BEC2FF)
        BTN_PRIMARY_HOVER = "#D8DAFF"   # Light tonal hover
        BTN_PRIMARY_PRESSED = "#959BF0"
        BTN_BASE_BG = "#373F8F"
        BTN_BASE_TEXT = "#DFE0FF"
        BTN_OUTLINE_BG = "#1A1B21"
        BTN_OUTLINE_TEXT = "#C6C5D0"
        BTN_DANGER_HOVER_TEXT = "#690005"

        INPUT_BG = "#24252C"
        INPUT_BORDER = "#46464F"

        # M3 secondary container — list / combo / menu selection (baseline tonal)
        SEC_CONT_BG = "#4A4458"
        SEC_CONT_TEXT = "#E8DEF8"
        # M3 inverse surface — tooltips
        INVERSE_BG = "#E6E1E5"
        INVERSE_TEXT = "#313033"
        # M3 menu container — surface container high
        MENU_BG = "#33343B"

        COMBO_POPUP_BG = "#24252C"
        COMBO_POPUP_TEXT = p.TEXT_PRIMARY
        COMBO_SEL_BG = SEC_CONT_BG
        COMBO_SEL_TEXT = SEC_CONT_TEXT

        SCROLL_HANDLE = "rgba(226, 226, 233, 0.20)"
        SCROLL_HANDLE_HOVER = "rgba(226, 226, 233, 0.35)"
        ACCENT_TITLE_COLOR = p.PRIMARY
        BG_DARK = "#0D0E13"

        # Interactive-state tokens — M3 state layers
        FOCUS_BORDER = "#BEC2FF"
        PRIMARY_PRESSED = "#959BF0"
        DISABLED_BG = "#24252C"
        DISABLED_TEXT = "#90909A"
        DISABLED_BORDER = "#33343B"
        OUTLINE_BORDER = "#8A8994"
        ERROR_TEXT_ON_TINT = "#FFB4AB"


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
            font-weight: 600;
            color: {TEXT_SECONDARY};
            letter-spacing: 0.2px;
            padding-left: 4px;
        }}
        /* Nav buttons — M3 Navigation Rail active pill shape */
        QToolButton#StemNavBtn {{
            background-color: transparent;
            color: {TEXT_SECONDARY};
            border: none;
            border-radius: 22px;
            padding: 8px 18px;
            margin: 2px 12px;
            font-size: 13px;
            font-weight: 500;
            text-align: left;
        }}
        QToolButton#StemNavBtn:hover {{
            background-color: {NAV_HOVER_BG};
            color: {TEXT_PRIMARY};
            border-radius: 22px;
        }}
        QToolButton#StemNavBtn:focus {{
            border: none;
            background-color: {NAV_HOVER_BG};
            border-radius: 22px;
        }}
        QToolButton#StemNavBtn[active="true"] {{
            background-color: {NAV_ACTIVE_BG};
            color: {NAV_ACTIVE_TEXT};
            font-weight: 700;
            border: none;
            border-radius: 22px;
        }}
        QToolButton#StemNavBtn[active="true"]:focus {{
            background-color: {NAV_ACTIVE_BG};
            color: {NAV_ACTIVE_TEXT};
            font-weight: 700;
            border: none;
            border-radius: 22px;
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
           CARDS — Clean M3 Surface Container Lowest with uniform 1px border
           ══════════════════════════════════════════════ */
        QFrame#CardFrame, QFrame#VanguardCardOuter, QWidget#Card, QFrame#Card,
        #HomeViewerCard, #HomeRightSection, #CardFrameElevated, #HomeHeroCard,
        #HomeHistoryCard, #HomeLoadedCard,
        #VanguardCardInner, QFrame[type="statistics_card"],
        QWidget[type="statistics_card"], #HomeViewerSurface,
        QFrame#ModernCard {{
            background-color: {SURFACE_1};
            border: 1px solid {BORDER_COLOR};
            border-radius: {RADIUS_LG}px;
        }}
        QFrame#SettingsControlBar {{
            background-color: {SURFACE_1};
            border-top: 1px solid {BORDER_LIGHT};
            border-radius: 0px;
        }}

        /* ══════════════════════════════════════════════
           BUTTONS — Material You (M3 Full Pill Variants)
           ══════════════════════════════════════════════ */
        QPushButton, QToolButton {{
            background-color: transparent;
            color: {TEXT_PRIMARY};
            border: none;
            border-radius: {RADIUS_FULL}px;
            padding: 8px 20px;
            font-weight: 600;
            font-size: 13px;
        }}

        /* Primary / Start — M3 Filled Button */
        QPushButton[type="primary"], QPushButton[type="start"] {{
            background-color: {PRIMARY_COLOR};
            color: {BTN_PRIMARY_TEXT};
            font-weight: 600;
            border: none;
            border-radius: {RADIUS_FULL}px;
            padding: 8px 22px;
        }}
        QPushButton[type="primary"]:hover, QPushButton[type="start"]:hover {{
            background-color: {BTN_PRIMARY_HOVER};
        }}
        QPushButton[type="primary"]:pressed, QPushButton[type="start"]:pressed {{
            background-color: {PRIMARY_PRESSED};
        }}
        QPushButton[type="primary"]:focus, QPushButton[type="start"]:focus {{
            border: 2px solid {FOCUS_BORDER};
        }}
        QPushButton[type="primary"]:disabled, QPushButton[type="start"]:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
        }}

        /* Base / Back — M3 Filled Tonal Button */
        QPushButton[type="base"], QPushButton[type="back"] {{
            background-color: {BTN_BASE_BG};
            color: {BTN_BASE_TEXT};
            font-weight: 600;
            border: none;
            border-radius: {RADIUS_FULL}px;
            padding: 8px 20px;
        }}
        QPushButton[type="base"]:hover, QPushButton[type="back"]:hover {{
            background-color: {NAV_HOVER_BG};
        }}
        QPushButton[type="base"]:focus, QPushButton[type="back"]:focus {{
            border: 2px solid {FOCUS_BORDER};
            background-color: {NAV_HOVER_BG};
        }}

        /* Stop / Danger — M3 Error Container Button */
        QPushButton[type="stop"], QPushButton[type="danger"] {{
            background-color: {STATUS_ERROR_BG};
            color: {STATUS_ERROR};
            font-weight: 600;
            border: none;
            border-radius: {RADIUS_FULL}px;
            padding: 8px 20px;
        }}
        QPushButton[type="stop"]:hover, QPushButton[type="danger"]:hover {{
            background-color: {STATUS_ERROR};
            color: {BTN_DANGER_HOVER_TEXT};
        }}
        QPushButton[type="stop"]:focus, QPushButton[type="danger"]:focus {{
            border: 2px solid {FOCUS_BORDER};
        }}

        /* Danger outline — M3 Outlined Error Button */
        QPushButton[type="danger_outline"] {{
            background-color: transparent;
            color: {STATUS_ERROR};
            border: 1px solid {STATUS_ERROR};
            border-radius: {RADIUS_FULL}px;
            padding: 7px 18px;
            font-weight: 600;
        }}
        QPushButton[type="danger_outline"]:hover {{
            background-color: {STATUS_ERROR_BG};
            border-color: {STATUS_ERROR};
        }}
        QPushButton[type="danger_outline"]:focus {{
            border: 2px solid {FOCUS_BORDER};
            background-color: {STATUS_ERROR_BG};
        }}

        /* Outline / Snip — M3 Outlined Button */
        QPushButton[type="outline"], QPushButton[type="snip"] {{
            background-color: {BTN_OUTLINE_BG};
            color: {BTN_OUTLINE_TEXT};
            border: 1px solid {OUTLINE_BORDER};
            border-radius: {RADIUS_FULL}px;
            padding: 7px 18px;
            font-weight: 600;
        }}
        QPushButton[type="outline"]:hover, QPushButton[type="snip"]:hover {{
            background-color: {FILL_PRIMARY};
            color: {TEXT_PRIMARY};
            border-color: {PRIMARY_COLOR};
        }}
        QPushButton[type="outline"]:pressed, QPushButton[type="snip"]:pressed {{
            background-color: {FILL_SECONDARY};
        }}
        QPushButton[type="outline"]:focus, QPushButton[type="snip"]:focus {{
            border: 2px solid {FOCUS_BORDER};
        }}

        /* Icon-only — M3 Tonal Squircle Button */
        QToolButton[type="icon"] {{
            background-color: {FILL_PRIMARY};
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 6px;
        }}
        QToolButton[type="icon"]:hover {{
            background-color: {FILL_SECONDARY};
        }}
        QToolButton[type="icon"]:pressed {{
            background-color: {FILL_PRIMARY};
        }}
        QToolButton[type="icon"]:checked {{
            background-color: {BTN_BASE_BG};
        }}
        QToolButton[type="icon"]:focus {{
            border-color: {FOCUS_BORDER};
            background-color: {FILL_SECONDARY};
        }}
        /* Generic tool button — transparent state layer */
        QToolButton:hover {{
            background-color: {NAV_HOVER_BG};
        }}
        QToolButton:pressed, QToolButton:checked {{
            background-color: {FILL_PRIMARY};
        }}

        QPushButton:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
            border: 1px solid {DISABLED_BORDER};
        }}

        /* ══════════════════════════════════════════════
           INPUTS — Refined form controls
           ══════════════════════════════════════════════ */
        QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QDateTimeEdit {{
            background-color: {INPUT_BG};
            border: 1px solid {INPUT_BORDER};
            border-radius: {RADIUS_SM}px;
            padding: 8px 12px;
            color: {TEXT_PRIMARY};
            selection-background-color: {PRIMARY_LIGHT};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {PRIMARY_COLOR};
            background-color: {SURFACE_1};
        }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
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
        QComboBox QAbstractItemView::item {{
            min-height: 36px;
            padding: 4px 8px;
            border-radius: {RADIUS_SM}px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {NAV_HOVER_BG};
            color: {TEXT_PRIMARY};
        }}
        QListView::item, QTreeView::item {{
            border-radius: {RADIUS_SM}px;
        }}
        QListView::item:hover, QTreeView::item:hover {{
            background-color: {NAV_HOVER_BG};
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
        QListWidget::item:selected:focus {{
            background-color: {COMBO_SEL_BG};
            color: {COMBO_SEL_TEXT};
        }}
        QTableWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {COMBO_SEL_BG};
            color: {COMBO_SEL_TEXT};
        }}
        QListWidget::item:disabled, QTableWidget::item:disabled {{
            color: {TEXT_TERTIARY};
        }}
        QHeaderView::section {{
            background-color: {FILL_PRIMARY};
            color: {TEXT_SECONDARY};
            padding: 6px 10px;
            border: none;
            border-bottom: 1px solid {BORDER_COLOR};
            font-weight: 600;
            font-size: 12px;
        }}
        QHeaderView::section:hover {{
            background-color: {FILL_SECONDARY};
            color: {TEXT_PRIMARY};
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
            font-weight: 600;
            color: {TEXT_PRIMARY};
            min-height: 4px;
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY_COLOR};
            border-radius: 4px;
        }}

        /* ══════════════════════════════════════════════
           SLIDER — Material You (M3 Track & Handle)
           ══════════════════════════════════════════════ */
        QSlider::groove:horizontal {{
            height: 6px;
            background: {FILL_PRIMARY};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {PRIMARY_COLOR};
            border-radius: 3px;
        }}
        QSlider::add-page:horizontal {{
            background: {FILL_TERTIARY};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {PRIMARY_COLOR};
            border: 2px solid {SURFACE_1};
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {BTN_PRIMARY_HOVER};
        }}
        QSlider::handle:horizontal:focus {{
            border: 2px solid {FOCUS_BORDER};
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

        /* Groove reset */
        QScrollBar::groove:vertical, QScrollBar::groove:horizontal {{
            background: transparent;
            border: none;
        }}
        QScrollBar:corner {{
            background: transparent;
            border: none;
        }}

        /* ══════════════════════════════════════════════
           CHROME EXTRAS — statusbar, separators, splitter
           ══════════════════════════════════════════════ */
        QStatusBar {{
            background-color: {SURFACE_0};
            color: {TEXT_SECONDARY};
            border-top: 1px solid {BORDER_COLOR};
        }}
        QMainWindow::separator {{
            background: transparent;
            width: 4px;
            height: 4px;
        }}
        QSplitter::handle {{
            background: transparent;
        }}
        QSplitter::handle:hover {{
            background-color: {NAV_HOVER_BG};
        }}

        /* ══════════════════════════════════════════════
           TERMINAL — Dark surface with refined type
           ══════════════════════════════════════════════ */
        QTextEdit, QPlainTextEdit {{
            background-color: {BG_DARK};
            color: {TERM_FG};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_LG}px;
            font-family: {MONO_FONT_STACK};
            font-size: 12px;
            padding: 16px;
            selection-background-color: rgba(78, 88, 169, 0.35);
        }}

        /* ══════════════════════════════════════════════
           DIALOG
           ══════════════════════════════════════════════ */
        QDialog {{
            background-color: {SURFACE_0};
            border-radius: {RADIUS_XL}px;
        }}
        QMessageBox {{
            background-color: {SURFACE_0};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 88px;
            min-height: 36px;
            border-radius: {RADIUS_FULL}px;
            font-weight: 600;
        }}

        /* ══════════════════════════════════════════════
           MENU — M3 menu container with pill item highlight
           ══════════════════════════════════════════════ */
        QMenu {{
            background-color: {MENU_BG};
            border: 1px solid {BORDER_LIGHT};
            border-radius: {RADIUS_SM}px;
            padding: 6px;
        }}
        QMenu::item {{
            color: {TEXT_PRIMARY};
            padding: 8px 24px 8px 14px;
            border-radius: {RADIUS_FULL}px;
            font-size: 13px;
        }}
        QMenu::item:selected {{
            background-color: {SEC_CONT_BG};
            color: {SEC_CONT_TEXT};
        }}
        QMenu::item:disabled {{
            color: {TEXT_TERTIARY};
        }}
        QMenu::separator {{
            height: 1px;
            background: {BORDER_COLOR};
            margin: 6px 8px;
        }}
        QMenu::icon {{
            padding-left: 8px;
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
            border-radius: 4px;
            border: 2px solid {BORDER_MID};
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
        QCheckBox::indicator:indeterminate {{
            background-color: {PRIMARY_COLOR};
            border-color: {PRIMARY_COLOR};
        }}
        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 10px;
            border: 2px solid {BORDER_MID};
            background-color: {SURFACE_1};
        }}
        QRadioButton::indicator:hover {{
            border-color: {PRIMARY_COLOR};
        }}
        QRadioButton::indicator:checked {{
            border: 6px solid {PRIMARY_COLOR};
            background-color: {SURFACE_1};
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
        /* Settings section header — crisp M3 section title */
        QLabel[type="settings_section_label"] {{
            font-size: 12px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            letter-spacing: 0.2px;
        }}
        QLabel[type="settings_section_label"][status="accent"] {{
            color: {ACCENT_TITLE_COLOR};
        }}
        /* Status label — pill badges with semantic colors (padding dọc 7px cho dấu chồng VN) */
        QLabel[type="status_label"] {{
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 11px;
            background-color: {FILL_TERTIARY};
            color: {TEXT_SECONDARY};
        }}
        QLabel[type="status_label"][status="success"] {{
            background-color: {STATUS_SUCCESS_BG};
            color: {STATUS_SUCCESS_TEXT_ON_TINT};
        }}
        QLabel[type="status_label"][status="error"] {{
            background-color: {STATUS_ERROR_BG};
            color: {ERROR_TEXT_ON_TINT};
        }}
        QLabel[type="status_label"][status="warning"] {{
            background-color: {STATUS_WARNING_BG};
            color: {STATUS_WARNING_TEXT_ON_TINT};
        }}
        QLabel[type="status_label"][status="accent"] {{
            background-color: {STATUS_ACCENT_BG};
            color: {STATUS_ACCENT_TEXT_ON_TINT};
        }}
        QLabel[type="status_label"][status="muted"] {{
            background-color: {FILL_PRIMARY};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_LIGHT};
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
            background-color: {INVERSE_BG};
            color: {INVERSE_TEXT};
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
            padding: 8px 18px;
            border: none;
            font-weight: 600;
            border-top-left-radius: {RADIUS_SM}px;
            border-top-right-radius: {RADIUS_SM}px;
        }}
        QTabBar::tab:selected {{
            color: {PRIMARY_COLOR};
            font-weight: 700;
            border-bottom: 3px solid {PRIMARY_COLOR};
        }}
        QTabBar::tab:hover {{
            color: {TEXT_PRIMARY};
            background-color: {NAV_HOVER_BG};
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
            border-radius: 13px;
        }}
        QLabel[type="hero_confidence"][level="high"] {{
            background-color: {STATUS_SUCCESS_BG};
            color: {STATUS_SUCCESS_TEXT_ON_TINT};
            border: none;
        }}
        QLabel[type="hero_confidence"][level="moderate"] {{
            background-color: {STATUS_WARNING_BG};
            color: {STATUS_WARNING_TEXT_ON_TINT};
            border: none;
        }}
        QLabel[type="hero_confidence"][level="low"] {{
            background-color: {STATUS_ERROR_BG};
            color: {ERROR_TEXT_ON_TINT};
            border: none;
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
            border-radius: 2px;
            max-height: 4px;
            min-height: 4px;
        }}
        QProgressBar[type="hero_confidence_bar"]::chunk {{
            background-color: {PRIMARY_COLOR};
            border-radius: 2px;
        }}
        /* Tip Card Container — M3 tonal container, no border */
        QFrame#HomeTipCard {{
            background-color: {PRIMARY_LIGHT};
            border: none;
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
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 8px 12px;
        }}
        QFrame[type="history_item_row"]:hover {{
            background-color: {NAV_HOVER_BG};
        }}
        QFrame[type="loaded_spell_row"] {{
            background-color: {SURFACE_0};
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 8px 14px;
        }}
        QFrame[type="loaded_spell_row"]:hover {{
            background-color: {NAV_HOVER_BG};
        }}
    """


def apply_modern_theme(widget_or_app, theme_name: str = "light") -> None:
    """
    Áp dụng theme hiện đại cho một widget hoặc toàn bộ ứng dụng.
    """
    is_dark = (str(theme_name).lower() == "dark")
    widget_or_app.setStyleSheet(get_modern_stylesheet(theme_name))
    # QSS không có selector cho placeholder text — đặt qua QPalette để đạt contrast
    # trên cả hai theme (mặc định của Qt quá nhạt trên nền tối).
    if hasattr(widget_or_app, "setPalette") and hasattr(widget_or_app, "palette"):
        pal = widget_or_app.palette()
        placeholder_color = "#90909A" if is_dark else "#71717A"
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_color))
        widget_or_app.setPalette(pal)


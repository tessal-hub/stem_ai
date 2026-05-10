"""
Consolidated design tokens for all UI pages.
Centralizes colors, sizes, stylesheet constants, and visual elements.

This module merges:
  - _STYLE_* constants from all 5 pages
  - _STATUS_STYLE template from page_wand
"""

from PyQt6.QtCore import QSize

APP_FONT_STACK = "SF Pro Text, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"

# ════════════════════════════════════════════════════════════════════════════
# MODERN PROFESSIONAL COLOR PALETTE (for modern theme)
# ════════════════════════════════════════════════════════════════════════════

# Primary monochrome color
PRIMARY_COLOR = "#2f3137"
PRIMARY_LIGHT = "#ececef"
PRIMARY_DARK = "#1f2024"

# Secondary accent colors (kept aligned to monochrome palette)
SECONDARY_COLOR = PRIMARY_COLOR
SECONDARY_LIGHT = PRIMARY_LIGHT
SECONDARY_DARK = PRIMARY_DARK

# Surface colors (single-color minimal look)
SURFACE_0 = "#f5f5f7"
SURFACE_1 = "#f5f5f7"
SURFACE_2 = "#f5f5f7"
SURFACE_PRIMARY = SURFACE_1
SURFACE_SECONDARY = SURFACE_0
SURFACE_TERTIARY = SURFACE_2

# Text colors
TEXT_PRIMARY = "#1c1c1e"
TEXT_SECONDARY = "#636366"
TEXT_TERTIARY = "#8e8e93"

# Border colors
BORDER_COLOR = "transparent"
BORDER_LIGHT = "transparent"

# Status/semantic colors
STATUS_SUCCESS = "#10b981"       # Green for success
STATUS_WARNING = "#f59e0b"       # Amber for warnings
STATUS_ERROR = "#ef4444"         # Red for errors

# Shadow colors for depth (disabled in flat mode)
SHADOW_LIGHT = "transparent"
SHADOW_MEDIUM = "transparent"
SHADOW_DARK = "transparent"

# Flat surfaces
GLASS_BG = SURFACE_1
GLASS_BG_STRONG = SURFACE_1
GLASS_BORDER = "transparent"
GLASS_EDGE = "transparent"

# ════════════════════════════════════════════════════════════════════════════

MAC_BG = SURFACE_0
MAC_SURFACE_SOLID = SURFACE_1
MAC_SIDEBAR_BG = SURFACE_2
MAC_TOOLBAR_BG = SURFACE_1
MAC_BORDER = BORDER_COLOR
MAC_BORDER_STRONG = BORDER_COLOR
MAC_TEXT_PRIMARY = TEXT_PRIMARY
MAC_TEXT_SECONDARY = TEXT_SECONDARY
MAC_ACCENT = PRIMARY_COLOR
MAC_ACCENT_DARK = PRIMARY_DARK

# Shell layout tokens
SHELL_SIDEBAR_W = 178
SHELL_NAV_H = 54
SHELL_BRAND_H = 80
SHELL_BRAND_ICON = QSize(30, 30)

# Home layout tokens
HOME_STATUS_H = 32
HOME_VIEWER_MIN_H = 360
HOME_ATTACH_H = 36
HOME_RIGHT_W = 320
HOME_MANAGER_DOT = 8
HOME_MODE_H = 48
HOME_VIEWER_INNER_MARGIN = 0

# ────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ────────────────────────────────────────────────────────────────────────────

# Base neutrals
BG_WHITE     = SURFACE_1
BG_LIGHT     = SURFACE_2
BG_DARK      = "#111827"
BORDER       = BORDER_COLOR
BORDER_MID   = BORDER_COLOR
TEXT_BODY    = TEXT_PRIMARY
TEXT_MUTED   = TEXT_TERTIARY

# Common accent colors (used in multiple pages)
ACCENT       = MAC_ACCENT
ACCENT_DARK  = MAC_ACCENT_DARK
ACCENT_TEXT  = "#ffffff"
SUCCESS      = "#10b981"
DANGER       = "#ef4444"
WARNING      = "#f59e0b"
HOVER_BG     = "#ececef"

# Terminal colors (used in wand page)
TERM_FG      = TEXT_BODY
TERM_BG      = SURFACE_1

# Graph colors (used in plotting)
CROP_REGION  = "#ff336644"
PLOT_AX_COLOR = "#ff5555"
PLOT_AY_COLOR = "#55ff55"
PLOT_AZ_COLOR = "#5555ff"
PLOT_GX_COLOR = "#ff00ff"
PLOT_GY_COLOR = "#00ffff"
PLOT_GZ_COLOR = "#ffff00"
PLOT_HANDLE_HOVER_COLOR = "#ffffff"

# Rarity colors (used in statistics)
RARITY_NONE  = "#9ca3af"
RARITY_COM   = "#10b981"
RARITY_UNC   = "#3b82f6"
RARITY_RARE  = "#8b5cf6"
RARITY_EPIC  = "#f59e0b"

# Settings-specific accents
SETTINGS_ACCENT       = "#6366f1"
SETTINGS_ACCENT_DARK  = "#4f46e5"
SETTINGS_HOVER_BG     = PRIMARY_LIGHT   # Light indigo hover for settings

# Wand-specific accents
WAND_ACCENT       = ACCENT

# Home page typography tokens
STYLE_HOME_SECTION_TITLE = f"color: {TEXT_BODY}; font-size: 17px; font-weight: 700;"
STYLE_HOME_SECTION_SUBTITLE = f"color: {TEXT_MUTED}; font-weight: 500; font-size: 12px;"
STYLE_HOME_MODE_LABEL = f"color: {ACCENT}; font-size: 13px; font-weight: 700;"
STYLE_HOME_STAT_NAME = f"color: {TEXT_BODY}; font-size: 12px; font-weight: 600;"
STYLE_HOME_STAT_VALUE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;"
STYLE_HOME_EMPTY_SPELL_TEXT = f"color: {TEXT_MUTED}; font-size: 12px; font-style: italic; padding: 4px 0;"
STYLE_HOME_OVERFLOW_TEXT = f"color: {TEXT_MUTED}; font-size: 10px; font-style: italic; padding: 2px 0;"
STYLE_HOME_MANAGER_INDICATOR = f"background-color: {ACCENT}; border-radius: 4px;"
STYLE_HOME_STATUS_TEMPLATE = (
    "QLabel {{ "
    "background-color: {bg_color}; "
    f"color: {{fg_color}}; padding: 8px 16px; font-size: 12px; "
    "font-weight: 700; border-radius: 12px; }}"
)
STYLE_HOME_STATUS_BAR = f"""
    #HomeStatusBar {{
        background-color: {DANGER};
        color: {ACCENT_TEXT};
        border-radius: 8px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 1px;
    }}
"""
STYLE_HOME_VIEWER_CARD = f"""
    #HomeViewerCard {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
    #HomeViewerSurface {{
        background-color: {GLASS_BG_STRONG};
        border: none;
        border-radius: 18px;
    }}
"""
STYLE_HOME_ATTACHMENT_BAR = """
    #HomeAttachmentBar {
        background-color: transparent;
        border: none;
    }
"""
STYLE_HOME_ATTACHMENT_PILL = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        color: {TEXT_BODY};
        border: 1px solid {GLASS_EDGE};
        border-radius: 12px;
        font-size: 10px;
        font-weight: 600;
        padding: 4px 10px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
"""
STYLE_HOME_RIGHT_PANEL = """
    #HomeRightPanel {
        background-color: transparent;
        border: none;
    }
"""
STYLE_HOME_RIGHT_SECTION = f"""
    #HomeRightSection {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
"""
STYLE_HOME_MANAGER_ROW = f"""
    #HomeManagerRow QLabel {{
        color: {TEXT_BODY};
    }}
    #HomeManagerRow QLabel#HomeManagerValue {{
        color: {TEXT_MUTED};
        font-weight: 700;
    }}
"""
STYLE_HOME_MANAGER_BAR = f"""
    QProgressBar#HomeManagerBar {{
        background-color: {BORDER};
        border: none;
        border-radius: 4px;
        min-height: 6px;
        max-height: 6px;
        text-align: right;
    }}
    QProgressBar#HomeManagerBar::chunk {{
        background-color: {ACCENT};
        border-radius: 4px;
    }}
"""
STYLE_HOME_SPELL_BTN = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        color: {TEXT_BODY};
        border: 1px solid {GLASS_EDGE};
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-align: left;
        padding-left: 10px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
"""
STYLE_HOME_MODULE_BTN = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: none;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 4px 8px;
    }}
    QPushButton:hover {{
        color: {ACCENT};
        background-color: {HOVER_BG};
    }}
"""
STYLE_HOME_ACTION_BTN = f"""
    QPushButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""
STYLE_HOME_ACTION_BTN_SECONDARY = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        color: {TEXT_SECONDARY};
        border: 1px solid {GLASS_EDGE};
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
    QPushButton:disabled {{ background-color: {BG_LIGHT}; color: {TEXT_MUTED}; }}
"""

# ────────────────────────────────────────────────────────────────────────────
# SIZING
# ────────────────────────────────────────────────────────────────────────────

ICON          = QSize(18, 18)
STATUS_H      = 28
SPELL_BTN_H   = 36
MODULE_BTN_H  = 28
GRAPH_MIN_H   = 360
TERM_MIN_H    = 140
PROGRESS_H    = 6
RIGHT_MAX_W   = 380
BTN_H         = 32
BTN_SMALL_H   = 28
SETTINGS_BTN_H    = 32
SETTINGS_INPUT_H  = 32
LABEL_W       = 170
RECORD_GRAPH_MIN_H = 150
RECORD_LIST_MIN_H = 180
SETTING_CONSOLE_MIN_H = 180
STATISTICS_FFT_MIN_H = 320
STATISTICS_SAMPLE_LIST_MIN_H = 220
WAND_SPELL_LIST_MIN_H = 220
WAND_TERMINAL_MIN_H = 210

# ────────────────────────────────────────────────────────────────────────────
# MAIN CONTAINER STYLES (used in all pages)
# ────────────────────────────────────────────────────────────────────────────

# PageHome
STYLE_HOME_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {MAC_BG};
        border-top: none;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
    }}
"""

# PageRecord
STYLE_RECORD_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {MAC_BG};
        border-top: none;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
    }}
"""

# PageWand
STYLE_WAND_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {MAC_BG};
        border-top: none;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
    }}
"""

# PageStatistics
STYLE_STATISTICS_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {MAC_BG};
        border-top: none;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
    }}
"""

# PageSetting
STYLE_SETTING_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {MAC_BG};
        border-top: none;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# CONTAINER & CARD STYLES
# ────────────────────────────────────────────────────────────────────────────

# Generic card frames
STYLE_CARD = f"""
    #CardFrame {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
"""

STYLE_CARD_NO_BORDER = """
    #CardFrame {
        background-color: transparent;
        border: none;
    }
"""

# PageStatistics card style (also applies to ClickableFrame)
STYLE_STATISTICS_CARD = f"""
    #CardFrame, ClickableFrame {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
    ClickableFrame:hover {{
        background-color: {GLASS_BG_STRONG};
        border: 1px solid rgba(0, 0, 0, 0.10);
    }}
"""

# PageSetting card style
STYLE_SETTING_CARD = f"""
    #CardFrame {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
"""

# PageRecord graph card style
STYLE_RECORD_GRAPH_CARD = f"""
    #CardFrame {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
"""

# PageWand card style
STYLE_WAND_CARD = f"""
    #CardFrame {{
        background-color: {GLASS_BG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 20px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# BUTTON STYLES
# ────────────────────────────────────────────────────────────────────────────

# Base button (PageRecord)
STYLE_BTN_BASE = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        border: none;
        border-radius: 14px;
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
        min-width: 64px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
"""

# Specific Record buttons
STYLE_BTN_START = f"""
    QPushButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""
STYLE_BTN_STOP = f"""
    QPushButton {{
        background-color: rgba(239, 68, 68, 31);
        color: {DANGER};
        border: 1px solid rgba(239, 68, 68, 71);
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{ background-color: {DANGER}; color: {ACCENT_TEXT}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""
STYLE_BTN_SNIP = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        color: {TEXT_SECONDARY};
        border: 1px solid {GLASS_EDGE};
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""
STYLE_BTN_DANGER_OUTLINE = STYLE_BTN_STOP
STYLE_BTN_BACK = f"""
    QPushButton {{
        background-color: {SURFACE_1};
        border: none;
        border-radius: 14px;
        color: {TEXT_BODY};
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
        min-width: 64px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {TEXT_BODY};
    }}
"""

# Outline button (generic, used in PageWand, PageSetting)
STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {GLASS_BG_STRONG};
        color: {TEXT_SECONDARY};
        border: 1px solid {GLASS_EDGE};
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

# Primary button (generic, used in PageWand, PageSetting)
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""

# Small button (PageWand)
STYLE_BTN_SMALL = f"""
    QPushButton {{
        background-color: {BG_LIGHT};
        color: {TEXT_SECONDARY};
        border: none;
        border-radius: 12px;
        min-height: 28px;
        max-height: 28px;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 8px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
"""

# Settings-specific buttons
STYLE_SETTING_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {BG_LIGHT};
        color: {TEXT_SECONDARY};
        border: none;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: {SETTINGS_HOVER_BG};
        color: {SETTINGS_ACCENT};
    }}
    QPushButton:disabled {{
        opacity: 0.5;
    }}
"""

STYLE_SETTING_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""

STYLE_SETTING_BTN_DANGER = f"""
    QPushButton {{
        background-color: rgba(239, 68, 68, 31);
        color: {DANGER};
        border: none;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {DANGER}; color: {ACCENT_TEXT}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

# PageHome spell & module buttons
STYLE_SPELL_BTN = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: none;
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        text-align: left;
        padding-left: 10px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
    }}
"""

STYLE_MODULE_BTN = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: none;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 4px 8px;
    }}
    QPushButton:hover {{
        color: {ACCENT};
        background-color: {HOVER_BG};
    }}
"""

# PageStatistics back button
STYLE_STATISTICS_BTN_BACK = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: none;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {HOVER_BG}; }}
"""

# ────────────────────────────────────────────────────────────────────────────
# COMPONENT STYLES (List, Checkbox, ComboBox, Input, Progress)
# ────────────────────────────────────────────────────────────────────────────

# List widget (used in multiple pages)
STYLE_LIST = f"""
    QListWidget {{
        background-color: {GLASS_BG_STRONG};
        border: none;
        border-radius: 16px;
        outline: 0;
        color: {TEXT_BODY};
    }}
    QListWidget::item {{
        border-bottom: none;
        min-height: 48px;
        padding: 0 12px;
        color: {TEXT_BODY};
    }}
    QListWidget::item:selected {{
        background-color: {PRIMARY_LIGHT};
        border-left: 3px solid {ACCENT};
        padding-left: 9px;
    }}
    QListWidget::item:hover:!selected {{ background-color: {BG_LIGHT}; }}
"""

# PageRecord list
STYLE_RECORD_LIST = f"""
    QListWidget {{
        background-color: {GLASS_BG_STRONG};
        border: none;
        border-radius: 16px;
        outline: 0;
        color: {TEXT_BODY};
    }}
    QListWidget::item {{
        border-bottom: none;
        min-height: 48px;
        padding: 0 12px;
        color: {TEXT_BODY};
        font-weight: 500;
    }}
    QListWidget::item:selected {{
        background-color: {PRIMARY_LIGHT};
        color: {TEXT_BODY};
        border-left: 3px solid {ACCENT};
        padding-left: 9px;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {BG_LIGHT};
    }}
"""

# PageStatistics list
STYLE_STATISTICS_LIST = f"""
    QListWidget {{
        background-color: {GLASS_BG_STRONG};
        border: none;
        border-radius: 16px;
        outline: 0;
        color: {TEXT_BODY};
    }}
    QListWidget::item {{
        border-bottom: none;
        min-height: 48px;
        padding: 0 12px;
        color: {TEXT_BODY};
        font-weight: 500;
    }}
    QListWidget::item:selected {{
        background-color: {PRIMARY_LIGHT};
        color: {TEXT_BODY};
        border-left: 3px solid {ACCENT};
        padding-left: 9px;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {BG_LIGHT};
    }}
"""

# Checkbox (generic)
STYLE_CHECKBOX = f"""
    QCheckBox {{
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
    }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 6px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER_MID};
        border-radius: 6px;
    }}
"""

# PageRecord checkbox
STYLE_RECORD_CHECKBOX = f"""
    QCheckBox {{ color: {TEXT_BODY}; font-weight: 600; font-size: 11px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 6px;
    }}
"""

# PageSetting checkbox
STYLE_SETTING_CHECKBOX = f"""
    QCheckBox {{ color: {TEXT_BODY}; font-weight: 600; font-size: 11px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:checked {{
        background-color: {SETTINGS_ACCENT};
        border: 1px solid {SETTINGS_ACCENT};
        border-radius: 6px;
    }}
    QCheckBox::indicator:unchecked {{
        border: 1px solid {BORDER_MID};
        border-radius: 6px;
        background-color: {BG_WHITE};
    }}
"""

# ComboBox (generic)
STYLE_COMBO = f"""
    QComboBox {{
        background-color: {GLASS_BG_STRONG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 12px;
        padding: 6px 10px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: none;
        selection-background-color: {HOVER_BG};
        selection-color: {TEXT_BODY};
        color: {TEXT_BODY};
    }}
"""

# PageRecord combo
STYLE_RECORD_COMBO = f"""
    QComboBox, QLineEdit {{
        background-color: {GLASS_BG_STRONG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 12px;
        padding: 6px 10px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
        min-height: 26px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: none;
        selection-background-color: {HOVER_BG};
        selection-color: {TEXT_BODY};
        color: {TEXT_BODY};
    }}
"""

# PageWand combo
STYLE_WAND_COMBO = f"""
    QComboBox {{
        background-color: {GLASS_BG_STRONG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 12px;
        padding: 6px 10px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
        min-height: 32px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: none;
        selection-background-color: {HOVER_BG};
        selection-color: {TEXT_BODY};
        color: {TEXT_BODY};
    }}
"""

# PageSetting input (combo, line edit, spinbox)
STYLE_SETTING_INPUT = f"""
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {GLASS_BG_STRONG};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 12px;
        padding: 6px 10px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: none;
        selection-background-color: {SETTINGS_HOVER_BG};
        color: {TEXT_BODY};
        selection-color: {TEXT_BODY};
    }}
    QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ border: none; width: 16px; }}
"""

# Progress bar (generic, used in multiple pages)
STYLE_PROGRESS = f"""
    QProgressBar {{
        border: none;
        border-radius: 4px;
        min-height: 6px;
        max-height: 6px;
        background-color: {BORDER};
    }}
    QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 4px; }}
"""

# PageSetting progress bar
STYLE_SETTING_PROGRESS = f"""
    QProgressBar {{
        border: none;
        border-radius: 4px;
        text-align: center;
        background-color: {BORDER};
        min-height: 6px;
        max-height: 6px;
        color: {TEXT_BODY};
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 4px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# TERMINAL & CONSOLE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand terminal
STYLE_TERMINAL = f"""
    QTextEdit, QPlainTextEdit, QTextBrowser {{
        background-color: {TERM_BG};
        color: {TERM_FG};
        border: none;
        border-radius: 12px;
        padding: 12px;
        font-family: Consolas, 'Courier New', monospace;
        font-size: 11px;
    }}
"""

# PageSetting console
STYLE_CONSOLE = f"""
    QTextEdit, QPlainTextEdit, QTextBrowser {{
        background-color: {TERM_BG};
        color: {TERM_FG};
        border: none;
        border-radius: 12px;
        font-family: Consolas, 'Courier New', monospace;
        font-size: 11px;
        padding: 12px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# SCROLL AREA & OTHER CONTAINER STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageStatistics scroll area
STYLE_SCROLL_AREA = """
    QScrollArea { border: none; background-color: transparent; }
    QScrollArea > QWidget > QWidget { background: transparent; }
    QScrollBar:vertical { border: none; background: transparent; width: 10px; margin: 0px; }
    QScrollBar::handle:vertical { background: rgba(128, 128, 128, 128); border-radius: 5px; min-height: 20px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; border: none; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar:horizontal { border: none; background: transparent; height: 10px; margin: 0px; }
    QScrollBar::handle:horizontal { background: rgba(128, 128, 128, 128); border-radius: 5px; min-width: 20px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: transparent; border: none; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""

STYLE_TRANSPARENT_WIDGET = "background: transparent;"

# ────────────────────────────────────────────────────────────────────────────
# RARITY BADGE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand rarity badge (border-only, aligned with statistics)
STYLE_RARITY_BADGE_WAND = """
    QLabel {{{{
        background-color: transparent;
        color: {{color}};
        border: 2px solid {{color}};
        border-radius: 6px;
        padding: 4px 8px;
        font-weight: 900;
        font-size: 10px;
        letter-spacing: 1px;
    }}}}
"""

# PageStatistics rarity badge (colored border)
STYLE_RARITY_BADGE_STATISTICS = """
    QLabel {{
        background-color: transparent;
        color: {color};
        border: 2px solid {color};
        border-radius: 6px;
        padding: 4px 8px;
        font-weight: 900;
        font-size: 10px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# STATUS LABEL TEMPLATE
# ────────────────────────────────────────────────────────────────────────────

# Used in PageWand for connection status labels (serial, bluetooth)
# Format with .format(color=SUCCESS) or .format(color=DANGER)
STATUS_LABEL_STYLE_TEMPLATE = (
    "background: transparent; border: none; "
    "color: {color}; font-weight: 800; font-size: 11px; letter-spacing: 0.8px;"
)
STYLE_RECORD_STATUS_TEMPLATE = "color: {color}; font-weight: 800; font-size: 12px;"
STYLE_RECORD_FIELD_LABEL = f"color: {TEXT_BODY}; font-weight: 700; font-size: 11px;"
STYLE_RECORD_METRIC_VALUE = f"color: {TEXT_BODY}; font-weight: 800; font-size: 16px;"
STYLE_RECORD_CURRENT_SPELL = f"color: {ACCENT}; font-weight: 700; font-size: 11px;"
STYLE_SETTINGS_FORM_LABEL = f"color: {TEXT_BODY}; font-weight: 700; font-size: 11px;"
STYLE_SETTINGS_HINT_TEMPLATE = "color: {color}; font-size: 11px;"
STYLE_SETTINGS_SECTION_LABEL_TEMPLATE = "color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
STYLE_SETTINGS_INPUT_INVALID = (
    f"border: 2px solid {DANGER}; border-radius: 6px;"
    f" background-color: rgba(239, 68, 68, 15);"
)
STYLE_STATISTICS_INFO_LABEL = f"color: {TEXT_BODY}; font-weight: 500; font-size: 11px;"
STYLE_STATISTICS_META_LABEL = f"color: {TEXT_MUTED}; font-size: 10px;"
STYLE_STATISTICS_CURRENT_SPELL = f"color: {WAND_ACCENT}; font-weight: 700; font-size: 11px;"
STYLE_SECTION_LABEL_TEMPLATE = "color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
STYLE_STAT_LABEL = f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700;"
STYLE_HINT_LABEL_TEMPLATE = "color: {color}; font-size: 11px; font-weight: 500;"
STYLE_CARD_NAME_LABEL = f"color: {TEXT_BODY}; font-weight: 700; font-size: 12px;"
STYLE_CARD_COUNT_LABEL = f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700;"
STYLE_GRAPH_PLACEHOLDER = (
    f"background-color: {PRIMARY_LIGHT}; color: {TEXT_SECONDARY}; "
    f"border: none; border-radius: 14px;"
)
STYLE_FORM_ROW_LABEL = STYLE_SETTINGS_FORM_LABEL
STYLE_WAND_LIST_TITLE = f"color: {TEXT_BODY}; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
STYLE_WAND_SPELL_NAME = f"color: {TEXT_BODY}; font-size: 12px; font-weight: 700;"
STYLE_WAND_EMPTY_ROW_TEMPLATE = "color: {color}; font-size: 11px; font-style: italic; padding: 8px 12px;"
STYLE_WAND_FLASH_STATUS = f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700;"
STYLE_STATE_EMPTY_CARD = (
    f"background-color: {GLASS_BG}; border: none; border-radius: 18px;"
)
STYLE_STATE_EMPTY_TITLE = f"color: {TEXT_BODY}; font-size: 14px; font-weight: 700;"
STYLE_STATE_EMPTY_BODY = f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"
STYLE_STATE_ERROR_CARD = (
    f"background-color: {SURFACE_1}; border: none; border-radius: 18px;"
)
STYLE_STATE_ERROR_TITLE = f"color: {TEXT_BODY}; font-size: 14px; font-weight: 700;"
STYLE_STATE_ERROR_BODY = f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"

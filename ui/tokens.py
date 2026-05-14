"""
Consolidated design tokens for all UI pages.
Centralizes colors, sizes, stylesheet constants, and visual elements.

This module merges:
  - _STYLE_* constants from all 5 pages
  - _STATUS_STYLE template from page_wand
"""

from PyQt6.QtCore import QSize

APP_FONT_STACK = "'SF Pro Display', 'Geist Sans', 'Helvetica Neue', 'Switzer', sans-serif"
TITLE_FONT_STACK = "'Newsreader', 'Georgia', 'Times New Roman', serif"

# ════════════════════════════════════════════════════════════════════════════
# PREMIUM MINIMALIST COLOR PALETTE (Minimalist Book Redesign)
# ════════════════════════════════════════════════════════════════════════════

# Primary monochrome color
PRIMARY_COLOR = "#111111"
PRIMARY_LIGHT = "#333333"
PRIMARY_DARK = "#000000"

# Secondary accent colors
SECONDARY_COLOR = PRIMARY_COLOR
SECONDARY_LIGHT = PRIMARY_LIGHT
SECONDARY_DARK = PRIMARY_DARK

# Surface colors (Warm Paper Monochrome)
SURFACE_0 = "#FDFCFB"            # Warm Canvas / Paper
SURFACE_1 = "#FFFFFF"            # Primary Surface (Cards)
SURFACE_2 = "#F9F8F6"            # Alternative Surface (Sidebar)
SURFACE_PRIMARY = SURFACE_1
SURFACE_SECONDARY = SURFACE_0
SURFACE_TERTIARY = SURFACE_2

# Text colors
TEXT_PRIMARY = "#2F3437"         # Off-black/charcoal for body
TEXT_SECONDARY = "#787774"       # Muted gray (Lead)
TEXT_TERTIARY = "#999999"

# Border colors
BORDER_COLOR = "#EAEAEA"         # Structural Borders / Dividers
BORDER_LIGHT = "rgba(0,0,0,0.06)"

# Status/semantic colors (Desaturated Pastels)
STATUS_SUCCESS = "#EDF3EC"       # Pale Green (Text: #346538)
STATUS_SUCCESS_TEXT = "#346538"
STATUS_WARNING = "#FBF3DB"       # Pale Yellow (Text: #956400)
STATUS_WARNING_TEXT = "#956400"
STATUS_ERROR = "#FDEBEC"         # Pale Red (Text: #9F2F2D)
STATUS_ERROR_TEXT = "#9F2F2D"
STATUS_INFO = "#E1F3FE"          # Pale Blue (Text: #1F6C9F)
STATUS_INFO_TEXT = "#1F6C9F"


# Shadow colors (Ultra-diffuse, low opacity)
SHADOW_LIGHT = "rgba(0,0,0,0.02)"
SHADOW_MEDIUM = "rgba(0,0,0,0.04)"
SHADOW_DARK = "rgba(0,0,0,0.05)"

# Flat surfaces
GLASS_BG = SURFACE_1
GLASS_BG_STRONG = SURFACE_1
GLASS_BORDER = BORDER_COLOR
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
SHELL_SIDEBAR_W = 200            # Slightly wider for editorial feel
SHELL_NAV_H = 64                 # More whitespace
SHELL_BRAND_H = 100
SHELL_BRAND_ICON = QSize(32, 32)

# Home layout tokens
HOME_STATUS_H = 40
HOME_VIEWER_MIN_H = 400
HOME_ATTACH_H = 44
HOME_RIGHT_W = 340
HOME_MANAGER_DOT = 8
HOME_MODE_H = 54
HOME_VIEWER_INNER_MARGIN = 0

# ────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE MAPPING
# ────────────────────────────────────────────────────────────────────────────

# Base neutrals
BG_WHITE     = SURFACE_1
BG_LIGHT     = SURFACE_2
BG_DARK      = "#111111"
BORDER       = BORDER_COLOR
BORDER_MID   = BORDER_COLOR
TEXT_BODY    = TEXT_PRIMARY
TEXT_MUTED   = TEXT_TERTIARY

# Common accent colors
ACCENT       = MAC_ACCENT
ACCENT_DARK  = MAC_ACCENT_DARK
ACCENT_TEXT  = "#ffffff"
SUCCESS      = STATUS_SUCCESS_TEXT
DANGER       = STATUS_ERROR_TEXT
WARNING      = STATUS_WARNING_TEXT
HOVER_BG     = "#F0F0F0"

# Terminal colors
TERM_FG      = TEXT_BODY
TERM_BG      = SURFACE_2

# Graph colors
CROP_REGION  = "rgba(0, 0, 0, 0.05)"
PLOT_AX_COLOR = "#9F2F2D"        # Desaturated Red
PLOT_AY_COLOR = "#346538"        # Desaturated Green
PLOT_AZ_COLOR = "#1F6C9F"        # Desaturated Blue
PLOT_GX_COLOR = "#956400"        # Desaturated Yellow
PLOT_GY_COLOR = "#6B4C9A"        # Muted Purple
PLOT_GZ_COLOR = "#1F6C9F"
PLOT_HANDLE_HOVER_COLOR = PRIMARY_COLOR

# Rarity colors (Muted variants)
RARITY_NONE  = "#B1B1B1"
RARITY_COM   = "#346538"
RARITY_UNC   = "#1F6C9F"
RARITY_RARE  = "#6B4C9A"
RARITY_EPIC  = "#956400"

# Settings-specific accents
SETTINGS_ACCENT       = PRIMARY_COLOR
SETTINGS_ACCENT_DARK  = PRIMARY_DARK
SETTINGS_HOVER_BG     = HOVER_BG

# Wand-specific accents
WAND_ACCENT       = ACCENT

# Home page typography tokens
STYLE_HOME_SECTION_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {TEXT_BODY}; font-size: 24px; font-weight: 500; letter-spacing: -0.01em;"
STYLE_HOME_SECTION_SUBTITLE = f"color: {TEXT_MUTED}; font-weight: 500; font-size: 13px; letter-spacing: 0.02em; text-transform: uppercase;"
STYLE_HOME_MODE_LABEL = f"color: {ACCENT}; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;"
STYLE_HOME_STAT_NAME = f"color: {TEXT_BODY}; font-size: 12px; font-weight: 600;"
STYLE_HOME_STAT_VALUE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;"
STYLE_HOME_EMPTY_SPELL_TEXT = f"color: {TEXT_MUTED}; font-size: 12px; font-style: italic; padding: 4px 0;"
STYLE_HOME_OVERFLOW_TEXT = f"color: {TEXT_MUTED}; font-size: 11px; font-style: italic; padding: 2px 0;"
STYLE_HOME_MANAGER_INDICATOR = f"background-color: {ACCENT}; border-radius: 4px;"
STYLE_HOME_STATUS_TEMPLATE = (
    "QLabel {{ "
    "background-color: {bg_color}; "
    f"color: {{fg_color}}; padding: 10px 20px; font-size: 13px; "
    "font-weight: 600; border: 1px solid rgba(0,0,0,0.06); border-radius: 8px; }}"
)
STYLE_HOME_STATUS_BAR = f"""
    #HomeStatusBar {{
        background-color: {STATUS_ERROR};
        color: {STATUS_ERROR_TEXT};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.05em;
    }}
"""
STYLE_HOME_VIEWER_CARD = f"""
    #HomeViewerCard {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}
    #HomeViewerSurface {{
        background-color: {SURFACE_1};
        border: none;
        border-radius: 10px;
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
        background-color: {SURFACE_2};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        padding: 6px 14px;
        letter-spacing: 0.02em;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
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
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
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
        background-color: {BORDER_COLOR};
        border: none;
        border-radius: 2px;
        min-height: 4px;
        max-height: 4px;
        text-align: right;
    }}
    QProgressBar#HomeManagerBar::chunk {{
        background-color: {ACCENT};
        border-radius: 2px;
    }}
"""
STYLE_HOME_SPELL_BTN = f"""
    QPushButton {{
        background-color: {SURFACE_1};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        text-align: left;
        padding: 12px;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_2};
        border-color: {TEXT_SECONDARY};
    }}
"""
STYLE_HOME_MODULE_BTN = f"""
    QPushButton {{
        background-color: {SURFACE_1};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
    }}
"""
STYLE_HOME_ACTION_BTN = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        padding: 10px 20px;
    }}
    QPushButton:hover {{ background-color: {PRIMARY_LIGHT}; }}
    QPushButton:disabled {{ background-color: {BORDER_COLOR}; color: {TEXT_MUTED}; }}
"""
STYLE_HOME_ACTION_BTN_SECONDARY = f"""
    QPushButton {{
        background-color: {SURFACE_1};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        padding: 10px 20px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
    }}
    QPushButton:disabled {{ background-color: {SURFACE_0}; color: {TEXT_MUTED}; }}
"""

# ────────────────────────────────────────────────────────────────────────────
# SIZING
# ────────────────────────────────────────────────────────────────────────────

ICON          = QSize(20, 20)
STATUS_H      = 32
SPELL_BTN_H   = 48
MODULE_BTN_H  = 36
GRAPH_MIN_H   = 400
TERM_MIN_H    = 200
PROGRESS_H    = 4
RIGHT_MAX_W   = 400
BTN_H         = 40
BTN_SMALL_H   = 32
SETTINGS_BTN_H    = 36
SETTINGS_INPUT_H  = 36
LABEL_W       = 180
RECORD_GRAPH_MIN_H = 200
RECORD_LIST_MIN_H = 250
SETTING_CONSOLE_MIN_H = 250
STATISTICS_FFT_MIN_H = 360
STATISTICS_SAMPLE_LIST_MIN_H = 250
WAND_SPELL_LIST_MIN_H = 250
WAND_TERMINAL_MIN_H = 250

# ────────────────────────────────────────────────────────────────────────────
# MAIN CONTAINER STYLES (used in all pages)
# ────────────────────────────────────────────────────────────────────────────

# PageHome
STYLE_HOME_MAIN_CONTAINER = "#MainBox { border: none; background-color: transparent; }"
STYLE_RECORD_MAIN_CONTAINER = "#MainBox { border: none; background-color: transparent; }"
STYLE_WAND_MAIN_CONTAINER = "#MainBox { border: none; background-color: transparent; }"
STYLE_STATISTICS_MAIN_CONTAINER = "#MainBox { border: none; background-color: transparent; }"
STYLE_SETTING_MAIN_CONTAINER = "#MainBox { border: none; background-color: transparent; }"

# ────────────────────────────────────────────────────────────────────────────
# CONTAINER & CARD STYLES
# ────────────────────────────────────────────────────────────────────────────

# Generic card frames
STYLE_CARD = f"""
    #CardFrame {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
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
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}
    ClickableFrame:hover {{
        background-color: {SURFACE_2};
        border: 1px solid {TEXT_TERTIARY};
    }}
"""

# PageSetting card style
STYLE_SETTING_CARD = f"""
    #CardFrame {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}
"""

# PageRecord graph card style
STYLE_RECORD_GRAPH_CARD = f"""
    #CardFrame {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}
"""

# PageWand card style
STYLE_WAND_CARD = f"""
    #CardFrame {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# BUTTON STYLES
# ────────────────────────────────────────────────────────────────────────────

# Base button
STYLE_BTN_BASE = f"""
    QPushButton {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        color: {TEXT_BODY};
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
        min-width: 80px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
    }}
"""

# Specific Record buttons
STYLE_BTN_START = STYLE_HOME_ACTION_BTN
STYLE_BTN_STOP = f"""
    QPushButton {{
        background-color: {STATUS_ERROR};
        color: {STATUS_ERROR_TEXT};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        font-size: 13px;
        font-weight: 700;
        padding: 8px 16px;
    }}
    QPushButton:hover {{ background-color: #F8D7DA; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""
STYLE_BTN_SNIP = STYLE_BTN_BASE
STYLE_BTN_DANGER_OUTLINE = STYLE_BTN_STOP
STYLE_BTN_BACK = f"""
    QPushButton {{
        background-color: transparent;
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        color: {TEXT_BODY};
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_2};
    }}
"""

# Outline button (generic)
STYLE_BTN_OUTLINE = STYLE_HOME_ACTION_BTN_SECONDARY

# Primary button (generic)
STYLE_BTN_PRIMARY = STYLE_HOME_ACTION_BTN

# Small button
STYLE_BTN_SMALL = f"""
    QPushButton {{
        background-color: {SURFACE_2};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        min-height: 28px;
        max-height: 28px;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 10px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
    }}
"""

# Settings-specific buttons
STYLE_SETTING_BTN_OUTLINE = STYLE_BTN_BASE
STYLE_SETTING_BTN_PRIMARY = STYLE_BTN_PRIMARY
STYLE_SETTING_BTN_DANGER = STYLE_BTN_STOP

# PageHome spell & module buttons (legacy mappings, preferred tokens above)
STYLE_SPELL_BTN = STYLE_HOME_SPELL_BTN
STYLE_MODULE_BTN = STYLE_HOME_MODULE_BTN

# PageStatistics back button
STYLE_STATISTICS_BTN_BACK = STYLE_BTN_BACK

# ────────────────────────────────────────────────────────────────────────────
# COMPONENT STYLES (List, Checkbox, ComboBox, Input, Progress)
# ────────────────────────────────────────────────────────────────────────────

# List widget
STYLE_LIST = f"""
    QListWidget {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        outline: 0;
        color: {TEXT_BODY};
    }}
    QListWidget::item {{
        border-bottom: 1px solid {BORDER_COLOR};
        min-height: 56px;
        padding: 0 16px;
        color: {TEXT_BODY};
    }}
    QListWidget::item:last {{ border-bottom: none; }}
    QListWidget::item:selected {{
        background-color: {SURFACE_2};
        color: {PRIMARY_COLOR};
        font-weight: 700;
    }}
    QListWidget::item:hover:!selected {{ background-color: {SURFACE_0}; }}
"""

# PageRecord list
STYLE_RECORD_LIST = STYLE_LIST

# PageStatistics list
STYLE_STATISTICS_LIST = STYLE_LIST

# Checkbox (generic)
STYLE_CHECKBOX = f"""
    QCheckBox {{
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 13px;
    }}
    QCheckBox::indicator {{ width: 20px; height: 20px; }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        border-radius: 4px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
    }}
"""

# PageRecord checkbox
STYLE_RECORD_CHECKBOX = STYLE_CHECKBOX

# PageSetting checkbox
STYLE_SETTING_CHECKBOX = STYLE_CHECKBOX

# ComboBox (generic)
STYLE_COMBO = f"""
    QComboBox {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 8px 12px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 13px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        selection-background-color: {SURFACE_2};
        selection-color: {PRIMARY_COLOR};
        color: {TEXT_BODY};
    }}
"""

# PageRecord combo
STYLE_RECORD_COMBO = STYLE_COMBO

# PageWand combo
STYLE_WAND_COMBO = STYLE_COMBO

# PageSetting input (combo, line edit, spinbox)
STYLE_SETTING_INPUT = f"""
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 8px 12px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 13px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE_1};
        border: 1px solid {BORDER_COLOR};
        selection-background-color: {SURFACE_2};
        color: {TEXT_BODY};
    }}
    QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ border: none; width: 20px; }}
"""

# Progress bar
STYLE_PROGRESS = f"""
    QProgressBar {{
        border: none;
        border-radius: 2px;
        min-height: 4px;
        max-height: 4px;
        background-color: {BORDER_COLOR};
    }}
    QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 2px; }}
"""

# PageSetting progress bar
STYLE_SETTING_PROGRESS = STYLE_PROGRESS

# ────────────────────────────────────────────────────────────────────────────
# TERMINAL & CONSOLE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand terminal
STYLE_TERMINAL = f"""
    QTextEdit, QPlainTextEdit, QTextBrowser {{
        background-color: {SURFACE_2};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        padding: 16px;
        font-family: 'Geist Mono', 'SF Mono', monospace;
        font-size: 12px;
        line-height: 1.6;
    }}
"""

# PageSetting console
STYLE_CONSOLE = STYLE_TERMINAL

# ────────────────────────────────────────────────────────────────────────────
# SCROLL AREA & OTHER CONTAINER STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageStatistics scroll area
STYLE_SCROLL_AREA = """
    QScrollArea { border: none; background-color: transparent; }
    QScrollArea > QWidget > QWidget { background: transparent; }
    QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
    QScrollBar::handle:vertical { background: rgba(0, 0, 0, 0.05); border-radius: 4px; min-height: 30px; }
    QScrollBar::handle:vertical:hover { background: rgba(0, 0, 0, 0.1); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 0px; }
    QScrollBar::handle:horizontal { background: rgba(0, 0, 0, 0.05); border-radius: 4px; min-width: 30px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
"""

STYLE_TRANSPARENT_WIDGET = "background: transparent; border: none;"

# ────────────────────────────────────────────────────────────────────────────
# RARITY BADGE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand rarity badge
STYLE_RARITY_BADGE_WAND = """
    QLabel {{{{
        background-color: {{{{bg_color}}}};
        color: {{{{fg_color}}}};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 999px;
        padding: 4px 12px;
        font-weight: 700;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}}}
"""

# PageStatistics rarity badge
STYLE_RARITY_BADGE_STATISTICS = """
    QLabel {{
        background-color: {bg_color};
        color: {fg_color};
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 999px;
        padding: 4px 12px;
        font-weight: 700;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# STATUS LABEL TEMPLATE
# ────────────────────────────────────────────────────────────────────────────

STATUS_LABEL_STYLE_TEMPLATE = (
    "background: transparent; border: none; "
    "color: {color}; font-weight: 700; font-size: 12px; letter-spacing: 0.02em;"
)
STYLE_RECORD_STATUS_TEMPLATE = "color: {color}; font-weight: 700; font-size: 13px;"
STYLE_RECORD_FIELD_LABEL = f"color: {TEXT_SECONDARY}; font-weight: 600; font-size: 12px;"
STYLE_RECORD_METRIC_VALUE = f"color: {TEXT_BODY}; font-weight: 700; font-size: 18px; letter-spacing: -0.01em;"
STYLE_RECORD_CURRENT_SPELL = f"color: {ACCENT}; font-weight: 700; font-size: 12px; text-transform: uppercase;"
STYLE_SETTINGS_FORM_LABEL = f"color: {TEXT_BODY}; font-weight: 600; font-size: 13px;"
STYLE_SETTINGS_HINT_TEMPLATE = "color: {color}; font-size: 12px;"
STYLE_SETTINGS_SECTION_LABEL_TEMPLATE = "color: {color}; font-weight: 700; font-size: 14px; letter-spacing: 0.02em; text-transform: uppercase;"
STYLE_SETTINGS_INPUT_INVALID = (
    f"border: 1px solid {STATUS_ERROR_TEXT}; border-radius: 6px;"
    f" background-color: {STATUS_ERROR};"
)
STYLE_STATISTICS_INFO_LABEL = f"color: {TEXT_BODY}; font-weight: 500; font-size: 12px;"
STYLE_STATISTICS_META_LABEL = f"color: {TEXT_SECONDARY}; font-size: 11px;"
STYLE_STATISTICS_CURRENT_SPELL = f"color: {ACCENT}; font-weight: 700; font-size: 12px; text-transform: uppercase;"
STYLE_SECTION_LABEL_TEMPLATE = f"font-family: {TITLE_FONT_STACK}; color: {{color}}; font-weight: 700; font-size: 15px; letter-spacing: 0.02em; text-transform: uppercase;"
STYLE_STAT_LABEL = f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;"
STYLE_HINT_LABEL_TEMPLATE = "color: {color}; font-size: 12px; font-weight: 500;"
STYLE_CARD_NAME_LABEL = f"color: {TEXT_BODY}; font-weight: 700; font-size: 14px; letter-spacing: -0.01em;"
STYLE_CARD_COUNT_LABEL = f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
STYLE_GRAPH_PLACEHOLDER = (
    f"background-color: {SURFACE_2}; color: {TEXT_SECONDARY}; "
    f"border: 1px solid {BORDER_COLOR}; border-radius: 8px;"
)
STYLE_FORM_ROW_LABEL = STYLE_SETTINGS_FORM_LABEL
STYLE_WAND_LIST_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;"
STYLE_WAND_SPELL_NAME = f"color: {TEXT_BODY}; font-size: 14px; font-weight: 600;"
STYLE_WAND_EMPTY_ROW_TEMPLATE = "color: {color}; font-size: 12px; font-style: italic; padding: 12px 16px;"
STYLE_WAND_FLASH_STATUS = f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;"
STYLE_STATE_EMPTY_CARD = (
    f"background-color: {SURFACE_0}; border: 1px solid {BORDER_COLOR}; border-radius: 12px;"
)
STYLE_STATE_EMPTY_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {TEXT_BODY}; font-size: 18px; font-weight: 700; letter-spacing: -0.01em;"
STYLE_STATE_EMPTY_BODY = f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 500; line-height: 1.5;"
STYLE_STATE_ERROR_CARD = (
    f"background-color: {STATUS_ERROR}; border: 1px solid {BORDER_COLOR}; border-radius: 12px;"
)
STYLE_STATE_ERROR_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {STATUS_ERROR_TEXT}; font-size: 18px; font-weight: 700; letter-spacing: -0.01em;"
STYLE_STATE_ERROR_BODY = f"color: {STATUS_ERROR_TEXT}; font-size: 13px; font-weight: 500; line-height: 1.5;"

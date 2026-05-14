"""
Consolidated design tokens for all UI pages.
Centralizes colors, sizes, stylesheet constants, and visual elements.
Aligned with Industrial Brutalist & Tactical Telemetry Interface Engineering.
"""

from PyQt6.QtCore import QSize
from ui.palettes import LIGHT_PALETTE, DARK_PALETTE
from ui.color_utils import readable_text_on

# Initial default (Light)
_p = LIGHT_PALETTE

# ── Semantic Colors (Read once, components should use theme_manager for dynamic) ──
PRIMARY_COLOR = _p.PRIMARY
PRIMARY_LIGHT = _p.PRIMARY_LIGHT
PRIMARY_DARK  = _p.PRIMARY_DARK
SURFACE_0     = _p.SURFACE_SECONDARY
SURFACE_1     = _p.SURFACE_PRIMARY
SURFACE_2     = _p.SURFACE_TERTIARY
TEXT_PRIMARY  = _p.TEXT_PRIMARY
TEXT_SECONDARY = _p.TEXT_SECONDARY
TEXT_TERTIARY  = _p.TEXT_TERTIARY
TEXT_BODY      = _p.TEXT_SECONDARY  # Alias for comfort
TEXT_MUTED     = _p.TEXT_TERTIARY   # Alias for comfort
ACCENT         = _p.PRIMARY
ACCENT_TEXT    = readable_text_on(PRIMARY_COLOR, dark_text=TEXT_PRIMARY, light_text="#FFFFFF")
BG_WHITE       = _p.SURFACE_PRIMARY
BG_DARK        = _p.SURFACE_TERTIARY
SUCCESS        = _p.STATUS_SUCCESS
WARNING        = _p.STATUS_WARNING
DANGER         = _p.STATUS_ERROR
BORDER         = _p.BORDER
BORDER_COLOR  = _p.BORDER
BORDER_MID    = _p.BORDER  # Alias for comfort
HOVER_BG      = _p.HOVER_BG
SHADOW_COLOR  = _p.SHADOW_COLOR

# Rarity Colors (Legacy)
RARITY_NONE = "#94A3B8"
RARITY_COM  = "#10B981"
RARITY_UNC  = "#3B82F6"
RARITY_RARE = "#8B5CF6"
RARITY_EPIC = "#F59E0B"

# Plot Colors (Mapped to palette for consistency)
PLOT_AX_COLOR = "#FF3B30"  # Hazard Red
PLOT_AY_COLOR = "#34C759"  # Signal Green
PLOT_AZ_COLOR = "#007AFF"  # Telemetry Blue
PLOT_GX_COLOR = "#FF9500"  # Warning Orange
PLOT_GY_COLOR = "#AF52DE"  # System Purple
PLOT_GZ_COLOR = "#5856D6"  # Matrix Indigo
PLOT_HANDLE_HOVER_COLOR = "#007AFF"

# Status colors
STATUS_SUCCESS = _p.STATUS_SUCCESS
STATUS_WARNING = _p.STATUS_WARNING
STATUS_ERROR   = _p.STATUS_ERROR
STATUS_SUCCESS_TEXT = _p.STATUS_SUCCESS_TEXT
STATUS_ERROR_TEXT   = _p.STATUS_ERROR_TEXT
STATUS_WARNING_TEXT = _p.STATUS_WARNING_TEXT

# Typography - Brutalist Mono Focus
APP_FONT_STACK = "'JetBrains Mono', 'IBM Plex Mono', 'Geist Mono', 'Space Mono', monospace"
TITLE_FONT_STACK = "'Archivo Black', 'JetBrains Mono', 'Arial Black', sans-serif"

# ── Shell layout tokens ──
SHELL_SIDEBAR_W = 200
SHELL_NAV_H = 40
SHELL_BRAND_H = 64
SHELL_BRAND_ICON = QSize(24, 24)
SHELL_NAV_ICON = QSize(18, 18)

HOME_STATUS_H = 32
HOME_VIEWER_MIN_H = 500
HOME_ATTACH_H = 40
HOME_RIGHT_W = 320
HOME_MANAGER_DOT = 8
HOME_MODE_H = 44
HOME_VIEWER_INNER_MARGIN = 0

BTN_H         = 40
BTN_SMALL_H   = 30
SETTINGS_BTN_H    = 34
SETTINGS_INPUT_H  = 34
LABEL_W       = 180
RECORD_GRAPH_MIN_H = 220
RECORD_LIST_MIN_H = 260
SETTING_CONSOLE_MIN_H = 260
STATISTICS_FFT_MIN_H = 380
STATISTICS_SAMPLE_LIST_MIN_H = 260
WAND_SPELL_LIST_MIN_H = 260
WAND_TERMINAL_MIN_H = 260
TERM_MIN_H = 260

PROGRESS_H    = 10
SETTINGS_ACCENT = PRIMARY_COLOR

MARGIN_COMFORTABLE = 24
SPACING_LG = 32
SPACING_MD = 20
SPACING_SM = 16
SPACING_XS = 10

SPELL_BTN_H   = 34
RIGHT_MAX_W   = 360
CROP_REGION   = (0, 122, 255, 40)

BORDER_LIGHT  = _p.BORDER_LIGHT

# ── Component Styles (Industrial Brutalist) ──
STYLE_HOME_SECTION_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 900; letter-spacing: -0.04em; text-transform: uppercase;"
STYLE_HOME_SECTION_SUBTITLE = f"font-family: {APP_FONT_STACK}; color: {TEXT_SECONDARY}; font-weight: 700; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;"
STYLE_SECTION_LABEL_TEMPLATE = f"font-family: {TITLE_FONT_STACK}; color: {{color}}; font-weight: 900; font-size: 14px; letter-spacing: 0.05em; text-transform: uppercase;"

STYLE_HOME_STATUS_TEMPLATE = (
    "QLabel {{ "
    "background-color: {bg_color}; "
    "color: {fg_color}; padding: 8px 20px; font-family: {app_font}; font-size: 12px; "
    "font-weight: 700; border: 2px solid {fg_color}; border-radius: 0px; }}"
).replace("{app_font}", APP_FONT_STACK)

STYLE_STATE_EMPTY_TITLE = f"font-family: {TITLE_FONT_STACK}; color: {TEXT_PRIMARY}; font-size: 18px; font-weight: 900; letter-spacing: -0.02em; text-transform: uppercase;"
STYLE_STATE_EMPTY_BODY = f"font-family: {APP_FONT_STACK}; color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500; line-height: 1.6;"

STYLE_RARITY_BADGE_WAND = """
    QLabel {{
        background-color: {bg_color};
        color: {fg_color};
        border-radius: 0px;
        border: 1px solid {fg_color};
        padding: 4px 12px;
        font-weight: 800;
        font-size: 10px;
        font-family: 'JetBrains Mono';
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
"""
STYLE_RARITY_BADGE_STATISTICS = STYLE_RARITY_BADGE_WAND

# High-end Industrial Buttons (90-degree corners)
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: {ACCENT_TEXT};
        border: 1px solid {PRIMARY_DARK};
        border-radius: 0px;
        font-family: {APP_FONT_STACK};
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 12px 28px;
    }}
    QPushButton:hover {{ background-color: {PRIMARY_LIGHT}; border: 1px solid {PRIMARY_COLOR}; }}
    QPushButton:pressed {{ background-color: {PRIMARY_DARK}; padding-top: 14px; padding-left: 30px; }}
"""
STYLE_BTN_OUTLINE = f"""
    QPushButton {{ 
        background-color: transparent; 
        color: {TEXT_PRIMARY}; 
        border: 2px solid {BORDER_COLOR}; 
        border-radius: 0px; 
        font-family: {APP_FONT_STACK};
        font-size: 11px; 
        font-weight: 800; 
        padding: 12px 28px; 
        text-transform: uppercase;
    }}
    QPushButton:hover {{ background-color: {HOVER_BG}; border-color: {TEXT_PRIMARY}; }}
"""

STYLE_SCROLL_AREA = "QScrollArea { border: none; background: transparent; }"
STYLE_TRANSPARENT_WIDGET = "background: transparent;"

STYLE_RECORD_MAIN_CONTAINER = "background: transparent;"
STYLE_RECORD_GRAPH_CARD = f"background-color: {SURFACE_1}; border: 2px solid {BORDER_COLOR}; border-radius: 0px;"
STYLE_RECORD_FIELD_LABEL = f"font-family: {APP_FONT_STACK}; color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;"
STYLE_RECORD_STATUS_TEMPLATE = "font-family: {app_font}; color: {color}; font-weight: 800; font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;".replace("{app_font}", APP_FONT_STACK)
STATUS_LABEL_STYLE_TEMPLATE = STYLE_RECORD_STATUS_TEMPLATE

STYLE_BTN_BASE = f"""
    QPushButton {{ background-color: {SURFACE_2}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; font-family: {APP_FONT_STACK}; font-size: 11px; font-weight: 700; padding: 10px 20px; text-transform: uppercase; }}
    QPushButton:hover {{ background-color: {HOVER_BG}; border-color: {TEXT_PRIMARY}; }}
"""
STYLE_BTN_START = STYLE_BTN_PRIMARY
STYLE_BTN_STOP  = f"QPushButton {{ background-color: {STATUS_ERROR}; color: {STATUS_ERROR_TEXT}; border: 1px solid {STATUS_ERROR_TEXT}; border-radius: 0px; font-family: {APP_FONT_STACK}; font-size: 12px; font-weight: 800; padding: 12px 28px; text-transform: uppercase; }}"
STYLE_BTN_SNIP  = f"QPushButton {{ background-color: {STATUS_WARNING}; color: {TEXT_PRIMARY}; border: 1px solid {STATUS_WARNING_TEXT}; border-radius: 0px; font-family: {APP_FONT_STACK}; font-size: 12px; font-weight: 800; padding: 12px 28px; text-transform: uppercase; }}"
STYLE_BTN_DANGER_OUTLINE = f"QPushButton {{ background-color: transparent; color: {STATUS_ERROR_TEXT}; border: 2px solid {STATUS_ERROR_TEXT}; border-radius: 0px; font-family: {APP_FONT_STACK}; font-size: 11px; font-weight: 800; padding: 10px 20px; text-transform: uppercase; }}"
STYLE_BTN_BACK = STYLE_BTN_BASE
STYLE_BTN_SMALL = f"QPushButton {{ background-color: {SURFACE_2}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; font-family: {APP_FONT_STACK}; font-size: 10px; font-weight: 700; padding: 6px 12px; text-transform: uppercase; }}"

STYLE_RECORD_LIST = f"QListWidget {{ background-color: transparent; border: none; color: {TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; }}"
STYLE_LIST = STYLE_RECORD_LIST
STYLE_WAND_LIST_ITEM = f"QListWidget::item {{ background-color: {SURFACE_2}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; margin-bottom: 4px; padding: 12px; }}"
STYLE_RECORD_COMBO = f"QComboBox {{ background-color: {SURFACE_2}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; padding: 6px 14px; color: {TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; }}"
STYLE_RECORD_CURRENT_SPELL = f"color: {TEXT_PRIMARY}; font-family: {TITLE_FONT_STACK}; font-size: 20px; font-weight: 900; text-transform: uppercase;"
STYLE_RECORD_METRIC_VALUE = f"color: {TEXT_PRIMARY}; font-size: 26px; font-weight: 800; font-family: 'JetBrains Mono', monospace;"

STYLE_STATISTICS_CARD = f"background-color: {SURFACE_1}; border: 2px solid {BORDER_COLOR}; border-radius: 0px;"
STYLE_STATISTICS_MAIN_CONTAINER = "background: transparent;"
STYLE_STATISTICS_BTN_BACK = STYLE_BTN_BACK
STYLE_STATISTICS_LIST = STYLE_RECORD_LIST
STYLE_STATISTICS_CURRENT_SPELL = STYLE_RECORD_CURRENT_SPELL
STYLE_STATISTICS_INFO_LABEL = f"font-family: {APP_FONT_STACK}; color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"
STYLE_STATISTICS_META_LABEL = f"font-family: {APP_FONT_STACK}; color: {TEXT_TERTIARY}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;"
WAND_ACCENT = PRIMARY_COLOR

STYLE_SETTING_INPUT = STYLE_RECORD_COMBO
STYLE_SETTING_CARD = STYLE_STATISTICS_CARD
STYLE_SETTING_BTN_PRIMARY = STYLE_BTN_PRIMARY
STYLE_SETTING_BTN_DANGER = STYLE_BTN_STOP
STYLE_SETTING_BTN_OUTLINE = STYLE_BTN_OUTLINE
STYLE_SETTING_CHECKBOX = f"QCheckBox {{ color: {TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; font-size: 11px; font-weight: 600; text-transform: uppercase; }}"
STYLE_SETTING_PROGRESS = f"QProgressBar {{ background-color: {SURFACE_2}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; text-align: center; color: {TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; font-weight: 800; }}"
STYLE_PROGRESS = STYLE_SETTING_PROGRESS
STYLE_WAND_FLASH_STATUS = STYLE_RECORD_STATUS_TEMPLATE
STYLE_SETTINGS_HINT_TEMPLATE = f"font-family: {APP_FONT_STACK}; color: {{color}}; font-size: 11px; font-weight: 500; line-height: 1.5;"
STYLE_SETTINGS_INPUT_INVALID = f"border: 2px solid {STATUS_ERROR}; background-color: rgba(255, 59, 48, 0.1);"
STYLE_SETTINGS_SECTION_LABEL_TEMPLATE = STYLE_SECTION_LABEL_TEMPLATE

STYLE_CONSOLE = f"background-color: {SURFACE_0}; color: {TEXT_PRIMARY}; border: 2px solid {BORDER_COLOR}; border-radius: 0px; padding: 14px; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
STYLE_TERMINAL = STYLE_CONSOLE
STYLE_WAND_TERMINAL_CARD = STYLE_STATISTICS_CARD
STYLE_WAND_STATS_CARD = STYLE_STATISTICS_CARD
STYLE_WAND_EMPTY_ROW_TEMPLATE = f"font-family: {APP_FONT_STACK}; color: {{color}}; font-size: 11px; font-style: italic; padding: 12px; text-transform: uppercase;"
STYLE_WAND_LIST_TITLE = f"font-family: {APP_FONT_STACK}; color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em;"
STYLE_WAND_SPELL_NAME = f"font-family: {APP_FONT_STACK}; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700; text-transform: uppercase;"
STYLE_WAND_SPELL_COUNT = f"font-family: {APP_FONT_STACK}; color: {TEXT_TERTIARY}; font-size: 11px; font-weight: 800;"
STYLE_SETTINGS_FORM_LABEL = STYLE_RECORD_FIELD_LABEL
STYLE_WAND_COMBO = f"QComboBox {{ background-color: {SURFACE_2}; border: 1px solid {BORDER_COLOR}; border-radius: 0px; padding: 6px 14px; color: {TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; }}"

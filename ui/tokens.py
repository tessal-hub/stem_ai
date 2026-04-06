"""
Consolidated design tokens for all UI pages.
Centralizes colors, sizes, stylesheet constants, and visual elements.

This module merges:
  - _STYLE_* constants from all 5 pages
  - _STATUS_STYLE template from page_wand
"""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor

APP_FONT_STACK = "SF Pro Text, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"

MAC_BG = "#f5f5f7"
MAC_SURFACE = "rgba(255, 255, 255, 0.72)"
MAC_SURFACE_SOLID = "#ffffff"
MAC_SIDEBAR_BG = "rgba(242, 242, 247, 0.82)"
MAC_TOOLBAR_BG = "rgba(248, 248, 250, 0.88)"
MAC_BORDER = "rgba(60, 60, 67, 0.14)"
MAC_BORDER_STRONG = "rgba(60, 60, 67, 0.22)"
MAC_SHADOW = "rgba(0, 0, 0, 0.18)"
MAC_SHADOW_LIGHT = "rgba(0, 0, 0, 0.08)"
MAC_TEXT_PRIMARY = "#1d1d1f"
MAC_TEXT_SECONDARY = "#6e6e73"
MAC_ACCENT = "#0a84ff"
MAC_ACCENT_DARK = "#0060df"

# ────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ────────────────────────────────────────────────────────────────────────────

# Base neutrals
BG_WHITE     = MAC_SURFACE_SOLID
BG_LIGHT     = "#f5f5f7"
BG_DARK      = "#111827"
BORDER       = MAC_BORDER
BORDER_MID   = MAC_BORDER_STRONG
TEXT_BODY    = MAC_TEXT_PRIMARY
TEXT_MUTED   = MAC_TEXT_SECONDARY

# Common accent colors (used in multiple pages)
ACCENT       = MAC_ACCENT
ACCENT_DARK  = MAC_ACCENT_DARK
ACCENT_TEXT  = "#ffffff"
SUCCESS      = "#10b981"
DANGER       = "#ef4444"
DANGER_DARK  = "#dc2626"      # Darker red for hover states
WARNING      = "#f59e0b"
HOVER_BG     = "rgba(10, 132, 255, 0.10)"

# Terminal colors (used in wand page)
TERM_FG      = "#10b981"
TERM_BG      = "#0d1117"

# Graph colors (used in plotting)
GRAPH_LINE_1 = "#00d4ff"
GRAPH_LINE_2 = "#00ff88"
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
SETTINGS_HOVER_BG     = "#e0e7ff"      # Light blue hover for settings

# Wand-specific accents
WAND_ACCENT       = "#00ff88"
WAND_ACCENT_TEXT  = "#0a0a0a"

# ────────────────────────────────────────────────────────────────────────────
# SIZING
# ────────────────────────────────────────────────────────────────────────────

ICON          = QSize(18, 18)
STATUS_H      = 28
MODE_BOX_H    = 38
MODULE_BAR_H  = 40
MGR_BOX_H     = 90
SPELL_BTN_H   = 36
MODULE_BTN_H  = 28
SIM_MIN_H     = 320
GRAPH_MIN_H   = 360
TERM_MIN_H    = 140
TERM_MAX_H    = 760
PROGRESS_H    = 10
RIGHT_MAX_W   = 320
BTN_H         = 32
SETTINGS_BTN_H    = 30
SETTINGS_INPUT_H  = 28
LABEL_W       = 144

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

# PageHome wand container (3D widget box)
STYLE_WAND_CONTAINER = f"""
    #WandBox {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
"""

# Generic card frames
STYLE_CARD = f"""
    #CardFrame {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
"""

STYLE_CARD_NO_BORDER = f"""
    #CardFrame {{
        background-color: transparent;
        border: none;
    }}
"""

# PageStatistics card style (also applies to ClickableFrame)
STYLE_STATISTICS_CARD = f"""
    #CardFrame, ClickableFrame {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
    ClickableFrame:hover {{
        background-color: {BG_LIGHT};
    }}
"""

# PageSetting card style
STYLE_SETTING_CARD = f"""
    #CardFrame {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
"""

# PageRecord card style
STYLE_RECORD_CARD = f"""
    #CardFrame {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
"""

# PageRecord graph card style
STYLE_RECORD_GRAPH_CARD = f"""
    #CardFrame {{
        background-color: {BG_DARK};
        border: none;
        border-radius: 0px;
    }}
"""

# PageWand card style
STYLE_WAND_CARD = f"""
    #CardFrame {{
        background-color: {MAC_SURFACE_SOLID};
        border: none;
        border-radius: 0px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# BUTTON STYLES
# ────────────────────────────────────────────────────────────────────────────

# Base button (PageRecord)
STYLE_BTN_BASE = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        padding: 5px 10px;
        min-width: 64px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
    }}
"""

# Specific Record buttons
STYLE_BTN_START = STYLE_BTN_BASE + f" QPushButton {{ color: {SUCCESS}; }}"
STYLE_BTN_STOP  = STYLE_BTN_BASE + f" QPushButton {{ color: {DANGER}; }}"
STYLE_BTN_SNIP  = (
    STYLE_BTN_BASE +
    f" QPushButton {{ color: {ACCENT}; background-color: {HOVER_BG}; border-color: {ACCENT}; }}"
)
STYLE_BTN_BACK = STYLE_BTN_BASE + f" QPushButton {{ color: {TEXT_BODY}; }}"

# Outline button (generic, used in PageWand, PageSetting)
STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 10px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
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
        border-radius: 8px;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""

# Small button (PageWand)
STYLE_BTN_SMALL = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {TEXT_MUTED};
        border: 1px solid {BORDER_MID};
        border-radius: 5px;
        font-size: 9px;
        font-weight: bold;
        padding: 2px 8px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
"""

# Settings-specific buttons
STYLE_SETTING_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: 1px solid {MAC_BORDER};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: {SETTINGS_HOVER_BG};
        border-color: {SETTINGS_ACCENT};
        color: {SETTINGS_ACCENT};
    }}
    QPushButton:disabled {{
        opacity: 0.5;
    }}
"""

STYLE_SETTING_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {SETTINGS_ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {SETTINGS_ACCENT_DARK}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

STYLE_SETTING_BTN_DANGER = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {DANGER};
        border: 1px solid {DANGER};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {DANGER}; color: {BG_WHITE}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

# PageHome spell & module buttons
STYLE_SPELL_BTN = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: 1px solid {MAC_BORDER};
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        text-align: left;
        padding-left: 10px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        color: {ACCENT};
        border-color: {ACCENT};
    }}
"""

STYLE_MODULE_BTN = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 4px 8px;
    }}
    QPushButton:hover {{
        color: {ACCENT};
        background-color: {HOVER_BG};
        border-color: {ACCENT};
    }}
"""

# PageStatistics back button
STYLE_STATISTICS_BTN_BACK = f"""
    QPushButton {{
        background-color: {MAC_SURFACE_SOLID};
        color: {TEXT_BODY};
        border: 1px solid {MAC_BORDER};
        border-radius: 6px;
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
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 12px;
        outline: 0;
    }}
    QListWidget::item {{
        border-bottom: 1px solid {BORDER};
        min-height: 44px;
    }}
    QListWidget::item:hover {{ background-color: {HOVER_BG}; }}
"""

# PageRecord list
STYLE_RECORD_LIST = f"""
    QListWidget {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        outline: 0;
    }}
    QListWidget::item {{
        padding: 12px;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_BODY};
        font-weight: 500;
    }}
    QListWidget::item:selected {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border-radius: 6px;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {HOVER_BG};
        border-radius: 6px;
    }}
"""

# PageStatistics list
STYLE_STATISTICS_LIST = f"""
    QListWidget {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        outline: 0;
    }}
    QListWidget::item {{
        padding: 12px;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_BODY};
        font-weight: 500;
    }}
    QListWidget::item:selected {{
        background-color: {TEXT_BODY};
        color: {BG_WHITE};
        border-radius: 6px;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {HOVER_BG};
        border-radius: 6px;
    }}
"""

# Checkbox (generic)
STYLE_CHECKBOX = f"""
    QCheckBox {{
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 12px;
    }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 4px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER_MID};
        border-radius: 4px;
    }}
"""

# PageRecord checkbox
STYLE_RECORD_CHECKBOX = f"""
    QCheckBox {{ color: {TEXT_BODY}; font-weight: 600; font-size: 11px; }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 3px;
    }}
"""

# PageSetting checkbox
STYLE_SETTING_CHECKBOX = f"""
    QCheckBox {{ color: {TEXT_BODY}; font-weight: 600; font-size: 11px; }}
    QCheckBox::indicator:checked {{
        background-color: {SETTINGS_ACCENT};
        border: 1px solid {SETTINGS_ACCENT};
        border-radius: 3px;
    }}
    QCheckBox::indicator:unchecked {{
        border: 1px solid {BORDER_MID};
        border-radius: 3px;
        background-color: {BG_WHITE};
    }}
"""

# ComboBox (generic)
STYLE_COMBO = f"""
    QComboBox {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        padding: 4px 8px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; }}
"""

# PageRecord combo
STYLE_RECORD_COMBO = f"""
    QComboBox {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 11px;
        min-height: 26px;
    }}
    QComboBox::drop-down {{ border: none; }}
"""

# PageWand combo
STYLE_WAND_COMBO = f"""
    QComboBox {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 8px;
        padding: 4px 8px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; }}
"""

# PageSetting input (combo, line edit, spinbox)
STYLE_SETTING_INPUT = f"""
    QComboBox, QLineEdit, QSpinBox {{
        background-color: {MAC_SURFACE_SOLID};
        border: 1px solid {MAC_BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        selection-background-color: {SETTINGS_HOVER_BG};
        color: {TEXT_BODY};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{ border: none; width: 16px; }}
"""

# Progress bar (generic, used in multiple pages)
STYLE_PROGRESS = f"""
    QProgressBar {{
        border: 1px solid {MAC_BORDER};
        border-radius: 4px;
        text-align: center;
        color: {TEXT_BODY};
        font-weight: 600;
        font-size: 10px;
        background-color: {MAC_SURFACE_SOLID};
    }}
    QProgressBar::chunk {{ background-color: {SUCCESS}; border-radius: 3px; }}
"""

# PageSetting progress bar
STYLE_SETTING_PROGRESS = f"""
    QProgressBar {{
        border: 1px solid {MAC_BORDER};
        border-radius: 4px;
        text-align: center;
        background-color: {MAC_SURFACE_SOLID};
    }}
    QProgressBar::chunk {{
        background-color: {SUCCESS};
        border-radius: 3px;
    }}
"""

# ────────────────────────────────────────────────────────────────────────────
# TERMINAL & CONSOLE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand terminal
STYLE_TERMINAL = f"""
    QTextEdit {{
        background-color: {TERM_BG};
        color: {TERM_FG};
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 10px;
    }}
"""

# PageSetting console
STYLE_CONSOLE = """
    QTextEdit {
        background-color: #0d0d0d;
        color: #00ff88;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 10px;
        padding: 8px;
    }
"""

# ────────────────────────────────────────────────────────────────────────────
# SCROLL AREA & OTHER CONTAINER STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageStatistics scroll area
STYLE_SCROLL_AREA = f"""
    QScrollArea {{ border: none; background-color: transparent; }}
    QScrollBar:vertical {{ border: none; background: {BG_LIGHT}; width: 8px; border-radius: 4px; }}
    QScrollBar::handle:vertical {{ background: {BORDER_MID}; border-radius: 4px; }}
"""

# PageHome module bar
STYLE_MODULE_BAR = f"""
    QWidget {{
        background-color: transparent;
        border: none;
    }}
"""

STYLE_TRANSPARENT_WIDGET = "background: transparent;"

# ────────────────────────────────────────────────────────────────────────────
# RARITY BADGE STYLES
# ────────────────────────────────────────────────────────────────────────────

# PageWand rarity badge (colored background)
STYLE_RARITY_BADGE_WAND = """
    QLabel {{
        background-color: {color};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 4px 10px;
        font-weight: 900;
        font-size: 10px;
        letter-spacing: 1px;
    }}
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
STATUS_LABEL_STYLE_TEMPLATE = "color: {color}; font-weight: 800; font-size: 11px;"

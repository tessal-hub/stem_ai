"""
ui/tokens.py — Hệ thống Design Tokens trung tâm cho toàn bộ UI.

Tập trung quản lý màu sắc, kích thước, font chữ và các hằng số stylesheet.
Hỗ trợ đa ngôn ngữ (Tiếng Việt) và đảm bảo tính nhất quán của giao diện.
"""

from PyQt6.QtCore import QSize

from ui.palettes import LIGHT_PALETTE

# ── Primitive Palette ────────────────────────────────────────────────
# Do not use these directly in QSS or page code.
# Reference semantic tokens below instead.

_BLUE_500    = "#007AFF"   # Apple system blue
_GREEN_500   = "#34C759"   # Apple system green
_RED_500     = "#FF3B30"   # Apple system red
_ORANGE_500  = "#FF9500"   # Apple system orange
_YELLOW_500  = "#FFCC00"   # Apple system yellow
_INDIGO_500  = "#5856D6"   # Apple system indigo

_GRAY_50     = "#F2F2F7"   # systemBackground
_GRAY_100    = "#E5E5EA"   # opaqueSeparator
_GRAY_200    = "#C7C7CC"   # systemGray4
_GRAY_300    = "#AEAEB2"   # systemGray3
_GRAY_400    = "#8E8E93"   # systemGray
_GRAY_600    = "#3A3A3C"   # label secondary (dark)
_GRAY_900    = "#1C1C1E"   # label primary

_WHITE       = "#FFFFFF"
_BLACK       = "#000000"

# ── Semantic Color Tokens ────────────────────────────────────────────
# Background surfaces (light mode, Apple layering model)
SURFACE_0        = _GRAY_50     # outermost app background
SURFACE_1        = _WHITE       # card / grouped content background
SURFACE_2        = _GRAY_50     # secondary grouped content
SURFACE_PRIMARY  = SURFACE_1
SURFACE_SECONDARY = SURFACE_0
SURFACE_TERTIARY  = _GRAY_50

# Text hierarchy — aligned to DESIGN.md Bench (ink/body/muted) for AA contrast
TEXT_PRIMARY     = "#0f172a"    # Ink — 10px tracked caps still legible
TEXT_SECONDARY   = "#334155"    # Body — 10.35:1 on white
TEXT_TERTIARY    = "#5b6b7f"    # Muted — 5.45:1 (AA) — for hints/status, not placeholder
TEXT_MUTED       = "#5b6b7f"
TEXT_BODY        = "#0f172a"

# Interactive accent — calibrated blue (DESIGN.md / lab_style)
PRIMARY_COLOR    = "#0668d1"    # 5.37:1 on white
PRIMARY_LIGHT    = "rgba(10, 122, 255, 0.07)"
PRIMARY_DARK     = "#0557b0"

ACCENT           = PRIMARY_COLOR
ACCENT_DARK      = PRIMARY_DARK
ACCENT_TEXT      = _WHITE

# Semantic status — calibrated to DESIGN.md / WCAG AA (≥4.5:1 on white)
SUCCESS          = "#1e7a46"   # 5.35:1 on white
DANGER           = "#dc2626"   # 4.54:1 on white
WARNING          = "#b45309"   # 4.56:1 on white

STATUS_SUCCESS   = "#1e7a46"
STATUS_WARNING   = "#b45309"
STATUS_ERROR     = "#dc2626"

# Borders — tonal ink-based (DESIGN.md)
BORDER_COLOR     = "#e4e9f0"
BORDER_LIGHT     = "rgba(15, 23, 42, 0.06)"
BORDER_MID       = "#cdd6e1"

# Fill colors — tonal sunk layer (DESIGN.md)
FILL_PRIMARY     = "#f1f5f9"
FILL_SECONDARY   = "rgba(15, 23, 42, 0.06)"
FILL_TERTIARY    = "rgba(15, 23, 42, 0.04)"

# Surface states — bench layering
HOVER_BG         = "rgba(10, 122, 255, 0.07)"
BG_WHITE         = _WHITE
BG_LIGHT         = "#f6f7f9"
BG_DARK          = "#16181d"   # terminal dark (DESIGN.md)

# Legacy aliases — keep these pointing to new semantic tokens
# (existing page files import these names)
MAC_BG                = SURFACE_0
MAC_SURFACE_SOLID     = SURFACE_1
MAC_SIDEBAR_BG        = SURFACE_0
MAC_TOOLBAR_BG        = SURFACE_1
MAC_BORDER            = BORDER_COLOR
MAC_BORDER_STRONG     = BORDER_MID
MAC_TEXT_PRIMARY      = TEXT_PRIMARY
MAC_TEXT_SECONDARY    = TEXT_SECONDARY
MAC_ACCENT            = PRIMARY_COLOR
MAC_ACCENT_DARK       = PRIMARY_DARK
SECONDARY_COLOR       = PRIMARY_COLOR
SECONDARY_LIGHT       = PRIMARY_LIGHT
SECONDARY_DARK        = PRIMARY_DARK
GLASS_BG              = SURFACE_1
GLASS_BG_STRONG       = SURFACE_0
GLASS_BORDER          = BORDER_COLOR
GLASS_EDGE            = BORDER_LIGHT
SHADOW_LIGHT          = "transparent"
SHADOW_MEDIUM         = "transparent"
SHADOW_DARK           = "transparent"
BORDER                = BORDER_COLOR
TERM_FG               = "#d7dde6"    # DESIGN.md terminal_fg
TERM_BG               = BG_DARK

SETTINGS_ACCENT       = PRIMARY_COLOR
SETTINGS_ACCENT_DARK  = PRIMARY_DARK
SETTINGS_HOVER_BG     = PRIMARY_LIGHT

WAND_ACCENT           = PRIMARY_COLOR

# ── Typography ─────────────────────────────────────────────────────────────
APP_FONT_STACK = "'Geist', 'Plus Jakarta Sans', 'Be Vietnam Pro', 'SF Pro Display', 'Segoe UI', sans-serif"
TITLE_FONT_STACK = "'PP Editorial New', 'Clash Display', 'Geist', 'Be Vietnam Pro', sans-serif"
MONO_FONT_STACK = "'JetBrains Mono', 'SF Mono', 'Cascadia Code', monospace"

# ── Geometry & Border Radius — aligned to DESIGN.md / lab_style (6/8/10/999)
RADIUS_XS   = 6    # checkboxes, small tags
RADIUS_SM   = 6    # chips (lab RADIUS_SM)
RADIUS_MD   = 8    # buttons, inputs (lab RADIUS_MD)
RADIUS_LG   = 10   # standard cards (lab RADIUS_LG)
RADIUS_XL   = 10   # large hero cards — capped at 10 per Do's
RADIUS_FULL = 999  # pill shape

RADIUS_CARD = f"{RADIUS_LG}px"
RADIUS_BUTTON = f"{RADIUS_SM}px"
RADIUS_INPUT = f"{RADIUS_SM}px"
RADIUS_PILL = "999px"

CROP_REGION = (0, 122, 255, 40)

# ── Spacing & Margins ──────────────────────────────────────────────────────
SPACING_XS = 8
SPACING_SM = 12
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32
SPACING_XXL = 48

MARGIN_COMPACT = 12
MARGIN_STANDARD = 16
MARGIN_COMFORTABLE = 24
MARGIN_SPACIOUS = 32
MARGIN_LUXURIOUS = 48

SPACE_PAGE = 24
SPACE_CARD_PADDING = 20
SPACE_SECTION_GAP = 16
SPACE_ELEMENT_GAP = 12
SPACE_TINY = 8

# ── Dimensions — breathable, touch-aware
SHELL_SIDEBAR_W = 220
SHELL_NAV_H = 48
SHELL_BRAND_H = 72
SHELL_BRAND_ICON = QSize(28, 28)
SHELL_NAV_ICON = QSize(20, 20)

BTN_H = 36            # touch min 36 (44 ideal — use padding for icon-only)
BTN_SMALL_H = 32
SETTINGS_BTN_H = 36
SETTINGS_INPUT_H = 36
SPELL_BTN_H = 36
PROGRESS_H = 6
LABEL_W = 180

RECORD_GRAPH_MIN_H = 220
RECORD_LIST_MIN_H = 260
SETTING_CONSOLE_MIN_H = 260
STATISTICS_FFT_MIN_H = 380
STATISTICS_SAMPLE_LIST_MIN_H = 260
WAND_SPELL_LIST_MIN_H = 260
WAND_TERMINAL_MIN_H = 260
TERM_MIN_H = 260

RIGHT_MAX_W = 420
RIGHT_MIN_W = 320

# ── Colors for Plotting (IMU) — all ≥3:1 on white (WCAG 1.4.11 chart lines) ──
PLOT_AX_COLOR = "#c2417a"
PLOT_AY_COLOR = "#2563eb"
PLOT_AZ_COLOR = "#0f766e"
PLOT_GX_COLOR = "#b45309"
PLOT_GY_COLOR = "#7c3aed"
PLOT_GZ_COLOR = "#4d7c0f"
PLOT_HANDLE_HOVER_COLOR = "#5b7fc7"


# ── Legacy Constants & QSS ───────────────────────────────────────────────
DANGER_TEXT = "#FFFFFF"
SHADOW_COLOR = "transparent"

CARD_RADIUS = RADIUS_CARD
BTN_RADIUS = RADIUS_BUTTON
INPUT_RADIUS = RADIUS_INPUT
CARD_INNER_RADIUS = f"{RADIUS_MD}px"
CARD_OUTER_RADIUS = RADIUS_CARD
V_SURFACE_DEFAULT = SURFACE_0
V_SURFACE_RAISED = SURFACE_1

BADGE_RADIUS = "999px"
CARD_BEZEL = 4

RARITY_NONE = "#94A3B8"
RARITY_COM = "#10B981"
RARITY_UNC = "#3B82F6"
RARITY_RARE = "#8B5CF6"
RARITY_EPIC = "#F59E0B"

MARGIN_COMFORTABLE = SPACE_PAGE
SPACING_LG = SPACE_PAGE
SPACING_MD = SPACE_SECTION_GAP
SPACING_SM = SPACE_ELEMENT_GAP
SPACING_XS = SPACE_TINY

SPACE_4 = 4
SPACE_8 = 8
SPACE_12 = 12
SPACE_16 = 16
SPACE_24 = 24
SPACE_32 = 32

STYLE_SCROLL_AREA = ""
STYLE_TRANSPARENT_WIDGET = ""
STYLE_HOME_SECTION_TITLE = ""
STYLE_HOME_SECTION_SUBTITLE = ""
STYLE_SECTION_LABEL_TEMPLATE = ""
STYLE_STATE_EMPTY_TITLE = ""
STYLE_STATE_EMPTY_BODY = ""

STYLE_PAGE_MAIN_CONTAINER = f"background-color: {SURFACE_0};"
STYLE_RECORD_MAIN_CONTAINER = STYLE_PAGE_MAIN_CONTAINER
STYLE_WAND_MAIN_CONTAINER = STYLE_PAGE_MAIN_CONTAINER
STYLE_HOME_MAIN_CONTAINER = STYLE_PAGE_MAIN_CONTAINER
STYLE_STATISTICS_MAIN_CONTAINER = STYLE_PAGE_MAIN_CONTAINER
STYLE_SETTING_MAIN_CONTAINER = STYLE_PAGE_MAIN_CONTAINER

STYLE_BTN_PRIMARY = f"background-color: {PRIMARY_COLOR}; color: {ACCENT_TEXT}; border-radius: {RADIUS_SM}px; font-weight: 600;"
STYLE_BTN_START = STYLE_BTN_PRIMARY

STYLE_BTN_BASE = f"background-color: rgba(6, 104, 209, 0.10); color: {PRIMARY_COLOR}; border-radius: {RADIUS_SM}px; font-weight: 600;"
STYLE_BTN_STOP = f"background-color: rgba(220, 38, 38, 0.10); color: #b91c1c; border-radius: {RADIUS_SM}px;"
STYLE_BTN_DANGER_OUTLINE = STYLE_BTN_STOP

STYLE_BTN_OUTLINE = f"background-color: {FILL_TERTIARY}; color: {TEXT_SECONDARY}; border-radius: {RADIUS_SM}px;"
STYLE_BTN_SNIP = STYLE_BTN_OUTLINE
STYLE_BTN_BACK = STYLE_BTN_BASE
STYLE_BTN_SMALL = f"border-radius: {RADIUS_SM}px;"

STYLE_CARD = f"background-color: {SURFACE_1}; border: 1px solid {BORDER_COLOR}; border-radius: {RADIUS_LG}px;"
STYLE_RECORD_GRAPH_CARD = STYLE_CARD
STYLE_STATISTICS_CARD = STYLE_CARD
STYLE_SETTING_CARD = STYLE_CARD
STYLE_WAND_TERMINAL_CARD = STYLE_CARD
STYLE_WAND_STATS_CARD = STYLE_CARD

STYLE_RECORD_COMBO = f"background-color: {SURFACE_0}; border: none; border-radius: {RADIUS_SM}px;"
STYLE_WAND_COMBO = STYLE_RECORD_COMBO
STYLE_SETTING_INPUT = STYLE_RECORD_COMBO

STYLE_RECORD_LIST = ""
STYLE_STATISTICS_LIST = STYLE_RECORD_LIST

STYLE_RECORD_FIELD_LABEL = ""
STYLE_RECORD_CURRENT_SPELL = ""
STYLE_RECORD_METRIC_VALUE = ""
STYLE_STATISTICS_BTN_BACK = ""
STYLE_STATISTICS_CURRENT_SPELL = ""
STYLE_STATISTICS_INFO_LABEL = ""
STYLE_STATISTICS_META_LABEL = ""
STYLE_SETTING_BTN_OUTLINE = STYLE_BTN_OUTLINE
STYLE_SETTING_BTN_PRIMARY = STYLE_BTN_PRIMARY
STYLE_SETTING_BTN_DANGER = STYLE_BTN_STOP
STYLE_SETTING_CHECKBOX = ""
STYLE_SETTING_PROGRESS = ""
STYLE_SETTINGS_FORM_LABEL = ""
STYLE_SETTINGS_INPUT_INVALID = ""
STYLE_SETTINGS_SECTION_LABEL_TEMPLATE = ""
STYLE_PROGRESS = ""
STYLE_WAND_LIST_TITLE = ""
STYLE_WAND_SPELL_NAME = ""
STYLE_WAND_SPELL_COUNT = ""
STYLE_CONSOLE = f"background-color: {TERM_BG}; color: {TERM_FG};"
STYLE_TERMINAL = f"background-color: {TERM_BG}; color: {TERM_FG}; border: none;"

STYLE_RECORD_STATUS_TEMPLATE = "font-family: {app_font}; color: {color}; font-weight: 600; font-size: 12px;".replace(
    "{app_font}", APP_FONT_STACK)
STATUS_LABEL_STYLE_TEMPLATE = STYLE_RECORD_STATUS_TEMPLATE
STYLE_WAND_FLASH_STATUS = STYLE_RECORD_STATUS_TEMPLATE
STYLE_SETTINGS_HINT_TEMPLATE = "font-family: 'Geist', sans-serif; color: {color}; font-size: 11px; line-height: 1.5;"
STYLE_WAND_EMPTY_ROW_TEMPLATE = "font-family: 'Geist', sans-serif; color: {color}; font-size: 11px; font-style: italic; padding: 12px;"

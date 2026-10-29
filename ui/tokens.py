"""
ui/tokens.py — Hệ thống Design Tokens trung tâm cho toàn bộ UI.

Tập trung quản lý màu sắc, kích thước, font chữ và các hằng số stylesheet.
Hỗ trợ đa ngôn ngữ (Tiếng Việt) và đảm bảo tính nhất quán của giao diện.
"""

from PyQt6.QtCore import QSize

from ui.palettes import LIGHT_PALETTE

# ── Primitive Palette (Material You M3 Baseline) ──────────────────────────
# Do not use these directly in QSS or page code.
# Reference semantic tokens below instead.

_M3_PRIMARY         = "#4E58A9"   # M3 Primary (Indigo)
_M3_PRIMARY_CONTAIN = "#DFE0FF"   # M3 Primary Container
_M3_ON_PRIMARY_CONT = "#0A1365"   # M3 On-Primary Container
_M3_SUCCESS         = "#1A6C39"   # M3 Success
_M3_SUCCESS_CONTAIN = "#A5F5B4"   # M3 Success Container
_M3_ERROR           = "#BA1A1A"   # M3 Error
_M3_ERROR_CONTAIN   = "#FFDAD6"   # M3 Error Container
_M3_WARNING         = "#875200"   # M3 Warning
_M3_WARNING_CONTAIN = "#FFDDB8"   # M3 Warning Container

_M3_SURFACE         = "#FAF8FD"   # M3 Surface Canvas
_M3_SURFACE_LOW     = "#F5F2FA"   # M3 Surface Container Low
_M3_SURFACE_CONT    = "#EFEBF4"   # M3 Surface Container
_M3_SURFACE_HIGH    = "#E9E6EE"   # M3 Surface Container High
_M3_SURFACE_HIGHEST = "#E3DFE8"   # M3 Surface Container Highest / Divider
_M3_OUTLINE         = "#71717A"   # M3 Outline / Muted (WCAG AA)
_M3_OUTLINE_VARIANT = "#CAC4D0"   # M3 Outline Variant

_M3_ON_SURFACE      = "#1B1B21"   # M3 On-Surface (Ink)
_M3_ON_SURF_VARIANT = "#46464F"   # M3 On-Surface Variant (Body)

_WHITE              = "#FFFFFF"
_BLACK              = "#000000"

# ── Semantic Color Tokens ────────────────────────────────────────────
# ── Semantic Color Tokens (Material You M3) ──────────────────────────
# Background surfaces (M3 Tonal Layering)
SURFACE_0        = LIGHT_PALETTE.SURFACE_SECONDARY  # M3 Surface (#FAF8FD)
SURFACE_1        = LIGHT_PALETTE.SURFACE_PRIMARY    # M3 Surface Container Lowest (#FFFFFF)
SURFACE_2        = LIGHT_PALETTE.SURFACE_TERTIARY   # M3 Surface Container (#EFEBF4)
SURFACE_PRIMARY  = SURFACE_1
SURFACE_SECONDARY = SURFACE_0
SURFACE_TERTIARY  = SURFACE_2

# Text hierarchy — M3 On-Surface & On-Surface Variant (high contrast, WCAG AAA/AA)
TEXT_PRIMARY     = LIGHT_PALETTE.TEXT_PRIMARY       # M3 On-Surface (#1B1B21, 16.2:1)
TEXT_SECONDARY   = LIGHT_PALETTE.TEXT_SECONDARY     # M3 On-Surface Variant (#46464F, 8.5:1)
TEXT_TERTIARY    = LIGHT_PALETTE.TEXT_TERTIARY      # M3 Outline / Muted (#767680, 4.8:1)
TEXT_MUTED       = TEXT_TERTIARY
TEXT_BODY        = TEXT_PRIMARY

# Interactive accent — Material 3 Baseline Tech Indigo
PRIMARY_COLOR    = LIGHT_PALETTE.PRIMARY            # #4E58A9 (5.7:1 on white)
PRIMARY_LIGHT    = LIGHT_PALETTE.PRIMARY_LIGHT      # #DFE0FF (M3 Primary Container)
PRIMARY_DARK     = LIGHT_PALETTE.PRIMARY_DARK       # #38428B (Pressed / Active)

ACCENT           = PRIMARY_COLOR
ACCENT_DARK      = PRIMARY_DARK
ACCENT_TEXT      = _WHITE

# Semantic status — M3 semantic tokens
SUCCESS          = LIGHT_PALETTE.STATUS_SUCCESS     # #1A6C39
DANGER           = LIGHT_PALETTE.STATUS_ERROR       # #BA1A1A
WARNING          = LIGHT_PALETTE.STATUS_WARNING     # #875200

STATUS_SUCCESS   = SUCCESS
STATUS_WARNING   = WARNING
STATUS_ERROR     = DANGER

# Borders — M3 Outline Variant & Dividers
BORDER_COLOR     = LIGHT_PALETTE.BORDER             # #E3DFE8
BORDER_LIGHT     = LIGHT_PALETTE.BORDER_LIGHT       # #CAC4D0
BORDER_MID       = LIGHT_PALETTE.BORDER_LIGHT       # #CAC4D0

# Fill colors — M3 Surface Containers
FILL_PRIMARY     = LIGHT_PALETTE.SURFACE_TERTIARY   # #EFEBF4
FILL_SECONDARY   = "rgba(78, 88, 169, 0.08)"        # 8% Primary State Layer
FILL_TERTIARY    = "rgba(78, 88, 169, 0.05)"

# Surface states
HOVER_BG         = LIGHT_PALETTE.HOVER_BG
BG_WHITE         = _WHITE
BG_LIGHT         = LIGHT_PALETTE.SURFACE_SECONDARY
BG_DARK          = LIGHT_PALETTE.TERM_BG            # #191C20

# Legacy aliases — keep these pointing to new semantic tokens
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
TERM_FG               = LIGHT_PALETTE.TERM_FG
TERM_BG               = BG_DARK

SETTINGS_ACCENT       = PRIMARY_COLOR
SETTINGS_ACCENT_DARK  = PRIMARY_DARK
SETTINGS_HOVER_BG     = PRIMARY_LIGHT

WAND_ACCENT           = PRIMARY_COLOR

# ── Typography (Material You M3) ──────────────────────────────────────────
APP_FONT_STACK = "'Segoe UI', 'Google Sans', 'Roboto', 'Plus Jakarta Sans', 'Be Vietnam Pro', sans-serif"
TITLE_FONT_STACK = "'Segoe UI', 'Google Sans', 'Roboto', 'Plus Jakarta Sans', 'Be Vietnam Pro', sans-serif"
MONO_FONT_STACK = "'Cascadia Code', 'JetBrains Mono', 'Roboto Mono', Consolas, monospace"

# ── Geometry & Border Radius (Material You M3 Shape Scale) ───────────────
# Spec: extra-small 4 / small 8 / medium 12 / large 16 / extra-large 28 / full
RADIUS_XS   = 4    # tooltips, tags, dense indicators
RADIUS_SM   = 8    # chips, text inputs, menus
RADIUS_MD   = 12   # compact cards, dialog elements
RADIUS_LG   = 16   # standard M3 cards & surface containers
RADIUS_XL   = 28   # large hero cards, modal dialogs (M3 extra-large)
RADIUS_FULL = 16   # M3 pill (stadium) — Qt discards corners if radius > h/2, so ≤16 works for ≥32px buttons
RADIUS_BADGE = 11  # M3 pill badge for status labels (~22-24px height)

RADIUS_CARD = f"{RADIUS_LG}px"
RADIUS_BUTTON = f"{RADIUS_FULL}px"
RADIUS_INPUT = f"{RADIUS_SM}px"
RADIUS_PILL = f"{RADIUS_FULL}px"

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

BADGE_RADIUS = f"{RADIUS_BADGE}px"
CARD_BEZEL = 4

# Material You M3 Tonal Containers & On-Container text for rarity badges
RARITY_NONE = "#EFEBF4"
RARITY_COM = "#DFE0FF"
RARITY_UNC = "#E8DEF8"
RARITY_RARE = "#A5F5B4"
RARITY_EPIC = "#FFDDB8"

RARITY_TEXT_NONE = "#46464F"
RARITY_TEXT_COM = "#0A1365"
RARITY_TEXT_UNC = "#1D192B"
RARITY_TEXT_RARE = "#0A3B1C"
RARITY_TEXT_EPIC = "#613800"

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

STYLE_BTN_PRIMARY = f"background-color: {PRIMARY_COLOR}; color: {ACCENT_TEXT}; border-radius: {RADIUS_FULL}px; font-weight: 600; padding: 8px 20px; border: none;"
STYLE_BTN_START = STYLE_BTN_PRIMARY

STYLE_BTN_BASE = f"background-color: {PRIMARY_LIGHT}; color: #0A1365; border-radius: {RADIUS_FULL}px; font-weight: 600; padding: 8px 18px; border: none;"
STYLE_BTN_STOP = f"background-color: #FFDAD6; color: #93000A; border-radius: {RADIUS_FULL}px; font-weight: 600; padding: 8px 18px; border: none;"
STYLE_BTN_DANGER_OUTLINE = f"background-color: transparent; border: 1px solid #BA1A1A; color: #BA1A1A; border-radius: {RADIUS_FULL}px; font-weight: 600; padding: 7px 18px;"

STYLE_BTN_OUTLINE = f"background-color: transparent; border: 1px solid #767680; color: {PRIMARY_COLOR}; border-radius: {RADIUS_FULL}px; font-weight: 600; padding: 7px 18px;"
STYLE_BTN_SNIP = STYLE_BTN_OUTLINE
STYLE_BTN_BACK = STYLE_BTN_BASE
STYLE_BTN_SMALL = f"border-radius: {RADIUS_FULL}px; padding: 4px 12px;"

STYLE_CARD = f"background-color: {SURFACE_1}; border: 1px solid {BORDER_COLOR}; border-radius: {RADIUS_LG}px;"
STYLE_RECORD_GRAPH_CARD = STYLE_CARD
STYLE_STATISTICS_CARD = STYLE_CARD
STYLE_SETTING_CARD = STYLE_CARD
STYLE_WAND_TERMINAL_CARD = STYLE_CARD
STYLE_WAND_STATS_CARD = STYLE_CARD

STYLE_RECORD_COMBO = f"background-color: {SURFACE_TERTIARY}; border: 1px solid {BORDER_LIGHT}; border-radius: {RADIUS_SM}px; padding: 6px 12px; color: {TEXT_PRIMARY};"
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
STYLE_SETTINGS_HINT_TEMPLATE = f"font-family: {APP_FONT_STACK}; color: {{color}}; font-size: 11px; line-height: 1.5;"
STYLE_WAND_EMPTY_ROW_TEMPLATE = f"font-family: {APP_FONT_STACK}; color: {{color}}; font-size: 11px; font-style: italic; padding: 12px;"

"""
Common design tokens for UI pages across the application.
Centralizes colors, sizes, and other visual constants used in multiple pages.
"""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor

# ── Common Color Palette ─────────────────────────────────────────────────────
# These colors are shared across multiple UI pages for consistency

# Base neutrals
BG_WHITE     = "#ffffff"
BG_LIGHT     = "#f3f4f6"      # Slightly darker light gray for contrast
BG_DARK      = "#111827"
BORDER       = "#e5e7eb"
BORDER_MID   = "#d1d5db"
TEXT_BODY    = "#1f2937"
TEXT_MUTED   = "#6b7280"

# Common accent colors (used in multiple pages)
ACCENT       = "#ff3366"      # Pink vibrant accent
ACCENT_DARK  = "#e62e5c"      # Darker pink for hover states
ACCENT_TEXT  = "#ffffff"
SUCCESS      = "#10b981"
DANGER       = "#ef4444"
DANGER_DARK  = "#dc2626"      # Darker red for hover states
WARNING      = "#f59e0b"
HOVER_BG     = "#fce7ec"      # Light pink hover

# Terminal colors (used in wand page)
TERM_FG      = "#10b981"
TERM_BG      = "#0d1117"

# Graph colors (used in plotting)
GRAPH_LINE_1 = "#00d4ff"
GRAPH_LINE_2 = "#00ff88"
CROP_REGION  = "#ff336644"

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

# ── Common Sizing ────────────────────────────────────────────────────────────
ICON          = QSize(18, 18)
STATUS_H      = 32
MODE_BOX_H    = 44
MODULE_BAR_H  = 48
MGR_BOX_H     = 100
SPELL_BTN_H   = 44
MODULE_BTN_H  = 32
SIM_MIN_H     = 340
GRAPH_MIN_H   = 400
TERM_MIN_H    = 160
TERM_MAX_H    = 800
PROGRESS_H    = 12
RIGHT_MAX_W   = 300
BTN_H         = 44          # Standard button height
SETTINGS_BTN_H    = 36      # Settings page button height
SETTINGS_INPUT_H  = 32      # Settings page input height
LABEL_W       = 130         # Standard label width
"""
Design tokens for consistent UI styling across the application.
Centralizes colors, sizes, and other visual constants.
"""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor

# ── Layout & Sizing ──────────────────────────────────────────────────────────
TOPBAR_H         = 48          # total topbar height (px)
TAB_TOP_PAD      = 8           # gap above tabs — topbar shows dark bg here
ACTIVE_TAB_H     = TOPBAR_H - TAB_TOP_PAD   # = 40 — fills flush to bottom
INACTIVE_TAB_H   = 32          # shorter: sits "behind" the page edge

ICON_SZ          = QSize(18, 18)
ANIM_MS          = 200

# ── Color Palette ────────────────────────────────────────────────────────────
# Base colors
C_PAGE_BG        = "#ffffff"   # MUST match page/container background
C_TOPBAR_BG      = "#1a1d23"
C_BORDER         = "#e5e7eb"   # topbar bottom border AND active tab side borders
C_INACTIVE_BG    = "#252830"
C_INACTIVE_BDR   = "#373c47"
C_INACTIVE_TEXT  = "#8b919d"
C_ACTIVE_TEXT    = "#111827"
C_ICON_INACTIVE  = QColor("#8b919d")
C_ICON_ACTIVE    = QColor("#111827")

# Accent colors for tabs (matching MENUS definition)
TAB_ACCENTS = {
    "Home":       "#00d4ff",
    "Record":     "#ff3366",
    "Statistics": "#00ff88",
    "Wand":       "#ffaa00",
    "Setting":    "#8b5cf6",
}

# Fallback emojis for when SVG icons are not found
TAB_FALLBACKS = {
    "Home": "⌂", "Record": "●", "Statistics": "≋",
    "Wand": "✦",  "Setting": "⚙",
}
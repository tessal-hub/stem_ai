"""
ui/palettes.py — High-end color palette definitions for Vanguard Studio.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Palette:
    PRIMARY: str
    PRIMARY_LIGHT: str
    PRIMARY_DARK: str
    
    SURFACE_PRIMARY: str   # Pure high-contrast (White/Deep Black)
    SURFACE_SECONDARY: str # Background canvas (Cream/Obsidian)
    SURFACE_TERTIARY: str  # Staggered paper/card depth
    
    TEXT_PRIMARY: str      # Pure ink
    TEXT_SECONDARY: str    # Lead/Muted
    TEXT_TERTIARY: str     # Ghost
    
    BORDER: str
    BORDER_LIGHT: str
    
    STATUS_SUCCESS: str
    STATUS_WARNING: str
    STATUS_ERROR: str
    STATUS_SUCCESS_TEXT: str
    STATUS_ERROR_TEXT: str
    STATUS_WARNING_TEXT: str
    
    HOVER_BG: str
    TERM_BG: str
    TERM_FG: str
    
    GLASS_BG: str
    GLASS_BG_STRONG: str
    GLASS_EDGE: str
    
    SHADOW_COLOR: str

# Vanguard Editorial Luxury (Light)
LIGHT_PALETTE = Palette(
    PRIMARY="#1A1918",
    PRIMARY_LIGHT="#3D3C3A",
    PRIMARY_DARK="#000000",
    
    SURFACE_PRIMARY="#FFFFFF",
    SURFACE_SECONDARY="#FDFBF7",
    SURFACE_TERTIARY="#F9F7F2",
    
    TEXT_PRIMARY="#1A1918",
    TEXT_SECONDARY="#6B6A67",
    TEXT_TERTIARY="#72716D",
    
    BORDER="rgba(26, 25, 24, 0.08)",
    BORDER_LIGHT="rgba(26, 25, 24, 0.04)",
    
    STATUS_SUCCESS="#EDF3EC",
    STATUS_WARNING="#FBF3DB",
    STATUS_ERROR="#FDEBEC",
    STATUS_SUCCESS_TEXT="#346538",
    STATUS_ERROR_TEXT="#9F2F2D",
    STATUS_WARNING_TEXT="#956400",
    
    HOVER_BG="rgba(26, 25, 24, 0.05)",
    TERM_BG="#F9F7F2",
    TERM_FG="#1A1918",
    
    GLASS_BG="rgba(255, 255, 255, 0.7)",
    GLASS_BG_STRONG="rgba(255, 255, 255, 0.9)",
    GLASS_EDGE="rgba(0, 0, 0, 0.05)",
    
    SHADOW_COLOR="rgba(15, 23, 42, 0.12)"
)

# Vanguard Obsidian (Dark)
DARK_PALETTE = Palette(
    PRIMARY="#EAEAEA",
    PRIMARY_LIGHT="#FFFFFF",
    PRIMARY_DARK="#A1A1AA",
    
    SURFACE_PRIMARY="#050505",    # Deep Black
    SURFACE_SECONDARY="#09090B",  # Obsidian
    SURFACE_TERTIARY="#121214",   # Depth
    
    TEXT_PRIMARY="#EAEAEA",
    TEXT_SECONDARY="#A1A1AA",
    TEXT_TERTIARY="#7D7D86",
    
    BORDER="rgba(255, 255, 255, 0.1)",
    BORDER_LIGHT="rgba(255, 255, 255, 0.05)",
    
    STATUS_SUCCESS="#064E3B",
    STATUS_WARNING="#78350F",
    STATUS_ERROR="#7F1D1D",
    STATUS_SUCCESS_TEXT="#34D399",
    STATUS_ERROR_TEXT="#F87171",
    STATUS_WARNING_TEXT="#F59E0B",
    
    HOVER_BG="rgba(255, 255, 255, 0.08)",
    TERM_BG="#050505",
    TERM_FG="#EAEAEA",
    
    GLASS_BG="rgba(9, 9, 11, 0.7)",
    GLASS_BG_STRONG="rgba(5, 5, 5, 0.9)",
    GLASS_EDGE="rgba(255, 255, 255, 0.1)",
    
    SHADOW_COLOR="rgba(0, 0, 0, 0.4)"
)

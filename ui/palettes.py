"""
ui/palettes.py — Color palette definitions for Light and Dark themes.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Palette:
    PRIMARY: str
    PRIMARY_LIGHT: str
    PRIMARY_DARK: str
    
    SURFACE_PRIMARY: str
    SURFACE_SECONDARY: str
    SURFACE_TERTIARY: str
    
    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_TERTIARY: str
    
    BORDER: str
    BORDER_LIGHT: str
    
    STATUS_SUCCESS: str
    STATUS_WARNING: str
    STATUS_ERROR: str
    
    HOVER_BG: str
    TERM_BG: str
    TERM_FG: str
    
    GLASS_BG: str
    GLASS_BG_STRONG: str
    GLASS_EDGE: str

LIGHT_PALETTE = Palette(
    PRIMARY="#2f3137",
    PRIMARY_LIGHT="#ececef",
    PRIMARY_DARK="#1f2024",
    
    SURFACE_PRIMARY="#ffffff",
    SURFACE_SECONDARY="#f5f5f7",
    SURFACE_TERTIARY="#f5f5f7",
    
    TEXT_PRIMARY="#1c1c1e",
    TEXT_SECONDARY="#636366",
    TEXT_TERTIARY="#8e8e93",
    
    BORDER="rgba(0, 0, 0, 0.1)",
    BORDER_LIGHT="rgba(0, 0, 0, 0.05)",
    
    STATUS_SUCCESS="#10b981",
    STATUS_WARNING="#f59e0b",
    STATUS_ERROR="#ef4444",
    
    HOVER_BG="#f2f2f7",
    TERM_BG="#f2f2f7",
    TERM_FG="#1c1c1e",
    
    GLASS_BG="rgba(255, 255, 255, 0.8)",
    GLASS_BG_STRONG="rgba(255, 255, 255, 0.95)",
    GLASS_EDGE="rgba(0, 0, 0, 0.05)"
)

DARK_PALETTE = Palette(
    PRIMARY="#a1a1aa",
    PRIMARY_LIGHT="#27272a",
    PRIMARY_DARK="#ffffff",
    
    SURFACE_PRIMARY="#09090b",
    SURFACE_SECONDARY="#18181b",
    SURFACE_TERTIARY="#09090b",
    
    TEXT_PRIMARY="#f4f4f5",
    TEXT_SECONDARY="#a1a1aa",
    TEXT_TERTIARY="#71717a",
    
    BORDER="rgba(255, 255, 255, 0.1)",
    BORDER_LIGHT="rgba(255, 255, 255, 0.05)",
    
    STATUS_SUCCESS="#10b981",
    STATUS_WARNING="#f59e0b",
    STATUS_ERROR="#ef4444",
    
    HOVER_BG="#27272a",
    TERM_BG="#09090b",
    TERM_FG="#f4f4f5",
    
    GLASS_BG="rgba(24, 24, 27, 0.8)",
    GLASS_BG_STRONG="rgba(39, 39, 42, 0.95)",
    GLASS_EDGE="rgba(255, 255, 255, 0.1)"
)

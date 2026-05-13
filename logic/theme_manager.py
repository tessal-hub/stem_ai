"""
logic/theme_manager.py — Manages application themes and dynamic style generation.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from ui.palettes import LIGHT_PALETTE, DARK_PALETTE, Palette

class ThemeManager(QObject):
    """
    Manager for application themes.
    Emits theme_changed signal when switching between Light and Dark modes.
    """
    theme_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._current_theme = "light"

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @current_theme.setter
    def current_theme(self, value: str):
        if value in ["light", "dark"] and value != self._current_theme:
            self._current_theme = value
            self.theme_changed.emit(value)

    def get_palette(self) -> Palette:
        return DARK_PALETTE if self._current_theme == "dark" else LIGHT_PALETTE

# Singleton instance for the application
theme_manager = ThemeManager()

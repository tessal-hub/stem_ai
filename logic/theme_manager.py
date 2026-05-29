"""
logic/theme_manager.py — Quản lý theme ứng dụng (chỉ Light Mode).
"""

from PyQt6.QtCore import QObject, pyqtSignal
from ui.palettes import LIGHT_PALETTE, Palette

class ThemeManager(QObject):
    """
    Manager cho theme ứng dụng (bỏ qua Dark Mode).
    Phát signal khi có yêu cầu đổi theme hợp lệ.
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
        theme = "light" if value != "light" else value
        if theme != self._current_theme:
            self._current_theme = theme
            self.theme_changed.emit(theme)

    def get_palette(self) -> Palette:
        return LIGHT_PALETTE

# Singleton instance for the application
theme_manager = ThemeManager()

"""
logic/theme_manager.py — Quản lý theme toàn cục ứng dụng (Hỗ trợ Light Mode & Dark Mode).
"""

from PyQt6.QtCore import QObject, pyqtSignal
from ui.palettes import LIGHT_PALETTE, DARK_PALETTE, Palette


class ThemeManager(QObject):
    """
    Manager cho theme ứng dụng (Light Mode / Dark Mode).
    Phát signal theme_changed(str) khi đổi theme thành công.
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
        theme = "dark" if str(value).lower() == "dark" else "light"
        if theme != self._current_theme:
            self._current_theme = theme
            self.theme_changed.emit(theme)

    def get_palette(self) -> Palette:
        if self._current_theme == "dark":
            return DARK_PALETTE
        return LIGHT_PALETTE


# Singleton instance toàn cục
theme_manager = ThemeManager()

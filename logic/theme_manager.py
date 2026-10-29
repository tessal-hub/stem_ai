"""
logic/theme_manager.py — Quản lý giao diện sáng/tối; tương thích cấu hình theme.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from ui.palettes import DARK_PALETTE, LIGHT_PALETTE, Palette


class ThemeManager(QObject):
    """
    Manager cho giao diện sáng/tối của ứng dụng.
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

    @property
    def is_dark(self) -> bool:
        """Kiểm tra xem theme hiện tại có phải là Dark Mode không."""
        return self._current_theme == "dark"

    def get_palette(self) -> Palette:
        return DARK_PALETTE if self._current_theme == "dark" else LIGHT_PALETTE


# Singleton instance toàn cục
theme_manager = ThemeManager()


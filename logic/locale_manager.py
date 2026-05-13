"""App-wide UI language; other pages can listen to ``language_changed``."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from logic.setting_i18n import normalize_ui_language


class LocaleManager(QObject):
    """Emits ``language_changed`` when ``ui_language`` updates (``en`` / ``vi``)."""

    language_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._current_language = "en"

    @property
    def current_language(self) -> str:
        return self._current_language

    @current_language.setter
    def current_language(self, value: str | None) -> None:
        normalized = normalize_ui_language(value)
        if normalized == self._current_language:
            return
        self._current_language = normalized
        self.language_changed.emit(normalized)


locale_manager = LocaleManager()

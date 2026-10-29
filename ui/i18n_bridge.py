"""UI-layer access to translations without pages importing ``logic`` directly."""

from __future__ import annotations

from logic.locale_manager import locale_manager
from logic.ui_i18n import tr as _tr


def tr_ui(key: str, default: str | None = None, **kwargs: object) -> str:
    """Translate *key* for the current ``locale_manager`` language."""
    text = _tr(locale_manager.current_language, key, default=default)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

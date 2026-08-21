"""Central UI strings (English / Vietnamese) loaded from ``ui_strings.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import sys

Lang = Literal["en", "vi"]


def _get_ui_strings_path() -> Path:
    """Trả về đường dẫn chính xác tới ui_strings.json, cả khi frozen (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "logic" / "ui_strings.json"
    return Path(__file__).resolve().with_name("ui_strings.json")


_PATH = _get_ui_strings_path()
_TABLE: dict[str, dict[str, str]] = json.loads(_PATH.read_text(encoding="utf-8"))



def normalize_ui_language(code: str | None) -> Lang:
    if code is None:
        return "en"
    c = str(code).strip().lower()
    return "vi" if c in {"vi", "vn", "vietnamese"} else "en"


def tr(lang: str | None, key: str, default: str | None = None) -> str:
    lg = normalize_ui_language(lang)
    val = _TABLE.get(lg, {}).get(key) or _TABLE.get("en", {}).get(key)
    if val is not None:
        return val
    return default if default is not None else key

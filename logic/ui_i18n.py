"""Central UI strings (English / Vietnamese) loaded from ``ui_strings.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

Lang = Literal["en", "vi"]

_PATH = Path(__file__).resolve().with_name("ui_strings.json")
_TABLE: dict[str, dict[str, str]] = json.loads(_PATH.read_text(encoding="utf-8"))


def normalize_ui_language(code: str | None) -> Lang:
    if code is None:
        return "en"
    c = str(code).strip().lower()
    return "vi" if c in {"vi", "vn", "vietnamese"} else "en"


def tr(lang: str | None, key: str) -> str:
    lg = normalize_ui_language(lang)
    return _TABLE.get(lg, {}).get(key) or _TABLE.get("en", {}).get(key, key)

"""Helpers for resolving asset file paths reliably."""

from __future__ import annotations

from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_asset_path(asset_path: str) -> str:
    """Return an absolute existing asset path when possible."""
    raw = Path(asset_path)
    if raw.is_absolute():
        return str(raw)

    resolved = (_PROJECT_ROOT / raw).resolve()
    if resolved.exists():
        return str(resolved)

    if resolved.suffix.lower() == ".svg":
        png_fallback = resolved.with_suffix(".png")
        if png_fallback.exists():
            return str(png_fallback)

    return str(resolved)


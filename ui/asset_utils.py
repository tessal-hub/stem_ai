"""Hàm tiện ích phân giải đường dẫn asset file."""

from __future__ import annotations

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    _PROJECT_ROOT = Path(sys._MEIPASS)
else:
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


def make_tinted_icon(asset_path: str, color_hex: str) -> QIcon:
    """Tạo QIcon từ file SVG/PNG và phủ màu (tint) theo color_hex."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap

    abs_path = resolve_asset_path(asset_path)
    pixmap = QPixmap(abs_path)
    if pixmap.isNull():
        return QIcon(abs_path)

    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color_hex))
    painter.end()

    return QIcon(tinted)

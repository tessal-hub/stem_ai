"""Shared macOS-style material helpers for soft depth."""

from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PyQt6.QtGui import QColor


def apply_soft_shadow(
    widget: QWidget,
    *,
    blur_radius: int = 28,
    x_offset: int = 0,
    y_offset: int = 7,
    color: str = "rgba(0, 0, 0, 0.18)",
) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur_radius)
    effect.setOffset(x_offset, y_offset)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)

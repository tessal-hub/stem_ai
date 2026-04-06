"""Shared UI helpers for PageWand panel widgets."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QLayout, QPushButton, QVBoxLayout

from ui.tokens import BTN_H, STYLE_WAND_CARD, TEXT_BODY


def clear_layout(layout: QLayout | None) -> None:
    """Recursively remove and delete all child items in a layout."""
    if layout is None:
        return

    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        if (widget := item.widget()) is not None:
            widget.deleteLater()
        elif (child := item.layout()) is not None:
            clear_layout(child)
            child.deleteLater()


def make_card(
    margins: tuple[int, int, int, int] = (16, 16, 16, 16),
    spacing: int = 12,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a wand-themed card frame with a configured vertical layout."""
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setStyleSheet(STYLE_WAND_CARD)

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def make_button(label: str, style: str, height: int = BTN_H) -> QPushButton:
    """Create a styled button with pointer cursor and fixed height."""
    btn = QPushButton(label)
    btn.setFixedHeight(height)
    btn.setStyleSheet(style)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_section_label(text: str) -> QLabel:
    """Create a bold section title label used across wand panels."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {TEXT_BODY}; font-weight: 900; font-size: 13px; letter-spacing: 1px;"
    )
    return lbl

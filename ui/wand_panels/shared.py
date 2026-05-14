"""Hàm UI helper dùng chung cho các panel widget trang Wand — Theme aware."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

import ui.component_factory as factory
from logic.theme_manager import theme_manager

def make_card(
    margins: tuple[int, int, int, int] = (16, 16, 16, 16),
    spacing: int = 12,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a high-end Vanguard card for hardware panels."""
    return factory.make_card(margins=margins, spacing=spacing)

def make_button(label: str, style: str = "", height: int = 36) -> QPushButton:
    """Create a Vanguard button."""
    if "primary" in style.lower():
        return factory.make_primary_button(label, height=height)
    return factory.make_outline_button(label, height=height)

def make_section_label(text: str) -> QLabel:
    """Create a Vanguard section title."""
    return factory.make_section_label(text)

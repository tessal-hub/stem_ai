"""
ui/wand_panels/shared.py — Các hàm helper giao diện dùng chung cho Panel.

Tập hợp các hàm khởi tạo widget nhanh (Card, Button, Label) tuân thủ 
phong cách thiết kế Vanguard, giúp các panel con trong trang Wand đồng bộ về thẩm mỹ.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

import ui.component_factory as factory


def make_card(
    margins: tuple[int, int, int, int] = (16, 16, 16, 16),
    spacing: int = 12,
) -> tuple[QFrame, QVBoxLayout]:
    """
    Tạo một thẻ (Card) cao cấp cho các panel phần cứng.

    Args:
        margins: Khoảng cách lề (Trái, Trên, Phải, Dưới).
        spacing: Khoảng cách giữa các widget con.

    Returns:
        Tuple chứa đối tượng QFrame và layout QVBoxLayout bên trong.
    """
    return factory.make_card(margins=margins, spacing=spacing)


def make_button(label: str, style: str = "", height: int = 36) -> QPushButton:
    """
    Tạo một nút bấm theo phong cách Vanguard.

    Args:
        label: Nội dung văn bản hiển thị trên nút.
        style: Chuỗi định danh kiểu (Primary hoặc Outline).
        height: Chiều cao của nút bấm.

    Returns:
        Đối tượng QPushButton đã được cấu hình.
    """
    if "primary" in style.lower():
        return factory.make_primary_button(label, height=height)
    return factory.make_outline_button(label, height=height)


def make_section_label(text: str) -> QLabel:
    """
    Tạo một nhãn tiêu đề phân đoạn (Section Label).

    Args:
        text: Nội dung tiêu đề.

    Returns:
        Đối tượng QLabel đã được định dạng.
    """
    return factory.make_section_label(text)

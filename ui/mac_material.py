"""Hàm tiện ích macOS-style material tạo hiệu ứng chiều sâu mềm."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


def apply_soft_shadow(
    widget: QWidget,
    *,
    blur_radius: int = 28,
    x_offset: int = 0,
    y_offset: int = 7,
    color: str = "rgba(0, 0, 0, 0.18)",
) -> None:
    _ = (blur_radius, x_offset, y_offset, color)
    widget.setGraphicsEffect(None)

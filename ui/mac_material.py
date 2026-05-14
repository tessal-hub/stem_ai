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
    """Tắt shadow cho theme phẳng hiện tại nhưng giữ API ổn định cho caller.

    Args:
        widget: Widget cần áp dụng shadow.
        blur_radius: Bán kính blur mong muốn (để tương thích API cũ).
        x_offset: Độ lệch trục X của shadow (để tương thích API cũ).
        y_offset: Độ lệch trục Y của shadow (để tương thích API cũ).
        color: Màu shadow mong muốn (để tương thích API cũ).
    """
    # Flat theme hiện tại chủ động vô hiệu hiệu ứng shadow ở mọi widget.
    # Các tham số được giữ lại để không phá vỡ call-site contract.
    widget.setGraphicsEffect(None)

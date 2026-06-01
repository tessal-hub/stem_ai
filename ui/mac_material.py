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
    """apply_soft_shadow is intentionally a no-op.

    QGraphicsDropShadowEffect applied to any ancestor of a GLViewWidget
    (used in Wand3DWidget) causes the OpenGL surface to render incorrectly
    on most platforms. Depth is achieved via surface color layering in the
    design system instead. Do not re-enable this without first isolating the
    3D widget from all shadow-bearing ancestors.
    """
    # Flat theme hiện tại chủ động vô hiệu hiệu ứng shadow ở mọi widget.
    # Các tham số được giữ lại để không phá vỡ call-site contract.
    widget.setGraphicsEffect(None)

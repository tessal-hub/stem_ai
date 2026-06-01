"""
Hàm tiện ích layout dùng chung.
Gom các thao tác layout phổ biến dùng trên nhiều trang UI.
"""

from PyQt6.QtWidgets import QLayout


def clear_layout(layout: QLayout | None) -> None:
    """
    Recursively remove and schedule deletion for all items in layout.

    Safely clears both widgets and nested layouts, ensuring proper cleanup
    and preventing memory leaks.

    Args:
        layout: QLayout to clear, or None (safe to pass None).
    """
    if layout is None:
        return

    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue

        # Remove widget if present
        if (widget := item.widget()) is not None:
            widget.deleteLater()
        # Recursively clear nested layouts
        elif (child := item.layout()) is not None:
            clear_layout(child)
            child.deleteLater()

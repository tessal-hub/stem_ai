"""
Tiện ích layout hiện đại cho hệ thống thiết kế card-based.

Cung cấp helpers cho:
  - Tạo panel/card hiện đại với spacing chuẩn
  - Thêm hiệu ứng shadow tạo chiều sâu
  - Cấu hình margins và spacing nhất quán
  - Xây dựng spacer items
"""

from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QSizePolicy, QSpacerItem,
                             QVBoxLayout, QWidget)

# Modern spacing values (in pixels) - Claude web aesthetic
SPACING_XS = 8       # Minimal spacing between tightly grouped items
SPACING_SM = 12      # Small spacing between form elements
SPACING_MD = 16      # Medium spacing between sections
SPACING_LG = 24      # Large spacing between panels
SPACING_XL = 32      # Extra large spacing for major sections
SPACING_XXL = 48     # Maximum spacing

# Modern margins for containers - Claude web aesthetic
MARGIN_COMPACT = 12
MARGIN_STANDARD = 16
MARGIN_COMFORTABLE = 24
MARGIN_SPACIOUS = 32
MARGIN_LUXURIOUS = 48


def create_modern_card(
    margin: int = MARGIN_COMFORTABLE,
    spacing: int = SPACING_MD,
    orientation: str = "vertical",
) -> tuple[QFrame, QVBoxLayout | QHBoxLayout]:
    """
    Create a modern card/panel with proper spacing and styling.

    Args:
        margin: Margin inside card (pixels)
        spacing: Spacing between items (pixels)
        orientation: "vertical" for QVBoxLayout, "horizontal" for QHBoxLayout

    Returns:
        Tuple of (frame, layout) ready for addWidget/addLayout calls
    """
    card = QFrame()
    card.setFrameShape(QFrame.Shape.NoFrame)
    card.setFrameShadow(QFrame.Shadow.Plain)
    card.setObjectName("ModernCard")

    if orientation.lower() == "horizontal":
        layout = QHBoxLayout(card)
    else:
        layout = QVBoxLayout(card)

    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)

    return card, layout


def add_card_shadow(
    widget: QWidget,
    blur_radius: float = 12,
    offset_x: float = 0,
    offset_y: float = 4,
    color: str = "rgba(0, 0, 0, 0.12)",
) -> None:
    """Apply a subtle shadow to improve card depth.
    (Currently a no-op to comply with Apple HIG flat aesthetics)
    """
    pass


def create_spacer(
    horizontal: bool = False,
    size: int = SPACING_MD,
) -> QSpacerItem:
    """
    Create a spacer item for layout spacing.

    Args:
        horizontal: If True, create horizontal spacer; else vertical
        size: Minimum size of spacer (pixels)

    Returns:
        QSpacerItem ready to add to layout
    """
    if horizontal:
        return QSpacerItem(
            size,
            0,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Minimum,
        )
    else:
        return QSpacerItem(
            0,
            size,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Minimum,
        )


def create_expandable_spacer(horizontal: bool = False) -> QSpacerItem:
    """
    Create an expandable spacer that grows to fill available space.

    Args:
        horizontal: If True, create horizontal; else vertical

    Returns:
        QSpacerItem that expands to fill space
    """
    if horizontal:
        return QSpacerItem(
            40,
            0,
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
    else:
        return QSpacerItem(
            0,
            40,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )


def set_layout_spacing(
    layout: QVBoxLayout | QHBoxLayout,
    margin: int = MARGIN_COMFORTABLE,
    spacing: int = SPACING_MD,
) -> None:
    """
    Set modern spacing on a layout.

    Args:
        layout: Layout to configure
        margin: Margin around edges
        spacing: Spacing between items
    """
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)


def create_section_container(
    title_widget: QWidget | None = None,
    margin: int = MARGIN_COMFORTABLE,
    spacing: int = SPACING_MD,
) -> tuple[QFrame, QVBoxLayout]:
    """
    Create a card-based section with optional title.

    Args:
        title_widget: Optional title widget to add at top
        margin: Internal margin
        spacing: Item spacing

    Returns:
        Tuple of (card_frame, layout)
    """
    card, layout = create_modern_card(margin=margin, spacing=spacing)

    if title_widget:
        layout.addWidget(title_widget)

    return card, layout


def create_elevated_panel(
    shadow_blur: float = 16,
    shadow_offset_y: float = 4,
    margin: int = MARGIN_COMFORTABLE,
    spacing: int = SPACING_MD,
) -> tuple[QFrame, QVBoxLayout]:
    """
    Create an elevated panel container.

    Args:
        shadow_blur: Unused in no-shadow mode; kept for compatibility
        shadow_offset_y: Unused in no-shadow mode; kept for compatibility
        margin: Internal margin
        spacing: Item spacing

    Returns:
        Tuple of (elevated_panel, layout)
    """
    _ = (shadow_blur, shadow_offset_y)
    panel, layout = create_modern_card(margin=margin, spacing=spacing)
    return panel, layout


def create_column_layout(
    margin: int = 0,
    spacing: int = SPACING_MD,
) -> QVBoxLayout:
    """Create a vertical layout with modern spacing."""
    layout = QVBoxLayout()
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)
    return layout


def create_row_layout(
    margin: int = 0,
    spacing: int = SPACING_MD,
) -> QHBoxLayout:
    """Create a horizontal layout with modern spacing."""
    layout = QHBoxLayout()
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)
    return layout


def apply_card_styling(widget: QWidget, with_shadow: bool = True) -> None:
    """
    Apply standard card styling to a widget.

    Args:
        widget: Widget to style
        with_shadow: Unused in no-shadow mode; kept for compatibility
    """
    _ = with_shadow
    widget.setObjectName("ModernCard")

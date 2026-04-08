"""
Modern layout utilities for card-based design system.

Provides helpers for:
  - Creating modern panels/cards with proper spacing
  - Adding shadow effects for visual depth
  - Configuring consistent margins and spacing
  - Building spacer items
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

# Modern spacing values (in pixels)
SPACING_XS = 4       # Minimal spacing between tightly grouped items
SPACING_SM = 8       # Small spacing between form elements
SPACING_MD = 12      # Medium spacing between sections
SPACING_LG = 16      # Large spacing between panels
SPACING_XL = 24      # Extra large spacing for major sections
SPACING_XXL = 32     # Maximum spacing (rarely used)

# Modern margins for containers
MARGIN_COMPACT = 8
MARGIN_STANDARD = 12
MARGIN_COMFORTABLE = 16
MARGIN_SPACIOUS = 20
MARGIN_LUXURIOUS = 24


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
    spread: float = 0,
) -> QGraphicsDropShadowEffect:
    """
    Add a drop shadow to a widget for depth and elevation.
    
    Args:
        widget: Widget to apply shadow to
        blur_radius: Shadow blur radius (0-20 typically)
        offset_x: Horizontal offset
        offset_y: Vertical offset
        color: Shadow color (QColor-compatible string)
        spread: Shadow spread radius
    
    Returns:
        The shadow effect applied to the widget
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(offset_x, offset_y)
    shadow.setColor(QColor(color))
    shadow.setBlurRadius(spread)
    widget.setGraphicsEffect(shadow)
    return shadow


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
    Create an elevated panel with shadow for prominence.
    
    Args:
        shadow_blur: Shadow blur radius
        shadow_offset_y: Shadow vertical offset
        margin: Internal margin
        spacing: Item spacing
    
    Returns:
        Tuple of (elevated_panel, layout)
    """
    panel, layout = create_modern_card(margin=margin, spacing=spacing)
    add_card_shadow(
        panel,
        blur_radius=shadow_blur,
        offset_y=shadow_offset_y,
        color="rgba(0, 0, 0, 0.08)",
    )
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
        with_shadow: If True, add drop shadow
    """
    widget.setObjectName("ModernCard")
    
    if with_shadow:
        add_card_shadow(widget, blur_radius=12, offset_y=3)

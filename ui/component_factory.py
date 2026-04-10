"""
Unified UI component factories.

Consolidates widget creation patterns from all 5 UI pages into a single,
consistent module. Ensures consistent styling and behavior across the application.

Factories return bare widgets; signal connections happen in parent components.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.tokens import (
    # Colors
    ACCENT,
    ACCENT_TEXT,
    BG_DARK,
    BG_LIGHT,
    BG_WHITE,
    BORDER,
    BORDER_MID,
    TEXT_BODY,
    TEXT_MUTED,
    HOVER_BG,
    WAND_ACCENT,
    SETTINGS_ACCENT,
    # Sizes
    ICON,
    BTN_H,
    SPELL_BTN_H,
    MODULE_BTN_H,
    SETTINGS_BTN_H,
    SETTINGS_INPUT_H,
    LABEL_W,
    GRAPH_MIN_H,
    # Button styles
    STYLE_BTN_OUTLINE,
    STYLE_BTN_PRIMARY,
    STYLE_SETTING_BTN_OUTLINE,
    STYLE_SETTING_BTN_PRIMARY,
    STYLE_SETTING_BTN_DANGER,
    STYLE_SPELL_BTN,
    STYLE_MODULE_BTN,
    # Card styles
    STYLE_CARD,
    STYLE_CARD_NO_BORDER,
    # Component styles
    STYLE_CHECKBOX,
    STYLE_RECORD_CHECKBOX,
    STYLE_SETTING_CHECKBOX,
    STYLE_COMBO,
    STYLE_RECORD_COMBO,
    STYLE_WAND_COMBO,
    STYLE_SETTING_INPUT,
    STYLE_LIST,
    STYLE_RECORD_LIST,
    STYLE_STATISTICS_LIST,
    STYLE_RARITY_BADGE_WAND,
    STYLE_RARITY_BADGE_STATISTICS,
    # Status/template styles
    STATUS_LABEL_STYLE_TEMPLATE,
)


# ────────────────────────────────────────────────────────────────────────────
# CARD & FRAME FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_card(
    margins: tuple[int, int, int, int] = (16, 16, 16, 16),
    spacing: int = 12,
) -> tuple[QFrame, QVBoxLayout]:
    """
    Create a styled card frame with a vertical layout.
    
    Returns both the frame and its configured layout for convenience.
    
    Args:
        margins: (top, left, bottom, right) margins for the layout.
        spacing: Spacing between items in the layout.
    
    Returns:
        Tuple of (frame, layout) ready for adding widgets.
    """
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setStyleSheet(STYLE_CARD)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def make_card_frame() -> QFrame:
    """
    Create a styled card frame (no layout).
    
    Use when you need to manage the layout yourself.
    
    Returns:
        QFrame: Styled card frame ready for layout attachment.
    """
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setStyleSheet(STYLE_CARD)
    return frame


def make_section_frame() -> QFrame:
    """
    Create a generic section frame.
    
    Returns:
        QFrame: Styled frame for grouping related content.
    """
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setStyleSheet(STYLE_CARD)
    return frame


def make_borderless_frame() -> QFrame:
    """
    Create a transparent frame with no border.
    
    Returns:
        QFrame: Borderless frame for layout organization.
    """
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setStyleSheet(STYLE_CARD_NO_BORDER)
    return frame


# ────────────────────────────────────────────────────────────────────────────
# BUTTON FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_button(
    label: str,
    style: str,
    height: int = BTN_H,
    cursor: bool = True,
) -> QPushButton:
    """
    Create a styled button.
    
    Args:
        label: Button text.
        style: Stylesheet to apply.
        height: Button height in pixels.
        cursor: If True, set pointing hand cursor.
    
    Returns:
        QPushButton: Styled button ready for signals.
    """
    btn = QPushButton(label)
    btn.setFixedHeight(height)
    btn.setStyleSheet(style)
    if cursor:
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_outline_button(label: str, height: int = BTN_H) -> QPushButton:
    """Create an outline button (secondary action)."""
    return make_button(label, STYLE_BTN_OUTLINE, height)


def make_primary_button(label: str, height: int = BTN_H) -> QPushButton:
    """Create a primary button (accent color)."""
    return make_button(label, STYLE_BTN_PRIMARY, height)


def make_setting_outline_button(label: str) -> QPushButton:
    """Create a settings outline button."""
    return make_button(label, STYLE_SETTING_BTN_OUTLINE, SETTINGS_BTN_H)


def make_setting_primary_button(label: str) -> QPushButton:
    """Create a settings primary button."""
    return make_button(label, STYLE_SETTING_BTN_PRIMARY, SETTINGS_BTN_H)


def make_setting_danger_button(label: str) -> QPushButton:
    """Create a settings danger button (red, for destructive actions)."""
    return make_button(label, STYLE_SETTING_BTN_DANGER, SETTINGS_BTN_H)


# ────────────────────────────────────────────────────────────────────────────
# LABEL & TEXT FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_label(text: str, style: str = "") -> QLabel:
    """
    Create a generic label.
    
    Args:
        text: Label text.
        style: Optional stylesheet.
    
    Returns:
        QLabel: Unstyled or custom-styled label.
    """
    lbl = QLabel(text)
    if style:
        lbl.setStyleSheet(style)
    return lbl


def make_section_label(
    text: str,
    accent_color: str = SETTINGS_ACCENT,
) -> QLabel:
    """
    Create a section header label.
    
    Args:
        text: Label text.
        accent_color: Color for the text (default: settings accent).
    
    Returns:
        QLabel: Bold, larger section label.
    """
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {accent_color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
    )
    return lbl


def make_stat_label(text: str) -> QLabel:
    """
    Create a statistic/info label (muted, smaller).
    
    Args:
        text: Label text.
    
    Returns:
        QLabel: Small, muted info label.
    """
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")
    return lbl


def make_hint(text: str, color: str = TEXT_MUTED) -> QLabel:
    """
    Create a hint/help text label.
    
    Args:
        text: Hint text.
        color: Text color.
    
    Returns:
        QLabel: Small, wrapped hint label.
    """
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
    lbl.setWordWrap(True)
    return lbl


def make_card_name_label(name: str) -> QLabel:
    """Create a card name label (bold, main text color)."""
    lbl = QLabel(name)
    lbl.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 12px;")
    return lbl


def make_card_count_label(count: int) -> QLabel:
    """Create a card count label (muted, smaller)."""
    lbl = QLabel(f"Samples: {count}")
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")
    return lbl


def make_graph_placeholder() -> QLabel:
    """
    Create a placeholder for missing graph/data.
    
    Returns:
        QLabel: Centered, placeholder label with minimum height.
    """
    lbl = QLabel("DATA GRAPH")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background-color: {BG_DARK}; color: {TEXT_MUTED}; border-radius: 6px;"
    )
    lbl.setMinimumHeight(GRAPH_MIN_H)
    return lbl


def make_status_label(text: str, color: str) -> QLabel:
    """
    Create a colored status label (for connection states, etc.).
    
    Args:
        text: Status text.
        color: Status color (e.g., SUCCESS, DANGER).
    
    Returns:
        QLabel: Colored status label.
    """
    lbl = QLabel(text)
    lbl.setStyleSheet(STATUS_LABEL_STYLE_TEMPLATE.format(color=color))
    return lbl


def make_rarity_badge_wand(label: str, color: str) -> QLabel:
    """
    Create a rarity badge with background color (PageWand style).
    
    Args:
        label: Rarity tier label (e.g., "EPIC").
        color: Background color from rarity tier.
    
    Returns:
        QLabel: Colored badge label.
    """
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(STYLE_RARITY_BADGE_WAND.format(color=color))
    return lbl


def make_rarity_badge_statistics(label: str, color: str) -> QLabel:
    """
    Create a rarity badge with border (PageStatistics style).
    
    Args:
        label: Rarity tier label (e.g., "EPIC").
        color: Border and text color from rarity tier.
    
    Returns:
        QLabel: Bordered badge label.
    """
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(STYLE_RARITY_BADGE_STATISTICS.format(color=color))
    return lbl


# ────────────────────────────────────────────────────────────────────────────
# INPUT COMPONENT FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_checkbox(label: str, checked: bool = False) -> QCheckBox:
    """
    Create a styled checkbox.
    
    Args:
        label: Checkbox label text.
        checked: Initial checked state.
    
    Returns:
        QCheckBox: Styled checkbox ready for signals.
    """
    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setStyleSheet(STYLE_CHECKBOX)
    return chk


def make_record_checkbox(label: str, checked: bool = False) -> QCheckBox:
    """Create a PageRecord-styled checkbox."""
    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setStyleSheet(STYLE_RECORD_CHECKBOX)
    return chk


def make_setting_checkbox(label: str, checked: bool = False) -> QCheckBox:
    """Create a PageSetting-styled checkbox."""
    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setStyleSheet(STYLE_SETTING_CHECKBOX)
    return chk


def make_combo(items: list[str], height: int = 32) -> QComboBox:
    """
    Create a styled dropdown combobox.
    
    Args:
        items: List of combobox items.
        height: Height in pixels.
    
    Returns:
        QComboBox: Styled combobox ready for signals.
    """
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLE_COMBO)
    combo.setFixedHeight(height)
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    return combo


def make_record_combo(items: list[str]) -> QComboBox:
    """Create a PageRecord-styled combobox."""
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLE_RECORD_COMBO)
    combo.setFixedHeight(32)
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    return combo


def make_wand_combo(items: list[str]) -> QComboBox:
    """Create a PageWand-styled combobox."""
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLE_WAND_COMBO)
    combo.setFixedHeight(32)
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    return combo


def make_setting_combo(items: list[str]) -> QComboBox:
    """Create a PageSetting-styled combobox."""
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLE_SETTING_INPUT)
    combo.setFixedHeight(SETTINGS_INPUT_H)
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    return combo


def make_spinbox(
    min_val: int,
    max_val: int,
    *,
    step: int = 1,
    suffix: str = "",
    height: int = SETTINGS_INPUT_H,
) -> QSpinBox:
    """
    Create a styled spinbox (number input).
    
    Args:
        min_val: Minimum value.
        max_val: Maximum value.
        step: Step size (keyword-only).
        suffix: Unit suffix (e.g., "ms", "%").
        height: Height in pixels.
    
    Returns:
        QSpinBox: Styled spinbox ready for signals.
    """
    spin = QSpinBox()
    spin.setRange(min_val, max_val)
    spin.setSingleStep(step)
    if suffix:
        spin.setSuffix(suffix)
    spin.setStyleSheet(STYLE_SETTING_INPUT)
    spin.setFixedHeight(height)
    return spin


# ────────────────────────────────────────────────────────────────────────────
# LAYOUT FACTORIES
# ────────────────────────────────────────────────────────────────────────────

def make_form_row(
    label_text: str,
    widget: QWidget,
    label_width: int = LABEL_W,
) -> QHBoxLayout:
    """
    Create a labeled form row layout.
    
    Typical usage:
        label_lbl = QLineEdit(...)
        row = make_form_row("Project Name:", label_lbl)
        some_layout.addLayout(row)
    
    Args:
        label_text: Label text (e.g., "Project Name:").
        widget: Widget to place on the right.
        label_width: Width of the label in pixels.
    
    Returns:
        QHBoxLayout: Row layout with label | stretch | widget.
    """
    row = QHBoxLayout()
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
    lbl.setMinimumWidth(label_width)
    lbl.setWordWrap(True)
    row.addWidget(lbl)
    row.addWidget(widget, stretch=1)
    return row

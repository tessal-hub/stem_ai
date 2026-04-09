"""
top_bar.py — Navigation topbar with a physical bookmark-tab effect.

How the illusion works
----------------------
The topbar renders a border-bottom: 1px solid #e5e7eb.
The *active* TechButton fills all the way to the topbar's bottom edge and
draws border-bottom: 1px solid #ffffff (= page background).  Because child
widgets are painted after their parent, that white 1-px line paints *over*
the parent's gray bottom border at exactly the button's footprint — punching
a "hole" that makes the tab feel physically connected to the page below.

Inactive buttons are shorter and don't reach the bottom edge, so they sit
"behind" the page level, reinforcing the depth cue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from PyQt6.QtCore import QEasingCurve, QSize, Qt, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

# Import centralized design tokens
from .design_tokens import (
    TOPBAR_H, TAB_TOP_PAD, ACTIVE_TAB_H, INACTIVE_TAB_H,
    ICON_SZ, ANIM_MS,
    C_PAGE_BG, C_TOPBAR_BG, C_BORDER, C_INACTIVE_BG, C_INACTIVE_BDR,
    C_INACTIVE_TEXT, C_ACTIVE_TEXT, C_ICON_INACTIVE, C_ICON_ACTIVE
)


# ── Menu definition ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MenuEntry:
    icon:   str
    label:  str
    accent: str


MENUS: tuple[MenuEntry, ...] = (
    MenuEntry("assets/icon/home.svg",      "Home",       "#00d4ff"),
    MenuEntry("assets/icon/record.svg",    "Record",     "#ff3366"),
    MenuEntry("assets/icon/statistic.svg", "Statistics", "#00ff88"),
    MenuEntry("assets/icon/wand.svg",      "Wand",       "#ffaa00"),
    MenuEntry("assets/icon/setting.svg",   "Setting",    "#8b5cf6"),
)


# ── TechButton ───────────────────────────────────────────────────────────────

class TechButton(QPushButton):
    """
    A navigation tab that animates between a compact icon-only square (inactive)
    and an expanded icon + label pill (active).

    When active it grows taller and its bottom border erases the topbar
    separator, completing the bookmark illusion.
    """

    def __init__(self, entry: MenuEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.entry        = entry
        self._is_active   = False
        self._w_collapsed = INACTIVE_TAB_H          # square when icon-only
        self._w_expanded  = self._measure_expanded_width()

        self.setAccessibleName(f"Navigate to {entry.label}")

        # ── icon / fallback emoji ────────────────────────────────────────
        from .design_tokens import TAB_FALLBACKS
        if os.path.exists(entry.icon):
            self.setIcon(self._tint_svg(entry.icon, C_ICON_INACTIVE))
        else:
            self.setText(TAB_FALLBACKS.get(entry.label, "●"))
        self.setIconSize(ICON_SZ)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.setFixedHeight(INACTIVE_TAB_H)
        self.setFixedWidth(self._w_collapsed)

        # ── expand animation ─────────────────────────────────────────────
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._anim.valueChanged.connect(lambda v: self.setFixedWidth(int(v)))

        self._refresh(False)

    # ── public ───────────────────────────────────────────────────────────────

    def set_active(self, active: bool) -> None:
        """Transition the button into active or inactive visual state."""
        if self._is_active == active:
            return
        self._is_active = active
        self.blockSignals(True)
        self.setChecked(active)
        self.blockSignals(False)
        self._refresh(active)

    # ── private ──────────────────────────────────────────────────────────────

    def _refresh(self, active: bool) -> None:
        """Update height, icon tint, label and style; then kick off animation."""
        self.setFixedHeight(ACTIVE_TAB_H if active else INACTIVE_TAB_H)

        if active:
            self.setText(f"  {self.entry.label}")
            if os.path.exists(self.entry.icon):
                self.setIcon(self._tint_svg(self.entry.icon, C_ICON_ACTIVE))
        else:
            self.setText("")
            if os.path.exists(self.entry.icon):
                self.setIcon(self._tint_svg(self.entry.icon, C_ICON_INACTIVE))

        self._apply_style(active)

        target_w = self._w_expanded if active else self._w_collapsed
        self._anim.setStartValue(float(self.width()))
        self._anim.setEndValue(float(target_w))
        self._anim.start()

    def _apply_style(self, active: bool) -> None:
        if active:
            # ┌─────────────────────────────────────────────────────────┐
            # │  KEY: border-bottom = page background color             │
            # │  This paints over the topbar's bottom border, creating  │
            # │  the seamless "tab opens into page" bookmark effect.     │
            # └─────────────────────────────────────────────────────────┘
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C_PAGE_BG};
                    border-top:    2px solid {self.entry.accent};
                    border-left:   1px solid {C_BORDER};
                    border-right:  1px solid {C_BORDER};
                    border-bottom: 1px solid {C_PAGE_BG};
                    border-top-left-radius:     8px;
                    border-top-right-radius:    8px;
                    border-bottom-left-radius:  0px;
                    border-bottom-right-radius: 0px;
                    color: {C_ACTIVE_TEXT};
                    padding: 0px 12px 0px 10px;
                    font-weight: bold;
                    font-size: 11px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #fafafa;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C_INACTIVE_BG};
                    border: 1px solid {C_INACTIVE_BDR};
                    border-radius: 6px;
                    color: {C_INACTIVE_TEXT};
                    padding: 6px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: #2e3340;
                    border-color: #4a5568;
                    color: #d1d5db;
                }}
            """)

    @staticmethod
    def _tint_svg(path: str, color: QColor) -> QIcon:
        """Render an SVG and flood-fill it with *color* using SourceIn compositing."""
        renderer = QSvgRenderer(path)
        pixmap = QPixmap(ICON_SZ)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        renderer.render(p)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(pixmap.rect(), color)
        p.end()
        return QIcon(pixmap)

    def _measure_expanded_width(self) -> int:
        """Estimate label width without mutating visible state."""
        fm = QFontMetrics(QFont("Segoe UI", 10, QFont.Weight.Bold))
        text_w = fm.horizontalAdvance(f"  {self.entry.label}")
        return max(ICON_SZ.width() + 8 + text_w + 24, 110)


# ── Topbar ───────────────────────────────────────────────────────────────────

class Topbar(QWidget):
    """
    Dark top navigation bar.

    Emits ``nav_requested(int)`` with the clicked tab index.
    """

    nav_requested = pyqtSignal(int)

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self.buttons: list[TechButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, TAB_TOP_PAD, 12, 0)
        layout.setSpacing(4)
        # AlignBottom: buttons are flush with the topbar's bottom edge,
        # so the active tab's white bottom border coincides with (and erases)
        # the topbar's own bottom border.
        layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        for i, entry in enumerate(MENUS):
            btn = TechButton(entry, self)
            btn.clicked.connect(lambda _, idx=i: self._on_click(idx))
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.setFixedHeight(TOPBAR_H)
        self.setStyleSheet(f"""
            Topbar {{
                background-color: {C_TOPBAR_BG};
                border-bottom: 1px solid {C_BORDER};
            }}
        """)

        # Activate first tab without animation
        self._set_active(0)

    # ── private ──────────────────────────────────────────────────────────────

    def _on_click(self, index: int) -> None:
        self._set_active(index)
        self.nav_requested.emit(index)

    def _set_active(self, index: int) -> None:
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == index)
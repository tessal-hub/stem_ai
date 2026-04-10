"""Spell payload selection panel used for firmware compile selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from logic.rarity_utils import RARITY_TIERS, RarityTier
from ui.tokens import (
    STYLE_LIST,
    STYLE_RARITY_BADGE_WAND,
)
from ui.wand_panels.shared import make_section_label


class WandSpellPayloadPanel(QWidget):
    """Panel that renders selectable spell payload entries."""

    def __init__(self) -> None:
        super().__init__()
        self._spell_order: list[str] = []
        self._selected_spells: set[str] = set()
        self._spell_counts: dict[str, int] = {}
        self._build_ui()

    def load_spell_list(self, spell_counts: dict[str, int]) -> None:
        self._spell_counts = dict(spell_counts)
        self._spell_order = [name for name in spell_counts.keys() if str(name).strip()]

        # Keep only currently valid selected spells after dataset refresh.
        self._selected_spells.intersection_update(self._spell_order)
        self._refresh_lists()

    def get_checked_spells(self) -> list[str]:
        return [name for name in self._spell_order if name in self._selected_spells]

    def get_available_spell_names(self) -> list[str]:
        return [name for name in self._spell_order if name not in self._selected_spells]

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(make_section_label("FIRMWARE PAYLOAD"))

        split = QSplitter(Qt.Orientation.Horizontal)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_title = QLabel("SELECTED FOR TRAINING")
        left_title.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        left_layout.addWidget(left_title)

        self.list_selected_spells = QListWidget()
        self.list_selected_spells.setStyleSheet(STYLE_LIST)
        self.list_selected_spells.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_selected_spells.setMinimumHeight(220)
        left_layout.addWidget(self.list_selected_spells, stretch=1)

        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_title = QLabel("AVAILABLE SPELLS")
        right_title.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        right_layout.addWidget(right_title)

        self.list_available_spells = QListWidget()
        self.list_available_spells.setStyleSheet(STYLE_LIST)
        self.list_available_spells.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_available_spells.setMinimumHeight(220)
        right_layout.addWidget(self.list_available_spells, stretch=1)

        split.addWidget(left_col)
        split.addWidget(right_col)
        split.setChildrenCollapsible(False)
        split.setSizes([1, 1])
        layout.addWidget(split, stretch=1)

        # Backward-compat alias for old references.
        self.list_firmware = self.list_selected_spells

        self.list_selected_spells.itemClicked.connect(self._on_selected_item_clicked)
        self.list_available_spells.itemClicked.connect(self._on_available_item_clicked)

    def _refresh_lists(self) -> None:
        self.list_selected_spells.clear()
        self.list_available_spells.clear()

        for name in self._spell_order:
            count = int(self._spell_counts.get(name, 0))
            if name in self._selected_spells:
                self._add_spell_row(self.list_selected_spells, name, count)
            else:
                self._add_spell_row(self.list_available_spells, name, count)

    def _add_spell_row(self, list_widget: QListWidget, spell_name: str, count: int) -> None:
        item = QListWidgetItem(list_widget)
        item.setData(Qt.ItemDataRole.UserRole, spell_name)

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")

        row = QHBoxLayout(widget)
        row.setContentsMargins(12, 8, 12, 8)

        name_label = QLabel(spell_name)
        name_label.setStyleSheet("font-size: 12px; font-weight: 700;")
        font = QFont()
        font.setBold(True)
        name_label.setFont(font)

        rarity = self._resolve_rarity(count)
        badge = self._make_rarity_badge(rarity.label, rarity.color)

        row.addWidget(name_label)
        row.addStretch()
        row.addWidget(badge)

        item.setSizeHint(widget.sizeHint())
        list_widget.setItemWidget(item, widget)

    def _toggle_spell(self, spell_name: str) -> None:
        if spell_name not in self._spell_order:
            return
        if spell_name in self._selected_spells:
            self._selected_spells.remove(spell_name)
        else:
            self._selected_spells.add(spell_name)
        self._refresh_lists()

    def _on_selected_item_clicked(self, item: QListWidgetItem) -> None:
        spell_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if spell_name:
            self._toggle_spell(spell_name)

    def _on_available_item_clicked(self, item: QListWidgetItem) -> None:
        spell_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if spell_name:
            self._toggle_spell(spell_name)

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(STYLE_RARITY_BADGE_WAND.format(color=color))
        return lbl

    @staticmethod
    def _resolve_rarity(count: int) -> RarityTier:
        return max(
            (tier for tier in RARITY_TIERS if count >= tier.min_count),
            key=lambda tier: tier.min_count,
            default=RARITY_TIERS[0],
        )

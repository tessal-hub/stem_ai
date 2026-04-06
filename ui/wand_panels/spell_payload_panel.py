"""Spell payload selection panel used for firmware compile selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from logic.rarity_utils import RARITY_TIERS, RarityTier
from ui.tokens import (
    STYLE_CHECKBOX,
    STYLE_LIST,
    STYLE_RARITY_BADGE_WAND,
)
from ui.wand_panels.shared import make_section_label


class WandSpellPayloadPanel(QWidget):
    """Panel that renders selectable spell payload entries."""

    def __init__(self) -> None:
        super().__init__()
        self._spell_checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()

    def load_spell_list(self, spell_counts: dict[str, int]) -> None:
        self.list_firmware.clear()
        self._spell_checkboxes.clear()

        for name, count in spell_counts.items():
            item = QListWidgetItem(self.list_firmware)
            widget = QWidget()
            widget.setStyleSheet("background: transparent;")

            row = QHBoxLayout(widget)
            row.setContentsMargins(12, 4, 12, 4)

            chk = QCheckBox(name)
            chk.setStyleSheet(STYLE_CHECKBOX)
            self._spell_checkboxes[name] = chk

            rarity = self._resolve_rarity(count)
            badge = self._make_rarity_badge(rarity.label, rarity.color)

            row.addWidget(chk)
            row.addStretch()
            row.addWidget(badge)

            item.setSizeHint(widget.sizeHint())
            self.list_firmware.setItemWidget(item, widget)

    def get_checked_spells(self) -> list[str]:
        return [name for name, chk in self._spell_checkboxes.items() if chk.isChecked()]

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(make_section_label("FIRMWARE PAYLOAD"))

        self.list_firmware = QListWidget()
        self.list_firmware.setStyleSheet(STYLE_LIST)
        self.list_firmware.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_firmware, stretch=1)

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

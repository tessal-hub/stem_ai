"""Hardware stats and dataset chart panel."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.tokens import ACCENT, BG_WHITE, BORDER_MID, TEXT_BODY, TEXT_MUTED
from ui.wand_panels.shared import clear_layout, make_card, make_section_label


class WandStatsPanel(QWidget):
    """Panel for ESP telemetry labels and spell-count bar chart."""

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        clear_layout(self.layout_stats)
        if not stats:
            lbl = QLabel("Awaiting connection...")
            lbl.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 11px; font-style: italic;"
            )
            self.layout_stats.addWidget(lbl)
            return

        for key, val in stats.items():
            lbl = QLabel(f"■  {key}: {val}")
            lbl.setStyleSheet(f"color: {TEXT_BODY}; font-size: 11px; font-weight: 600;")
            self.layout_stats.addWidget(lbl)

    def update_spell_chart(self, spell_counts: dict[str, int]) -> None:
        self.stats_plot.clear()

        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_left = self.stats_plot.getAxis("left")
        ax_left.setPen(TEXT_MUTED)
        ax_bottom.setPen(TEXT_MUTED)

        spells = list(spell_counts.keys())
        counts = list(spell_counts.values())

        if spells:
            bar = pg.BarGraphItem(
                x=np.arange(len(spells)),
                height=counts,
                width=0.6,
                brush=pg.mkBrush(ACCENT),
            )
            self.stats_plot.addItem(bar)
            ax_bottom.setTicks([list(enumerate(spells))])
            return

        bar = pg.BarGraphItem(x=[0], height=[0], width=0.6, brush=pg.mkBrush(QColor(BORDER_MID)))
        self.stats_plot.addItem(bar)
        self.stats_plot.setYRange(0, 10)
        ax_bottom.setTicks([[(0, "No data yet")]])

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(make_section_label("DATASET STATISTICS"))

        card, card_layout = make_card()

        self.layout_stats = QHBoxLayout()
        card_layout.addLayout(self.layout_stats)

        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setBackground(BG_WHITE)
        self.stats_plot.setMouseEnabled(x=False, y=False)
        self.stats_plot.hideButtons()
        self.stats_plot.showGrid(x=False, y=True, alpha=0.3)

        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_bottom.setPen(TEXT_MUTED)
        ax_bottom.setTextPen(TEXT_BODY)
        ax_bottom.setStyle(tickTextOffset=8)

        ax_left = self.stats_plot.getAxis("left")
        ax_left.setPen(TEXT_MUTED)
        ax_left.setTextPen(TEXT_BODY)

        card_layout.addWidget(self.stats_plot, stretch=1)
        layout.addWidget(card, stretch=1)

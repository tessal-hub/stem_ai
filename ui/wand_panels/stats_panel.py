"""Panel thống kê phần cứng ESP32 và biểu đồ phân bố spell."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from ui.layout_utils import clear_layout
from ui.modern_layout import SPACING_LG, SPACING_SM, SPACING_XS
from ui.tokens import (
    ACCENT,
    BG_WHITE,
    BORDER_MID,
    STYLE_SETTINGS_HINT_TEMPLATE,
    STYLE_STATISTICS_INFO_LABEL,
    TEXT_BODY,
    TEXT_MUTED,
)
from ui.wand_panels.shared import make_card, make_section_label


class WandStatsPanel(QWidget):
    """Panel hiển thị telemetry ESP32 và biểu đồ bar chart số lượng mẫu spell."""

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        """Cập nhật nhãn thống kê phần cứng ESP32.

        Args:
            stats: Dict chứa các thông số (Battery, RAM Free, RSSI...).
        """
        clear_layout(self.layout_stats)
        if not stats:
            lbl = QLabel("Awaiting connection...")
            lbl.setStyleSheet(STYLE_SETTINGS_HINT_TEMPLATE.format(color=TEXT_MUTED))
            self.layout_stats.addWidget(lbl, 0, 0)
            return

        for idx, (key, val) in enumerate(stats.items()):
            lbl = QLabel(f"■  {key}: {val}")
            lbl.setStyleSheet(STYLE_STATISTICS_INFO_LABEL)
            lbl.setWordWrap(True)
            row = idx // 2
            col = idx % 2
            self.layout_stats.addWidget(lbl, row, col)

        self.layout_stats.setColumnStretch(0, 1)
        self.layout_stats.setColumnStretch(1, 1)

    def update_spell_chart(self, spell_counts: dict[str, int]) -> None:
        """Vẽ lại biểu đồ bar chart phân bố spell.

        Args:
            spell_counts: Dict spell_name → số lượng mẫu.
        """
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

    def _init_ui(self) -> None:
        """Xây dựng layout gồm grid thống kê và biểu đồ plot."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        layout.addWidget(make_section_label("DATASET STATISTICS"))

        card, card_layout = make_card()

        self.layout_stats = QGridLayout()
        self.layout_stats.setHorizontalSpacing(SPACING_LG)
        self.layout_stats.setVerticalSpacing(SPACING_XS)
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

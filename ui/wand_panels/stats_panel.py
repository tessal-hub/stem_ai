"""Panel thống kê phần cứng ESP32 và biểu đồ phân bố spell."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from ui.layout_utils import clear_layout
from ui.modern_layout import SPACING_LG, SPACING_SM, SPACING_XS
from ui.tokens import (
    STYLE_SETTINGS_HINT_TEMPLATE,
    STYLE_STATISTICS_INFO_LABEL,
)
from ui.wand_panels.shared import make_card, make_section_label
from ui.i18n_bridge import tr_ui
from logic.theme_manager import theme_manager


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
        p = theme_manager.get_palette()
        if not stats:
            lbl = QLabel(tr_ui("wand_stats_waiting"))
            lbl.setStyleSheet(STYLE_SETTINGS_HINT_TEMPLATE.format(color=p.TEXT_SECONDARY))
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
        p = theme_manager.get_palette()

        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_left = self.stats_plot.getAxis("left")
        ax_left.setPen(p.TEXT_SECONDARY)
        ax_bottom.setPen(p.TEXT_SECONDARY)
        ax_left.setTextPen(p.TEXT_PRIMARY)
        ax_bottom.setTextPen(p.TEXT_PRIMARY)

        spells = list(spell_counts.keys())
        counts = list(spell_counts.values())

        if spells:
            bar = pg.BarGraphItem(
                x=np.arange(len(spells)),
                height=counts,
                width=0.6,
                brush=pg.mkBrush(QColor(p.PRIMARY)),
            )
            self.stats_plot.addItem(bar)
            ax_bottom.setTicks([list(enumerate(spells))])
            return

        bar = pg.BarGraphItem(x=[0], height=[0], width=0.6, brush=pg.mkBrush(QColor(p.TEXT_TERTIARY)))
        self.stats_plot.addItem(bar)
        self.stats_plot.setYRange(0, 10)
        ax_bottom.setTicks([[(0, tr_ui("wand_no_data"))]])

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        self.stats_plot.setBackground("transparent")
        self.stats_plot.getAxis("left").setPen(p.TEXT_SECONDARY)
        self.stats_plot.getAxis("bottom").setPen(p.TEXT_SECONDARY)
        self.stats_plot.getAxis("left").setTextPen(p.TEXT_PRIMARY)
        self.stats_plot.getAxis("bottom").setTextPen(p.TEXT_PRIMARY)
        # Update any info labels already in the grid
        for i in range(self.layout_stats.count()):
            widget = self.layout_stats.itemAt(i).widget()
            if isinstance(widget, QLabel):
                widget.setStyleSheet(f"color: {p.TEXT_PRIMARY}; font-size: 11px; font-weight: 600;")

    def _init_ui(self) -> None:
        """Xây dựng layout gồm grid thống kê và biểu đồ plot."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._stats_section = make_section_label(tr_ui("wand_section_stats"))
        layout.addWidget(self._stats_section)

        card, card_layout = make_card()

        self.layout_stats = QGridLayout()
        self.layout_stats.setHorizontalSpacing(SPACING_LG)
        self.layout_stats.setVerticalSpacing(SPACING_XS)
        card_layout.addLayout(self.layout_stats)

        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setBackground("transparent")
        self.stats_plot.setMouseEnabled(x=False, y=False)
        self.stats_plot.hideButtons()
        self.stats_plot.showGrid(x=False, y=True, alpha=0.3)

        p = theme_manager.get_palette()
        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_bottom.setPen(p.TEXT_SECONDARY)
        ax_bottom.setTextPen(p.TEXT_PRIMARY)
        ax_bottom.setStyle(tickTextOffset=8)

        ax_left = self.stats_plot.getAxis("left")
        ax_left.setPen(p.TEXT_SECONDARY)
        ax_left.setTextPen(p.TEXT_PRIMARY)

        card_layout.addWidget(self.stats_plot, stretch=1)
        layout.addWidget(card, stretch=1)

    def apply_ui_language(self) -> None:
        self._stats_section.setText(tr_ui("wand_section_stats"))

"""
ui/wand_panels/stats_panel.py — Panel thống kê telemetry và dataset cho Wand.

Hiển thị các thông số tài nguyên từ ESP32 (Pin, RAM, RSSI) và biểu đồ phân bố 
các mẫu cử chỉ (Spells) hiện có trong tập dữ liệu.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget, QFrame, QStackedWidget

from logic.theme_manager import theme_manager
from ui.i18n_bridge import tr_ui
from ui.layout_utils import clear_layout
from ui.modern_layout import SPACING_LG, SPACING_SM, SPACING_XS
from ui.tokens import (
    TITLE_FONT_STACK,
)
from .shared import make_card, make_section_label


class WandStatsPanel(QWidget):
    """
    Panel hiển thị trạng thái phần cứng và phân bổ dữ liệu mẫu.
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện thống kê (Requirement 6)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._stats_section = make_section_label(tr_ui("wand_section_stats"))
        layout.addWidget(self._stats_section)

        # Requirement 6: Chart container with 20px padding
        card, card_layout = make_card(margins=(20, 20, 20, 20), spacing=SPACING_LG)

        # Grid thông số phần cứng
        self.layout_stats = QGridLayout()
        self.layout_stats.setHorizontalSpacing(SPACING_LG)
        self.layout_stats.setVerticalSpacing(SPACING_XS)
        card_layout.addLayout(self.layout_stats)

        # Biểu đồ dataset
        # Requirement 6: Height 300px
        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setFixedHeight(300)
        self.stats_plot.setBackground("transparent")
        self.stats_plot.setMouseEnabled(x=False, y=False)
        self.stats_plot.hideButtons()
        self.stats_plot.showGrid(x=False, y=True, alpha=0.3)

        # Ensure labels are not cut off
        self.stats_plot.getPlotItem().setContentsMargins(10, 10, 10, 30)

        self.chart_stack = QStackedWidget()
        self.chart_stack.addWidget(self._make_empty_state_widget())
        self.chart_stack.addWidget(self.stats_plot)
        card_layout.addWidget(self.chart_stack, stretch=1)
        layout.addWidget(card, stretch=1)
        
        # Requirement 3: Empty state handling inside update_spell_chart
        self.refresh_styles()

    # ── Public methods ──────────────────────────

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        """Cập nhật các nhãn thông số từ ESP32."""
        clear_layout(self.layout_stats)
        palette = theme_manager.get_palette()
        
        if not stats:
            lbl = QLabel(tr_ui("wand_stats_waiting"))
            lbl.setProperty("type", "settings_hint")
            lbl.setStyleSheet(f"color: {palette.TEXT_SECONDARY};")
            self.layout_stats.addWidget(lbl, 0, 0)
            return

        for idx, (key, val) in enumerate(stats.items()):
            lbl = QLabel(f"■ {key}: {val}")
            lbl.setProperty("type", "statistics_info_label")
            lbl.setWordWrap(True)
            self.layout_stats.addWidget(lbl, idx // 2, idx % 2)

    def update_spell_chart(self, spell_counts: dict[str, int]) -> None:
        """Vẽ lại biểu đồ cột phân bổ dataset (Requirement 3: Empty State)."""
        self.stats_plot.clear()
        palette = theme_manager.get_palette()
        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_left = self.stats_plot.getAxis("left")
        
        ax_left.setPen(palette.TEXT_SECONDARY)
        ax_bottom.setPen(palette.TEXT_SECONDARY)
        
        spells = list(spell_counts.keys())
        counts = list(spell_counts.values())

        if spells and sum(counts) > 0:
            self.chart_stack.setCurrentIndex(1)
            bar = pg.BarGraphItem(x=np.arange(len(spells)), height=counts, width=0.6, brush=pg.mkBrush(palette.PRIMARY))
            self.stats_plot.addItem(bar)
            ax_bottom.setTicks([list(enumerate(spells))])
        else:
            # Requirement 3: Show centered empty state if no data
            self.chart_stack.setCurrentIndex(0)

    def refresh_styles(self) -> None:
        """Làm mới style cho đồ thị và nhãn theo theme."""
        palette = theme_manager.get_palette()
        self.stats_plot.setBackground("transparent")
        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_left = self.stats_plot.getAxis("left")
        ax_bottom.setPen(palette.TEXT_SECONDARY)
        ax_bottom.setTextPen(palette.TEXT_PRIMARY)
        ax_left.setPen(palette.TEXT_SECONDARY)
        ax_left.setTextPen(palette.TEXT_PRIMARY)

    def _make_empty_state_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setMinimumHeight(220)
        icon = QLabel("📊")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setProperty("type", "empty_state_icon")
        text = QLabel("No data to evaluate yet")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setProperty("type", "empty_state_text")
        layout.addWidget(icon)
        layout.addWidget(text)
        return widget

    def apply_ui_language(self) -> None:
        """Cập nhật tiêu đề khi đổi ngôn ngữ."""
        self._stats_section.setText(tr_ui("wand_section_stats"))

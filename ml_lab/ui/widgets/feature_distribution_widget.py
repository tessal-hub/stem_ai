"""
ml_lab/ui/widgets/feature_distribution_widget.py — Biểu đồ phân phối đặc trưng (Histogram / Density).

Trực quan hóa sự phân bố giá trị của một đặc trưng qua các lớp cử chỉ khác nhau
để học viên phân tích khả năng phân tách dữ liệu (Feature Separability).
"""

from __future__ import annotations

from typing import Sequence
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget


class FeatureDistributionWidget(QWidget):
    """
    Widget hiển thị phân bố Histogram / Đường cong mật độ của 1 đặc trưng theo các class.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(380, 240)
        self._feature_name: str = ""
        self._class_data: dict[str, np.ndarray] = {}

    def set_distribution_data(self, feature_name: str, class_data: dict[str, np.ndarray]) -> None:
        self._feature_name = feature_name
        self._class_data = class_data or {}
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))

            if not self._class_data:
                self._draw_empty_state(painter, w, h)
                return

            margin_left = 50
            margin_right = 30
            margin_top = 35
            margin_bottom = 45

            plot_w = max(10, w - margin_left - margin_right)
            plot_h = max(10, h - margin_top - margin_bottom)

            # Tìm min / max toàn cục của feature
            all_vals = np.concatenate(list(self._class_data.values()))
            if len(all_vals) == 0:
                self._draw_empty_state(painter, w, h)
                return

            val_min = float(np.percentile(all_vals, 1))
            val_max = float(np.percentile(all_vals, 99))
            if val_max == val_min:
                val_max = val_min + 1.0
            val_range = val_max - val_min

            # Grid & Trục
            painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
            painter.drawRect(margin_left, margin_top, plot_w, plot_h)

            n_bins = 20
            bin_edges = np.linspace(val_min, val_max, n_bins + 1)
            bin_w = plot_w / n_bins

            # Tìm max count
            hist_per_class: dict[str, np.ndarray] = {}
            max_count = 1
            for cls_name, arr in self._class_data.items():
                counts, _ = np.histogram(arr, bins=bin_edges)
                hist_per_class[cls_name] = counts
                if len(counts) > 0 and np.max(counts) > max_count:
                    max_count = int(np.max(counts))

            # Vẽ Histogram từng class với độ trong suốt
            for c_idx, (cls_name, counts) in enumerate(hist_per_class.items()):
                col = self._get_class_color(c_idx)
                fill_col = QColor(col)
                fill_col.setAlpha(80)

                for b in range(n_bins):
                    cnt = counts[b]
                    if cnt > 0:
                        bar_h = (cnt / max_count) * plot_h
                        bx = margin_left + b * bin_w
                        by = margin_top + plot_h - bar_h
                        painter.fillRect(QRectF(bx + 1, by, bin_w - 2, bar_h), fill_col)

                # Vẽ đường viền đa giác nối các đỉnh
                path = QPainterPath()
                for b in range(n_bins):
                    cnt = counts[b]
                    bar_h = (cnt / max_count) * plot_h
                    bx = margin_left + (b + 0.5) * bin_w
                    by = margin_top + plot_h - bar_h
                    if b == 0:
                        path.moveTo(bx, by)
                    else:
                        path.lineTo(bx, by)
                painter.setPen(QPen(col, 2))
                painter.drawPath(path)

            # X Axis Labels
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(100, 100, 110))
            painter.drawText(margin_left - 10, h - margin_bottom + 18, f"{val_min:.2f}")
            painter.drawText(w - margin_right - 30, h - margin_bottom + 18, f"{val_max:.2f}")

            # Title
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.setPen(QColor(50, 50, 60))
            painter.drawText(
                QRectF(margin_left, 8, plot_w, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"Phân phối đặc trưng: {self._feature_name}",
            )

            # Legend
            leg_x = margin_left + 10
            leg_y = margin_top + 10
            for c_idx, cls_name in enumerate(self._class_data.keys()):
                col = self._get_class_color(c_idx)
                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(leg_x + c_idx * 110, leg_y, 8, 8))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
                painter.setPen(QColor(60, 60, 70))
                painter.drawText(leg_x + c_idx * 110 + 12, leg_y + 8, cls_name)

        finally:
            painter.end()

    def _get_class_color(self, idx: int) -> QColor:
        palette = [
            QColor(0, 122, 255),
            QColor(255, 59, 48),
            QColor(52, 199, 89),
            QColor(255, 149, 0),
            QColor(88, 86, 214),
        ]
        return palette[idx % len(palette)]

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(100, 110, 122))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "Chưa có dữ liệu phân phối đặc trưng.\nHãy nạp dataset để khám phá.",
        )

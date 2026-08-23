"""
ml_lab/ui/widgets/feature_importance_widget.py — Biểu đồ xếp hạng tầm quan trọng của đặc trưng.

Hiển thị thanh ngang (Horizontal Bar Chart) xếp hạng các đặc trưng mang tính phân biệt
cao nhất trong tập dữ liệu cử chỉ (Feature Importance Ranking).
"""

from __future__ import annotations

from typing import Sequence
import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class FeatureImportanceWidget(QWidget):
    """
    Biểu đồ xếp hạng tầm quan trọng của đặc trưng.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(380, 260)
        self._feature_names: list[str] = []
        self._importances: list[float] = []

    def set_importances(self, feature_names: Sequence[str], importances: Sequence[float]) -> None:
        if not feature_names or not importances:
            self._feature_names = []
            self._importances = []
            self.update()
            return

        # Sắp xếp giảm dần và lấy top 12
        pairs = sorted(zip(feature_names, importances), key=lambda p: p[1], reverse=True)[:12]
        self._feature_names = [p[0] for p in pairs]
        self._importances = [float(p[1]) for p in pairs]
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))

            if not self._feature_names or not self._importances:
                self._draw_empty_state(painter, w, h)
                return

            margin_left = 110
            margin_right = 50
            margin_top = 20
            margin_bottom = 20

            plot_w = max(10, w - margin_left - margin_right)
            plot_h = max(10, h - margin_top - margin_bottom)

            n_items = len(self._feature_names)
            row_h = plot_h / n_items
            bar_max_val = max(1e-5, max(self._importances))

            for i in range(n_items):
                feat_name = self._feature_names[i]
                val = self._importances[i]
                norm_val = val / bar_max_val
                bar_len = norm_val * plot_w

                y = margin_top + i * row_h
                bar_rect = QRectF(margin_left, y + row_h * 0.15, bar_len, row_h * 0.7)

                # Màu thanh theo kênh (ax/ay/az -> xanh, gx/gy/gz -> cam, mag -> tím)
                col = self._get_feature_color(feat_name)
                painter.fillRect(bar_rect, col)

                # Label tên feature bên trái
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
                painter.setPen(QColor(50, 50, 60))
                painter.drawText(
                    QRectF(0, y, margin_left - 10, row_h),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    feat_name,
                )

                # Giá trị số bên phải
                painter.setFont(QFont("Segoe UI", 8))
                painter.setPen(QColor(120, 120, 130))
                pct_str = f"{val*100:.1f}%" if max(self._importances) <= 1.0 else f"{val:.3f}"
                painter.drawText(
                    QRectF(margin_left + bar_len + 6, y, 40, row_h),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    pct_str,
                )

        finally:
            painter.end()

    def _get_feature_color(self, name: str) -> QColor:
        name_lower = name.lower()
        if name_lower.startswith("a") or "acc" in name_lower:
            return QColor(0, 122, 255, 180)    # Blue for accel
        elif name_lower.startswith("g") or "gyro" in name_lower:
            return QColor(255, 149, 0, 180)   # Orange for gyro
        elif "jerk" in name_lower:
            return QColor(255, 59, 48, 180)    # Red for Jerk
        else:
            return QColor(88, 86, 214, 180)    # Indigo for combined
        return QColor(52, 199, 89, 180)

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(140, 145, 155))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "📊 Chưa có dữ liệu tầm quan trọng đặc trưng.\nHãy huấn luyện Cây Quyết Định hoặc Rừng Ngẫu Nhiên.",
        )

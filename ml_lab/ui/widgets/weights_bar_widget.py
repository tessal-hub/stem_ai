"""
ml_lab/ui/widgets/weights_bar_widget.py — Biểu đồ trọng số đặc trưng (Logistic Regression / SVM Weights).

Trực quan hóa vector trọng số W: giải thích đặc trưng nào có tác động dương (ủng hộ)
hoặc tác động âm (chống lại) đối với từng lớp phép thuật.
"""

from __future__ import annotations

from typing import Sequence
import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class WeightsBarWidget(QWidget):
    """
    Biểu đồ trực quan hóa trọng số W của Logistic Regression / Linear SVM.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 260)
        self._feature_names: list[str] = []
        self._weights_matrix: np.ndarray = np.empty((0, 0))
        self._class_names: list[str] = []
        self._selected_class_idx: int = 0

        # UI Controls
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        lbl = QLabel("🎯 Chọn Lớp Cử Chỉ Xem Trọng Số (W):")
        lbl.setStyleSheet("font-weight: 600; font-size: 11px; color: #007aff;")
        self.combo_class = QComboBox()
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        top_bar.addWidget(lbl)
        top_bar.addWidget(self.combo_class, stretch=1)
        layout.addLayout(top_bar)

        self.canvas = _WeightsCanvas(self)
        layout.addWidget(self.canvas, stretch=1)

    def set_weights(
        self,
        weights_matrix: np.ndarray,
        feature_names: Sequence[str],
        class_names: Sequence[str],
    ) -> None:
        self._weights_matrix = weights_matrix
        self._feature_names = list(feature_names)
        self._class_names = list(class_names)

        self.combo_class.blockSignals(True)
        self.combo_class.clear()
        self.combo_class.addItems(self._class_names)
        self.combo_class.blockSignals(False)

        self._update_canvas()

    def _on_class_changed(self, idx: int) -> None:
        self._selected_class_idx = max(0, idx)
        self._update_canvas()

    def _update_canvas(self) -> None:
        if self._weights_matrix.size == 0 or len(self._feature_names) == 0:
            self.canvas.set_data([], [], "")
            return

        n_rows = self._weights_matrix.shape[0]
        c_idx = min(self._selected_class_idx, n_rows - 1)
        row_weights = self._weights_matrix[c_idx]

        cls_name = self._class_names[c_idx] if c_idx < len(self._class_names) else f"Class {c_idx}"
        self.canvas.set_data(self._feature_names, row_weights, cls_name)


class _WeightsCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._feature_names: list[str] = []
        self._weights: list[float] = []
        self._class_name: str = ""

    def set_data(self, feature_names: list[str], weights: Sequence[float], class_name: str) -> None:
        # Lấy top 12 đặc trưng có |W| lớn nhất
        if feature_names and len(weights) > 0:
            pairs = sorted(zip(feature_names, weights), key=lambda p: abs(p[1]), reverse=True)[:12]
            self._feature_names = [p[0] for p in pairs]
            self._weights = [float(p[1]) for p in pairs]
        else:
            self._feature_names = []
            self._weights = []
        self._class_name = class_name
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))

            if not self._feature_names or not self._weights:
                self._draw_empty_state(painter, w, h)
                return

            margin_left = 110
            margin_right = 50
            margin_top = 10
            margin_bottom = 20

            plot_w = max(10, w - margin_left - margin_right)
            plot_h = max(10, h - margin_top - margin_bottom)

            n_items = len(self._feature_names)
            row_h = plot_h / n_items
            center_x = margin_left + plot_w / 2.0

            max_abs_w = max(1e-5, max(abs(v) for v in self._weights))
            half_w = plot_w / 2.0

            # Trục giữa 0
            painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
            painter.drawLine(int(center_x), margin_top, int(center_x), h - margin_bottom)

            for i in range(n_items):
                feat_name = self._feature_names[i]
                val = self._weights[i]
                bar_len = (abs(val) / max_abs_w) * (half_w - 20)

                y = margin_top + i * row_h
                rect_h = row_h * 0.7

                if val >= 0:
                    bar_rect = QRectF(center_x, y + row_h * 0.15, bar_len, rect_h)
                    col = QColor(52, 199, 89, 190)  # Positive: Green
                else:
                    bar_rect = QRectF(center_x - bar_len, y + row_h * 0.15, bar_len, rect_h)
                    col = QColor(255, 59, 48, 190)  # Negative: Red

                painter.fillRect(bar_rect, col)

                # Label bên trái
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
                painter.setPen(QColor(50, 50, 60))
                painter.drawText(
                    QRectF(0, y, margin_left - 10, row_h),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    feat_name,
                )

                # Giá trị số
                painter.setFont(QFont("Segoe UI", 8))
                painter.setPen(QColor(100, 100, 110))
                val_x = center_x + bar_len + 4 if val >= 0 else center_x - bar_len - 38
                painter.drawText(
                    QRectF(val_x, y, 36, row_h),
                    Qt.AlignmentFlag.AlignLeft if val >= 0 else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"{val:+.2f}",
                )

        finally:
            painter.end()

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(140, 145, 155))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "⚖️ Chưa có ma trận trọng số.\nHãy huấn luyện Hồi quy Logistic hoặc SVM Tuyến tính.",
        )

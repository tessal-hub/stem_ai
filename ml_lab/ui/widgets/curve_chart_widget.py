"""
ml_lab/ui/widgets/curve_chart_widget.py — Biểu đồ đường cong Bias-Variance & Hyperparameter Sweep.

Trực quan hóa đường cong Train Accuracy vs Validation Accuracy theo siêu tham số.
Làm nổi bật vùng Underfitting (thiếu khớp), vùng Overfitting (quá khớp), và điểm Sweet Spot tối ưu.
"""

from __future__ import annotations

from typing import Sequence
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

import ml_lab.ui.lab_style as ls


class CurveChartWidget(QWidget):
    """
    Widget vẽ đồ thị đường cong học và quét tham số (Sweep Curve).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self.setAccessibleName("Biểu đồ đường cong Train và Validation theo siêu tham số")
        self._param_name: str = "Tham số"
        self._x_values: list[float | int | str] = []
        self._train_scores: list[float] = []
        self._val_scores: list[float] = []
        self._val_stds: list[float] = []

    def set_curve_data(
        self,
        param_name: str,
        x_values: Sequence[float | int | str],
        train_scores: Sequence[float],
        val_scores: Sequence[float],
        val_stds: Sequence[float] | None = None,
    ) -> None:
        self._param_name = param_name
        self._x_values = list(x_values)
        self._train_scores = list(train_scores)
        self._val_scores = list(val_scores)
        self._val_stds = list(val_stds) if val_stds else [0.0] * len(val_scores)
        # Screen reader: tóm tắt kết quả thay vì chỉ thấy canvas trống
        if self._val_scores:
            best_idx = int(np.argmax(self._val_scores))
            best_x = self._x_values[best_idx] if best_idx < len(self._x_values) else "?"
            self.setAccessibleDescription(
                f"Quét theo {param_name}: {len(self._x_values)} cấu hình. "
                f"Tốt nhất {best_x} đạt {self._val_scores[best_idx]*100:.1f}% trên dữ liệu mới."
            )
        else:
            self.setAccessibleDescription("Chưa có dữ liệu thử nghiệm.")
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(ls.SURFACE))

            if not self._x_values or not self._val_scores:
                self._draw_empty_state(painter, w, h)
                return

            margin_left = 50
            margin_right = 30
            margin_top = 40
            margin_bottom = 50

            plot_w = max(10, w - margin_left - margin_right)
            plot_h = max(10, h - margin_top - margin_bottom)

            n_points = len(self._x_values)
            y_min = max(0.0, min(min(self._val_scores or [0.0]), min(self._train_scores or [0.0])) - 0.08)
            y_max = min(1.05, max(max(self._val_scores or [1.0]), max(self._train_scores or [1.0])) + 0.05)
            y_range = max(0.05, y_max - y_min)

            def to_screen_x(i: int) -> float:
                if n_points == 1:
                    return margin_left + plot_w / 2.0
                return margin_left + (i / (n_points - 1)) * plot_w

            def to_screen_y(score: float) -> float:
                return margin_top + plot_h - ((score - y_min) / y_range) * plot_h

            # 1. Grid & Trục
            grid_pen = QPen(QColor(ls.BORDER), 1, Qt.PenStyle.DashLine)
            painter.setPen(grid_pen)
            for s in np.linspace(y_min, y_max, 5):
                sy = to_screen_y(s)
                painter.drawLine(int(margin_left), int(sy), int(w - margin_right), int(sy))
                painter.setFont(QFont("Segoe UI", 9))
                painter.setPen(QColor(ls.MUTED))
                painter.drawText(margin_left - 42, int(sy + 4), f"{s*100:.0f}%")
                painter.setPen(grid_pen)

            # Border
            painter.setPen(QPen(QColor(ls.BORDER_STRONG), 1))
            painter.drawRect(margin_left, margin_top, plot_w, plot_h)

            # 2. Vùng Sweet Spot (Điểm Validation cao nhất)
            if self._val_scores:
                best_idx = int(np.argmax(self._val_scores))
                bx = to_screen_x(best_idx)
                # Dải highlight
                _hl = QColor(ls.SUCCESS)
                _hl.setAlpha(25)
                _hl_line = QColor(ls.SUCCESS)
                _hl_line.setAlpha(120)
                highlight_rect = QRectF(bx - 18, margin_top, 36, plot_h)
                painter.fillRect(highlight_rect, _hl)
                painter.setPen(QPen(_hl_line, 1, Qt.PenStyle.DotLine))
                painter.drawLine(int(bx), margin_top, int(bx), int(h - margin_bottom))

            # 3. Vẽ đường Train Score (Màu Xám / Xanh lam nhạt)
            if self._train_scores and len(self._train_scores) == n_points:
                train_path = QPainterPath()
                for i, score in enumerate(self._train_scores):
                    pt = QPointF(to_screen_x(i), to_screen_y(score))
                    if i == 0:
                        train_path.moveTo(pt)
                    else:
                        train_path.lineTo(pt)
                painter.setPen(QPen(QColor(ls.MUTED), 2))
                painter.drawPath(train_path)

                for i, score in enumerate(self._train_scores):
                    pt = QPointF(to_screen_x(i), to_screen_y(score))
                    painter.setBrush(QBrush(QColor(ls.MUTED)))
                    painter.setPen(QPen(QColor(ls.SURFACE), 1.5))
                    painter.drawEllipse(pt, 3.5, 3.5)

            # 4. Vẽ đường Validation Score (ACCENT nổi bật)
            if self._val_scores and len(self._val_scores) == n_points:
                val_path = QPainterPath()
                for i, score in enumerate(self._val_scores):
                    pt = QPointF(to_screen_x(i), to_screen_y(score))
                    if i == 0:
                        val_path.moveTo(pt)
                    else:
                        val_path.lineTo(pt)
                painter.setPen(QPen(QColor(ls.ACCENT), 2.5))
                painter.drawPath(val_path)

                for i, score in enumerate(self._val_scores):
                    pt = QPointF(to_screen_x(i), to_screen_y(score))
                    is_best = (i == int(np.argmax(self._val_scores)))
                    painter.setBrush(QBrush(QColor(ls.SUCCESS) if is_best else QColor(ls.ACCENT)))
                    painter.setPen(QPen(QColor(ls.SURFACE), 2.0))
                    painter.drawEllipse(pt, 5.0 if is_best else 4.0, 5.0 if is_best else 4.0)

            # 5. X Ticks & Labels
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            painter.setPen(QColor(ls.BODY))
            for i, x_val in enumerate(self._x_values):
                sx = to_screen_x(i)
                text = str(x_val)
                painter.drawText(QRectF(sx - 25, h - margin_bottom + 8, 50, 20), Qt.AlignmentFlag.AlignCenter, text)

            # Trục X Label
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                QRectF(margin_left, h - margin_bottom + 28, plot_w, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"Cài đặt được thử: {self._param_name}",
            )

            # 6. Legend ở góc trên
            leg_x = margin_left + 15
            leg_y = margin_top + 15
            # Train dot
            painter.setBrush(QBrush(QColor(ls.MUTED)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(leg_x, leg_y, 8, 8))
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(ls.BODY))
            painter.drawText(leg_x + 14, leg_y + 8, "Điểm trên dữ liệu cũ (máy đã học)")

            # Val dot
            painter.setBrush(QBrush(QColor(ls.ACCENT)))
            painter.drawEllipse(QRectF(leg_x + 180, leg_y, 8, 8))
            painter.setPen(QColor(ls.ACCENT))
            painter.drawText(leg_x + 194, leg_y + 8, "Điểm trên dữ liệu MỚI (quan trọng nhất)")

        finally:
            painter.end()

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(ls.MUTED))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            "Chưa có dữ liệu thử nghiệm.\nChọn thuật toán và tham số ở bên trái rồi bấm 'Chạy thử & vẽ biểu đồ'.",
        )

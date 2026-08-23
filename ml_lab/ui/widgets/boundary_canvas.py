"""
ml_lab/ui/widgets/boundary_canvas.py — Trực quan hóa 2D PCA Decision Boundary & Data Points.

Trực quan hóa không gian đặc trưng thu gọn qua PCA và biên phân lớp của mô hình ML.
Hỗ trợ tương tác hover điểm dữ liệu và hiển thị tỷ lệ phương sai giải thích.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget


class DecisionBoundaryCanvas(QWidget):
    """
    Canvas vẽ Decision Boundary 2D với lưới phân lớp mịn và điểm phân bố dữ liệu.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 280)
        self.setMouseTracking(True)

        self._pca_result: dict[str, Any] = {}
        self._class_names: list[str] = []
        self._is_dark: bool = False
        self._hovered_point_idx: int = -1

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        self.update()

    def set_data(self, pca_result: dict[str, Any], class_names: list[str]) -> None:
        self._pca_result = pca_result or {}
        self._class_names = list(class_names)
        self._hovered_point_idx = -1
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._pca_result or "X_2d" not in self._pca_result:
            return

        w, h = self.width(), self.height()
        margin = 44
        plot_w = max(10, w - margin * 2)
        plot_h = max(10, h - margin * 2)

        x_min = self._pca_result.get("x_min", -3.0)
        x_max = self._pca_result.get("x_max", 3.0)
        y_min = self._pca_result.get("y_min", -3.0)
        y_max = self._pca_result.get("y_max", 3.0)

        def to_screen_x(val_x: float) -> float:
            return margin + ((val_x - x_min) / (x_max - x_min + 1e-6)) * plot_w

        def to_screen_y(val_y: float) -> float:
            return h - margin - ((val_y - y_min) / (y_max - y_min + 1e-6)) * plot_h

        mx, my = event.position().x(), event.position().y()
        X_2d = self._pca_result.get("X_2d", np.empty((0, 2)))
        y_labels = self._pca_result.get("y", self._pca_result.get("y_2d", np.empty((0,))))

        nearest_idx = -1
        min_dist_sq = 100.0  # 10px radius

        for i in range(len(X_2d)):
            sx = to_screen_x(X_2d[i, 0])
            sy = to_screen_y(X_2d[i, 1])
            dist_sq = (mx - sx) ** 2 + (my - sy) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_idx = i

        if nearest_idx != self._hovered_point_idx:
            self._hovered_point_idx = nearest_idx
            self.update()

            if nearest_idx >= 0:
                cls_id = int(y_labels[nearest_idx]) if nearest_idx < len(y_labels) else 0
                cls_name = self._class_names[cls_id] if cls_id < len(self._class_names) else f"Class {cls_id}"
                px, py = X_2d[nearest_idx, 0], X_2d[nearest_idx, 1]
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"✨ <b>{cls_name}</b><br>PC1: {px:.2f}, PC2: {py:.2f}",
                    self,
                )

    def leaveEvent(self, _event: Any) -> None:
        if self._hovered_point_idx != -1:
            self._hovered_point_idx = -1
            self.update()

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()

            # Nền Canvas Card
            bg_color = QColor(26, 29, 36) if self._is_dark else QColor(255, 255, 255)
            painter.fillRect(0, 0, w, h, bg_color)

            if not self._pca_result or "X_2d" not in self._pca_result:
                self._draw_empty_state(painter, w, h)
                return

            margin = 44
            plot_w = max(10, w - margin * 2)
            plot_h = max(10, h - margin * 2)

            x_min = self._pca_result.get("x_min", -3.0)
            x_max = self._pca_result.get("x_max", 3.0)
            y_min = self._pca_result.get("y_min", -3.0)
            y_max = self._pca_result.get("y_max", 3.0)

            def to_screen_x(val_x: float) -> float:
                return margin + ((val_x - x_min) / (x_max - x_min + 1e-6)) * plot_w

            def to_screen_y(val_y: float) -> float:
                return h - margin - ((val_y - y_min) / (y_max - y_min + 1e-6)) * plot_h

            # 1. Vẽ vùng quyết định (Decision Mesh)
            xx = self._pca_result.get("xx")
            yy = self._pca_result.get("yy")
            Z = self._pca_result.get("Z")

            if xx is not None and yy is not None and Z is not None:
                rows, cols = Z.shape
                cell_w = plot_w / float(cols)
                cell_h = plot_h / float(rows)

                for r in range(rows):
                    for c in range(cols):
                        cls_id = int(Z[r, c])
                        base_color = self._get_class_color(cls_id)
                        mesh_color = QColor(base_color)
                        mesh_color.setAlpha(40 if self._is_dark else 35)

                        px = margin + c * cell_w
                        py = h - margin - (r + 1) * cell_h
                        painter.fillRect(QRectF(px, py, cell_w + 0.8, cell_h + 0.8), mesh_color)

            # 2. Vẽ lưới Grid & Trục tọa độ
            grid_color = QColor(255, 255, 255, 18) if self._is_dark else QColor(0, 0, 0, 15)
            painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DashLine))

            x_zero = to_screen_x(0.0)
            y_zero = to_screen_y(0.0)
            painter.drawLine(int(x_zero), margin, int(x_zero), h - margin)
            painter.drawLine(margin, int(y_zero), w - margin, int(y_zero))

            # Khung viền đồ thị
            border_color = QColor(255, 255, 255, 40) if self._is_dark else QColor(0, 0, 0, 35)
            painter.setPen(QPen(border_color, 1))
            painter.drawRect(margin, margin, plot_w, plot_h)

            # 3. Vẽ các điểm dữ liệu (Scatter Points)
            X_2d = self._pca_result.get("X_2d", np.empty((0, 2)))
            y_labels = self._pca_result.get("y", self._pca_result.get("y_2d", np.empty((0,))))

            for i in range(len(X_2d)):
                cls_id = int(y_labels[i]) if i < len(y_labels) else 0
                sx = to_screen_x(X_2d[i, 0])
                sy = to_screen_y(X_2d[i, 1])

                color = self._get_class_color(cls_id)

                if i == self._hovered_point_idx:
                    # Hover halo
                    halo_col = QColor(color)
                    halo_col.setAlpha(90)
                    painter.setBrush(QBrush(halo_col))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(sx, sy), 10.0, 10.0)

                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(QColor(255, 255, 255), 2.0))
                    painter.drawEllipse(QPointF(sx, sy), 6.5, 6.5)
                else:
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(QColor(255, 255, 255, 180), 1.0))
                    painter.drawEllipse(QPointF(sx, sy), 4.2, 4.2)

            # 4. Chú thích trục với phương sai giải thích
            exp_var = self._pca_result.get("explained_variance", [0.0, 0.0])
            pc1_text = f"Trục chính 1 (PC 1: {exp_var[0]*100:.1f}%)" if len(exp_var) > 0 else "Trục chính 1"
            pc2_text = f"Trục 2 (PC 2: {exp_var[1]*100:.1f}%)" if len(exp_var) > 1 else "Trục chính 2"

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            text_color = QColor(180, 185, 195) if self._is_dark else QColor(90, 95, 105)
            painter.setPen(text_color)
            painter.drawText(margin + 6, h - margin + 22, pc1_text)
            painter.drawText(margin + 6, margin - 12, pc2_text)

            # 5. Legend
            leg_x = w - margin - 130
            leg_y = margin + 14
            for c_idx, c_name in enumerate(self._class_names[:6]):
                col = self._get_class_color(c_idx)
                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(leg_x, leg_y + c_idx * 16 - 7, 8, 8))
                painter.setPen(text_color)
                painter.drawText(int(leg_x + 14), int(leg_y + c_idx * 16), c_name)

        finally:
            painter.end()

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        text_color = QColor(130, 135, 145)
        painter.setPen(text_color)
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "📊 Chưa có dữ liệu huấn luyện.\nHãy chọn tham số và nhấn 'Huấn Luyện & Đánh Giá'.",
        )

    def _get_class_color(self, class_idx: int) -> QColor:
        palette = [
            QColor(0, 122, 255),   # Apple Blue
            QColor(255, 59, 48),   # Apple Red
            QColor(52, 199, 89),   # Apple Green
            QColor(255, 149, 0),   # Apple Orange
            QColor(88, 86, 214),   # Apple Indigo
            QColor(255, 45, 85),   # Apple Pink
            QColor(0, 199, 190),   # Apple Teal
        ]
        return palette[class_idx % len(palette)]

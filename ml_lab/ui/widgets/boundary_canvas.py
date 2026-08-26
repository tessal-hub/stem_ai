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
        # Tooltip nền trắng chữ đậm — mặc định của hệ thống quá nhạt để đọc
        self.setStyleSheet(
            "QToolTip { background-color: #ffffff; color: #0f172a; "
            "border: 1px solid #cdd6e1; padding: 5px; font-size: 12px; }"
        )

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
                    f"<b style='color:#0f172a;'>{cls_name}</b>"
                    f"<br><span style='color:#334155;'>PC1: {px:.2f} · PC2: {py:.2f}</span>",
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
            var1 = float(self._pca_result.get("var_ratio_1", 0.0))
            var2 = float(self._pca_result.get("var_ratio_2", 0.0))
            pc1_text = f"Trục chính 1 (PC 1: {var1:.1f}%)"
            pc2_text = f"Trục 2 (PC 2: {var2:.1f}%)"

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            text_color = QColor(180, 185, 195) if self._is_dark else QColor(90, 95, 105)
            painter.setPen(text_color)
            painter.drawText(margin + 6, h - margin + 22, pc1_text)
            painter.drawText(margin + 6, margin - 12, pc2_text)

            # 5. Legend — 2 cột, hiển thị TẤT CẢ các lớp
            col_w = 150
            leg_x = max(margin + 10, w - margin - 2 * col_w - 10)
            leg_y = margin + 14
            col_w = 150
            per_col = max(1, (len(self._class_names) + 1) // 2)
            for c_idx, c_name in enumerate(self._class_names):
                col = self._get_class_color(c_idx)
                col_x = leg_x + (c_idx // per_col) * col_w
                row_y = leg_y + (c_idx % per_col) * 16
                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(col_x, row_y - 7, 8, 8))
                painter.setPen(text_color)
                painter.drawText(int(col_x + 14), int(row_y), c_name[:14])

        finally:
            painter.end()

    def _get_class_color(self, class_idx: int) -> QColor:
        # 10 màu phân biệt rõ (đủ cho tối đa 10 lớp không trùng)
        palette = [
            QColor(0, 102, 204),    # Xanh dương
            QColor(220, 38, 38),    # Đỏ
            QColor(22, 138, 74),    # Xanh lục
            QColor(217, 119, 6),    # Cam
            QColor(109, 40, 217),   # Tím
            QColor(219, 39, 119),   # Hồng đậm
            QColor(8, 145, 178),    # Cyan đậm
            QColor(101, 163, 13),   # Xanh chanh
            QColor(120, 53, 15),    # Nâu đậm
            QColor(71, 85, 105),    # Xám xanh đậm
        ]
        return palette[class_idx % len(palette)]

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        text_color = QColor(100, 110, 122)
        painter.setPen(text_color)
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "Chưa có dữ liệu huấn luyện.\nChọn thuật toán ở tab Huấn luyện rồi bấm 'Huấn luyện & đánh giá'.",
        )

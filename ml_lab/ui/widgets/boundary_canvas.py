"""
ml_lab/ui/widgets/boundary_canvas.py — Trực quan hóa 2D PCA Decision Boundary & Data Points.

Trực quan hóa không gian đặc trưng thu gọn qua PCA và biên phân lớp của mô hình ML.
Hỗ trợ tương tác hover điểm dữ liệu và hiển thị tỷ lệ phương sai giải thích.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QToolTip, QWidget

import ml_lab.ui.lab_style as ls


class DecisionBoundaryCanvas(QWidget):
    """
    Canvas vẽ Decision Boundary 2D với lưới phân lớp mịn và điểm phân bố dữ liệu.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 280)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Bản đồ ranh giới quyết định 2D PCA")
        self.setAccessibleDescription("Biểu đồ phân bố các điểm dữ liệu và biên quyết định trong không gian 2 trục chính PC1 và PC2")
        self._tooltip_colors = (ls.INK, ls.BODY)
        self.setStyleSheet(
            f"QToolTip {{ background-color: {ls.SURFACE}; color: {ls.INK}; "
            f"border: 1px solid {ls.BORDER_STRONG}; padding: 5px; font-size: 12px; }}"
        )

        self._pca_result: dict[str, Any] = {}
        self._class_names: list[str] = []
        self._hovered_point_idx: int = -1
        self._mesh_pixmap: QPixmap | None = None

    def set_data(self, pca_result: dict[str, Any], class_names: list[str]) -> None:
        self._pca_result = pca_result or {}
        self._class_names = list(class_names)
        self._hovered_point_idx = -1
        self._rebuild_mesh_pixmap()
        # Harden a11y: tóm tắt số liệu cho screen reader, elide tên dài
        try:
            n_pts = 0
            X = self._pca_result.get("X_2d")
            if isinstance(X, np.ndarray):
                n_pts = int(X.shape[0])
            names = ", ".join((n[:18] + "…") if len(n) > 18 else n for n in self._class_names[:6])
            var1 = float(self._pca_result.get("var_ratio_1", 0.0))
            var2 = float(self._pca_result.get("var_ratio_2", 0.0))
            if n_pts:
                self.setAccessibleDescription(
                    f"{n_pts} điểm, {len(self._class_names)} lớp ({names}). "
                    f"PC1 {var1:.0f}%, PC2 {var2:.0f}%."
                )
            else:
                self.setAccessibleDescription("Chưa có dữ liệu. Huấn luyện ở tab 2 trước.")
        except Exception:
            pass
        self.update()

    def _rebuild_mesh_pixmap(self) -> None:
        Z = self._pca_result.get("Z")
        if Z is None or not isinstance(Z, np.ndarray) or Z.size == 0:
            self._mesh_pixmap = None
            return
        rows, cols = Z.shape
        alpha = 35
        cls_ids = Z.astype(np.int64)
        # Format_RGBA8888: 4 byte/pixel theo thứ tự R,G,B,A — không premultiply
        rgba = np.empty((rows, cols, 4), dtype=np.uint8)
        n_colors = len(ls.CLASS_COLORS)
        for ci in np.unique(cls_ids):
            color = QColor(ls.CLASS_COLORS[int(ci) % n_colors])
            rgba[cls_ids == ci] = (color.red(), color.green(), color.blue(), alpha)
        rgba = rgba[::-1]  # hàng 0 của Z ứng với đỉnh biểu đồ
        buf = np.ascontiguousarray(rgba)
        img = QImage(buf.data, cols, rows, cols * 4, QImage.Format.Format_RGBA8888)
        self._mesh_pixmap = QPixmap.fromImage(img.copy())

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
        if len(X_2d) == 0:
            return

        # Vector hóa: khoảng cách tới tất cả điểm trong một lần tính
        sx = margin + ((X_2d[:, 0] - x_min) / (x_max - x_min + 1e-6)) * plot_w
        sy = h - margin - ((X_2d[:, 1] - y_min) / (y_max - y_min + 1e-6)) * plot_h
        dist_sq = (mx - sx) ** 2 + (my - sy) ** 2
        nearest_idx = int(np.argmin(dist_sq))
        if dist_sq[nearest_idx] >= 100.0:  # ngoài bán kính 10px
            nearest_idx = -1

        if nearest_idx != self._hovered_point_idx:
            self._hovered_point_idx = nearest_idx
            self.update()

            if nearest_idx >= 0:
                cls_id = int(y_labels[nearest_idx]) if nearest_idx < len(y_labels) else 0
                cls_name = self._class_names[cls_id] if cls_id < len(self._class_names) else f"Class {cls_id}"
                px, py = X_2d[nearest_idx, 0], X_2d[nearest_idx, 1]
                title_color, body_color = self._tooltip_colors
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"<b style='color:{title_color};'>{cls_name}</b>"
                    f"<br><span style='color:{body_color};'>PC1: {px:.2f} · PC2: {py:.2f}</span>",
                    self,
                )

    def leaveEvent(self, _event: Any) -> None:
        if self._hovered_point_idx != -1:
            self._hovered_point_idx = -1
            self.update()

    def keyPressEvent(self, event: Any) -> None:
        """Bàn phím duyệt từng điểm (StrongFocus đã bật) — thay hover chuột."""
        try:
            X_2d = self._pca_result.get("X_2d", np.empty((0, 2)))
            n = len(X_2d)
            if n == 0:
                return
            key = event.key()
            if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                self._hovered_point_idx = (self._hovered_point_idx + 1) % n
            elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                self._hovered_point_idx = (self._hovered_point_idx - 1) % n
            else:
                super().keyPressEvent(event)
                return
            self.update()
        except Exception:
            pass

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()

            # Nền Canvas Card
            bg_color = QColor(255, 255, 255)
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

            # 1. Vẽ vùng quyết định (Decision Mesh) từ cached pixmap
            if self._mesh_pixmap and not self._mesh_pixmap.isNull():
                painter.drawPixmap(QRect(margin, margin, int(plot_w), int(plot_h)), self._mesh_pixmap)

            # 2. Vẽ lưới Grid & Trục tọa độ
            grid_color = QColor(0, 0, 0, 15)
            painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DashLine))

            x_zero = to_screen_x(0.0)
            y_zero = to_screen_y(0.0)
            painter.drawLine(int(x_zero), margin, int(x_zero), h - margin)
            painter.drawLine(margin, int(y_zero), w - margin, int(y_zero))

            # Khung viền đồ thị
            border_color = QColor(0, 0, 0, 35)
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

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            text_color = QColor(ls.MUTED)
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
                leg_text = painter.fontMetrics().elidedText(
                    c_name, Qt.TextElideMode.ElideRight, col_w - 20
                )
                painter.drawText(int(col_x + 14), int(row_y), leg_text)

        finally:
            painter.end()

    def _get_class_color(self, class_idx: int) -> QColor:
        return QColor(ls.CLASS_COLORS[class_idx % len(ls.CLASS_COLORS)])

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        text_color = QColor(ls.MUTED)
        painter.setPen(text_color)
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "Chưa có dữ liệu huấn luyện.\nChọn thuật toán ở tab Huấn luyện rồi bấm 'Huấn luyện và đánh giá'.",
        )

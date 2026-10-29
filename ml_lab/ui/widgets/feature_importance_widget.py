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

import ml_lab.ui.lab_style as ls


class FeatureImportanceWidget(QWidget):
    """
    Biểu đồ xếp hạng tầm quan trọng của đặc trưng.
    """

    # Nhóm cảm biến → màu PLOT_* của hệ thống (không palette ngoài)
    FAMILY_LEGEND = [
        ("Gia tốc", ls.PLOT_AY),
        ("Con quay", ls.PLOT_GX),
        ("Độ giật", ls.DANGER),
        ("Tổng hợp", ls.ACCENT),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(380, 260)
        self.setAccessibleName("Biểu đồ tầm quan trọng đặc trưng")
        self._feature_names: list[str] = []
        self._importances: list[float] = []

    def set_importances(self, feature_names: Sequence[str], importances: Sequence[float]) -> None:
        if not feature_names or not importances:
            self._feature_names = []
            self._importances = []
            self.setAccessibleDescription("Chưa có dữ liệu tầm quan trọng đặc trưng.")
            self.update()
            return

        # Sắp xếp giảm dần và lấy top 12
        pairs = sorted(zip(feature_names, importances), key=lambda p: p[1], reverse=True)[:12]
        self._feature_names = [p[0] for p in pairs]
        self._importances = [float(p[1]) for p in pairs]
        # Screen reader: đọc được top đặc trưng thay vì chỉ canvas vẽ
        top = ", ".join(self._feature_names[:5])
        self.setAccessibleDescription(f"Top đặc trưng quan trọng nhất: {top}.")
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(ls.SURFACE))

            if not self._feature_names or not self._importances:
                self._draw_empty_state(painter, w, h)
                return

            margin_left = 165
            margin_right = 50
            margin_top = 36
            margin_bottom = 20

            plot_w = max(10, w - margin_left - margin_right)
            plot_h = max(10, h - margin_top - margin_bottom)

            self._draw_legend(painter, w)

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

                # Màu thanh theo nhóm cảm biến — giải nghĩa ở legend phía trên
                col = self._get_feature_color(feat_name)
                painter.fillRect(bar_rect, col)

                # Label tên feature bên trái
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
                painter.setPen(QColor(ls.BODY))
                painter.drawText(
                    QRectF(0, y, margin_left - 10, row_h),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    feat_name,
                )

                # Giá trị số bên phải (9pt = sàn cỡ chữ 11px của hệ thống)
                painter.setFont(QFont("Segoe UI", 9))
                painter.setPen(QColor(ls.MUTED))
                pct_str = f"{val*100:.1f}%" if max(self._importances) <= 1.0 else f"{val:.3f}"
                painter.drawText(
                    QRectF(margin_left + bar_len + 6, y, 40, row_h),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    pct_str,
                )

        finally:
            painter.end()

    def _draw_legend(self, painter: QPainter, w: int) -> None:
        """Legend nhóm cảm biến — màu không phải kênh thông tin duy nhất."""
        x = 8.0
        y = 8.0
        painter.setFont(QFont("Segoe UI", 9))
        for label, hexcol in self.FAMILY_LEGEND:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(hexcol))
            painter.drawEllipse(QRectF(x, y, 8, 8))
            painter.setPen(QColor(ls.BODY))
            painter.drawText(int(x + 12), int(y + 9), label)
            x += 24 + painter.fontMetrics().horizontalAdvance(label)

    def _get_feature_color(self, name: str) -> QColor:
        # Chấp nhận cả tên gốc (ax_std) lẫn tên thân thiện tiếng Việt (friendly_feature_name)
        name_lower = name.lower()
        accel_keys = ("ax", "ay", "az", "acc", "gia tốc", "tăng tốc")
        gyro_keys = ("gx", "gy", "gz", "gyro", "con quay", "góc")
        col = None
        if name_lower.startswith("a") or any(k in name_lower for k in accel_keys):
            col = QColor(ls.PLOT_AY)           # Xanh cho gia tốc
        elif name_lower.startswith("g") or any(k in name_lower for k in gyro_keys):
            col = QColor(ls.PLOT_GX)           # Cam cho con quay
        elif "jerk" in name_lower or "giật" in name_lower or "độ giật" in name_lower:
            col = QColor(ls.DANGER)            # Đỏ cho độ giật
        else:
            col = QColor(ls.ACCENT)            # Indigo cho tổng hợp
        col.setAlpha(180)
        return col

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(ls.MUTED))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "Chưa có dữ liệu tầm quan trọng đặc trưng.\nHãy huấn luyện Cây Quyết Định hoặc Rừng Ngẫu Nhiên.",
        )

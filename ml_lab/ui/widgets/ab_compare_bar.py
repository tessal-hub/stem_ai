"""
ml_lab/ui/widgets/ab_compare_bar.py — Biểu đồ cột so sánh A/B (Trước vs Sau tăng cường).

Vẽ 2 thanh ngang accuracy để học sinh trực tiếp thấy tác động của Data Augmentation:
- Thanh xám  : mô hình train với dữ liệu gốc
- Thanh xanh : mô hình train với dữ liệu tăng cường (cùng validation set)
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

import ml_lab.ui.lab_style as ls


class AbCompareBarWidget(QWidget):
    """Widget vẽ 2 thanh so sánh accuracy trước/sau tăng cường."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 150)
        self.setAccessibleName("So sánh A/B: mô hình huấn luyện trên dữ liệu gốc và dữ liệu tăng cường")
        self._baseline: float | None = None
        self._augmented: float | None = None
        self._baseline_label: str = "Dữ liệu gốc"
        self._augmented_label: str = "Dữ liệu + Tăng cường"
        self._caption: str = ""

    def reset(self) -> None:
        """Về trạng thái rỗng ban đầu."""
        self._baseline = None
        self._augmented = None
        self._caption = ""
        self.setAccessibleDescription("Chưa có kết quả thí nghiệm.")
        self.update()

    def set_results(
        self,
        baseline_acc: float,
        augmented_acc: float,
        baseline_label: str = "Dữ liệu gốc",
        augmented_label: str = "Dữ liệu + Tăng cường",
    ) -> None:
        self._baseline = float(baseline_acc)
        self._augmented = float(augmented_acc)
        self._baseline_label = baseline_label
        self._augmented_label = augmented_label

        delta = (self._augmented - self._baseline) * 100.0
        if delta > 0.05:
            self._caption = (
                f"Tăng cường giúp mô hình chính xác hơn {delta:+.1f}%. "
                "Nhiều dữ liệu đa dạng giúp máy học quy luật tổng quát thay vì thuộc lòng từng mẫu."
            )
        elif delta < -0.05:
            self._caption = (
                f"Trong thí nghiệm này tăng cường làm giảm {delta:.1f}%. "
                "Có thể nhiễu làm dữ liệu gốc vốn sạch bị 'loãng'. Hãy thử mức nhiễu nhỏ hơn hoặc số nhân bản khác!"
            )
        else:
            self._caption = (
                "Hai mô hình ngang nhau. Khi dữ liệu gốc đã đủ phong phú, tăng cường ít tác dụng — "
                "đây cũng là một kết luận khoa học quý giá!"
            )
        # Screen reader: kết luận thí nghiệm là thông tin chính — công bố qua accessibleDescription
        self.setAccessibleDescription(
            f"{self._baseline_label} {self._baseline*100:.1f}%, {self._augmented_label} "
            f"{self._augmented*100:.1f}%. {self._caption}"
        )
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(ls.SURFACE))

            if self._baseline is None or self._augmented is None:
                painter.setFont(QFont("Segoe UI", 11))
                painter.setPen(QColor(ls.MUTED))
                painter.drawText(
                    QRectF(0, 0, w, h),
                    Qt.AlignmentFlag.AlignCenter,
                    "Chưa có kết quả thí nghiệm.\nBấm 'Chạy Thí Nghiệm So Sánh' để bắt đầu!",
                )
                return

            margin_left = 130
            margin_right = 60
            margin_top = 14
            row_gap = 34
            bar_h = 22

            plot_w = max(10, w - margin_left - margin_right)

            def draw_bar(y: float, value: float, label: str, color: QColor) -> None:
                # Nhãn trái
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
                painter.setPen(QColor(ls.BODY))
                painter.drawText(
                    QRectF(0, y, margin_left - 10, bar_h),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )
                # Track nền
                painter.setPen(Qt.PenStyle.NoPen)
                _track = QColor(ls.BORDER)
                _track.setAlpha(80)
                painter.setBrush(_track)
                painter.drawRoundedRect(QRectF(margin_left, y, plot_w, bar_h), 6, 6)
                # Thanh giá trị
                bar_len = max(6.0, min(1.0, max(0.0, value)) * plot_w)
                painter.setBrush(color)
                painter.drawRoundedRect(QRectF(margin_left, y, bar_len, bar_h), 6, 6)
                # Giá trị %
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QColor(ls.INK))
                painter.drawText(
                    QRectF(margin_left + plot_w + 4, y, margin_right, bar_h),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"{value*100:.1f}%",
                )

            _baseline_col = QColor(ls.MUTED)
            _baseline_col.setAlpha(200)
            draw_bar(float(margin_top), self._baseline, self._baseline_label, _baseline_col)
            draw_bar(float(margin_top + row_gap), self._augmented, self._augmented_label, QColor(ls.ACCENT))

            # Caption kết luận
            caption_y = margin_top + row_gap * 2 + 6
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(ls.ACCENT_NOTE_TEXT))
            painter.drawText(QRectF(10, caption_y, w - 20, h - caption_y - 6),
                             Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                             self._caption)

            # Trục % mốc 0/50/100 (9pt = sàn cỡ chữ 11px của hệ thống)
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(ls.MUTED))
            for frac in (0.0, 0.5, 1.0):
                gx = margin_left + frac * plot_w
                painter.drawLine(int(gx), margin_top - 4, int(gx), margin_top + row_gap + bar_h + 4)
                painter.drawText(QRectF(gx - 15, margin_top + row_gap + bar_h + 5, 30, 14),
                                 Qt.AlignmentFlag.AlignCenter, f"{frac*100:.0f}%")
        finally:
            painter.end()

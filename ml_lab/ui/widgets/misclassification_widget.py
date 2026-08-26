"""
ml_lab/ui/widgets/misclassification_widget.py — "Xem tại sao máy nhầm".

Liệt kê các mẫu tập kiểm tra bị dự đoán sai; chọn một mẫu để xem dạng sóng thô
64×6 của chính cử chỉ đó — học sinh nhìn thấy bằng mắt vì sao hai cử chỉ dễ nhầm.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls

_CHANNELS = [
    ("ax", "Gia tốc X", QColor("#0668d1")),
    ("ay", "Gia tốc Y", QColor("#7c3aed")),
    ("az", "Gia tốc Z", QColor("#0d9488")),
    ("gx", "Xoay X", QColor("#d97706")),
    ("gy", "Xoay Y", QColor("#dc2626")),
    ("gz", "Xoay Z", QColor("#4d7c0f")),
]


class _WaveCanvas(QWidget):
    """Vẽ dạng sóng 6 kênh chồng lên nhau, mỗi kênh tự chuẩn hóa."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(260)
        self._window: np.ndarray | None = None

    def set_window(self, window: np.ndarray | None) -> None:
        self._window = window
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor("#16181d"))

            if self._window is None or self._window.size == 0:
                painter.setPen(QColor("#8494a7"))
                painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                                 "Chọn một mẫu bị sai ở bên trái để xem dạng sóng.")
                return

            win = np.asarray(self._window, dtype=np.float32)
            n = win.shape[0]
            margin_l, margin_r, margin_t, margin_b = 46, 10, 8, 8
            plot_w = max(10.0, w - margin_l - margin_r)
            strip_h = (h - margin_t - margin_b) / 6.0

            # nhãn kênh
            painter.setFont(ls.font(ls.FS_MICRO, 600))
            for ci, (code, label, color) in enumerate(_CHANNELS):
                y_top = margin_t + ci * strip_h
                painter.setPen(QColor(color))
                painter.drawText(QRectF(4, y_top, margin_l - 8, strip_h),
                                 Qt.AlignmentFlag.AlignVCenter, label)

            x0 = margin_l
            for ci, (code, _label, color) in enumerate(_CHANNELS):
                y_top = margin_t + ci * strip_h
                y_mid = y_top + strip_h / 2.0

                # vạch 0
                painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
                painter.drawLine(int(x0), int(y_mid), int(x0 + plot_w), int(y_mid))

                vals = win[:, ci]
                vmin, vmax = float(vals.min()), float(vals.max())
                span = (vmax - vmin) or 1.0
                amp = strip_h * 0.42

                painter.setPen(QPen(color, 1.4))
                path_pts = []
                for i in range(n):
                    x = x0 + (i / max(1, n - 1)) * plot_w
                    y = y_mid - ((float(vals[i]) - vmin) / span - 0.5) * 2 * amp
                    path_pts.append(QPointF(x, y))
                for i in range(1, len(path_pts)):
                    painter.drawLine(path_pts[i - 1], path_pts[i])

            # trục thời gian
            painter.setPen(QColor(255, 255, 255, 90))
            painter.setFont(ls.font(ls.FS_MICRO))
            painter.drawText(QRectF(0, h - margin_b - 14, w, 14),
                             Qt.AlignmentFlag.AlignRight, "64 mẫu · ~1.3 giây")
        finally:
            painter.end()


class MisclassificationWidget(QWidget):
    """Danh sách mẫu bị sai + xem dạng sóng của mẫu được chọn."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.lbl_title = QLabel("XEM TẠI SAO MÁY NHẦM (các mẫu kiểm tra bị sai)")
        self.lbl_title.setStyleSheet(ls.section_label())
        layout.addWidget(self.lbl_title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.list_errors = QListWidget()
        self.list_errors.setStyleSheet(
            f"QListWidget {{ background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_MD}px; {ls.font(ls.FS_CAPTION)} color: {ls.BODY}; }} "
            f"QListWidget::item {{ padding: 6px 8px; }} "
            f"QListWidget::item:selected {{ background: {ls.ACCENT_TINT_STRONG}; color: {ls.INK}; }}"
        )
        self.list_errors.currentRowChanged.connect(self._on_select)
        splitter.addWidget(self.list_errors)

        right = QWidget()
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(4)

        self.lbl_compare = QLabel("—")
        self.lbl_compare.setWordWrap(True)
        self.lbl_compare.setStyleSheet(ls.font(ls.FS_BODY, 600) + f"color: {ls.BODY}; border: none; background: transparent;")
        r_layout.addWidget(self.lbl_compare)

        self.canvas = _WaveCanvas()
        r_layout.addWidget(self.canvas, stretch=1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        layout.addWidget(splitter, stretch=1)

    def clear(self) -> None:
        self.list_errors.clear()
        self.canvas.set_window(None)
        self.lbl_compare.setText("—")
        self.lbl_title.setText("XEM TẠI SAO MÁY NHẦM (các mẫu kiểm tra bị sai)")

    def set_result(self, result: Any) -> None:
        self.clear()
        samples = getattr(result, "val_samples", None)
        preds = getattr(result, "val_predictions", None)
        if not samples or preds is None:
            self.lbl_summary_unavailable()
            return

        try:
            preds = np.asarray(preds).ravel()
        except Exception:
            self.lbl_summary_unavailable()
            return

        class_names = list(result.class_names)
        errors = [(i, s) for i, s in enumerate(samples) if i < len(preds) and s[1] != int(preds[i])]

        if not errors:
            self.lbl_title.setText("XEM TẠI SAO MÁY NHẦM — không có mẫu nào bị sai!")
            self.lbl_compare.setText(
                "Tuyệt vời: mô hình đoán đúng toàn bộ tập kiểm tra. "
                "Hãy thử vung theo cách khác người để kiểm tra thêm."
            )
            return

        self.lbl_title.setText(f"XEM TẠI SAO MÁY NHẦM — {len(errors)} mẫu bị sai trên tập kiểm tra")
        for idx, (window, true_label) in errors:
            pred = int(preds[idx])
            true_name = class_names[true_label] if true_label < len(class_names) else str(true_label)
            pred_name = class_names[pred] if pred < len(class_names) else str(pred)
            item = QListWidgetItem(f"Mẫu #{idx + 1} · thật: {true_name} → máy đoán: {pred_name}")
            item.setData(Qt.ItemDataRole.UserRole, (window, true_name, pred_name))
            self.list_errors.addItem(item)

        self.list_errors.setCurrentRow(0)

    def lbl_summary_unavailable(self) -> None:
        self.lbl_compare.setText("Chưa có dữ liệu mẫu để phân tích (huấn luyện bằng phiên bản cũ?).")

    def _on_select(self, row: int) -> None:
        item = self.list_errors.item(row)
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        window, true_name, pred_name = data
        self.canvas.set_window(window)
        self.lbl_compare.setText(
            f"Máy đoán “{pred_name}” trong khi thật ra là “{true_name}”. "
            "So sánh dạng sóng này với cử chỉ thường ngày của hai thần chú để thấy điểm giống nhau."
        )

"""
ml_lab/ui/widgets/advice_card.py — Thẻ Chẩn Đoán AI Coach (Auto-Explain).

Sau mỗi lần huấn luyện, hiển thị các chẩn đoán tự động dạng thẻ màu:
- Xanh lá: điểm sáng / sẵn sàng triển khai
- Cam    : cần chú ý / gợi ý cải thiện
- Đỏ     : vấn đề nghiêm trọng cần sửa
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

import ml_lab.ui.lab_style as ls
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.core.result_advisor import AdviceItem, generate_advice

_SEVERITY_STYLE = {
    "good": ("✓", "rgba(47, 158, 87, 0.10)", "#166534"),
    "warn": ("!", "rgba(217, 119, 6, 0.12)", "#92400e"),
    "bad": ("×", "rgba(220, 38, 38, 0.09)", "#991b1b"),
}


class _AdviceRow(QFrame):
    """1 dòng chẩn đoán."""

    def __init__(self, item: AdviceItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        icon, bg, fg = _SEVERITY_STYLE.get(item.severity, ("💡", "rgba(0, 122, 255, 0.08)", "#1e3a8a"))
        self.setStyleSheet(f"background: {bg}; border-radius: 8px;")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)

        lbl_icon = QLabel(icon)
        lbl_icon.setFixedWidth(22)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(lbl_icon)

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(1)
        lbl_title = QLabel(item.title)
        lbl_title.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {fg}; border: none; background: transparent;")
        lbl_detail = QLabel(item.detail)
        lbl_detail.setWordWrap(True)
        lbl_detail.setStyleSheet(f"font-size: 11px; color: {fg}; border: none; background: transparent;")
        text_vbox.addWidget(lbl_title)
        text_vbox.addWidget(lbl_detail)
        row.addLayout(text_vbox, stretch=1)


class AdviceCardWidget(QFrame):
    """
    Thẻ chẩn đoán & lời khuyên sau huấn luyện.
    Cách dùng: advice_card.set_result(result) sau khi train xong.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            ".QFrame { background: white; border: 1px solid #e4e9f0; border-radius: 10px; padding: 10px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 6)
        layout.setSpacing(6)

        lbl_title = QLabel("AI COACH — CHẨN ĐOÁN & LỜI KHUYÊN")
        lbl_title.setStyleSheet(f"{ls.font(ls.FS_CAPTION, 800)} color: {ls.ACCENT}; border: none; background: transparent;")
        layout.addWidget(lbl_title)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(5)
        layout.addLayout(self._rows_layout)

        self.lbl_empty = QLabel(
            "Huấn luyện xong, AI Coach sẽ phân tích kết quả và tư vấn bước tiếp theo tại đây."
        )
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setStyleSheet("color: #5b6b7f; font-size: 11px; font-style: italic; border: none;; border: none; background: transparent;")
        self._rows_layout.addWidget(self.lbl_empty)

    def set_result(self, result: TrainClassicResult) -> None:
        self.clear()
        try:
            items = generate_advice(result)
        except Exception:
            items = []
        if not items:
            return
        for item in items[:7]:
            self._rows_layout.addWidget(_AdviceRow(item))
        self.lbl_empty.setVisible(False)

    def clear(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self.lbl_empty:
                w.deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        if self.lbl_empty.parent() is None:
            self._rows_layout.addWidget(self.lbl_empty)
        self.lbl_empty.setVisible(True)

"""
ml_lab/ui/widgets/class_breakdown_widget.py — Bảng "Thần chú nào yếu nhất?".

Liệt kê từng lớp sắp xếp từ YẾU nhất, kèm thanh độ chính xác và gợi ý hành
động cụ thể (ghi thêm bao nhiêu mẫu, nhầm với ai).
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ml_lab.core.model_card import per_class_stats


class ClassBreakdownWidget(QWidget):
    """Bảng chẩn đoán từng lớp — yếu nhất đứng đầu, kèm gợi ý hành động."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.lbl_title = QLabel("THẦN CHÚ NÀO YẾU NHẤT?")
        self.lbl_title.setStyleSheet(ls.section_label())
        layout.addWidget(self.lbl_title)

        self.lbl_summary = QLabel("Huấn luyện xong, bảng này sẽ chỉ lớp yếu nhất và cách khắc phục.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
        layout.addWidget(self.lbl_summary)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Thần chú", "Đoán đúng", "Số mẫu", "Gợi ý hành động"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setStyleSheet(ls.DATA_TABLE)
        layout.addWidget(self.table)

    def clear(self) -> None:
        self.table.setRowCount(0)
        self.lbl_summary.setText("Huấn luyện xong, bảng này sẽ chỉ lớp yếu nhất và cách khắc phục.")

    def set_result(self, result: Any) -> None:
        try:
            stats = per_class_stats(np.asarray(result.confusion_matrix), list(result.class_names))
        except Exception:
            self.clear()
            return

        if not stats:
            self.clear()
            return

        worst = stats[0]
        self.lbl_summary.setText(
            f"Yếu nhất: “{worst['name']}” — chỉ đoán đúng {worst['accuracy']*100:.0f}%. "
            "Làm theo cột Gợi ý để cải thiện rồi huấn luyện lại."
        )

        self.table.setRowCount(len(stats))
        for r, st in enumerate(stats):
            name_item = QTableWidgetItem(st["name"])
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(r, 0, name_item)

            acc = st["accuracy"]
            acc_item = QTableWidgetItem(f"{acc*100:.0f}%")
            acc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            acc_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if acc >= 0.9:
                acc_item.setBackground(QColor(ls.SUCCESS_TINT_HEX))
                acc_item.setForeground(QColor(ls.SUCCESS))
            elif acc >= 0.75:
                acc_item.setBackground(QColor(ls.WARNING_TINT_HEX))
                acc_item.setForeground(QColor(ls.WARNING))
            else:
                acc_item.setBackground(QColor(ls.DANGER_TINT_HEX))
                acc_item.setForeground(QColor(ls.DANGER))
            self.table.setItem(r, 1, acc_item)

            support_item = QTableWidgetItem(str(st["support"]))
            support_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, support_item)

            hint_item = QTableWidgetItem(st["hint"])
            hint_item.setToolTip(st["hint"])
            self.table.setItem(r, 3, hint_item)

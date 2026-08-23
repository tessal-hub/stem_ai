"""
ml_lab/ui/widgets/confusion_matrix_widget.py — Ma trận nhầm lẫn và chỉ số phân lớp.

Hiển thị Validation Accuracy, Cross-Validation, Train-Val gap và Heatmap trực quan.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ConfusionMatrixWidget(QWidget):
    """
    Widget hiển thị Ma trận nhầm lẫn (Confusion Matrix) và bảng điểm chi tiết.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Metrics Header Frame ────────────────────────────
        self.metrics_card = QFrame()
        self.metrics_card.setStyleSheet("background: rgba(0, 122, 255, 0.06); border-radius: 8px; padding: 8px;")
        m_layout = QHBoxLayout(self.metrics_card)
        m_layout.setContentsMargins(10, 6, 10, 6)
        m_layout.setSpacing(16)

        # Val Accuracy
        vbox_val = QVBoxLayout()
        vbox_val.setSpacing(1)
        lbl_v_title = QLabel("VAL ACCURACY")
        lbl_v_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #007aff;")
        self.lbl_val_acc = QLabel("--")
        self.lbl_val_acc.setStyleSheet("font-size: 20px; font-weight: 800; color: #007aff;")
        vbox_val.addWidget(lbl_v_title)
        vbox_val.addWidget(self.lbl_val_acc)
        m_layout.addLayout(vbox_val)

        # CV Score
        vbox_cv = QVBoxLayout()
        vbox_cv.setSpacing(1)
        lbl_cv_title = QLabel("CROSS-VALIDATION")
        lbl_cv_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #34c759;")
        self.lbl_cv_score = QLabel("--")
        self.lbl_cv_score.setStyleSheet("font-size: 16px; font-weight: 700; color: #34c759;")
        vbox_cv.addWidget(lbl_cv_title)
        vbox_cv.addWidget(self.lbl_cv_score)
        m_layout.addLayout(vbox_cv)

        # Train Accuracy & Gap
        vbox_tr = QVBoxLayout()
        vbox_tr.setSpacing(1)
        lbl_tr_title = QLabel("TRAIN GAP")
        lbl_tr_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #8e8e93;")
        self.lbl_train_gap = QLabel("--")
        self.lbl_train_gap.setStyleSheet("font-size: 14px; font-weight: 600; color: #8e8e93;")
        vbox_tr.addWidget(lbl_tr_title)
        vbox_tr.addWidget(self.lbl_train_gap)
        m_layout.addLayout(vbox_tr)

        layout.addWidget(self.metrics_card)

        # ── Confusion Matrix Table ──────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; } "
            "QHeaderView::section { font-weight: 600; font-size: 11px; padding: 4px; }"
        )
        layout.addWidget(self.table, stretch=1)

    def set_results(
        self,
        cm: np.ndarray,
        class_names: list[str],
        val_acc: float,
        train_acc: float,
        cv_mean: float,
        cv_std: float,
    ) -> None:
        self.lbl_val_acc.setText(f"{val_acc * 100:.1f}%")
        self.lbl_cv_score.setText(f"{cv_mean * 100:.1f}% ± {cv_std * 100:.1f}%")

        gap = (train_acc - val_acc) * 100
        gap_sign = "+" if gap >= 0 else ""
        gap_status = " (Khớp tốt)" if abs(gap) < 5.0 else (" (Dễ Overfit)" if gap > 10.0 else "")
        self.lbl_train_gap.setText(f"Train {train_acc*100:.1f}% ({gap_sign}{gap:.1f}%{gap_status})")

        num_classes = len(class_names)
        self.table.setRowCount(num_classes)
        self.table.setColumnCount(num_classes)
        self.table.setHorizontalHeaderLabels([f"Dự đoán\n{name}" for name in class_names])
        self.table.setVerticalHeaderLabels([f"Thực tế\n{name}" for name in class_names])

        max_val = max(1, int(np.max(cm))) if cm.size > 0 else 1

        for r in range(num_classes):
            for c in range(num_classes):
                val = int(cm[r, c]) if r < cm.shape[0] and c < cm.shape[1] else 0
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold if val > 0 else QFont.Weight.Normal))

                if r == c and val > 0:
                    # True Positives: Green intensity
                    alpha = int(40 + (val / max_val) * 160)
                    item.setBackground(QColor(52, 199, 89, alpha))
                    item.setForeground(QColor(0, 80, 20) if alpha < 120 else QColor(255, 255, 255))
                elif val > 0:
                    # Confusion Errors: Red intensity
                    alpha = int(50 + (val / max_val) * 150)
                    item.setBackground(QColor(255, 59, 48, alpha))
                    item.setForeground(QColor(255, 255, 255))
                else:
                    item.setForeground(QColor(160, 160, 160))

                self.table.setItem(r, c, item)

"""
ml_lab/ui/tabs/tab_history.py — Tab 6: Nhật Ký Thử Nghiệm & Lịch Sử Huấn Luyện (Experiment Store).

Lưu trữ và duyệt lại toàn bộ các lần thử nghiệm mô hình đã chạy trong quá khứ.
"""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ml_lab.core.experiment_store import ExperimentStore


class TabHistory(QWidget):
    """
    Tab Lịch Sử Thử Nghiệm.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.experiment_store = ExperimentStore()
        self._init_ui()
        self.reload_history()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Box
        header_box = QFrame()
        header_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header_box)

        lbl = QLabel("📜 NHẬT KÝ THỬ NGHIỆM HUẤN LUYỆN (EXPERIMENT HISTORY)")
        lbl.setStyleSheet("font-weight: 700; color: #007aff; font-size: 12px;")
        h_layout.addWidget(lbl)
        h_layout.addStretch()

        btn_clear = QPushButton("🗑️ Xóa Tất Cả")
        btn_clear.setStyleSheet(
            "QPushButton { padding: 6px 12px; font-weight: 600; border-radius: 5px; background: #fff1f2; color: #e11d48; border: 1px solid #fecdd3; } "
            "QPushButton:hover { background: #ffe4e6; }"
        )
        btn_clear.clicked.connect(self._clear_history)
        h_layout.addWidget(btn_clear)

        btn_refresh = QPushButton("🔄 Tải lại")
        btn_refresh.setStyleSheet(
            "QPushButton { padding: 6px 12px; font-weight: 600; border-radius: 5px; background: #f8fafc; border: 1px solid #cbd5e1; } "
            "QPushButton:hover { background: #f1f5f9; }"
        )
        btn_refresh.clicked.connect(self.reload_history)
        h_layout.addWidget(btn_refresh)

        layout.addWidget(header_box)

        # Table Card
        table_box = QFrame()
        table_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        t_layout = QVBoxLayout(table_box)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Thời Gian", "Mô Hình", "Val Accuracy", "CV Score", "Số Đặc Trưng", "Độ Trễ ESP32"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; } "
            "QHeaderView::section { font-weight: 700; font-size: 11px; padding: 8px; background: #f8fafc; color: #475569; }"
        )
        t_layout.addWidget(self.table, stretch=1)

        layout.addWidget(table_box, stretch=1)

    def reload_history(self) -> None:
        exps = self.experiment_store.list_experiments()
        self.table.setRowCount(len(exps))

        for r_idx, exp in enumerate(exps):
            ts = exp.get("timestamp", "")[:19].replace("T", " ")
            name = exp.get("algo_name", exp.get("algo", ""))
            val_acc = exp.get("val_accuracy", 0.0)
            cv_mean = exp.get("cv_mean", 0.0)
            n_feat = exp.get("num_features", 0)
            bench = exp.get("benchmark", {})
            lat = bench.get("mcu_latency_ms", 0.0)

            self.table.setItem(r_idx, 0, QTableWidgetItem(ts))
            
            name_item = QTableWidgetItem(name)
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            self.table.setItem(r_idx, 1, name_item)

            acc_item = QTableWidgetItem(f"{val_acc*100:.1f}%")
            acc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            acc_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            acc_item.setBackground(QColor(52, 199, 89, 45))
            self.table.setItem(r_idx, 2, acc_item)

            cv_item = QTableWidgetItem(f"{cv_mean*100:.1f}%")
            cv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 3, cv_item)

            feat_item = QTableWidgetItem(f"{n_feat} đặc trưng")
            feat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 4, feat_item)

            lat_item = QTableWidgetItem(f"{lat:.2f} ms")
            lat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 5, lat_item)

    def _clear_history(self) -> None:
        if self.table.rowCount() == 0:
            return
        ans = QMessageBox.question(
            self,
            "Xác Nhận Xóa",
            "Bạn có chắc chắn muốn xóa toàn bộ lịch sử thử nghiệm không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            try:
                hist_file = self.experiment_store.store_path
                if hist_file.exists():
                    hist_file.write_text("[]", encoding="utf-8")
                self.reload_history()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa lịch sử: {exc}")

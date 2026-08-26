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

import ml_lab.ui.lab_style as ls
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
        header_box.setStyleSheet(ls.card())
        h_layout = QHBoxLayout(header_box)

        lbl = QLabel("CÁC LẦN HUẤN LUYỆN ĐÃ LƯU")
        lbl.setStyleSheet(ls.font(ls.FS_BODY, 800) + f"color: {ls.INK};; border: none; background: transparent;")
        h_layout.addWidget(lbl)
        h_layout.addStretch()

        btn_clear = QPushButton("Xóa tất cả")
        btn_clear.setStyleSheet(f"QPushButton {{ padding: 6px 12px; font-weight: 600; border-radius: {ls.RADIUS_SM}px; background: {ls.DANGER_TINT}; color: {ls.DANGER}; border: none; }} QPushButton:hover {{ background: rgba(220, 38, 38, 0.15); }}")
        btn_clear.clicked.connect(self._clear_history)
        h_layout.addWidget(btn_clear)

        btn_refresh = QPushButton("Tải lại")
        btn_refresh.setStyleSheet(ls.BTN_SECONDARY)
        btn_refresh.clicked.connect(self.reload_history)
        h_layout.addWidget(btn_refresh)

        layout.addWidget(header_box)

        # Table Card
        table_box = QFrame()
        table_box.setStyleSheet(ls.card())
        t_layout = QVBoxLayout(table_box)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Thời điểm", "Mô hình", "Đoán đúng (dữ liệu mới)", "Kiểm tra chéo", "Số đặc trưng", "Tốc độ trên ESP32"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(ls.DATA_TABLE)
        t_layout.addWidget(self.table, stretch=3)

        lbl_lb = QLabel("BẢNG VÀNG — KỶ LỤC CỦA TỪNG THUẬT TOÁN")
        lbl_lb.setStyleSheet(f"{ls.font(ls.FS_CAPTION, 700)} color: {ls.WARNING}; margin-top: 6px; border: none; background: transparent;")
        t_layout.addWidget(lbl_lb)

        self.table_leaderboard = QTableWidget()
        self.table_leaderboard.setColumnCount(5)
        self.table_leaderboard.setHorizontalHeaderLabels([
            "Hạng", "Mô hình", "Đoán đúng cao nhất", "Kiểm tra chéo", "Số đặc trưng"
        ])
        self.table_leaderboard.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_leaderboard.verticalHeader().setVisible(False)
        self.table_leaderboard.setMaximumHeight(170)
        self.table_leaderboard.setStyleSheet(
            ls.DATA_TABLE
            + f"QHeaderView::section {{ background: {ls.SURFACE_GOLD}; color: {ls.WARNING}; }}"
        )
        t_layout.addWidget(self.table_leaderboard, stretch=1)

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

        self._populate_leaderboard()

    def _populate_leaderboard(self) -> None:
        """Đổ bảng vàng: mô hình tốt nhất từng thuật toán theo Val Accuracy."""
        try:
            board = sorted(
                self.experiment_store.get_leaderboard(),
                key=lambda e: e.get("val_accuracy", 0.0),
                reverse=True,
            )
        except Exception:
            board = []

        medals = ["1", "2", "3"]
        self.table_leaderboard.setRowCount(len(board))
        for r_idx, exp in enumerate(board):
            medal = medals[r_idx] if r_idx < len(medals) else f"#{r_idx + 1}"
            rank_item = QTableWidgetItem(medal)
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_leaderboard.setItem(r_idx, 0, rank_item)

            name_item = QTableWidgetItem(exp.get("algo_name", exp.get("algo", "")))
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table_leaderboard.setItem(r_idx, 1, name_item)

            acc_item = QTableWidgetItem(f"{exp.get('val_accuracy', 0.0) * 100:.1f}%")
            acc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            acc_item.setForeground(QColor(ls.SUCCESS_TEXT))
            self.table_leaderboard.setItem(r_idx, 2, acc_item)

            cv_item = QTableWidgetItem(f"{exp.get('cv_mean', 0.0) * 100:.1f}%")
            cv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_leaderboard.setItem(r_idx, 3, cv_item)

            feat_item = QTableWidgetItem(str(exp.get("num_features", 0)))
            feat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_leaderboard.setItem(r_idx, 4, feat_item)

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
                removed = self.experiment_store.clear_all()
                self.reload_history()
                if removed > 0:
                    QMessageBox.information(self, "Đã Xóa", f"Đã xóa {removed} bản ghi thử nghiệm.")
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa lịch sử: {exc}")

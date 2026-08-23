"""
ml_lab/ui/tabs/tab_model_arena.py — Tab 4: Đấu Trường Mô Hình & So Sánh Hiệu Năng MCU.

Cho phép huấn luyện đối đầu đồng loạt tất cả các thuật toán chỉ trong 1-click và so sánh toàn diện
giữa Độ chính xác (Accuracy), Độ trễ thực thi (Latency), RAM, Flash và Tính giải thích.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ml_lab.core.hyperparam_schema import (
    DecisionTreeConfig,
    GradientBoostingConfig,
    KNNConfig,
    LDAConfig,
    LogisticRegressionConfig,
    MLPConfig,
    NaiveBayesConfig,
    RandomForestConfig,
    SVMConfig,
)
from ml_lab.core.pipeline import train_classic_model, TrainClassicResult
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.widgets.flash_dialog import FlashDialog


class ArenaWorker(QThread):
    sig_progress = pyqtSignal(int, str)
    sig_finished = pyqtSignal(list)  # list[TrainClassicResult]
    sig_error = pyqtSignal(str)

    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir

    def run(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                self.sig_progress.emit(10, "Đang chia dataset file-level...")
                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.2, window_size=64, step_size=16
                )
                if len(class_names) < 2:
                    self.sig_error.emit("Cần ít nhất 2 lớp cử chỉ để so sánh.")
                    return

                extractor = ClassicFeatureExtractor()
                X_train, y_train = extractor.extract_from_samples(train_wins)
                X_val, y_val = extractor.extract_from_samples(val_wins)

                algos = [
                    ("tree", DecisionTreeConfig(max_depth=4)),
                    ("logistic", LogisticRegressionConfig(c=1.0)),
                    ("knn", KNNConfig(k=3)),
                    ("forest", RandomForestConfig(n_estimators=5, max_depth=4)),
                    ("gbdt", GradientBoostingConfig(n_estimators=5, max_depth=3)),
                    ("svm", SVMConfig(c=1.0, kernel="rbf")),
                    ("nb", NaiveBayesConfig()),
                    ("lda", LDAConfig()),
                    ("mlp", MLPConfig(hidden_units=16)),
                ]

                results: list[TrainClassicResult] = []
                for i, (algo_key, cfg) in enumerate(algos):
                    self.sig_progress.emit(int(15 + i * 9), f"Đang huấn luyện {algo_key.upper()}...")
                    res = train_classic_model(
                        X_train, y_train, X_val, y_val, class_names, extractor.feature_names, algo=algo_key, config=cfg
                    )
                    results.append(res)

                self.sig_progress.emit(100, "Hoàn tất đấu trường!")
                self.sig_finished.emit(results)
        except Exception as exc:
            self.sig_error.emit(str(exc))


class TabModelArena(QWidget):
    """
    Tab Đấu Trường So Sánh Mô Hình.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._worker: ArenaWorker | None = None
        self._results: list[TrainClassicResult] = []

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header Box
        header_box = QFrame()
        header_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header_box)

        t_vbox = QVBoxLayout()
        lbl_t = QLabel("⚔️ ĐẤU TRƯỜNG SO SÁNH CÁC THUẬT TOÁN HỌC MÁY (MODEL ARENA)")
        lbl_t.setStyleSheet("font-weight: 700; color: #007aff; font-size: 13px;")
        lbl_d = QLabel("Huấn luyện đối đầu đồng loạt tất cả mô hình trên cùng một tập dữ liệu.")
        lbl_d.setStyleSheet("color: #64748b; font-size: 11px;")
        t_vbox.addWidget(lbl_t)
        t_vbox.addWidget(lbl_d)
        h_layout.addLayout(t_vbox, stretch=1)

        self.btn_run_arena = QPushButton("⚔️ Khởi Động Đấu Trường (Train All)")
        self.btn_run_arena.setStyleSheet(
            "QPushButton { background: #007aff; color: white; font-weight: 700; padding: 10px 18px; border-radius: 6px; border: none; } "
            "QPushButton:hover { background: #0066d6; } "
            "QPushButton:pressed { background: #0052ad; }"
        )
        self.btn_run_arena.clicked.connect(self.run_arena)
        h_layout.addWidget(self.btn_run_arena)

        layout.addWidget(header_box)

        # Comparison Table Card
        table_box = QFrame()
        table_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        tb_layout = QVBoxLayout(table_box)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Hạng", "Mô Hình", "Val Accuracy", "CV Score", "Độ Trễ ESP32", "RAM Tiêu Tốn", "Kích Thước Flash", "Thao Tác"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; } "
            "QHeaderView::section { font-weight: 700; font-size: 11px; padding: 8px; background: #f8fafc; color: #475569; }"
        )
        tb_layout.addWidget(self.table, stretch=1)

        # Pedagogical Comparison Card
        pedagogy_box = QFrame()
        pedagogy_box.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 10px 14px;")
        p_layout = QVBoxLayout(pedagogy_box)
        p_layout.setSpacing(4)

        lbl_p_title = QLabel("🎓 <b>Bí Quyết Chọn Mô Hình Cho Thiết Bị Nhúng (Embedded AI Strategy)</b>:")
        lbl_p_title.setStyleSheet("font-size: 12px; color: #1e3a8a;")
        lbl_p_desc = QLabel(
            "• <b>Tốc độ tức thì &lt;0.02ms</b>: <b>Gaussian Naive Bayes (GNB)</b>, <b>Cây Quyết Định</b>, <b>Hồi quy Logistic</b>, <b>LDA</b>.<br>"
            "• <b>Độ chính xác cao & chống rung lắc tay</b>: <b>Random Forest</b>, <b>Gradient Boosting (GBDT)</b>.<br>"
            "• <b>Mạng nơ-ron thông minh không cần TFLM</b>: <b>Shallow MLP</b> (tầng ẩn ReLU thuần C++).<br>"
            "• <b>Ranh giới cong phi tuyến phức tạp</b>: <b>SVM (RBF Kernel)</b>."
        )
        lbl_p_desc.setWordWrap(True)
        lbl_p_desc.setStyleSheet("font-size: 11px; color: #1e3a8a; line-height: 1.4;")
        p_layout.addWidget(lbl_p_title)
        p_layout.addWidget(lbl_p_desc)
        tb_layout.addWidget(pedagogy_box)

        layout.addWidget(table_box, stretch=1)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(5)
        layout.addWidget(self.progress_bar)

    def run_arena(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa Đủ Dữ Liệu",
                f"Hiện tại chỉ có {len(counts)} phép thuật trong dataset/spells/.\n\n"
                "Cần ít nhất 2 lớp cử chỉ khác nhau để khởi động đấu trường so sánh mô hình.",
            )
            return

        self.btn_run_arena.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        self._worker = ArenaWorker(self.dataset_dir)
        self._worker.sig_progress.connect(lambda pct, msg: self.progress_bar.setValue(pct))
        self._worker.sig_finished.connect(self._on_arena_finished)
        self._worker.sig_error.connect(self._on_arena_error)
        self._worker.start()

    def _on_arena_finished(self, results: list[TrainClassicResult]) -> None:
        self.btn_run_arena.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Sắp xếp theo Val Accuracy giảm dần
        sorted_results = sorted(results, key=lambda r: r.val_accuracy, reverse=True)
        self._results = sorted_results

        medals = ["🥇 Quán Quân", "🥈 Á Quân", "🥉 Hạng 3", "4️⃣ Hạng 4", "5️⃣ Hạng 5", "6️⃣ Hạng 6", "7️⃣ Hạng 7", "8️⃣ Hạng 8", "9️⃣ Hạng 9"]

        self.table.setRowCount(len(sorted_results))
        for r_idx, res in enumerate(sorted_results):
            bench = res.benchmark

            # Rank
            rank_text = medals[r_idx] if r_idx < len(medals) else f"#{r_idx+1}"
            rank_item = QTableWidgetItem(rank_text)
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(r_idx, 0, rank_item)

            # Model Name
            name_item = QTableWidgetItem(res.algo_name)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            self.table.setItem(r_idx, 1, name_item)

            # Accuracy
            val_acc_item = QTableWidgetItem(f"{res.val_accuracy * 100:.1f}%")
            val_acc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            val_acc_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if r_idx == 0:
                val_acc_item.setBackground(QColor(52, 199, 89, 60))
                val_acc_item.setForeground(QColor(22, 101, 52))
            else:
                val_acc_item.setBackground(QColor(52, 199, 89, 25))
            self.table.setItem(r_idx, 2, val_acc_item)

            # CV Score
            cv_item = QTableWidgetItem(f"{res.cv_mean * 100:.1f}% ± {res.cv_std * 100:.1f}%")
            cv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 3, cv_item)

            # Latency
            lat_item = QTableWidgetItem(f"{bench.get('mcu_latency_ms', 0):.2f} ms")
            lat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 4, lat_item)

            # RAM
            ram_item = QTableWidgetItem(f"{bench.get('mcu_ram_kb', 0):.1f} KB")
            ram_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 5, ram_item)

            # Flash
            flash_item = QTableWidgetItem(f"{bench.get('mcu_flash_kb', 0):.1f} KB")
            flash_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 6, flash_item)

            # Action Flash Button
            btn_f = QPushButton("🔥 Nạp Code")
            btn_f.setStyleSheet(
                "QPushButton { background: #34c759; color: white; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px; border: none; } "
                "QPushButton:hover { background: #2fb34f; }"
            )
            btn_f.clicked.connect(lambda _, r=res: self._flash_model(r))
            self.table.setCellWidget(r_idx, 7, btn_f)

    def _flash_model(self, result: TrainClassicResult) -> None:
        dlg = FlashDialog(result, self)
        dlg.exec()

    def _on_arena_error(self, msg: str) -> None:
        self.btn_run_arena.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi Đấu Trường", f"Không thể hoàn tất so sánh mô hình:\n{msg}")

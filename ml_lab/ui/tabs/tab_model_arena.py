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

import ml_lab.ui.lab_style as ls
from ml_lab.core.hyperparam_schema import (
    AdaBoostConfig,
    DecisionTreeConfig,
    ExtraTreesConfig,
    NearestCentroidConfig,
    QDAConfig,
    RandomForestConfig,
    RidgeConfig,
    SGDConfig,
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
    sig_warning = pyqtSignal(str)
    sig_finished = pyqtSignal(list)  # list[TrainClassicResult]
    sig_error = pyqtSignal(str)

    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    def run(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                self.sig_progress.emit(10, "Đang chia dataset file-level...")
                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
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
                    ("extra_trees", ExtraTreesConfig(n_estimators=5)),
                    ("adaboost", AdaBoostConfig(n_estimators=5)),
                    ("ridge", RidgeConfig(alpha=1.0)),
                    ("sgd", SGDConfig(alpha=0.0001)),
                    ("nearest_centroid", NearestCentroidConfig()),
                    ("qda", QDAConfig()),
                ]

                results: list[TrainClassicResult] = []
                failed: list[tuple[str, str]] = []
                step = 85 / max(1, len(algos))
                for i, (algo_key, cfg) in enumerate(algos):
                    self.sig_progress.emit(int(10 + i * step), f"Đang huấn luyện {algo_key.upper()}...")
                    try:
                        res = train_classic_model(
                            X_train, y_train, X_val, y_val, class_names, extractor.feature_names, algo=algo_key, config=cfg
                        )
                        results.append(res)
                    except Exception as algo_exc:
                        # 1 mô hình lỗi không cản trở 14 mô hình còn lại
                        failed.append((algo_key, str(algo_exc)))

                if not results:
                    self.sig_error.emit("Cả 15 mô hình đều lỗi. Chi tiết lỗi đầu tiên:\n" + (failed[0][1] if failed else ""))
                    return

                self.sig_progress.emit(100, "Hoàn tất đấu trường!")
                self.sig_finished.emit(results)
                if failed:
                    names = ", ".join(a for a, _ in failed)
                    self.sig_warning.emit(f"{len(failed)} mô hình bỏ qua vì lỗi: {names}")
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
        header_box.setStyleSheet(ls.card())
        h_layout = QHBoxLayout(header_box)

        t_vbox = QVBoxLayout()
        lbl_t = QLabel("SO SÁNH 15 THUẬT TOÁN — THUẬT NÀO PHÙ HỢP NHẤT?")
        lbl_t.setStyleSheet(f"{ls.font(ls.FS_SECTION, 700)} color: {ls.ACCENT}; border: none; background: transparent;")
        lbl_d = QLabel("Huấn luyện thử cả 15 thuật toán trên đúng dữ liệu của bạn, xếp hạng theo độ chính xác và tốc độ.")
        lbl_d.setStyleSheet("color: #5b6b7f; font-size: 11px;; border: none; background: transparent;")
        t_vbox.addWidget(lbl_t)
        t_vbox.addWidget(lbl_d)
        h_layout.addLayout(t_vbox, stretch=1)

        self.btn_run_arena = QPushButton("Huấn luyện thử cả 15 mô hình")
        self.btn_run_arena.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_run_arena.clicked.connect(self.run_arena)
        h_layout.addWidget(self.btn_run_arena)

        layout.addWidget(header_box)

        # Comparison Table Card
        table_box = QFrame()
        table_box.setStyleSheet(ls.card())
        tb_layout = QVBoxLayout(table_box)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Hạng", "Mô hình", "Đoán đúng (dữ liệu mới)", "Kiểm tra chéo", "Tốc độ ESP32", "RAM dùng", "Dung lượng Flash", ""
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(ls.DATA_TABLE)
        tb_layout.addWidget(self.table, stretch=1)

        # Pedagogical Comparison Card
        pedagogy_box = QFrame()
        pedagogy_box.setStyleSheet(f".QFrame {{ background: {ls.ACCENT_TINT}; border: none; border-radius: {ls.RADIUS_MD}px; padding: {ls.SP_2}px {ls.SP_3}px; }}")
        p_layout = QVBoxLayout(pedagogy_box)
        p_layout.setSpacing(4)

        lbl_p_title = QLabel("<b>Chọn mô hình thế nào cho hợp lý?</b>")
        lbl_p_title.setStyleSheet("font-size: 12px; color: #1e3a8a;; border: none; background: transparent;")
        lbl_p_desc = QLabel(
            "• Cần <b>phản ứng tức thì</b>: Naive Bayes, Cây quyết định, Hồi quy logistic, LDA.<br>"
            "• Cần <b>chính xác cao, ít bắt nhầm</b>: Random Forest, Gradient Boosting.<br>"
            "• Cần <b>mạng nơ-ron</b> mà không muốn cài TensorFlow: Shallow MLP.<br>"
            "• Cử chỉ <b>khó phân tách, cần ranh giới cong</b>: SVM (RBF)."
        )
        lbl_p_desc.setWordWrap(True)
        lbl_p_desc.setStyleSheet("font-size: 11px; color: #1e3a8a; line-height: 1.4;; border: none; background: transparent;")
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
        self._worker.sig_warning.connect(lambda msg: QMessageBox.warning(
            self, "Một số mô hình bỏ qua", msg + "\n\nCác mô hình còn lại vẫn được xếp hạng bình thường."
        ))
        self._worker.sig_error.connect(self._on_arena_error)
        self._worker.start()

    def _on_arena_finished(self, results: list[TrainClassicResult]) -> None:
        self.btn_run_arena.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Sắp xếp theo Val Accuracy giảm dần
        sorted_results = sorted(results, key=lambda r: r.val_accuracy, reverse=True)
        self._results = sorted_results

        medals = ["#1 · Quán quân", "#2 · Á quân", "#3", "#4", "#5", "#6", "#7", "#8", "#9",
                      "#10", "#11", "#12", "#13", "#14", "#15"]

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
                val_acc_item.setForeground(QColor(ls.SUCCESS_TEXT))
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
            btn_f = QPushButton("Nạp lên wand")
            btn_f.setStyleSheet(f"QPushButton {{ background: {ls.SUCCESS}; color: white; border: none; border-radius: {ls.RADIUS_SM}px; padding: 4px 10px; font-size: 11px; font-weight: 700; }} QPushButton:hover {{ background: {ls.SUCCESS_HOVER} }}")
            btn_f.clicked.connect(lambda _, r=res: self._flash_model(r))
            self.table.setCellWidget(r_idx, 7, btn_f)

    def _flash_model(self, result: TrainClassicResult) -> None:
        dlg = FlashDialog(result, self)
        dlg.exec()

    def _on_arena_error(self, msg: str) -> None:
        self.btn_run_arena.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi Đấu Trường", f"Không thể hoàn tất so sánh mô hình:\n{msg}")

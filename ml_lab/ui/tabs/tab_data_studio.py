"""
ml_lab/ui/tabs/tab_data_studio.py — Tab 1: Khám Phá Dữ Liệu & Phân Tích Đặc Trưng.

Cung cấp:
1. Phân phối đặc trưng (Histograms & Separability).
2. Phân tích tương quan đa chiều (Correlation Matrix & Redundant Pair Finder).
3. Studio Tăng Cường Dữ Liệu (Data Augmentation Studio with Gaussian noise, time-warping).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ml_lab.data.augmentation import augment_dataset_windows
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_analysis import compute_correlation_matrix, compute_feature_rankings
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.widgets.feature_distribution_widget import FeatureDistributionWidget
from ml_lab.ui.widgets.feature_importance_widget import FeatureImportanceWidget


class TabDataStudio(QWidget):
    """
    Tab Khám Phá Dữ Liệu, Tương Quan & Tăng Cường Mẫu.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._extractor = ClassicFeatureExtractor()
        self._cached_X: np.ndarray = np.empty((0, 0))
        self._cached_y: np.ndarray = np.empty((0,), dtype=np.int64)
        self._cached_class_names: list[str] = []
        self._cached_wins: dict[str, list[np.ndarray]] = {}

        self._init_ui()
        self.reload_dataset()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Column: Dataset Overview & Class Table ─────
        left_box = QFrame()
        left_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        l_layout = QVBoxLayout(left_box)

        lbl_l_title = QLabel("📁 DANH SÁCH CỬ CHỈ THẦN CHÚ")
        lbl_l_title.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        l_layout.addWidget(lbl_l_title)

        self.table_classes = QTableWidget()
        self.table_classes.setColumnCount(3)
        self.table_classes.setHorizontalHeaderLabels(["Thần Chú", "Số Mẫu", "Trạng Thái"])
        self.table_classes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_classes.verticalHeader().setVisible(False)
        self.table_classes.setStyleSheet(
            "QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; } "
            "QHeaderView::section { font-weight: 700; font-size: 11px; padding: 6px; background: #f8fafc; color: #475569; }"
        )
        l_layout.addWidget(self.table_classes, stretch=1)

        btn_reload = QPushButton("🔄 Tải lại Dữ liệu & Đặc trưng")
        btn_reload.setStyleSheet("padding: 8px; border-radius: 6px; background: #f8fafc; font-weight: 600; border: 1px solid #cbd5e1;")
        btn_reload.clicked.connect(self.reload_dataset)
        l_layout.addWidget(btn_reload)

        splitter.addWidget(left_box)

        # ── Right Column: Multi-Sub-Tab Data Science Studio ──
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet(
            "QTabBar::tab { font-weight: 600; padding: 8px 14px; } "
            "QTabBar::tab:selected { color: #007aff; border-bottom: 2px solid #007aff; }"
        )

        # Sub-tab 1: Feature Distribution & Separability
        tab_dist = QWidget()
        dist_layout = QVBoxLayout(tab_dist)
        dist_layout.setContentsMargins(8, 8, 8, 8)

        sel_row = QHBoxLayout()
        lbl_sel = QLabel("🔍 Chọn Đặc Trưng Khám Phá:")
        lbl_sel.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        self.combo_feat = QComboBox()
        self.combo_feat.setStyleSheet("padding: 5px; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px;")
        self.combo_feat.currentIndexChanged.connect(self._on_feature_selected)
        sel_row.addWidget(lbl_sel)
        sel_row.addWidget(self.combo_feat, stretch=1)
        dist_layout.addLayout(sel_row)

        self.dist_widget = FeatureDistributionWidget()
        dist_layout.addWidget(self.dist_widget, stretch=1)

        self.import_widget = FeatureImportanceWidget()
        dist_layout.addWidget(self.import_widget, stretch=1)

        right_tabs.addTab(tab_dist, "📊 Phân Phối & Tầm Quan Trọng")

        # Sub-tab 2: Correlation Matrix & Collinearity
        tab_corr = QWidget()
        corr_layout = QVBoxLayout(tab_corr)
        corr_layout.setContentsMargins(8, 8, 8, 8)

        lbl_c_info = QLabel("🔗 PHÂN TÍCH TƯƠNG QUAN & ĐẶC TRƯNG TRÙNG LẶP (|r| ≥ 0.85)")
        lbl_c_info.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        corr_layout.addWidget(lbl_c_info)

        self.table_corr = QTableWidget()
        self.table_corr.setColumnCount(4)
        self.table_corr.setHorizontalHeaderLabels(["Đặc Trưng A", "Đặc Trưng B", "Hệ Số Tương Quan (r)", "Đánh Giá"])
        self.table_corr.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_corr.verticalHeader().setVisible(False)
        self.table_corr.setStyleSheet("QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; }")
        corr_layout.addWidget(self.table_corr, stretch=1)

        lbl_corr_guide = QLabel(
            "💡 <b>Ý Nghĩa Sư Phạm</b>: Khi hai đặc trưng có tương quan $|r| > 0.90$ (ví dụ $a_z^{\\text{min}}$ và $a_z^{\\text{range}}$), chúng cung cấp thông tin trùng lặp. Bỏ bớt 1 trong 2 đặc trưng giúp mô hình nhẹ hơn và chạy nhanh hơn trên ESP32!"
        )
        lbl_corr_guide.setWordWrap(True)
        lbl_corr_guide.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 8px 10px; font-size: 11px; color: #1e3a8a;")
        corr_layout.addWidget(lbl_corr_guide)

        right_tabs.addTab(tab_corr, "🔗 Ma Trận Tương Quan (Collinearity)")

        # Sub-tab 3: Data Augmentation Studio
        tab_aug = QWidget()
        aug_layout = QVBoxLayout(tab_aug)
        aug_layout.setContentsMargins(8, 8, 8, 8)
        aug_layout.setSpacing(10)

        lbl_aug_title = QLabel("✨ BỘ SINH DỮ LIỆU TĂNG CƯỜNG TỰ ĐỘNG (DATA AUGMENTATION STUDIO)")
        lbl_aug_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        aug_layout.addWidget(lbl_aug_title)

        aug_card = QFrame()
        aug_card.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;")
        ac_layout = QVBoxLayout(aug_card)
        ac_layout.setSpacing(8)

        # Multiplier
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Hệ số nhân bản mẫu (Multiplier):"))
        self.spin_mult = QSpinBox()
        self.spin_mult.setRange(2, 10)
        self.spin_mult.setValue(3)
        self.spin_mult.setStyleSheet("padding: 4px 8px; font-weight: 700;")
        r1.addWidget(self.spin_mult)
        r1.addStretch()
        ac_layout.addLayout(r1)

        # Noise level
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Mức độ nhiễu rung tay (Gaussian Jitter Noise):"))
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0.01, 0.10)
        self.spin_noise.setSingleStep(0.01)
        self.spin_noise.setValue(0.03)
        self.spin_noise.setStyleSheet("padding: 4px 8px;")
        r2.addWidget(self.spin_noise)
        r2.addStretch()
        ac_layout.addLayout(r2)

        self.btn_run_aug = QPushButton("✨ Xem Thống Kê Dữ Liệu Sau Tăng Cường")
        self.btn_run_aug.setStyleSheet(
            "QPushButton { background: #007aff; color: white; font-weight: 700; padding: 8px 16px; border-radius: 6px; border: none; } "
            "QPushButton:hover { background: #0066d6; }"
        )
        self.btn_run_aug.clicked.connect(self._preview_augmentation)
        ac_layout.addWidget(self.btn_run_aug)

        self.lbl_aug_result = QLabel("Trạng thái: Sẵn sàng tăng cường dữ liệu.")
        self.lbl_aug_result.setStyleSheet("color: #166534; font-weight: 600; font-size: 11px;")
        ac_layout.addWidget(self.lbl_aug_result)

        aug_layout.addWidget(aug_card)

        lbl_aug_guide = QLabel(
            "💡 <b>Kỹ Thuật Tăng Cường Dữ Liệu (Data Augmentation)</b>: Bằng cách áp dụng nhiễu trắng và co giãn biên độ $\\pm 12\\%$, hệ thống mô phỏng hàng trăm lần vung gậy khác nhau của nhiều người, giúp mô hình học được ranh giới tổng quát hóa vững chắc hơn!"
        )
        lbl_aug_guide.setWordWrap(True)
        lbl_aug_guide.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 8px 10px; font-size: 11px; color: #1e3a8a;")
        aug_layout.addWidget(lbl_aug_guide)
        aug_layout.addStretch()

        right_tabs.addTab(tab_aug, "✨ Tăng Cường Dữ Liệu (Augmentation)")

        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter, stretch=1)

    def reload_dataset(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        self.table_classes.setRowCount(len(counts))

        for r_idx, (name, cnt) in enumerate(sorted(counts.items())):
            self.table_classes.setItem(r_idx, 0, QTableWidgetItem(name))
            
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_classes.setItem(r_idx, 1, cnt_item)

            badge = "✅ Đủ mẫu (≥5)" if cnt >= 5 else "⚠️ Cần thêm mẫu"
            badge_item = QTableWidgetItem(badge)
            badge_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if cnt >= 5:
                badge_item.setForeground(QColor(22, 101, 52))
            else:
                badge_item.setForeground(QColor(180, 83, 9))
            self.table_classes.setItem(r_idx, 2, badge_item)

        if len(counts) >= 2:
            try:
                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.0, window_size=64, step_size=16
                )
                self._cached_class_names = class_names
                self._cached_wins = train_wins

                all_wins: list[np.ndarray] = []
                all_labels: list[int] = []
                for cls_idx, cname in enumerate(class_names):
                    for w in train_wins.get(cname, []):
                        all_wins.append(w)
                        all_labels.append(cls_idx)

                X, y = self._extractor.extract_from_samples(train_wins)
                self._cached_X = X
                self._cached_y = y

                # Populate combo features
                self.combo_feat.clear()
                for f in self._extractor.feature_names:
                    self.combo_feat.addItem(f)

                # Importance
                rankings = compute_feature_rankings(X, y, self._extractor.feature_names)
                self.import_widget.set_data(rankings)

                # Correlation
                _, high_pairs = compute_correlation_matrix(X, self._extractor.feature_names)
                self._populate_correlation_table(high_pairs)

                if self.combo_feat.count() > 0:
                    self._on_feature_selected(0)

            except Exception:
                pass

    def _on_feature_selected(self, idx: int) -> None:
        if idx < 0 or len(self._cached_X) == 0:
            return
        feat_name = self.combo_feat.currentText()
        feat_data = self._cached_X[:, idx]
        self.dist_widget.set_data(feat_data, self._cached_y, self._cached_class_names, feat_name)

    def _populate_correlation_table(self, high_pairs: list[dict[str, Any]]) -> None:
        self.table_corr.setRowCount(len(high_pairs))
        for r_idx, pair in enumerate(high_pairs):
            self.table_corr.setItem(r_idx, 0, QTableWidgetItem(pair["feat_a"]))
            self.table_corr.setItem(r_idx, 1, QTableWidgetItem(pair["feat_b"]))
            
            r_item = QTableWidgetItem(f"{pair['r']:.4f}")
            r_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            r_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if pair["abs_r"] >= 0.95:
                r_item.setForeground(QColor(225, 29, 72))
            else:
                r_item.setForeground(QColor(217, 119, 6))
            self.table_corr.setItem(r_idx, 2, r_item)

            eval_text = "Trùng lặp rất cao (>95%)" if pair["abs_r"] >= 0.95 else "Tương quan mạnh"
            eval_item = QTableWidgetItem(eval_text)
            eval_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_corr.setItem(r_idx, 3, eval_item)

    def _preview_augmentation(self) -> None:
        if not self._cached_wins:
            QMessageBox.warning(self, "Chưa Có Dữ Liệu", "Vui lòng thu thập ít nhất 2 cử chỉ trước khi tăng cường.")
            return

        mult = self.spin_mult.value()
        noise = self.spin_noise.value()
        aug_dict = augment_dataset_windows(self._cached_wins, multiplier=mult, noise_std=noise)

        total_orig = sum(len(v) for v in self._cached_wins.values())
        total_aug = sum(len(v) for v in aug_dict.values())

        self.lbl_aug_result.setText(
            f"🎉 Đã tổng hợp thành công: Từ {total_orig} mẫu ban đầu $\\rightarrow$ {total_aug} mẫu tổng hợp ({mult}x)!"
        )

"""
ml_lab/ui/tabs/tab_data_studio.py — Tab 1: Khám Phá Dữ Liệu & Phân Tích Đặc Trưng.

Cung cấp:
1. Phân phối đặc trưng (Histograms & Separability).
2. Phân tích tương quan đa chiều (Correlation Matrix & Redundant Pair Finder).
3. Studio Tăng Cường Dữ Liệu (Data Augmentation Studio with Gaussian noise, time-warping).
"""

from __future__ import annotations

from ml_lab.data.window_config import STEP_SAMPLES, WINDOW_SAMPLES

import logging
from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
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

import ml_lab.ui.lab_style as ls
from ml_lab.ui.friendly_terms import friendly_feature_name
from ml_lab.core.augment_experiment import compare_augmentation_effect
from ml_lab.data.augmentation import augment_dataset_windows
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_analysis import compute_feature_rankings
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.widgets.ab_compare_bar import AbCompareBarWidget
from ml_lab.ui.widgets.feature_distribution_widget import FeatureDistributionWidget
from ml_lab.ui.widgets.feature_importance_widget import FeatureImportanceWidget

log = logging.getLogger(__name__)


class AugmentCompareWorker(QThread):
    """Worker chạy thí nghiệm A/B (train 2 mô hình) trong luồng nền."""

    sig_done = pyqtSignal(dict)
    sig_error = pyqtSignal(str)

    def __init__(self, dataset_dir: Path, allowed_spells: set[str] | None = None, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.allowed_spells = set(allowed_spells) if allowed_spells is not None else None

    def run(self) -> None:
        try:
            result = compare_augmentation_effect(
                self.dataset_dir, val_fraction=0.2, multiplier=3, allowed_spells=self.allowed_spells
            )
            self.sig_done.emit(result)
        except Exception as exc:
            self.sig_error.emit(str(exc))


class DatasetAnalysisWorker(QThread):
    """
    Worker phân tích dataset nền: đọc CSV, chia cửa sổ, trích đặc trưng,
    xếp hạng tầm quan trọng và tương quan. Khởi động app không bị đóng băng.
    """

    sig_done = pyqtSignal(object)  # dict kết quả phân tích
    sig_error = pyqtSignal(str)

    def __init__(self, dataset_dir: Path, allowed_spells: set[str] | None = None, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.allowed_spells = set(allowed_spells) if allowed_spells is not None else None

    def run(self) -> None:
        try:
            train_samples, _val_samples, class_names = split_user_dataset_file_level(
                self.dataset_dir, val_fraction=0.0, window_size=WINDOW_SAMPLES, step_size=STEP_SAMPLES,
                allowed_spells=self.allowed_spells,
            )
            wins_by_class: dict[str, list[np.ndarray]] = {name: [] for name in class_names}
            for window, cls_idx in train_samples:
                if 0 <= cls_idx < len(class_names):
                    wins_by_class[class_names[cls_idx]].append(window)

            extractor = ClassicFeatureExtractor()
            X, y = extractor.extract_from_samples(train_samples)

            rankings: list[dict[str, Any]] = []
            if len(X) > 0 and len(np.unique(y)) >= 2:
                rankings = compute_feature_rankings(X, y, extractor.feature_names)

            self.sig_done.emit({
                "X": X,
                "y": y,
                "class_names": class_names,
                "wins_by_class": wins_by_class,
                "total_windows": len(train_samples),
                "feature_names": extractor.feature_names,
                "rankings": rankings,
            })
        except Exception as exc:
            log.exception("Phân tích dataset lỗi")
            self.sig_error.emit(str(exc))


class TabDataStudio(QWidget):
    """
    Tab Khám Phá Dữ Liệu, Tương Quan & Tăng Cường Mẫu.

    Khởi động nhẹ: chỉ đổ bảng lớp từ số lượng file (nhanh).
    Phân tích đặc trưng nặng chạy trong DatasetAnalysisWorker nền.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._compare_worker: AugmentCompareWorker | None = None
        self._analysis_worker: DatasetAnalysisWorker | None = None
        self._analysis_done: bool = False
        self._cached_X: np.ndarray = np.empty((0, 0))
        self._cached_y: np.ndarray = np.empty((0,), dtype=np.int64)
        self._cached_class_names: list[str] = []
        self._cached_wins_by_class: dict[str, list[np.ndarray]] = {}
        self._total_windows: int = 0
        self._cached_code_index: dict[str, int] = {}
        self._allowed_spells: set[str] | None = None
        self._pending_reload: bool = False

        self._init_ui()
        self.reload_dataset()

    def set_allowed_spells(self, allowed: set[str] | None) -> None:
        self._allowed_spells = set(allowed) if allowed is not None else None
        # Nếu worker đang chạy, đánh dấu reload pending thay vì giết thread
        if self._analysis_worker is not None and self._analysis_worker.isRunning():
            self._pending_reload = True
            # cập nhật bảng lớp ngay (rẻ) để UI phản hồi tức thì
            counts = count_user_spell_samples(self.dataset_dir, allowed_spells=self._get_allowed())
            self.table_classes.setRowCount(len(counts))
            for r_idx, (name, cnt) in enumerate(sorted(counts.items())):
                self.table_classes.setItem(r_idx, 0, QTableWidgetItem(name))
                ci = QTableWidgetItem(str(cnt))
                ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_classes.setItem(r_idx, 1, ci)
                bi = QTableWidgetItem("Đủ mẫu" if cnt >= 5 else "Cần thêm")
                bi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                bi.setForeground(QColor(ls.SUCCESS_TEXT if cnt >= 5 else ls.WARNING))
                self.table_classes.setItem(r_idx, 2, bi)
            return
        self.reload_dataset()

    def _get_allowed(self) -> set[str] | None:
        return self._allowed_spells

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        main_layout.setSpacing(ls.SP_3)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Column: Dataset Overview & Class Table ─────
        left_box = QFrame()
        left_box.setObjectName("ClassListCard")
        left_box.setStyleSheet(ls.card(pad=ls.SP_3))
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        l_layout.setSpacing(ls.SP_2)

        lbl_l_title = QLabel("DANH SÁCH THẦN CHÚ")
        lbl_l_title.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_l_title)

        self.table_classes = QTableWidget()
        self.table_classes.setColumnCount(3)
        self.table_classes.setHorizontalHeaderLabels(["Thần chú", "Số mẫu", "Đủ để học?"])
        self.table_classes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_classes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_classes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_classes.verticalHeader().setVisible(False)
        self.table_classes.setStyleSheet(ls.DATA_TABLE)
        l_layout.addWidget(self.table_classes, stretch=1)

        btn_reload = QPushButton("Tải lại dữ liệu")
        btn_reload.setStyleSheet(ls.BTN_SECONDARY)
        btn_reload.clicked.connect(self.reload_dataset)
        l_layout.addWidget(btn_reload)

        splitter.addWidget(left_box)

        # ── Right Column: Multi-Sub-Tab Data Science Studio ──
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet(ls.SUB_TAB_BAR)

        # Sub-tab 1: Feature Distribution & Separability
        tab_dist = QWidget()
        dist_layout = QVBoxLayout(tab_dist)
        dist_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        dist_layout.setSpacing(ls.SP_3)

        lbl_sel = QLabel("CHỌN ĐẶC TRƯNG ĐỂ XEM PHÂN BỐ")
        lbl_sel.setStyleSheet(ls.section_label())
        self.combo_feat = QComboBox()
        self.combo_feat.setStyleSheet(ls.INPUT_COMBO)
        self.combo_feat.currentIndexChanged.connect(self._on_feature_selected)
        dist_layout.addWidget(lbl_sel)
        dist_layout.addWidget(self.combo_feat)

        self.dist_widget = FeatureDistributionWidget()
        self.dist_widget.setStyleSheet(
            f"background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; border-radius: {ls.RADIUS_MD}px;"
        )
        dist_layout.addWidget(self.dist_widget, stretch=1)

        self.import_widget = FeatureImportanceWidget()
        self.import_widget.setStyleSheet(
            f"background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; border-radius: {ls.RADIUS_MD}px;"
        )
        dist_layout.addWidget(self.import_widget, stretch=1)

        right_tabs.addTab(tab_dist, "Phân phối")

        # Sub-tab 3: Data Augmentation Studio
        tab_aug = QWidget()
        aug_layout = QVBoxLayout(tab_aug)
        aug_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        aug_layout.setSpacing(ls.SP_3)

        lbl_aug_title = QLabel("TẠO THÊM DỮ LIỆU MẪU TỪ DỮ LIỆU ĐÃ CÓ")
        lbl_aug_title.setStyleSheet(ls.section_label())
        aug_layout.addWidget(lbl_aug_title)

        aug_card = QFrame()
        aug_card.setObjectName("AugCard")
        aug_card.setStyleSheet(
            f"#AugCard {{ background: {ls.SURFACE_SUNK}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_MD}px; padding: {ls.SP_3}px;}}"
        )
        ac_layout = QVBoxLayout(aug_card)
        ac_layout.setSpacing(ls.SP_2)

        # Multiplier
        r1 = QHBoxLayout()
        r1.setSpacing(ls.SP_2)
        lbl_mult = QLabel("Nhân bản thành:")
        lbl_mult.setStyleSheet(ls.font(ls.FS_BODY, 600) + f"color: {ls.BODY}; border:none; background:transparent;")
        r1.addWidget(lbl_mult)
        self.spin_mult = QSpinBox()
        self.spin_mult.setRange(2, 10)
        self.spin_mult.setValue(3)
        self.spin_mult.setSuffix("×")
        self.spin_mult.setStyleSheet(ls.INPUT_SPIN)
        self.spin_mult.setMinimumWidth(90)
        r1.addWidget(self.spin_mult)
        lbl_mult_hint = QLabel("lần")
        lbl_mult_hint.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color:{ls.MUTED}; border:none; background:transparent;")
        r1.addWidget(lbl_mult_hint)
        r1.addStretch()
        ac_layout.addLayout(r1)

        # Noise level
        r2 = QHBoxLayout()
        r2.setSpacing(ls.SP_2)
        lbl_noise = QLabel("Mức nhiễu rung tay:")
        lbl_noise.setStyleSheet(ls.font(ls.FS_BODY, 600) + f"color: {ls.BODY}; border:none; background:transparent;")
        r2.addWidget(lbl_noise)
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0.01, 0.10)
        self.spin_noise.setSingleStep(0.01)
        self.spin_noise.setValue(0.03)
        self.spin_noise.setDecimals(2)
        self.spin_noise.setStyleSheet(ls.INPUT_SPIN)
        self.spin_noise.setMinimumWidth(110)
        r2.addWidget(self.spin_noise)
        r2.addStretch()
        ac_layout.addLayout(r2)

        self.btn_run_aug = QPushButton("Xem số lượng mẫu sau khi nhân bản")
        self.btn_run_aug.setStyleSheet(ls.BTN_SECONDARY)
        self.btn_run_aug.clicked.connect(self._preview_augmentation)
        ac_layout.addWidget(self.btn_run_aug)

        self.lbl_aug_result = QLabel("Sẵn sàng tạo thêm dữ liệu mẫu.")
        self.lbl_aug_result.setWordWrap(True)
        self.lbl_aug_result.setStyleSheet(
            ls.font(ls.FS_CAPTION, 600) + f"color: {ls.SUCCESS_TEXT}; border: none; background: transparent;"
        )
        ac_layout.addWidget(self.lbl_aug_result)

        aug_layout.addWidget(aug_card)

        # ── Thí nghiệm A/B: Train trước vs sau tăng cường ────
        compare_card = QFrame()
        compare_card.setObjectName("CompareCard")
        compare_card.setStyleSheet(ls.card(pad=ls.SP_3))
        cmp_layout = QVBoxLayout(compare_card)
        cmp_layout.setSpacing(ls.SP_2)

        lbl_cmp_title = QLabel("THÍ NGHIỆM SO SÁNH: DỮ LIỆU GỐC vs TĂNG CƯỜNG")
        lbl_cmp_title.setStyleSheet(ls.chart_title())
        cmp_layout.addWidget(lbl_cmp_title)

        lbl_cmp_desc = QLabel(
            "Huấn luyện <b>2 mô hình giống hệt nhau</b>, cho cùng làm một bài kiểm tra: "
            "A học từ dữ liệu gốc, B học từ dữ liệu nhân bản ×3. "
            "Bạn đoán thử ai đoán chính xác hơn rồi bấm chạy để kiểm tra!"
        )
        lbl_cmp_desc.setWordWrap(True)
        lbl_cmp_desc.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.BODY}; border: none; background: transparent;")
        cmp_layout.addWidget(lbl_cmp_desc)

        self.btn_run_compare = QPushButton("Chạy thử: dữ liệu gốc vs dữ liệu nhân bản")
        self.btn_run_compare.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_run_compare.clicked.connect(self._run_augment_compare)
        cmp_layout.addWidget(self.btn_run_compare)

        self.compare_bars = AbCompareBarWidget()
        self.compare_bars.setMinimumHeight(184)
        cmp_layout.addWidget(self.compare_bars)

        aug_layout.addWidget(compare_card)

        lbl_aug_guide = QLabel(
            "<b>Data Augmentation</b> — Bằng cách áp dụng nhiễu trắng và co giãn biên độ ±12%, "
            "hệ thống mô phỏng hàng trăm lần vung gậy khác nhau của nhiều người, giúp mô hình học được "
            "ranh giới tổng quát hóa vững chắc hơn."
        )
        lbl_aug_guide.setWordWrap(True)
        lbl_aug_guide.setStyleSheet(ls.note_box(ls.ACCENT))
        aug_layout.addWidget(lbl_aug_guide)
        aug_layout.addStretch()

        right_tabs.addTab(tab_aug, "Tạo dữ liệu")

        splitter.addWidget(right_tabs)
        # Bố cục mặc định: danh sách thần chú hẹp bên trái (~320px), biểu đồ chiếm phần rộng
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 900])
        main_layout.addWidget(splitter, stretch=1)

        self._configure_accessibility(btn_reload)

    def _configure_accessibility(self, btn_reload: QPushButton) -> None:
        self.table_classes.setAccessibleName("Bảng danh sách thần chú và số lượng mẫu đã ghi")
        btn_reload.setAccessibleName("Tải lại danh sách dữ liệu thần chú")
        self.combo_feat.setAccessibleName("Chọn đặc trưng cảm biến để xem phân phối")
        self.dist_widget.setAccessibleName("Biểu đồ phân phối đặc trưng theo từng lớp")
        self.import_widget.setAccessibleName("Biểu đồ xếp hạng mức độ quan trọng đặc trưng")
        self.spin_mult.setAccessibleName("Hệ số nhân bản dữ liệu mẫu")
        self.spin_noise.setAccessibleName("Mức độ nhiễu rung tay khi nhân bản")
        self.btn_run_aug.setAccessibleName("Xem trước số lượng mẫu sau khi nhân bản")
        self.btn_run_compare.setAccessibleName("Chạy thử nghiệm so sánh dữ liệu gốc và dữ liệu nhân bản")
        self.compare_bars.setAccessibleName("Biểu đồ so sánh độ chính xác A và B")

    def reload_dataset(self) -> None:
        """Làm mới: bảng lớp đổ ngay (rẻ); phân tích đặc trưng chạy nền (nặng)."""
        counts = count_user_spell_samples(self.dataset_dir, allowed_spells=self._get_allowed())
        self.table_classes.setRowCount(len(counts))

        for r_idx, (name, cnt) in enumerate(sorted(counts.items())):
            self.table_classes.setItem(r_idx, 0, QTableWidgetItem(name))

            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_classes.setItem(r_idx, 1, cnt_item)

            badge = "Đủ mẫu" if cnt >= 5 else "Cần thêm"
            badge_item = QTableWidgetItem(badge)
            badge_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if cnt >= 5:
                badge_item.setForeground(QColor(ls.SUCCESS_TEXT))
            else:
                badge_item.setForeground(QColor(ls.WARNING))
            self.table_classes.setItem(r_idx, 2, badge_item)

        if len(counts) < 2:
            self._reset_analysis_cache()
            return

        # Phân tích nặng chạy nền — không chặn UI khi mở app
        if self._analysis_worker is not None and self._analysis_worker.isRunning():
            self._pending_reload = True
            return
        self._pending_reload = False
        self._analysis_done = False
        # Giữ reference cũ để tránh orphan trước khi gán mới
        old_worker = self._analysis_worker
        if old_worker is not None:
            try:
                old_worker.sig_done.disconnect(self._on_analysis_done)
            except Exception:
                pass
            try:
                old_worker.sig_error.disconnect(self._on_analysis_error)
            except Exception:
                pass
        self._analysis_worker = DatasetAnalysisWorker(self.dataset_dir, allowed_spells=self._get_allowed())
        self._analysis_worker.sig_done.connect(self._on_analysis_done)
        self._analysis_worker.sig_error.connect(self._on_analysis_error)
        self._analysis_worker.start()

    def _reset_analysis_cache(self) -> None:
        self._analysis_done = True
        self._cached_X = np.empty((0, 0))
        self._cached_y = np.empty((0,), dtype=np.int64)
        self._cached_class_names = []
        self._cached_wins_by_class = {}
        self._total_windows = 0
        self._cached_code_index = {}
        self.combo_feat.blockSignals(True)
        self.combo_feat.clear()
        self.combo_feat.blockSignals(False)
        self.import_widget.set_importances([], [])
        self.dist_widget.set_distribution_data("", {})

    def _on_analysis_done(self, result: dict[str, Any]) -> None:
        self._analysis_done = True
        self._cached_class_names = result["class_names"]
        self._cached_wins_by_class = result["wins_by_class"]
        self._total_windows = result["total_windows"]
        X, y = result["X"], result["y"]
        if len(X) == 0 or len(np.unique(y)) < 2:
            if self._pending_reload:
                self._pending_reload = False
                self.reload_dataset()
            return

        self._cached_X = X
        self._cached_y = y
        self._cached_code_index = {code: i for i, code in enumerate(result["feature_names"])}

        # Populate combo features (tên dễ hiểu, tooltip giữ mã kỹ thuật)
        self.combo_feat.blockSignals(True)
        self.combo_feat.clear()
        for f in result["feature_names"]:
            self.combo_feat.addItem(friendly_feature_name(f), userData=f)
        self.combo_feat.blockSignals(False)

        # Importance
        rankings = result["rankings"]
        self.import_widget.set_importances(
            [friendly_feature_name(r["name"]) for r in rankings],
            [r["importance"] / 100.0 for r in rankings],
        )

        if self.combo_feat.count() > 0:
            self._on_feature_selected(0)
        if self._pending_reload:
            self._pending_reload = False
            self.reload_dataset()

    def _on_analysis_error(self, msg: str) -> None:
        self._analysis_done = True
        log.warning("Không thể phân tích dataset trong Data Studio: %s", msg)
        if self._pending_reload:
            self._pending_reload = False
            self.reload_dataset()

    def closeEvent(self, event: Any) -> None:
        # Chờ worker nền kết thúc để tránh crash khi teardown Qt
        for worker in (self._analysis_worker, self._compare_worker):
            if worker is not None and worker.isRunning():
                try:
                    worker.blockSignals(True)
                except Exception:
                    pass
                worker.wait(4000)
        super().closeEvent(event)

    def wait_for_workers(self, timeout_ms: int = 4000) -> None:
        """API cho MlLabWindow gọi trước khi destroy — chờ thread an toàn."""
        for worker in (self._analysis_worker, self._compare_worker):
            if worker is not None and worker.isRunning():
                try:
                    worker.blockSignals(True)
                except Exception:
                    pass
                worker.wait(timeout_ms)

    def _on_feature_selected(self, idx: int) -> None:
        if idx < 0 or len(self._cached_X) == 0:
            return
        feat_name = self.combo_feat.currentText()
        code = self.combo_feat.currentData() or ""
        feat_idx = self._cached_code_index.get(code, self.combo_feat.currentIndex())
        if feat_idx < 0 or feat_idx >= self._cached_X.shape[1]:
            return
        feat_data = self._cached_X[:, feat_idx]

        # Gom giá trị đặc trưng theo từng lớp cho histogram
        class_data: dict[str, np.ndarray] = {}
        for cls_idx, cls_name in enumerate(self._cached_class_names):
            mask = self._cached_y == cls_idx
            vals = feat_data[mask]
            if len(vals) > 0:
                class_data[cls_name] = vals
        self.dist_widget.set_distribution_data(feat_name, class_data)

    def _preview_augmentation(self) -> None:
        if not self._analysis_done:
            QMessageBox.information(
                self, "Đang phân tích", "Hệ thống đang phân tích dataset trong nền — thử lại sau vài giây."
            )
            return
        if not self._cached_wins_by_class or self._total_windows == 0:
            QMessageBox.warning(self, "Chưa Có Dữ Liệu", "Vui lòng thu thập ít nhất 2 cử chỉ trước khi tăng cường.")
            return

        mult = self.spin_mult.value()
        noise = self.spin_noise.value()
        aug_dict = augment_dataset_windows(self._cached_wins_by_class, multiplier=mult, noise_std=noise)

        total_orig = sum(len(v) for v in self._cached_wins_by_class.values())
        total_aug = sum(len(v) for v in aug_dict.values())

        self.lbl_aug_result.setText(
            f"Đã tạo thêm dữ liệu: {total_orig} mẫu gốc → {total_aug} mẫu sau nhân bản ({mult}x). "
            "Chạy thí nghiệm so sánh bên dưới để xem dữ liệu nhiều hơn có giúp máy đoán chuẩn hơn không."
        )

    def _run_augment_compare(self) -> None:
        if self._compare_worker is not None and self._compare_worker.isRunning():
            return
        counts = count_user_spell_samples(self.dataset_dir, allowed_spells=self._get_allowed())
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa đủ thần chú",
                f"Bạn đã chọn {len(counts)} thần chú, cần ít nhất 2 để so sánh.\n"
                "Hãy mở Tab 0 · Chọn thần chú và tích thêm.",
            )
            return

        self.btn_run_compare.setEnabled(False)
        self.btn_run_compare.setText("Đang huấn luyện 2 mô hình để so sánh...")
        self.compare_bars.reset()

        self._compare_worker = AugmentCompareWorker(self.dataset_dir, allowed_spells=self._get_allowed())
        self._compare_worker.sig_done.connect(self._on_compare_done)
        self._compare_worker.sig_error.connect(self._on_compare_error)
        self._compare_worker.start()

    def _on_compare_done(self, result: dict[str, Any]) -> None:
        self.btn_run_compare.setEnabled(True)
        self.btn_run_compare.setText("Chạy thử: dữ liệu gốc vs dữ liệu nhân bản")
        self.compare_bars.set_results(result["baseline_val"], result["augmented_val"])
        log.info(
            "A/B augment: baseline=%.3f augmented=%.3f (train %d -> %d mẫu)",
            result["baseline_val"], result["augmented_val"],
            result["baseline_train_size"], result["augmented_train_size"],
        )

    def _on_compare_error(self, msg: str) -> None:
        self.btn_run_compare.setEnabled(True)
        self.btn_run_compare.setText("Chạy thử: dữ liệu gốc vs dữ liệu nhân bản")
        QMessageBox.warning(self, "Lỗi Thí Nghiệm", f"Không thể hoàn tất thí nghiệm so sánh:\n{msg}")

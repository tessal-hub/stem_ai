"""
ml_lab/ui/tabs/tab_curves_studio.py — Tab 3: Nghiên Cứu Đường Cong Học & Bias-Variance Trade-off.

Cho phép học viên quét một dải siêu tham số (Hyperparameter Sweep) để vẽ trực tiếp
đường cong Train vs Validation Score, quan sát hiện tượng Overfitting, Underfitting và Sweet Spot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ml_lab.core.hyperparam_schema import (
    DecisionTreeConfig,
    KNNConfig,
    LogisticRegressionConfig,
    RandomForestConfig,
    SVMConfig,
)
from ml_lab.core.pipeline import build_sklearn_model
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.widgets.curve_chart_widget import CurveChartWidget


class SweepWorker(QThread):
    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal(list, list, list)  # x_vals, train_scores, val_scores
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        dataset_dir: Path,
        algo: str,
        param_name: str,
        param_values: list[Any],
        cv_folds: int = 5,
        include_standby: bool = False,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.algo = algo
        self.param_name = param_name
        self.param_values = param_values
        self.cv_folds = cv_folds
        self.include_standby = include_standby

    def run(self) -> None:
        try:
            from ml_lab.core.lazy_sklearn import ensure_sklearn

            ensure_sklearn()
            from sklearn.model_selection import StratifiedKFold, cross_val_score  # lazy import
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.01,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )
                all_wins = train_wins + val_wins
                if len(all_wins) == 0 or len(class_names) < 2:
                    self.sig_error.emit("Cần ít nhất 2 lớp cử chỉ để quét tham số.")
                    return

                extractor = ClassicFeatureExtractor()
                X, y = extractor.extract_from_samples(all_wins)

                train_scores: list[float] = []
                val_scores: list[float] = []

                n_splits = min(self.cv_folds, len(y) // max(1, len(np.unique(y))))
                cv = StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=42)

                for i, val in enumerate(self.param_values):
                    cfg = self._build_config_with_val(val)
                    model, use_scaler = build_sklearn_model(self.algo, cfg)

                    if use_scaler:
                        # Pipeline: scaler fit riêng trong từng fold CV -> không rò rỉ dữ liệu
                        pipe = Pipeline([("scaler", StandardScaler()), ("model", model)])
                    else:
                        pipe = Pipeline([("model", model)])

                    pipe.fit(X, y)
                    tr_acc = float(pipe.score(X, y))
                    train_scores.append(tr_acc)

                    scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")
                    val_scores.append(float(np.mean(scores)))

                    pct = int(((i + 1) / len(self.param_values)) * 100)
                    self.sig_progress.emit(pct)

                self.sig_finished.emit(self.param_values, train_scores, val_scores)
        except Exception as exc:
            self.sig_error.emit(str(exc))

    def _build_config_with_val(self, val: Any) -> Any:
        from ml_lab.core.hyperparam_schema import (
            AdaBoostConfig,
            ExtraTreesConfig,
            GradientBoostingConfig,
            MLPConfig,
            NaiveBayesConfig,
            QDAConfig,
            RidgeConfig,
            SGDConfig,
        )

        if self.algo == "knn":
            return KNNConfig(k=int(val))
        elif self.algo == "tree":
            return DecisionTreeConfig(max_depth=int(val))
        elif self.algo == "forest":
            return RandomForestConfig(n_estimators=int(val), max_depth=4)
        elif self.algo == "svm":
            return SVMConfig(c=float(val), kernel="rbf")
        elif self.algo == "logistic":
            return LogisticRegressionConfig(c=float(val))
        elif self.algo == "gbdt":
            return GradientBoostingConfig(n_estimators=int(val))
        elif self.algo == "extra_trees":
            return ExtraTreesConfig(n_estimators=int(val), max_depth=4)
        elif self.algo == "adaboost":
            return AdaBoostConfig(n_estimators=int(val))
        elif self.algo == "ridge":
            return RidgeConfig(alpha=float(val))
        elif self.algo == "sgd":
            return SGDConfig(alpha=float(val))
        elif self.algo == "mlp":
            return MLPConfig(hidden_units=int(val), max_iter=100)
        elif self.algo == "qda":
            return QDAConfig(reg_param=float(val))
        elif self.algo == "nb":
            return NaiveBayesConfig(var_smoothing=float(val))
        return None


class DataSizeWorker(QThread):
    """
    Worker trả lời câu hỏi "ghi thêm dữ liệu có đáng không?":
    huấn luyện cùng một mô hình với 25% → 50% → 75% → 100% dữ liệu học,
    đánh giá trên cùng một tập kiểm tra.
    """

    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal(list, list, list)  # (labels, train_scores, val_scores)
    sig_error = pyqtSignal(str)

    FRACTIONS = [0.25, 0.5, 0.75, 1.0]

    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    def run(self) -> None:
        try:
            from ml_lab.core.lazy_sklearn import ensure_sklearn

            ensure_sklearn()
            from sklearn.tree import DecisionTreeClassifier

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )
                if len(class_names) < 2 or len(train_samples) < 4 or len(val_samples) == 0:
                    self.sig_error.emit("Cần ít nhất 2 lớp và vài mẫu cho mỗi lớp để chạy thử.")
                    return

                extractor = ClassicFeatureExtractor()
                X_val, y_val = extractor.extract_from_samples(val_samples)

                # Gom mẫu theo lớp (giữ nguyên tuple window, nhãn) để cắt tỉa cân bằng
                by_class: dict[int, list] = {}
                for sample in train_samples:
                    cls_idx = sample[1]
                    by_class.setdefault(cls_idx, []).append(sample)

                labels: list[str] = []
                train_scores: list[float] = []
                val_scores: list[float] = []

                for step, frac in enumerate(self.FRACTIONS):
                    subset: list = []
                    for _cls, samples_cls in sorted(by_class.items()):
                        keep = max(1, int(round(len(samples_cls) * frac)))
                        subset.extend(samples_cls[:keep])
                    if len(subset) < 4:
                        continue

                    X_tr, y_tr = extractor.extract_from_samples(subset)
                    model = DecisionTreeClassifier(max_depth=4, random_state=42)
                    model.fit(X_tr, y_tr)
                    train_scores.append(float(model.score(X_tr, y_tr)))
                    val_scores.append(float(model.score(X_val, y_val)))
                    labels.append(f"{int(frac*100)}%")

                    self.sig_progress.emit(int((step + 1) / len(self.FRACTIONS) * 100))

                if len(labels) < 2:
                    self.sig_error.emit("Dữ liệu quá ít để chạy thử theo từng phần.")
                    return

                self.sig_finished.emit(labels, train_scores, val_scores)
        except Exception as exc:
            self.sig_error.emit(str(exc))


class TabCurvesStudio(QWidget):
    """
    Tab Phân Tích Đường Cong Học & Bias-Variance.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._worker: SweepWorker | None = None
        self._datasize_worker: DataSizeWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Panel: Controls ────────────────────────────
        left_box = QFrame()
        left_box.setStyleSheet(ls.card())
        l_layout = QVBoxLayout(left_box)
        l_layout.setSpacing(10)

        lbl_title = QLabel("THỬ NGHIỆM: CÀI ĐẶT NÀO TỐT NHẤT?")
        lbl_title.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_title)

        # Combo Algo
        lbl_algo = QLabel("THUẬT TOÁN")
        lbl_algo.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_algo)
        self.combo_algo = QComboBox()
        self.combo_algo.setStyleSheet(ls.INPUT_COMBO)
        self.combo_algo.addItem("K-Nearest Neighbors (KNN)", "knn")
        self.combo_algo.addItem("Cây Quyết Định (Decision Tree)", "tree")
        self.combo_algo.addItem("Rừng Ngẫu Nhiên (Random Forest)", "forest")
        self.combo_algo.addItem("Gradient Boosting (GBDT)", "gbdt")
        self.combo_algo.addItem("Support Vector Machine (SVM)", "svm")
        self.combo_algo.addItem("Hồi quy Logistic (Logistic Regression)", "logistic")
        self.combo_algo.addItem("Shallow MLP (Mạng nơ-ron)", "mlp")
        self.combo_algo.addItem("Extra Trees (Rừng siêu ngẫu nhiên)", "extra_trees")
        self.combo_algo.addItem("AdaBoost (Chuỗi cây sửa sai)", "adaboost")
        self.combo_algo.addItem("Ridge Classifier (Tuyến tính)", "ridge")
        self.combo_algo.addItem("SGD Classifier (Tuyến tính nhanh)", "sgd")
        self.combo_algo.addItem("Gaussian Naive Bayes (GNB)", "nb")
        self.combo_algo.addItem("QDA (Ranh giới thống kê)", "qda")
        self.combo_algo.addItem("LDA (Tuyến tính Fisher)", "lda")
        self.combo_algo.addItem("Nearest Centroid (So với tâm lớp)", "nearest_centroid")
        self.combo_algo.currentIndexChanged.connect(self._on_algo_changed)
        l_layout.addWidget(self.combo_algo)

        # Combo Param
        lbl_param = QLabel("THAM SỐ MUỐN THỬ")
        lbl_param.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_param)
        self.combo_param = QComboBox()
        self.combo_param.setStyleSheet(ls.INPUT_COMBO)
        l_layout.addWidget(self.combo_param)
        self._on_algo_changed()

        # Action Button
        self.btn_run_sweep = QPushButton("Chạy thử & vẽ biểu đồ")
        self.btn_run_sweep.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_run_sweep.clicked.connect(self.run_sweep)
        l_layout.addWidget(self.btn_run_sweep)

        # ── Thử nghiệm thứ hai: cần bao nhiêu dữ liệu? ──────
        lbl_data_t = QLabel("THỬ NGHIỆM: CẦN BAO NHIÊU DỮ LIỆU?")
        lbl_data_t.setStyleSheet(ls.section_label())
        l_layout.addSpacing(6)
        l_layout.addWidget(lbl_data_t)

        self.btn_run_datasize = QPushButton("Chạy thử: 25% → 100% dữ liệu")
        self.btn_run_datasize.setToolTip(
            "Huấn luyện cùng một mô hình với lượng dữ liệu tăng dần (25%, 50%, 75%, 100%)\n"
            "để trả lời câu hỏi: ghi thêm mẫu có giúp máy đoán chuẩn hơn không?"
        )
        self.btn_run_datasize.setStyleSheet(ls.BTN_SECONDARY)
        self.btn_run_datasize.clicked.connect(self.run_datasize)
        l_layout.addWidget(self.btn_run_datasize)

        # Pedagogical Callout Box
        lbl_guide = QLabel(
            "<b>Cách đọc biểu đồ</b> — chọn giá trị có cột xanh lá cao nhất:<br>"
            "• <b>Đường xám</b> — điểm số trên dữ liệu cũ (máy đã học): luôn tăng khi máy phức tạp lên.<br>"
            "• <b>Đường xanh dương</b> — điểm số trên dữ liệu mới: cái này mới quyết định mô hình tốt hay kém.<br>"
            "• <b>Cột xanh lá</b> — nơi dữ liệu mới đạt điểm cao nhất. Hãy quay lại tab 2 và chọn đúng giá trị đó!"
        )
        lbl_guide.setWordWrap(True)
        lbl_guide.setStyleSheet(ls.note_box(ls.ACCENT))
        l_layout.addWidget(lbl_guide)

        l_layout.addStretch()
        splitter.addWidget(left_box)

        # ── Right Panel: Curve Chart ────────────────────────
        right_box = QFrame()
        right_box.setStyleSheet(ls.card())
        r_layout = QVBoxLayout(right_box)
        r_layout.setSpacing(8)

        lbl_chart_title = QLabel("CÀI ĐẶT NÀO VỪA HỌC TỐT VỪA KHÔNG HỌC VỆT?")
        lbl_chart_title.setStyleSheet(ls.section_label())
        r_layout.addWidget(lbl_chart_title)

        self.lbl_chart_caption = QLabel("")
        self.lbl_chart_caption.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.MUTED}; border: none; background: transparent;")
        r_layout.addWidget(self.lbl_chart_caption)

        self.chart_widget = CurveChartWidget()
        r_layout.addWidget(self.chart_widget, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(5)
        r_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

    def _on_algo_changed(self) -> None:
        algo = self.combo_algo.currentData()
        self.combo_param.clear()
        if algo == "knn":
            self.combo_param.addItem("Số láng giềng K (1 → 15)", "k")
        elif algo == "tree":
            self.combo_param.addItem("Số câu hỏi tối đa (1 → 8)", "max_depth")
        elif algo in ("forest", "extra_trees"):
            self.combo_param.addItem("Số cây bỏ phiếu (1 → 12)", "n_estimators")
        elif algo == "gbdt":
            self.combo_param.addItem("Số vòng sửa sai (1 → 12)", "n_estimators")
        elif algo == "adaboost":
            self.combo_param.addItem("Số vòng sửa sai (1 → 12)", "n_estimators")
        elif algo == "svm":
            self.combo_param.addItem("Độ nghiêm khắc C (0.01 → 100)", "c")
        elif algo == "logistic":
            self.combo_param.addItem("Độ nghiêm khắc C (0.01 → 50)", "c")
        elif algo == "ridge":
            self.combo_param.addItem("Độ phẳng hóa alpha (0.01 → 10)", "alpha")
        elif algo == "sgd":
            self.combo_param.addItem("Độ phẳng hóa alpha (0.00001 → 0.01)", "alpha")
        elif algo == "mlp":
            self.combo_param.addItem("Số ô tính trung gian (4 → 64)", "hidden_units")
        elif algo == "qda":
            self.combo_param.addItem("Làm mịn thống kê (0.001 → 1)", "reg_param")
        elif algo == "nb":
            self.combo_param.addItem("Làm mịn dữ liệu (rất nhỏ → lớn)", "var_smoothing")
        else:
            # lda, nearest_centroid: không có tham số để thử
            self.combo_param.addItem("Mô hình này không có tham số — dùng mặc định", "")

    def run_sweep(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa Đủ Dữ Liệu",
                f"Hiện tại chỉ có {len(counts)} phép thuật trong dataset/spells/.\n\n"
                "Cần ít nhất 2 lớp cử chỉ khác nhau để thực hiện phân tích đường cong.",
            )
            return

        algo = self.combo_algo.currentData()
        param_name = self.combo_param.currentData()

        if not param_name:
            QMessageBox.information(
                self,
                "Không cần thử tham số",
                f"Mô hình này tự động toàn bộ, không có tham số để thử.\n"
                "Hãy chọn một thuật toán khác, hoặc quay lại tab 2 huấn luyện luôn.",
            )
            return

        if param_name == "k":
            param_vals = [1, 2, 3, 5, 7, 9, 11, 13, 15]
            display_name = "Số láng giềng K"
        elif param_name == "max_depth":
            param_vals = [1, 2, 3, 4, 5, 6, 7, 8]
            display_name = "Số câu hỏi tối đa"
        elif param_name == "n_estimators":
            param_vals = [1, 2, 3, 5, 7, 9, 12]
            display_name = "Số cây"
        elif param_name == "c":
            param_vals = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
            display_name = "Độ nghiêm khắc C"
        elif param_name == "alpha":
            param_vals = [0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0]
            display_name = "Độ phẳng hóa alpha"
        elif param_name == "hidden_units":
            param_vals = [4, 8, 16, 24, 32, 48, 64]
            display_name = "Số ô tính trung gian"
        elif param_name == "reg_param":
            param_vals = [0.001, 0.01, 0.05, 0.1, 0.3, 0.5, 1.0]
            display_name = "Làm mịn thống kê"
        elif param_name == "var_smoothing":
            param_vals = [1e-9, 1e-7, 1e-5, 1e-3, 1e-1]
            display_name = "Làm mịn dữ liệu"
        else:
            param_vals = [1, 2, 3, 4, 5]
            display_name = "Tham số"

        self.btn_run_sweep.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        self.lbl_chart_caption.setText(f"Đang thử: {display_name} của {self.combo_algo.currentText()}...")

        self._worker = SweepWorker(
            dataset_dir=self.dataset_dir,
            algo=algo,
            param_name=display_name,
            param_values=param_vals,
            cv_folds=5,
        )
        self._worker.sig_progress.connect(self.progress_bar.setValue)
        self._worker.sig_finished.connect(self._on_sweep_finished)
        self._worker.sig_error.connect(self._on_sweep_error)
        self._worker.start()

    def _on_sweep_finished(self, x_vals: list, train_scores: list, val_scores: list) -> None:
        self.btn_run_sweep.setEnabled(True)
        self.progress_bar.setVisible(False)
        param_name = self.combo_param.currentText()
        self.chart_widget.set_curve_data(param_name, x_vals, train_scores, val_scores)

    def run_datasize(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa Đủ Dữ Liệu",
                "Cần ít nhất 2 lớp cử chỉ để chạy thử theo lượng dữ liệu.",
            )
            return
        if self._datasize_worker is not None and self._datasize_worker.isRunning():
            return

        self.btn_run_datasize.setEnabled(False)
        self.btn_run_sweep.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.lbl_chart_caption.setText("Đang thử: cùng một mô hình, lượng dữ liệu tăng dần...")

        self._datasize_worker = DataSizeWorker(self.dataset_dir)
        self._datasize_worker.sig_progress.connect(self.progress_bar.setValue)
        self._datasize_worker.sig_finished.connect(self._on_datasize_finished)
        self._datasize_worker.sig_error.connect(self._on_datasize_error)
        self._datasize_worker.start()

    def _on_datasize_finished(self, labels: list, train_scores: list, val_scores: list) -> None:
        self.btn_run_datasize.setEnabled(True)
        self.btn_run_sweep.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_chart_caption.setText(
            "Kết luận: nếu đường xanh dương vẫn đang tăng ở 100% thì ghi thêm mẫu sẽ có lợi; "
            "nếu đã phẳng thì dữ liệu đã đủ."
        )
        self.chart_widget.set_curve_data("Lượng dữ liệu dùng để học", labels, train_scores, val_scores)

    def _on_datasize_error(self, err_msg: str) -> None:
        self.btn_run_datasize.setEnabled(True)
        self.btn_run_sweep.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_chart_caption.setText("")
        QMessageBox.warning(self, "Lỗi Thử Nghiệm", f"Không thể chạy thử theo lượng dữ liệu:\n{err_msg}")

    def _on_sweep_error(self, err_msg: str) -> None:
        self.btn_run_sweep.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi Quét Tham Số", f"Không thể hoàn tất quét tham số:\n{err_msg}")

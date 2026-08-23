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
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler


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
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.algo = algo
        self.param_name = param_name
        self.param_values = param_values
        self.cv_folds = cv_folds

    def run(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.01, window_size=64, step_size=16
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
                        scaler = StandardScaler()
                        X_proc = scaler.fit_transform(X)
                    else:
                        X_proc = X

                    model.fit(X_proc, y)
                    tr_acc = float(model.score(X_proc, y))
                    train_scores.append(tr_acc)

                    scores = cross_val_score(model, X_proc, y, cv=cv, scoring="accuracy")
                    val_scores.append(float(np.mean(scores)))

                    pct = int(((i + 1) / len(self.param_values)) * 100)
                    self.sig_progress.emit(pct)

                self.sig_finished.emit(self.param_values, train_scores, val_scores)
        except Exception as exc:
            self.sig_error.emit(str(exc))

    def _build_config_with_val(self, val: Any) -> Any:
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
        return None


class TabCurvesStudio(QWidget):
    """
    Tab Phân Tích Đường Cong Học & Bias-Variance.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._worker: SweepWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Panel: Controls ────────────────────────────
        left_box = QFrame()
        left_box.setStyleSheet("background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;")
        l_layout = QVBoxLayout(left_box)
        l_layout.setSpacing(10)

        lbl_title = QLabel("📈 THIẾT LẬP QUÉT SIÊU THAM SỐ")
        lbl_title.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        l_layout.addWidget(lbl_title)

        # Combo Algo
        l_layout.addWidget(QLabel("Thuật toán:"))
        self.combo_algo = QComboBox()
        self.combo_algo.setStyleSheet("padding: 5px; font-weight: 600; border: 1px solid #d1d5db; border-radius: 6px;")
        self.combo_algo.addItem("K-Nearest Neighbors (KNN)", "knn")
        self.combo_algo.addItem("Cây Quyết Định (Decision Tree)", "tree")
        self.combo_algo.addItem("Rừng Ngẫu Nhiên (Random Forest)", "forest")
        self.combo_algo.addItem("Support Vector Machine (SVM)", "svm")
        self.combo_algo.addItem("Hồi quy Logistic (Logistic Regression)", "logistic")
        self.combo_algo.currentIndexChanged.connect(self._on_algo_changed)
        l_layout.addWidget(self.combo_algo)

        # Combo Param
        l_layout.addWidget(QLabel("Trục tham số quét:"))
        self.combo_param = QComboBox()
        self.combo_param.setStyleSheet("padding: 5px; font-weight: 600; border: 1px solid #d1d5db; border-radius: 6px;")
        l_layout.addWidget(self.combo_param)
        self._on_algo_changed()

        # Action Button
        self.btn_run_sweep = QPushButton("🚀 Quét & Vẽ Đường Cong Học")
        self.btn_run_sweep.setStyleSheet("background-color: #007aff; color: white; font-weight: 700; padding: 10px; border-radius: 6px;")
        self.btn_run_sweep.clicked.connect(self.run_sweep)
        l_layout.addWidget(self.btn_run_sweep)

        # Pedagogical Callout Box
        lbl_guide = QLabel(
            "🎓 <b>Hướng Dẫn Đọc Đồ Thị Bias-Variance</b>:<br>"
            "• <b>Đường Xám (Train Accuracy)</b>: Khả năng học thuộc lòng tập huấn luyện. Thường tăng dần khi mô hình phức tạp hơn.<br>"
            "• <b>Đường Xanh (Validation Score)</b>: Khả năng tổng quát hóa trên dữ liệu mới.<br>"
            "• <b>Điểm Sweet Spot</b>: Cột màu xanh lá — nơi Validation Score đạt đỉnh. Hãy chọn giá trị tham số này để nạp vào ESP32!"
        )
        lbl_guide.setWordWrap(True)
        lbl_guide.setStyleSheet("background: rgba(0, 122, 255, 0.06); border-radius: 6px; padding: 10px; font-size: 11px; color: #1e3a8a;")
        l_layout.addWidget(lbl_guide)

        l_layout.addStretch()
        splitter.addWidget(left_box)

        # ── Right Panel: Curve Chart ────────────────────────
        right_box = QFrame()
        right_box.setStyleSheet("background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;")
        r_layout = QVBoxLayout(right_box)
        r_layout.setSpacing(8)

        lbl_chart_title = QLabel("📊 BIỂU ĐỒ ĐÁNH ĐỔI ĐỘ LỆCH - PHƯƠNG SAI (BIAS-VARIANCE TRADE-OFF)")
        lbl_chart_title.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        r_layout.addWidget(lbl_chart_title)

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
            self.combo_param.addItem("Số láng giềng (K: 1 -> 15)", "k")
        elif algo == "tree":
            self.combo_param.addItem("Độ sâu tối đa (Max Depth: 1 -> 8)", "max_depth")
        elif algo == "forest":
            self.combo_param.addItem("Số lượng cây (N Trees: 1 -> 12)", "n_estimators")
        elif algo == "svm":
            self.combo_param.addItem("Hệ số phạt (C: 0.01 -> 100)", "c")
        elif algo == "logistic":
            self.combo_param.addItem("Regularization (C: 0.01 -> 50)", "c")

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

        if param_name == "k":
            param_vals = [1, 2, 3, 5, 7, 9, 11, 13, 15]
            display_name = "K (Láng giềng)"
        elif param_name == "max_depth":
            param_vals = [1, 2, 3, 4, 5, 6, 7, 8]
            display_name = "Max Depth (Độ sâu cây)"
        elif param_name == "n_estimators":
            param_vals = [1, 2, 3, 5, 7, 9, 12]
            display_name = "Số lượng cây (N Trees)"
        elif param_name == "c":
            param_vals = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
            display_name = "Hệ số C"
        else:
            param_vals = [1, 2, 3, 4, 5]
            display_name = "Tham số"

        self.btn_run_sweep.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

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

    def _on_sweep_error(self, err_msg: str) -> None:
        self.btn_run_sweep.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi Quét Tham Số", f"Không thể hoàn tất quét tham số:\n{err_msg}")

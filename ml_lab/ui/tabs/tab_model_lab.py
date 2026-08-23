"""
ml_lab/ui/tabs/tab_model_lab.py — Tab 2: Huấn Luyện Mô Hình & Mổ Xẻ Toán Học (Model Lab).

Cho phép tinh chỉnh siêu tham số, xem 2D Decision Space, ma trận nhầm lẫn
và trực quan hóa cấu trúc toán học bên trong (Tree Graph, SVM Support Vectors, Logistic Weights, MLP Activations).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTabWidget,
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
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.ml_lab_worker import MlLabTrainWorker
from ml_lab.ui.widgets.boundary_canvas import DecisionBoundaryCanvas
from ml_lab.ui.widgets.confusion_matrix_widget import ConfusionMatrixWidget
from ml_lab.ui.widgets.flash_dialog import FlashDialog
from ml_lab.ui.widgets.tree_visualizer_widget import TreeVisualizerWidget
from ml_lab.ui.widgets.weights_bar_widget import WeightsBarWidget


class TabModelLab(QWidget):
    """
    Tab Huấn Luyện & Mổ Xẻ Thuật Toán.
    """

    sig_model_trained = pyqtSignal(object)  # TrainClassicResult

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._current_worker: MlLabTrainWorker | None = None
        self._last_result: TrainClassicResult | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Panel: Controls & Hyperparameters ──────────
        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)

        # ── Right Panel: Multi-Sub-Tab Visualizer ───────────
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter, stretch=1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #007aff; border-radius: 3px; }")
        main_layout.addWidget(self.progress_bar)

    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # 1. Chọn Thuật toán
        box_algo = QFrame()
        box_algo.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        algo_layout = QVBoxLayout(box_algo)
        lbl_a = QLabel("1. CHỌN THUẬT TOÁN HỌC MÁY")
        lbl_a.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        algo_layout.addWidget(lbl_a)

        self.combo_algo = QComboBox()
        self.combo_algo.setStyleSheet("padding: 6px; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px;")
        self.combo_algo.addItem("K-Nearest Neighbors (KNN)", "knn")
        self.combo_algo.addItem("Cây Quyết Định (Decision Tree)", "tree")
        self.combo_algo.addItem("Rừng Ngẫu Nhiên (Random Forest)", "forest")
        self.combo_algo.addItem("Gradient Boosting (GBDT)", "gbdt")
        self.combo_algo.addItem("Support Vector Machine (SVM)", "svm")
        self.combo_algo.addItem("Hồi quy Logistic (Logistic Regression)", "logistic")
        self.combo_algo.addItem("Gaussian Naive Bayes (GNB)", "nb")
        self.combo_algo.addItem("Linear Discriminant Analysis (LDA)", "lda")
        self.combo_algo.addItem("Mạng Nơ-ron (Shallow MLP)", "mlp")
        algo_layout.addWidget(self.combo_algo)

        self.lbl_algo_badge = QLabel("⚡ Non-parametric: Phân lớp theo khoảng cách")
        self.lbl_algo_badge.setStyleSheet("color: #64748b; font-size: 11px;")
        algo_layout.addWidget(self.lbl_algo_badge)
        layout.addWidget(box_algo)

        # 2. Feature Engineering
        box_feat = QFrame()
        box_feat.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        feat_layout = QVBoxLayout(box_feat)
        lbl_f = QLabel("2. FEATURE ENGINEERING (48 ĐẶC TRƯNG)")
        lbl_f.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        feat_layout.addWidget(lbl_f)

        self.chk_f_time = QCheckBox("Miền thời gian (Mean, Std, Min, Max, Range)")
        self.chk_f_time.setChecked(True)
        self.chk_f_energy = QCheckBox("Năng lượng & Động lực (RMS, Energy, ZCR)")
        self.chk_f_energy.setChecked(True)
        self.chk_f_mag = QCheckBox("Gia tốc & Góc tổng hợp (|a|, |g|)")
        self.chk_f_mag.setChecked(True)
        self.chk_f_cross = QCheckBox("Vi phân chéo (az*gx, az*gy, Jerk_z)")
        self.chk_f_cross.setChecked(True)

        feat_layout.addWidget(self.chk_f_time)
        feat_layout.addWidget(self.chk_f_energy)
        feat_layout.addWidget(self.chk_f_mag)
        feat_layout.addWidget(self.chk_f_cross)
        layout.addWidget(box_feat)

        # 3. Tinh chỉnh Siêu tham số
        box_param = QFrame()
        box_param.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        self.param_box_layout = QVBoxLayout(box_param)
        lbl_p = QLabel("3. TINH CHỈNH SIÊU THAM SỐ")
        lbl_p.setStyleSheet("font-weight: 700; color: #007aff; font-size: 11px;")
        self.param_box_layout.addWidget(lbl_p)

        self.param_container_layout = QVBoxLayout()
        self.param_box_layout.addLayout(self.param_container_layout)

        self.lbl_tip = QLabel()
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet("background: rgba(52, 199, 89, 0.08); border-radius: 6px; padding: 8px; font-size: 11px; color: #166534;")
        self.param_box_layout.addWidget(self.lbl_tip)

        self._build_param_controls()
        self.combo_algo.currentIndexChanged.connect(self._build_param_controls)
        layout.addWidget(box_param)

        # 4. Train Action CTA & 1-Click Flash CTA
        self.btn_train = QPushButton("🚀 Huấn Luyện & Đánh Giá")
        self.btn_train.setStyleSheet("background-color: #007aff; color: white; font-weight: 700; font-size: 13px; padding: 11px; border-radius: 6px; border: none;")
        self.btn_train.clicked.connect(self.start_training)
        layout.addWidget(self.btn_train)

        self.btn_flash_direct = QPushButton("🔥 Nạp Code Sang ESP32 Ngay (1-Click)")
        self.btn_flash_direct.setStyleSheet("background-color: #34c759; color: white; font-weight: 700; font-size: 12px; padding: 10px; border-radius: 6px; border: none;")
        self.btn_flash_direct.setVisible(False)
        self.btn_flash_direct.clicked.connect(self._open_flash_dialog)
        layout.addWidget(self.btn_flash_direct)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_right_panel(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { font-weight: 600; padding: 8px 16px; }")

        # Sub-tab 1: 2D Decision Space
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_layout.setContentsMargins(8, 8, 8, 8)
        self.canvas = DecisionBoundaryCanvas()
        t1_layout.addWidget(self.canvas, stretch=1)
        lbl_pca_note = QLabel(
            "💡 <b>Không Gian Quyết Định 2D (PCA Projection)</b>: "
            "Thuật toán PCA nén không gian 48 chiều về 2 trục chính (PC1 và PC2) để mắt người quan sát được. "
            "Các mảng màu thể hiện 'lãnh thổ' quyết định của mô hình; các chấm tròn là từng lần vung gậy của bạn."
        )
        lbl_pca_note.setWordWrap(True)
        lbl_pca_note.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 6px 10px; font-size: 11px; color: #1e3a8a;")
        t1_layout.addWidget(lbl_pca_note)
        tabs.addTab(tab1, "🗺️ Biên Phân Lớp 2D (PCA)")

        # Sub-tab 2: Confusion Matrix Heatmap
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        t2_layout.setContentsMargins(8, 8, 8, 8)
        self.cm_widget = ConfusionMatrixWidget()
        t2_layout.addWidget(self.cm_widget, stretch=1)
        lbl_cm_note = QLabel(
            "💡 <b>Đánh Giá Tập Kiểm Thử (Validation Set)</b>: "
            "Toàn bộ các số liệu trên được tính toán trên các file CSV độc lập mà mô hình <b>chưa từng nhìn thấy khi học</b>. "
            "Đường chéo màu xanh lá càng lớn thì độ chính xác của bạn càng cao!"
        )
        lbl_cm_note.setWordWrap(True)
        lbl_cm_note.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 6px 10px; font-size: 11px; color: #1e3a8a;")
        t2_layout.addWidget(lbl_cm_note)
        tabs.addTab(tab2, "🎯 Ma Trận Nhầm Lẫn (Validation)")

        # Sub-tab 3: Math Dissection (Tree / Weights)
        tab3 = QWidget()
        self.t3_layout = QVBoxLayout(tab3)
        self.t3_layout.setContentsMargins(8, 8, 8, 8)
        self.tree_vis = TreeVisualizerWidget()
        self.weights_vis = WeightsBarWidget()
        self.weights_vis.setVisible(False)
        self.t3_layout.addWidget(self.tree_vis, stretch=1)
        self.t3_layout.addWidget(self.weights_vis, stretch=1)

        lbl_math_note = QLabel(
            "🔬 <b>Mổ Xẻ Cấu Trúc Toán Học</b>: "
            "Xem trực tiếp các câu hỏi điều kiện rẽ nhánh (đối với Cây Quyết Định) hoặc vector trọng số W (đối với Hồi quy Logistic / LDA). "
            "Không còn là hộp đen — bạn có thể hiểu tường tận từng phép tính máy thực hiện!"
        )
        lbl_math_note.setWordWrap(True)
        lbl_math_note.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 6px 10px; font-size: 11px; color: #1e3a8a;")
        self.t3_layout.addWidget(lbl_math_note)
        tabs.addTab(tab3, "🔬 Mổ Xẻ Toán Học (Inner Math)")

        return tabs

    def _build_param_controls(self) -> None:
        while self.param_container_layout.count():
            item = self.param_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    c2 = item.layout().takeAt(0)
                    if c2.widget():
                        c2.widget().deleteLater()

        algo = self.combo_algo.currentData()

        if algo == "knn":
            self.lbl_algo_badge.setText("⚡ Non-parametric: Phân lớp theo K láng giềng gần nhất")
            r1 = QHBoxLayout()
            lbl_k = QLabel("K (Láng giềng):")
            self.lbl_k_v = QLabel("3")
            self.lbl_k_v.setStyleSheet("font-weight: 700; color: #007aff;")
            self.slider_k = QSlider(Qt.Orientation.Horizontal)
            self.slider_k.setRange(1, 9)
            self.slider_k.setValue(3)
            self.slider_k.valueChanged.connect(lambda v: self.lbl_k_v.setText(str(v)))
            r1.addWidget(lbl_k)
            r1.addWidget(self.slider_k, stretch=1)
            r1.addWidget(self.lbl_k_v)
            self.param_container_layout.addLayout(r1)

            r2 = QHBoxLayout()
            lbl_m = QLabel("Metric:")
            self.combo_metric = QComboBox()
            self.combo_metric.addItems(["Euclidean (L2)", "Manhattan (L1)", "Cosine"])
            r2.addWidget(lbl_m)
            r2.addWidget(self.combo_metric, stretch=1)
            self.param_container_layout.addLayout(r2)

            self.lbl_tip.setText("💡 <b>Ý nghĩa KNN</b>: K=1 rất nhạy với rung lắc nhỏ; K=3-5 giúp khử nhiễu tốt nhất mà không làm mờ ranh giới.")

        elif algo == "tree":
            self.lbl_algo_badge.setText("⚡ Cây nhị phân if-else: Tốc độ 0.04ms, dễ giải thích nhất")
            r1 = QHBoxLayout()
            lbl_d = QLabel("Max Depth (Độ sâu):")
            self.lbl_d_v = QLabel("4")
            self.lbl_d_v.setStyleSheet("font-weight: 700; color: #007aff;")
            self.slider_depth = QSlider(Qt.Orientation.Horizontal)
            self.slider_depth.setRange(2, 8)
            self.slider_depth.setValue(4)
            self.slider_depth.valueChanged.connect(lambda v: self.lbl_d_v.setText(str(v)))
            r1.addWidget(lbl_d)
            r1.addWidget(self.slider_depth, stretch=1)
            r1.addWidget(self.lbl_d_v)
            self.param_container_layout.addLayout(r1)

            r2 = QHBoxLayout()
            lbl_c = QLabel("Criterion:")
            self.combo_crit = QComboBox()
            self.combo_crit.addItem("Gini Impurity", "gini")
            self.combo_crit.addItem("Entropy (Info Gain)", "entropy")
            r2.addWidget(lbl_c)
            r2.addWidget(self.combo_crit, stretch=1)
            self.param_container_layout.addLayout(r2)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Cây Quyết Định</b>: Độ sâu 3-4 thường là Sweet Spot. Độ sâu > 5 dễ gây quá khớp (học vẹt).")

        elif algo == "forest":
            self.lbl_algo_badge.setText("⚡ Ensemble: Tập hợp nhiều cây quyết định, giảm phương sai")
            r1 = QHBoxLayout()
            lbl_t = QLabel("Số lượng cây (N Trees):")
            self.lbl_t_v = QLabel("5")
            self.lbl_t_v.setStyleSheet("font-weight: 700; color: #007aff;")
            self.slider_trees = QSlider(Qt.Orientation.Horizontal)
            self.slider_trees.setRange(2, 10)
            self.slider_trees.setValue(5)
            self.slider_trees.valueChanged.connect(lambda v: self.lbl_t_v.setText(str(v)))
            r1.addWidget(lbl_t)
            r1.addWidget(self.slider_trees, stretch=1)
            r1.addWidget(self.lbl_t_v)
            self.param_container_layout.addLayout(r1)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Random Forest</b>: 5-8 cây cho kết quả rất ổn định trên ESP32 với dung lượng Flash < 5KB.")

        elif algo == "gbdt":
            self.lbl_algo_badge.setText("⚡ Boosting: Chuỗi cây học tuần tự sửa sai cho cây trước")
            r1 = QHBoxLayout()
            lbl_t = QLabel("Số stage (N Estimators):")
            self.lbl_gbdt_n = QLabel("5")
            self.lbl_gbdt_n.setStyleSheet("font-weight: 700; color: #007aff;")
            self.slider_gbdt = QSlider(Qt.Orientation.Horizontal)
            self.slider_gbdt.setRange(2, 10)
            self.slider_gbdt.setValue(5)
            self.slider_gbdt.valueChanged.connect(lambda v: self.lbl_gbdt_n.setText(str(v)))
            r1.addWidget(lbl_t)
            r1.addWidget(self.slider_gbdt, stretch=1)
            r1.addWidget(self.lbl_gbdt_n)
            self.param_container_layout.addLayout(r1)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Gradient Boosting</b>: Tối ưu phần dư còn sót lại, độ chính xác cao ngay cả với số lượng cây rất ít.")

        elif algo == "svm":
            self.lbl_algo_badge.setText("⚡ Max-Margin: Tối đa hóa khoảng cách tới Support Vectors")
            r1 = QHBoxLayout()
            lbl_c = QLabel("Hệ số C:")
            self.combo_svm_c = QComboBox()
            self.combo_svm_c.addItems(["0.1", "1.0", "10.0", "50.0"])
            self.combo_svm_c.setCurrentText("1.0")
            r1.addWidget(lbl_c)
            r1.addWidget(self.combo_svm_c, stretch=1)
            self.param_container_layout.addLayout(r1)

            r2 = QHBoxLayout()
            lbl_k = QLabel("Kernel:")
            self.combo_kernel = QComboBox()
            self.combo_kernel.addItem("RBF (Gaussian phi tuyến)", "rbf")
            self.combo_kernel.addItem("Linear (Tuyến tính)", "linear")
            r2.addWidget(lbl_k)
            r2.addWidget(self.combo_kernel, stretch=1)
            self.param_container_layout.addLayout(r2)

            self.lbl_tip.setText("💡 <b>Ý nghĩa SVM</b>: RBF Kernel uốn cong không gian để phân tách các cử chỉ phức tạp mà đường thẳng không chia được.")

        elif algo == "logistic":
            self.lbl_algo_badge.setText("⚡ Linear + Softmax: Nhẹ nhất, tối ưu tuyệt đối cho MCU")
            r1 = QHBoxLayout()
            lbl_c = QLabel("Regularization (C):")
            self.combo_log_c = QComboBox()
            self.combo_log_c.addItems(["0.1", "1.0", "10.0"])
            self.combo_log_c.setCurrentText("1.0")
            r1.addWidget(lbl_c)
            r1.addWidget(self.combo_log_c, stretch=1)
            self.param_container_layout.addLayout(r1)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Logistic Regression</b>: Chỉ tốn vài phép tính nhân ma trận W*x + b, siêu nhanh (<0.08ms) trên chip ESP32.")

        elif algo == "nb":
            self.lbl_algo_badge.setText("⚡ Xác suất Bayes: Mô hình hóa phân phối hình chuông Gauss")
            r1 = QHBoxLayout()
            lbl_s = QLabel("Độ mịn phương sai (Smoothing):")
            self.combo_nb_s = QComboBox()
            self.combo_nb_s.addItems(["1e-9", "1e-5", "1e-3", "1e-1"])
            r1.addWidget(lbl_s)
            r1.addWidget(self.combo_nb_s, stretch=1)
            self.param_container_layout.addLayout(r1)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Naive Bayes</b>: Giả định các trục gia tốc độc lập nhau, tốc độ suy luận <0.01ms cực kỳ nhẹ.")

        elif algo == "lda":
            self.lbl_algo_badge.setText("⚡ Phân tích phân biệt tuyến tính: Tối đa hóa tỷ số phương sai Fisher")
            r1 = QHBoxLayout()
            lbl_s = QLabel("Solver:")
            self.combo_lda_s = QComboBox()
            self.combo_lda_s.addItems(["SVD (Singular Value Decomposition)", "LSQR"])
            r1.addWidget(lbl_s)
            r1.addWidget(self.combo_lda_s, stretch=1)
            self.param_container_layout.addLayout(r1)

            self.lbl_tip.setText("💡 <b>Ý nghĩa LDA</b>: Tìm siêu phẳng chiếu sao cho khoảng cách giữa các tâm cử chỉ là xa nhất.")

        elif algo == "mlp":
            self.lbl_algo_badge.setText("⚡ Mạng Nơ-ron Tầng Nông: 2 Tầng ẩn kích hoạt phi tuyến ReLU")
            r1 = QHBoxLayout()
            lbl_h = QLabel("Số nơ-ron tầng ẩn (Hidden):")
            self.combo_mlp_h = QComboBox()
            self.combo_mlp_h.addItems(["8", "16", "32", "64"])
            self.combo_mlp_h.setCurrentText("16")
            r1.addWidget(lbl_h)
            r1.addWidget(self.combo_mlp_h, stretch=1)
            self.param_container_layout.addLayout(r1)

            r2 = QHBoxLayout()
            lbl_lr = QLabel("Learning Rate:")
            self.combo_mlp_lr = QComboBox()
            self.combo_mlp_lr.addItems(["0.001", "0.01", "0.05"])
            self.combo_mlp_lr.setCurrentText("0.01")
            r2.addWidget(lbl_lr)
            r2.addWidget(self.combo_mlp_lr, stretch=1)
            self.param_container_layout.addLayout(r2)

            self.lbl_tip.setText("💡 <b>Ý nghĩa Shallow MLP</b>: Cầu nối sang Deep Learning — tính toán lan truyền thẳng W1*x + b1 -> ReLU -> W2*h + b2 thuần C++.")

    def _get_current_config(self) -> Any:
        algo = self.combo_algo.currentData()
        if algo == "knn":
            k = self.slider_k.value() if hasattr(self, "slider_k") else 3
            met_text = self.combo_metric.currentText().lower()
            metric = "manhattan" if "manhattan" in met_text else ("cosine" if "cosine" in met_text else "euclidean")
            return KNNConfig(k=k, metric=metric)
        elif algo == "tree":
            depth = self.slider_depth.value() if hasattr(self, "slider_depth") else 4
            crit = self.combo_crit.currentData() if hasattr(self, "combo_crit") else "gini"
            return DecisionTreeConfig(max_depth=depth, criterion=crit)
        elif algo == "forest":
            n = self.slider_trees.value() if hasattr(self, "slider_trees") else 5
            return RandomForestConfig(n_estimators=n, max_depth=4)
        elif algo == "gbdt":
            n = self.slider_gbdt.value() if hasattr(self, "slider_gbdt") else 5
            return GradientBoostingConfig(n_estimators=n)
        elif algo == "svm":
            c_val = float(self.combo_svm_c.currentText()) if hasattr(self, "combo_svm_c") else 1.0
            kern = self.combo_kernel.currentData() if hasattr(self, "combo_kernel") else "rbf"
            return SVMConfig(c=c_val, kernel=kern)
        elif algo == "logistic":
            c_val = float(self.combo_log_c.currentText()) if hasattr(self, "combo_log_c") else 1.0
            return LogisticRegressionConfig(c=c_val)
        elif algo == "nb":
            s_val = float(self.combo_nb_s.currentText()) if hasattr(self, "combo_nb_s") else 1e-9
            return NaiveBayesConfig(var_smoothing=s_val)
        elif algo == "lda":
            return LDAConfig(solver="svd")
        elif algo == "mlp":
            h_val = int(self.combo_mlp_h.currentText()) if hasattr(self, "combo_mlp_h") else 16
            lr_val = float(self.combo_mlp_lr.currentText()) if hasattr(self, "combo_mlp_lr") else 0.01
            return MLPConfig(hidden_units=h_val, learning_rate_init=lr_val)
        return None

    def start_training(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa Đủ Dữ Liệu",
                f"Hiện tại chỉ có {len(counts)} phép thuật được ghi nhận trong dataset/spells/.\n\n"
                "Cần ít nhất 2 lớp cử chỉ (ví dụ: Lumos và Nox) để máy học có thể phân loại.",
            )
            return

        algo = self.combo_algo.currentData()
        config = self._get_current_config()

        feat_cfg = FeatureGroupConfig(
            include_basic_stats=self.chk_f_time.isChecked(),
            include_energy_dynamics=self.chk_f_energy.isChecked(),
            include_magnitudes=self.chk_f_mag.isChecked(),
            include_cross_derivatives=self.chk_f_cross.isChecked(),
        )

        self.btn_train.setEnabled(False)
        self.btn_train.setText("⏳ Đang huấn luyện...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        self._current_worker = MlLabTrainWorker(
            dataset_root=self.dataset_dir,
            algo=algo,
            config=config,
            feature_config=feat_cfg,
            val_fraction=0.2,
        )
        self._current_worker.sig_progress.connect(lambda pct, msg: self.progress_bar.setValue(pct))
        self._current_worker.sig_finished.connect(self._on_training_finished)
        self._current_worker.sig_error.connect(self._on_training_error)
        self._current_worker.start()

    def _on_training_finished(self, result: TrainClassicResult) -> None:
        self.btn_train.setEnabled(True)
        self.btn_train.setText("🚀 Huấn Luyện & Đánh Giá")
        self.progress_bar.setVisible(False)
        self._last_result = result
        self.btn_flash_direct.setVisible(True)

        # Cập nhật Visualizer
        self.canvas.set_data(result.pca_result, result.class_names)
        self.cm_widget.set_results(
            cm=result.confusion_matrix,
            class_names=result.class_names,
            val_acc=result.val_accuracy,
            train_acc=result.train_accuracy,
            cv_mean=result.cv_mean,
            cv_std=result.cv_std,
        )

        # Cập nhật Math Dissection
        if result.algo in ("tree", "forest", "gbdt"):
            self.tree_vis.setVisible(True)
            self.weights_vis.setVisible(False)
            if result.algo == "forest":
                model_to_show = result.model.estimators_[0]
            elif result.algo == "gbdt":
                model_to_show = result.model.estimators_[0, 0] if hasattr(result.model, "estimators_") else result.model
            else:
                model_to_show = result.model
            self.tree_vis.set_tree_model(model_to_show, result.feature_names, result.class_names)
        elif result.algo in ("logistic", "svm", "lda"):
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "coef_"):
                self.weights_vis.set_weights(result.model.coef_, result.feature_names, result.class_names)
        elif result.algo == "mlp":
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "coefs_"):
                # Hiển thị trọng số tầng 1
                self.weights_vis.set_weights(result.model.coefs_[0].T, result.feature_names, [f"Neuron_{i}" for i in range(result.model.coefs_[0].shape[1])])
        else:
            self.tree_vis.setVisible(True)
            self.weights_vis.setVisible(False)

        self.sig_model_trained.emit(result)

    def _on_training_error(self, msg: str) -> None:
        self.btn_train.setEnabled(True)
        self.btn_train.setText("🚀 Huấn Luyện & Đánh Giá")
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi Huấn Luyện", f"Không thể hoàn tất huấn luyện:\n{msg}")

    def _open_flash_dialog(self) -> None:
        if not self._last_result:
            return
        dlg = FlashDialog(self._last_result, self)
        dlg.exec()

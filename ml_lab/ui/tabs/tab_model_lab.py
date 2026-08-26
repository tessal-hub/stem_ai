"""
ml_lab/ui/tabs/tab_model_lab.py — Tab 2: Huấn Luyện Mô Hình & Mổ Xẻ Toán Học (Model Lab).

Cho phép tinh chỉnh siêu tham số, xem 2D Decision Space, ma trận nhầm lẫn
và trực quan hóa cấu trúc toán học bên trong (Tree Graph, SVM Support Vectors, Logistic Weights, MLP Activations).
"""

from __future__ import annotations

import logging
from pathlib import Path

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
    QDoubleSpinBox,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
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
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.ml_lab_worker import AutoSelectWorker, MlLabTrainWorker
from ml_lab.ui.widgets.advice_card import AdviceCardWidget
from ml_lab.ui.widgets.class_breakdown_widget import ClassBreakdownWidget
from ml_lab.ui.widgets.misclassification_widget import MisclassificationWidget
from ml_lab.ui.widgets.model_card_dialog import ModelCardDialog
from ml_lab.ui.widgets.boundary_canvas import DecisionBoundaryCanvas
from ml_lab.ui.widgets.confusion_matrix_widget import ConfusionMatrixWidget
from ml_lab.ui.widgets.flash_dialog import FlashDialog
from ml_lab.ui.friendly_terms import friendly_feature_name
from ml_lab.ui.widgets.tree_visualizer_widget import TreeVisualizerWidget
from ml_lab.ui.widgets.weights_bar_widget import WeightsBarWidget

log = logging.getLogger(__name__)

_ALGO_BADGES = {
    "extra_trees": "Như Random Forest nhưng ngẫu nhiên hơn — nhanh, ít học vẹt",
    "adaboost": "Chuỗi cây nhỏ lần lượt sửa lỗi của cây trước",
    "ridge": "Mô hình tuyến tính siêu nhẹ, ổn định với dữ liệu nhiễu",
    "sgd": "Tuyến tính học nhanh từng bước nhỏ",
    "nearest_centroid": "So cử chỉ với “khuôn mẫu” trung bình của mỗi thần chú",
    "qda": "Ranh giới cong dựa trên phân phối thống kê từng lớp",
    "knn": "Phân lớp theo K láng giềng gần nhất",
    "tree": "Cây nhị phân if-else — nhanh, dễ giải thích nhất",
    "forest": "Ensemble nhiều cây quyết định, giảm phương sai",
    "gbdt": "Chuỗi cây học tuần tự, sửa sai cho cây trước",
    "svm": "Max-margin: tối đa hóa khoảng cách tới Support Vectors",
    "logistic": "Tuyến tính + Softmax — nhẹ nhất cho MCU",
    "nb": "Xác suất Bayes với phân phối Gauss",
    "lda": "Chiếu Fisher tối đa hóa khoảng cách giữa các lớp",
    "mlp": "Mạng nơ-ron 2 tầng ẩn ReLU — cầu nối sang Deep Learning",
}

_ALGO_TIPS = {
    "extra_trees": "<b>Extra Trees</b>: giống Random Forest nhưng chia ngẫu nhiên hơn — thường ít học vẹt hơn.",
    "adaboost": "<b>AdaBoost</b>: mỗi cây nhỏ tập trung sửa các mẫu mà cây trước đoán sai.",
    "ridge": "<b>Ridge</b>: tuyến tính nhẹ kèm phạt giữ trọng số nhỏ — rất ổn định với dữ liệu ít.",
    "sgd": "<b>SGD</b>: cùng họ logistic nhưng học nhanh, hợp dữ liệu nhiều mẫu.",
    "nearest_centroid": "<b>Nearest Centroid</b>: tính điểm trung bình mỗi lớp; cử chỉ mới thuộc lớp có tâm gần nhất.",
    "qda": "<b>QDA</b>: học cả hình dạng phân phối từng lớp — ranh giới cong tự nhiên.",
    "knn": "<b>KNN</b>: K=1 nhạy với rung lắc nhỏ; K=3-5 khử nhiễu tốt mà không làm mờ ranh giới.",
    "tree": "<b>Cây Quyết Định</b>: độ sâu 3-4 thường là điểm cân bằng. Độ sâu trên 5 dễ học vẹt.",
    "forest": "<b>Random Forest</b>: 5-8 cây rất ổn định trên ESP32, Flash dưới 5KB.",
    "gbdt": "<b>Gradient Boosting</b>: tối ưu phần dư sót lại, chính xác ngay cả khi số cây ít.",
    "svm": "<b>SVM</b>: RBF uốn cong không gian để tách các cử chỉ phức tạp mà đường thẳng không chia được.",
    "logistic": "<b>Logistic Regression</b>: chỉ vài phép nhân ma trận W·x + b, dưới 0.08ms trên ESP32.",
    "nb": "<b>Naive Bayes</b>: giả định các trục độc lập, suy luận dưới 0.01ms.",
    "lda": "<b>LDA</b>: tìm phép chiếu sao cho các tâm lớp cách nhau xa nhất.",
    "mlp": "<b>Shallow MLP</b>: W1·x + b1 → ReLU → W2·h + b2, toàn thuật toán thuần C++.",
}


class TabModelLab(QWidget):
    """Tab Huấn Luyện & Mổ Xẻ Thuật Toán."""

    sig_model_trained = pyqtSignal(object)  # TrainClassicResult

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._current_worker: MlLabTrainWorker | None = None
        self._auto_worker: AutoSelectWorker | None = None
        self._last_result: TrainClassicResult | None = None
        self._feat_checks: list[QCheckBox] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(ls.SP_4, ls.SP_4, ls.SP_4, ls.SP_4)
        main_layout.setSpacing(ls.SP_2)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)

        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(ls.PROGRESS_BAR)
        main_layout.addWidget(self.progress_bar)

    # ────────────────────────── Left panel ───────────────────────────────

    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, ls.SP_2, 0)
        layout.setSpacing(ls.SP_3)  # nhịp giữa các cụm chức năng

        # Chế độ người dùng (Beginner ẩn tinh chỉnh nâng cao)
        mode_row = QHBoxLayout()
        self.chk_beginner = QCheckBox("Chế độ Người mới bắt đầu")
        self.chk_beginner.setChecked(True)
        self.chk_beginner.setToolTip(
            "Ẩn tinh chỉnh nâng cao để tập trung vào luồng chính:\n"
            "chọn thuật toán → huấn luyện → đọc chẩn đoán."
        )
        self.chk_beginner.setStyleSheet(ls.font(ls.FS_BODY, 600) + f"color: {ls.BODY};; border: none; background: transparent;")
        self.chk_beginner.toggled.connect(self._apply_skill_mode)
        mode_row.addWidget(self.chk_beginner)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self.lbl_beginner_hint = QLabel(
            "Bước 1 — chọn một thuật toán ở khung bên dưới.\n"
            "Bước 2 — bấm nút xanh “Huấn luyện & đánh giá”.\n"
            "Xong! AI Coach sẽ chấm bài và hướng dẫn bước tiếp theo. "
            "Muốn tự chỉnh cài đặt nâng cao thì tắt chế độ này."
        )
        self.lbl_beginner_hint.setWordWrap(True)
        self.lbl_beginner_hint.setStyleSheet(ls.note_box(ls.WARNING))
        layout.addWidget(self.lbl_beginner_hint)

        # 1 · Chọn thuật toán
        self.box_algo = self._make_group("1 · CHỌN THUẬT TOÁN", layout)

        self.combo_algo = QComboBox()
        self.combo_algo.setStyleSheet(ls.INPUT_COMBO)
        self._populate_algorithms()
        self.box_algo.layout().addWidget(self.combo_algo)

        self.lbl_algo_badge = QLabel(_ALGO_BADGES["knn"])
        self.lbl_algo_badge.setWordWrap(True)
        self.lbl_algo_badge.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED};; border: none; background: transparent;")
        self.box_algo.layout().addWidget(self.lbl_algo_badge)

        # 2 · Feature Engineering (ẩn ở Beginner)
        self.box_feat = self._make_group("2 · DỮ LIỆU ĐO GÌ", layout)
        for text in (
            "Độ cao/thấp của tín hiệu (trung bình, dao động, min/max)",
            "Cường độ & năng lượng chuyển động",
            "Độ lớn tổng hợp của chuyển động",
            "Phối hợp giữa các trục cảm biến",
        ):
            chk = QCheckBox(text)
            chk.setChecked(True)
            chk.setStyleSheet(ls.font(ls.FS_BODY) + f"color: {ls.BODY};; border: none; background: transparent;")
            self._feat_checks.append(chk)
            self.box_feat.layout().addWidget(chk)
        self.chk_f_time = self._feat_checks[0]
        self.chk_f_energy = self._feat_checks[1]
        self.chk_f_mag = self._feat_checks[2]
        self.chk_f_cross = self._feat_checks[3]

        # 3 · Siêu tham số (ẩn ở Beginner)
        self.box_param = self._make_group("3 · CÀI ĐẶT THUẬT TOÁN", layout)
        self.param_box_layout = self.box_param.layout()

        self.param_container_layout = QVBoxLayout()
        self.param_container_layout.setSpacing(ls.SP_2)
        self.param_box_layout.addLayout(self.param_container_layout)

        self.lbl_tip = QLabel()
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet(ls.note_box(ls.SUCCESS))
        self.param_box_layout.addWidget(self.lbl_tip)

        self._build_param_controls()
        self.combo_algo.currentIndexChanged.connect(self._build_param_controls)

        # CTA — tách khỏi các cụm trên bằng khoảng trống lớn hơn
        cta_wrap = QVBoxLayout()
        cta_wrap.setSpacing(ls.SP_2)
        cta_wrap.setContentsMargins(0, ls.SP_2, 0, 0)

        self.btn_auto = QPushButton("Không biết chọn? Để máy tự chọn giúp bạn")
        self.btn_auto.setStyleSheet(
            f"QPushButton {{ background: {ls.SURFACE}; color: {ls.ACCENT}; border: 1px solid {ls.ACCENT}; "
            f"border-radius: {ls.RADIUS_MD}px; padding: 9px 16px; {ls.font(ls.FS_BODY, 700)} }} "
            f"QPushButton:hover {{ background: {ls.ACCENT_TINT} }} "
            f"QPushButton:disabled {{ color: {ls.FAINT}; border-color: {ls.BORDER} }}"
        )
        self.btn_auto.setToolTip(
            "Thử nhanh 11 mô hình nhẹ trên đúng dữ liệu của bạn,\n"
            "chọn mô hình đoán đúng nhất rồi huấn luyện luôn — toàn bộ tự động."
        )
        self.btn_auto.clicked.connect(self.start_auto_select)
        cta_wrap.addWidget(self.btn_auto)

        self.btn_train = QPushButton("Huấn luyện & đánh giá")
        self.btn_train.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_train.setMinimumHeight(44)
        self.btn_train.clicked.connect(self.start_training)
        cta_wrap.addWidget(self.btn_train)

        self.chk_augment = QCheckBox("Nhân bản dữ liệu ×3 (chống rung tay)")
        self.chk_augment.setToolTip(
            "Tạo thêm bản sao có nhiễu nhẹ từ dữ liệu train ×3 — máy học nhiều biến thể hơn nên ít bắt nhầm.\n"
            "Bài kiểm tra (validation) luôn dùng dữ liệu thật, không nhân bản."
        )
        self.chk_augment.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED};; border: none; background: transparent;")
        cta_wrap.addWidget(self.chk_augment)

        self.btn_flash_direct = QPushButton("Nạp mô hình lên ESP32")
        self.btn_flash_direct.setStyleSheet(ls.BTN_SUCCESS)
        self.btn_flash_direct.setVisible(False)
        self.btn_flash_direct.clicked.connect(self._open_flash_dialog)
        cta_wrap.addWidget(self.btn_flash_direct)

        self.btn_model_card = QPushButton("Xem hồ sơ mô hình (Model Card)")
        self.btn_model_card.setToolTip(
            "Tự sinh tài liệu mô tả mô hình: làm gì, chính xác từng lớp,\n"
            "khi nào KHÔNG nên tin. Xuất PDF nộp bài hoặc lưu portfolio."
        )
        self.btn_model_card.setStyleSheet(ls.BTN_SECONDARY)
        self.btn_model_card.setVisible(False)
        self.btn_model_card.clicked.connect(self._open_model_card)
        cta_wrap.addWidget(self.btn_model_card)

        layout.addLayout(cta_wrap)
        layout.addStretch()

        scroll.setWidget(container)
        self._apply_skill_mode()
        return scroll

    def _make_group(self, title: str, parent_layout: QVBoxLayout) -> QFrame:
        """Card nhóm điều khiển chuẩn: tiêu đề nhãn + nội dung."""
        box = QFrame()
        box.setStyleSheet(ls.card())
        v = QVBoxLayout(box)
        v.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        v.setSpacing(ls.SP_2)
        lbl = QLabel(title)
        lbl.setStyleSheet(ls.section_label())
        v.addWidget(lbl)
        parent_layout.addWidget(box)
        return box

    def _populate_algorithms(self) -> None:
        for label, key in (
            ("K-Nearest Neighbors (KNN)", "knn"),
            ("Decision Tree — Cây quyết định", "tree"),
            ("Random Forest — Rừng ngẫu nhiên", "forest"),
            ("Gradient Boosting (GBDT)", "gbdt"),
            ("Support Vector Machine (SVM)", "svm"),
            ("Logistic Regression — Hồi quy logistic", "logistic"),
            ("Gaussian Naive Bayes", "nb"),
            ("Linear Discriminant Analysis", "lda"),
            ("Shallow MLP — Mạng nơ-ron", "mlp"),
            ("Extra Trees — Rừng siêu ngẫu nhiên", "extra_trees"),
            ("AdaBoost — Chuỗi cây sửa sai", "adaboost"),
            ("Ridge Classifier — Tuyến tính ổn định", "ridge"),
            ("SGD Classifier — Tuyến tính học nhanh", "sgd"),
            ("Nearest Centroid — So với tâm lớp", "nearest_centroid"),
            ("QDA — Ranh giới thống kê cong", "qda"),
        ):
            self.combo_algo.addItem(label, key)

    # ────────────────────────── Right panel ──────────────────────────────

    def _build_right_panel(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setStyleSheet(ls.SUB_TAB_BAR)

        # Sub-tab 1: 2D Decision Space
        tab1 = QWidget()
        t1 = QVBoxLayout(tab1)
        t1.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t1.setSpacing(ls.SP_2)
        self.canvas = DecisionBoundaryCanvas()
        t1.addWidget(self.canvas, stretch=1)
        t1.addWidget(self._note_label(
            "<b>Không gian quyết định 2D (PCA)</b> — PCA nén không gian đặc trưng về 2 trục chính "
            "(PC1, PC2) để quan sát được. Vùng màu là “lãnh thổ” của mỗi lớp; chấm tròn là từng lần vung wand."
        ))
        tabs.addTab(tab1, "Bản đồ quyết định")

        # Sub-tab 2: Confusion Matrix + AI Coach
        tab2 = QWidget()
        t2 = QVBoxLayout(tab2)
        t2.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t2.setSpacing(ls.SP_2)
        self.cm_widget = ConfusionMatrixWidget()
        t2.addWidget(self.cm_widget, stretch=3)
        self.advice_card = AdviceCardWidget()
        t2.addWidget(self.advice_card, stretch=2)
        t2.addWidget(self._note_label(
            "<b>Đánh giá trên tập kiểm thử</b> — toàn bộ số liệu tính trên file CSV độc lập mà mô hình "
            "<b>chưa từng thấy khi học</b>. Đường chéo xanh càng đậm, mô hình càng đáng tin."
        ))
        tabs.addTab(tab2, "Kết quả & AI Coach")

        # Sub-tab 3: Math Dissection
        tab3 = QWidget()
        t3 = QVBoxLayout(tab3)
        t3.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t3.setSpacing(ls.SP_2)
        self.tree_vis = TreeVisualizerWidget()
        self.weights_vis = WeightsBarWidget()
        self.weights_vis.setVisible(False)
        t3.addWidget(self.tree_vis, stretch=1)
        t3.addWidget(self.weights_vis, stretch=1)
        t3.addWidget(self._note_label(
            "<b>Mổ xẻ cấu trúc toán học</b> — xem trực tiếp các câu hỏi điều kiện rẽ nhánh (cây quyết định) "
            "hoặc vector trọng số W (Logistic / LDA). Không còn hộp đen: bạn hiểu đúng từng phép tính máy thực hiện."
        ))
        tabs.addTab(tab3, "Bên trong mô hình")

        # Sub-tab 4: Lớp nào yếu? + xem tại sao máy nhầm
        tab4 = QWidget()
        t4 = QVBoxLayout(tab4)
        t4.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t4.setSpacing(ls.SP_2)
        split_v = QSplitter(Qt.Orientation.Vertical)
        self.class_breakdown = ClassBreakdownWidget()
        split_v.addWidget(self.class_breakdown)
        self.misclass_widget = MisclassificationWidget()
        split_v.addWidget(self.misclass_widget)
        split_v.setStretchFactor(0, 4)
        split_v.setStretchFactor(1, 6)
        t4.addWidget(split_v, stretch=1)
        t4.addWidget(self._note_label(
            "<b>Chẩn đoán từng thần chú</b> — lớp yếu nhất đứng đầu kèm gợi ý hành động. "
            "Chọn một mẫu bị sai bên dưới để xem dạng sóng thật và hiểu vì sao máy nhầm."
        ))
        tabs.addTab(tab4, "Lớp nào yếu?")

        return tabs

    def _note_label(self, html: str) -> QLabel:
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(ls.note_box(ls.ACCENT))
        return lbl

    # ───────────────────── Hyperparameter controls ───────────────────────

    def _clear_layout(self, lay: QVBoxLayout) -> None:
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _param_row(self, name: str, editor: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ls.SP_2)
        lbl = QLabel(name)
        lbl.setStyleSheet(ls.font(ls.FS_BODY) + f"color: {ls.BODY};; border: none; background: transparent;")
        row.addWidget(lbl)
        row.addWidget(editor, stretch=1)
        return row

    def _spin_int(self, lo: int, hi: int, val: int, tip: str = "") -> QSpinBox:
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        w.setStyleSheet(ls.INPUT_SPIN)
        w.setMaximumWidth(160)
        w.setMinimumHeight(30)
        if tip:
            w.setToolTip(tip)
        return w

    def _spin_double(self, lo: float, hi: float, dec: int, val: float, step: float, tip: str = "") -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setDecimals(dec)
        w.setValue(val)
        w.setSingleStep(step)
        w.setStyleSheet(ls.INPUT_SPIN)
        w.setMaximumWidth(180)
        w.setMinimumHeight(30)
        w.setKeyboardTracking(False)
        if tip:
            w.setToolTip(tip)
        return w

    def _combo(self, items: list, tip: str = "") -> QComboBox:
        w = QComboBox()
        w.setStyleSheet(ls.INPUT_COMBO)
        for label, data in items:
            w.addItem(label, data)
        if tip:
            w.setToolTip(tip)
        return w

    def _param_row(self, name: str, editor: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ls.SP_2)
        lbl = QLabel(name)
        lbl.setStyleSheet(ls.font(ls.FS_BODY) + f"color: {ls.BODY}; border: none; background: transparent;")
        row.addWidget(lbl)
        row.addWidget(editor, stretch=1)
        return row

    def _build_param_controls(self) -> None:
        self._clear_layout(self.param_container_layout)

        algo = self.combo_algo.currentData()
        self.lbl_algo_badge.setText(_ALGO_BADGES.get(algo, ""))
        self.lbl_tip.setText(_ALGO_TIPS.get(algo, ""))

        if algo == "knn":
            self.spin_k = self._spin_int(1, 50, 3, "Số cử chỉ giống nhất được mang ra bỏ phiếu. K nhỏ = nhạy, K lớn = ổn định.")
            self.param_container_layout.addLayout(self._param_row("Số láng giềng K", self.spin_k))
            self.combo_weights = self._combo([
                ("Đều nhau (uniform)", "uniform"),
                ("Láng giềng gần tính hơn (distance)", "distance"),
            ], "Láng giềng gần hơn có phiếu nặng hơn — hữu ích khi dữ liệu dày đặc không đều.")
            self.param_container_layout.addLayout(self._param_row("Trọng số bỏ phiếu", self.combo_weights))
            self.combo_metric = self._combo([
                ("Khoảng cách thẳng (Euclidean)", "euclidean"),
                ("Theo ô bàn cờ (Manhattan)", "manhattan"),
                ("So sánh hướng (Cosine)", "cosine"),
            ])
            self.param_container_layout.addLayout(self._param_row("Cách đo độ giống", self.combo_metric))

        elif algo == "tree":
            self.spin_depth = self._spin_int(1, 30, 4, "Số lần máy được hỏi if-else liên tiếp. Nhiều câu hỏi = học kỹ bài cũ nhưng dễ học vẹt.")
            self.param_container_layout.addLayout(self._param_row("Số câu hỏi tối đa (depth)", self.spin_depth))
            self.combo_crit = self._combo([("Gini — ít lẫn lộn nhất", "gini"), ("Entropy — theo độ bất ngờ", "entropy")])
            self.param_container_layout.addLayout(self._param_row("Cách chia nhóm", self.combo_crit))
            self.spin_min_split = self._spin_int(2, 100, 2, "Một nhóm phải có ít nhất n mẫu mới được tiếp tục chia. Số lớn = chống học vẹt.")
            self.param_container_layout.addLayout(self._param_row("Số mẫu tối thiểu để chia", self.spin_min_split))
            self.spin_min_leaf = self._spin_int(1, 100, 1, "Số mẫu tối thiểu ở một lá kết luận. Số lớn = mô hình mượt hơn.")
            self.param_container_layout.addLayout(self._param_row("Số mẫu tối thiểu mỗi lá", self.spin_min_leaf))

        elif algo == "forest":
            self.spin_trees = self._spin_int(1, 300, 5, "Nhiều cây cùng bỏ phiếu — kết quả theo đa số, ổn định hơn 1 cây đơn lẻ.")
            self.param_container_layout.addLayout(self._param_row("Số cây bỏ phiếu", self.spin_trees))
            self.spin_f_depth = self._spin_int(1, 30, 4, "Số câu hỏi tối đa của mỗi cây.")
            self.param_container_layout.addLayout(self._param_row("Độ sâu mỗi cây", self.spin_f_depth))
            self.combo_f_crit = self._combo([("Gini", "gini"), ("Entropy", "entropy")])
            self.param_container_layout.addLayout(self._param_row("Cách chia nhóm", self.combo_f_crit))
            self.spin_f_minleaf = self._spin_int(1, 50, 1, "Số mẫu tối thiểu ở một lá. Số lớn = ít học vẹt.")
            self.param_container_layout.addLayout(self._param_row("Số mẫu tối thiểu mỗi lá", self.spin_f_minleaf))

        elif algo == "gbdt":
            self.spin_gbdt = self._spin_int(1, 300, 5, "Số cây sửa sai nối tiếp nhau.")
            self.param_container_layout.addLayout(self._param_row("Số vòng sửa sai", self.spin_gbdt))
            self.dbl_gbdt_lr = self._spin_double(0.001, 1.0, 3, 0.1, 0.01,
                "Bước đi của mỗi vòng sửa sai. Nhỏ = học chậm nhưng mượt; lớn = học nhanh nhưng dễ vẹt.")
            self.param_container_layout.addLayout(self._param_row("Tốc độ học (learning rate)", self.dbl_gbdt_lr))
            self.spin_gbdt_depth = self._spin_int(1, 10, 3, "Độ sâu của mỗi cây sửa sai.")
            self.param_container_layout.addLayout(self._param_row("Độ sâu mỗi cây", self.spin_gbdt_depth))
            self.dbl_gbdt_sub = self._spin_double(0.10, 1.0, 2, 1.0, 0.05,
                "Mỗi cây chỉ nhìn thấy phần trăm này của dữ liệu — giúp đa dạng hóa và chống vẹt.")
            self.param_container_layout.addLayout(self._param_row("Phần trăm dữ liệu mỗi cây nhìn thấy", self.dbl_gbdt_sub))

        elif algo == "adaboost":
            self.spin_ada = self._spin_int(1, 300, 5, "Số cây nhỏ nối tiếp, cây sau tập trung vào chỗ cây trước sai.")
            self.param_container_layout.addLayout(self._param_row("Số vòng sửa sai", self.spin_ada))
            self.dbl_ada_lr = self._spin_double(0.01, 2.0, 2, 0.5, 0.05,
                "Mức đóng góp của mỗi cây vào kết quả cuối.")
            self.param_container_layout.addLayout(self._param_row("Tốc độ học", self.dbl_ada_lr))

        elif algo == "svm":
            self.dbl_svm_c = self._spin_double(0.01, 10000.0, 2, 1.0, 1.0,
                "C lớn: bắt buộc phân loại đúng từng mẫu — dễ học vẹt. C nhỏ: ưu tiên ranh giới tổng quát.")
            self.param_container_layout.addLayout(self._param_row("Độ nghiêm khắc (C)", self.dbl_svm_c))
            self.combo_kernel = self._combo([
                ("Ranh giới cong (RBF)", "rbf"),
                ("Ranh giới thẳng (tuyến tính)", "linear"),
                ("Đa thức (poly)", "poly"),
            ])
            self.param_container_layout.addLayout(self._param_row("Kiểu ranh giới", self.combo_kernel))
            self.combo_svm_gamma = self._combo([
                ("Tự động theo dữ liệu (scale)", "scale"),
                ("Tự động (auto)", "auto"),
                ("0.001", 0.001), ("0.01", 0.01), ("0.1", 0.1), ("1.0", 1.0),
            ], "Phạm vi ảnh hưởng của mỗi điểm mẫu: nhỏ = cong mượt, lớn = cong ôm dữ liệu.")
            self.param_container_layout.addLayout(self._param_row("Phạm vi ảnh hưởng (gamma)", self.combo_svm_gamma))
            self.spin_svm_degree = self._spin_int(2, 10, 3, "Bậc đa thức — chỉ dùng khi chọn ranh giới Đa thức (poly).")
            self.param_container_layout.addLayout(self._param_row("Bậc đa thức (degree)", self.spin_svm_degree))

        elif algo == "logistic":
            self.dbl_log_c = self._spin_double(0.01, 10000.0, 2, 1.0, 1.0,
                "C lớn: học bám sát từng mẫu. C nhỏ: ưu tiên quy luật tổng quát.")
            self.param_container_layout.addLayout(self._param_row("Độ nghiêm khắc (C)", self.dbl_log_c))
            self.combo_log_penalty = self._combo([
                ("L2 — phạt đều (mặc định)", "l2"),
                ("L1 — tự bỏ đặc trưng yếu", "l1"),
                ("Không phạt (none)", "none"),
            ], "Cách phạt mô hình quá phức tạp.")
            self.param_container_layout.addLayout(self._param_row("Kiểu phạt (penalty)", self.combo_log_penalty))
            self.spin_log_iter = self._spin_int(10, 5000, 300, "Số vòng lặp tối đa khi tìm lời giải.")
            self.param_container_layout.addLayout(self._param_row("Số vòng lặp tối đa", self.spin_log_iter))

        elif algo == "nb":
            self.dbl_nb_smooth = self._spin_double(0.0, 1.0, 10, 1e-9, 1e-9,
                "Làm mịn phương sai tránh chia 0. Thường để mặc định 1e-9.")
            self.param_container_layout.addLayout(self._param_row("Làm mịn phương sai", self.dbl_nb_smooth))

        elif algo == "lda":
            self.combo_lda_shrink = self._combo([
                ("Tự động (auto) — nên dùng", "auto"),
                ("Không co lại (none)", "none"),
                ("0.1", 0.1), ("0.3", 0.3), ("0.5", 0.5), ("0.9", 0.9),
            ], "Co nhỏ các con số thống kê để chịu được dữ liệu ít chiều sâu. Auto phù hợp hầu hết trường hợp.")
            self.param_container_layout.addLayout(self._param_row("Mức co (shrinkage)", self.combo_lda_shrink))

        elif algo == "mlp":
            self.spin_mlp_h = self._spin_int(2, 256, 16, "Số ô tính trung gian. Nhiều ô = thông minh hơn nhưng dễ học vẹt và chậm.")
            self.param_container_layout.addLayout(self._param_row("Số ô tính trung gian", self.spin_mlp_h))
            self.dbl_mlp_lr = self._spin_double(0.0001, 1.0, 4, 0.01, 0.001, "Bước đi khi học. Lớn = học nhanh nhưng dễ overshoot.")
            self.param_container_layout.addLayout(self._param_row("Tốc độ học", self.dbl_mlp_lr))
            self.dbl_mlp_alpha = self._spin_double(0.0, 10.0, 6, 0.0001, 0.0001, "Phạt trọng số lớn — giúp chống học vẹt.")
            self.param_container_layout.addLayout(self._param_row("Phạt trọng số (alpha)", self.dbl_mlp_alpha))
            self.spin_mlp_iter = self._spin_int(10, 2000, 200, "Số vòng học tối đa trên toàn bộ dữ liệu.")
            self.param_container_layout.addLayout(self._param_row("Số vòng học tối đa", self.spin_mlp_iter))
            self.combo_mlp_act = self._combo([("ReLU (mặc định)", "relu"), ("Tanh", "tanh")])
            self.param_container_layout.addLayout(self._param_row("Hàm kích hoạt", self.combo_mlp_act))

        elif algo == "ridge":
            self.dbl_ridge_a = self._spin_double(0.0001, 10000.0, 4, 1.0, 0.5,
                "Alpha lớn: trọng số nhỏ hơn, mô hình mượt và ổn định hơn với dữ liệu ít.")
            self.param_container_layout.addLayout(self._param_row("Độ phẳng hóa (alpha)", self.dbl_ridge_a))

        elif algo == "sgd":
            self.dbl_sgd_a = self._spin_double(0.000001, 1.0, 6, 0.0001, 0.0001,
                "Alpha lớn: mô hình mượt hơn, ít học vẹt.")
            self.param_container_layout.addLayout(self._param_row("Độ phẳng hóa (alpha)", self.dbl_sgd_a))
            self.spin_sgd_iter = self._spin_int(10, 5000, 500, "Số vòng học tối đa.")
            self.param_container_layout.addLayout(self._param_row("Số vòng học tối đa", self.spin_sgd_iter))
            self.combo_sgd_penalty = self._combo([
                ("L2 — phạt đều", "l2"),
                ("L1 — tự bỏ đặc trưng yếu", "l1"),
                ("ElasticNet — kết hợp cả hai", "elasticnet"),
            ])
            self.param_container_layout.addLayout(self._param_row("Kiểu phạt (penalty)", self.combo_sgd_penalty))

        elif algo == "nearest_centroid":
            self.combo_nc_m = self._combo([
                ("Khoảng cách thẳng (Euclidean)", "euclidean"),
                ("Theo ô bàn cờ (Manhattan)", "manhattan"),
            ])
            self.param_container_layout.addLayout(self._param_row("Cách đo độ giống", self.combo_nc_m))

        elif algo == "qda":
            self.dbl_qda_reg = self._spin_double(0.0, 1.0, 3, 0.1, 0.05,
                "Làm mịn ma trận thống kê — quan trọng khi dữ liệu ít so với số đặc trưng. 0.1 phù hợp hầu hết trường hợp.")
            self.param_container_layout.addLayout(self._param_row("Làm mịn thống kê (reg_param)", self.dbl_qda_reg))

    # ─────────────────────────── Actions ─────────────────────────────────

    def _apply_skill_mode(self) -> None:
        """Beginner: ẩn Feature Engineering + Siêu tham số, hiện gợi ý dẫn dắt."""
        beginner = self.chk_beginner.isChecked()
        self.box_feat.setVisible(not beginner)
        self.box_param.setVisible(not beginner)
        self.lbl_beginner_hint.setVisible(beginner)

    def _get_current_config(self) -> Any:
        algo = self.combo_algo.currentData()
        if algo == "knn":
            k = self.spin_k.value() if hasattr(self, "spin_k") else 3
            weights = self.combo_weights.currentData() if hasattr(self, "combo_weights") else "uniform"
            metric = self.combo_metric.currentData() if hasattr(self, "combo_metric") else "euclidean"
            return KNNConfig(k=k, weights=weights, metric=metric)
        elif algo == "tree":
            return DecisionTreeConfig(
                max_depth=self.spin_depth.value() if hasattr(self, "spin_depth") else 4,
                min_samples_split=self.spin_min_split.value() if hasattr(self, "spin_min_split") else 2,
                min_samples_leaf=self.spin_min_leaf.value() if hasattr(self, "spin_min_leaf") else 1,
                criterion=self.combo_crit.currentData() if hasattr(self, "combo_crit") else "gini",
            )
        elif algo == "forest":
            return RandomForestConfig(
                n_estimators=self.spin_trees.value() if hasattr(self, "spin_trees") else 5,
                max_depth=self.spin_f_depth.value() if hasattr(self, "spin_f_depth") else 4,
                min_samples_leaf=self.spin_f_minleaf.value() if hasattr(self, "spin_f_minleaf") else 1,
                criterion=self.combo_f_crit.currentData() if hasattr(self, "combo_f_crit") else "gini",
            )
        elif algo == "gbdt":
            return GradientBoostingConfig(
                n_estimators=self.spin_gbdt.value() if hasattr(self, "spin_gbdt") else 5,
                learning_rate=self.dbl_gbdt_lr.value() if hasattr(self, "dbl_gbdt_lr") else 0.1,
                max_depth=self.spin_gbdt_depth.value() if hasattr(self, "spin_gbdt_depth") else 3,
                subsample=self.dbl_gbdt_sub.value() if hasattr(self, "dbl_gbdt_sub") else 1.0,
            )
        elif algo == "svm":
            gamma_raw = self.combo_svm_gamma.currentData() if hasattr(self, "combo_svm_gamma") else "scale"
            return SVMConfig(
                c=self.dbl_svm_c.value() if hasattr(self, "dbl_svm_c") else 1.0,
                kernel=self.combo_kernel.currentData() if hasattr(self, "combo_kernel") else "rbf",
                gamma=gamma_raw,
                degree=self.spin_svm_degree.value() if hasattr(self, "spin_svm_degree") else 3,
            )
        elif algo == "logistic":
            return LogisticRegressionConfig(
                c=self.dbl_log_c.value() if hasattr(self, "dbl_log_c") else 1.0,
                penalty=self.combo_log_penalty.currentData() if hasattr(self, "combo_log_penalty") else "l2",
                max_iter=self.spin_log_iter.value() if hasattr(self, "spin_log_iter") else 300,
            )
        elif algo == "nb":
            smooth = self.dbl_nb_smooth.value() if hasattr(self, "dbl_nb_smooth") else 1e-9
            return NaiveBayesConfig(var_smoothing=smooth)
        elif algo == "lda":
            shrink = self.combo_lda_shrink.currentData() if hasattr(self, "combo_lda_shrink") else "auto"
            return LDAConfig(solver="lsqr", shrinkage=shrink)
        elif algo == "mlp":
            return MLPConfig(
                hidden_units=self.spin_mlp_h.value() if hasattr(self, "spin_mlp_h") else 16,
                learning_rate_init=self.dbl_mlp_lr.value() if hasattr(self, "dbl_mlp_lr") else 0.01,
                alpha=self.dbl_mlp_alpha.value() if hasattr(self, "dbl_mlp_alpha") else 0.0001,
                max_iter=self.spin_mlp_iter.value() if hasattr(self, "spin_mlp_iter") else 200,
                activation=self.combo_mlp_act.currentData() if hasattr(self, "combo_mlp_act") else "relu",
            )
        elif algo == "ridge":
            alpha = self.dbl_ridge_a.value() if hasattr(self, "dbl_ridge_a") else 1.0
            return RidgeConfig(alpha=alpha)
        elif algo == "sgd":
            return SGDConfig(
                alpha=self.dbl_sgd_a.value() if hasattr(self, "dbl_sgd_a") else 0.0001,
                max_iter=self.spin_sgd_iter.value() if hasattr(self, "spin_sgd_iter") else 500,
                penalty=self.combo_sgd_penalty.currentData() if hasattr(self, "combo_sgd_penalty") else "l2",
            )
        elif algo == "nearest_centroid":
            metric = "manhattan" if hasattr(self, "combo_nc_m") and self.combo_nc_m.currentIndex() == 1 else "euclidean"
            return NearestCentroidConfig(metric=metric)
        elif algo == "qda":
            reg = self.dbl_qda_reg.value() if hasattr(self, "dbl_qda_reg") else 0.1
            return QDAConfig(reg_param=reg)
        elif algo == "extra_trees":
            return ExtraTreesConfig(
                n_estimators=self.spin_et_n.value() if hasattr(self, "spin_et_n") else 5,
                max_depth=self.spin_et_depth.value() if hasattr(self, "spin_et_depth") else 4,
                min_samples_leaf=self.spin_et_minleaf.value() if hasattr(self, "spin_et_minleaf") else 1,
                criterion=self.combo_et_crit.currentData() if hasattr(self, "combo_et_crit") else "gini",
            )
        elif algo == "adaboost":
            return AdaBoostConfig(
                n_estimators=self.spin_ada_n.value() if hasattr(self, "spin_ada_n") else 5,
                learning_rate=self.dbl_ada_lr.value() if hasattr(self, "dbl_ada_lr") else 0.5,
            )
        return None

    def start_auto_select(self) -> None:
        """Để máy tự chọn: thử 11 mô hình nhẹ, chọn tốt nhất rồi huấn luyện luôn."""
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa đủ dữ liệu",
                f"Hiện chỉ có {len(counts)} thần chú.\nCần ít nhất 2 lớp để máy tự chọn được.",
            )
            return
        if self._auto_worker is not None and self._auto_worker.isRunning():
            return

        self.btn_auto.setEnabled(False)
        self.btn_train.setEnabled(False)
        self.btn_auto.setText("Đang thử từng mô hình để chọn giúp bạn...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(5)

        self._auto_worker = AutoSelectWorker(self.dataset_dir)
        self._auto_worker.sig_progress.connect(
            lambda pct, msg: (self.progress_bar.setValue(pct), self.btn_auto.setText(msg))
        )
        self._auto_worker.sig_finished.connect(self._on_auto_selected)
        self._auto_worker.sig_error.connect(self._on_auto_error)
        self._auto_worker.start()

    def _on_auto_selected(self, algo_key: str, config: Any, val_acc: float, tried: list) -> None:
        self.btn_auto.setEnabled(True)
        self.btn_train.setEnabled(True)
        self.btn_auto.setText("Không biết chọn? Để máy tự chọn giúp bạn")

        # Chọn thuật toán trong combo + áp tham số vào controls
        idx = self.combo_algo.findData(algo_key)
        if idx >= 0:
            self.combo_algo.setCurrentIndex(idx)
        self._apply_config_to_controls(algo_key, config)
        self.chk_beginner.setChecked(False)

        tried_txt = ", ".join(f"{k} {v*100:.0f}%" for k, v in sorted(tried, key=lambda t: -t[1])[:3])
        self.lbl_tip.setText(
            f"<b>Máy đã thử {len(tried)} mô hình</b> và chọn <b>{algo_key.upper()}</b> "
            f"vì đoán đúng nhất ({val_acc*100:.1f}%) trên dữ liệu kiểm tra. "
            f"Top đầu: {tried_txt}. Bấm “Huấn luyện & đánh giá” để chốt!"
        )

        # Huấn luyện luôn với cấu hình vừa chọn
        self.start_training()

    def _on_auto_error(self, msg: str) -> None:
        self.btn_auto.setEnabled(True)
        self.btn_train.setEnabled(True)
        self.btn_auto.setText("Không biết chọn? Để máy tự chọn giúp bạn")
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Không tự chọn được", f"Đã xảy ra lỗi khi thử các mô hình:\n{msg}")

    def _apply_config_to_controls(self, algo_key: str, config: Any) -> None:
        """Đổ giá trị config vào ô điền số / combo tương ứng sau khi đổi thuật toán."""
        try:
            if algo_key == "knn":
                if hasattr(self, "spin_k"):
                    self.spin_k.setValue(int(getattr(config, "k", 3)))
                if hasattr(self, "combo_weights"):
                    i = self.combo_weights.findData(getattr(config, "weights", "uniform"))
                    if i >= 0:
                        self.combo_weights.setCurrentIndex(i)
                if hasattr(self, "combo_metric"):
                    i = self.combo_metric.findData(getattr(config, "metric", "euclidean"))
                    if i >= 0:
                        self.combo_metric.setCurrentIndex(i)
            elif algo_key == "tree":
                self.spin_depth.setValue(int(getattr(config, "max_depth", 4)))
                self.spin_min_split.setValue(int(getattr(config, "min_samples_split", 2)))
                self.spin_min_leaf.setValue(int(getattr(config, "min_samples_leaf", 1)))
                i = self.combo_crit.findData(getattr(config, "criterion", "gini"))
                if i >= 0:
                    self.combo_crit.setCurrentIndex(i)
            elif algo_key == "forest":
                self.spin_trees.setValue(int(getattr(config, "n_estimators", 5)))
                self.spin_f_depth.setValue(int(getattr(config, "max_depth", 4)))
                self.spin_f_minleaf.setValue(int(getattr(config, "min_samples_leaf", 1)))
                i = self.combo_f_crit.findData(getattr(config, "criterion", "gini"))
                if i >= 0:
                    self.combo_f_crit.setCurrentIndex(i)
            elif algo_key == "gbdt":
                self.spin_gbdt.setValue(int(getattr(config, "n_estimators", 5)))
                self.dbl_gbdt_lr.setValue(float(getattr(config, "learning_rate", 0.1)))
                self.spin_gbdt_depth.setValue(int(getattr(config, "max_depth", 3)))
                self.dbl_gbdt_sub.setValue(float(getattr(config, "subsample", 1.0)))
            elif algo_key == "svm":
                self.dbl_svm_c.setValue(float(getattr(config, "c", 1.0)))
                i = self.combo_kernel.findData(getattr(config, "kernel", "rbf"))
                if i >= 0:
                    self.combo_kernel.setCurrentIndex(i)
                gamma = getattr(config, "gamma", "scale")
                i = self.combo_svm_gamma.findData(gamma)
                if i >= 0:
                    self.combo_svm_gamma.setCurrentIndex(i)
                self.spin_svm_degree.setValue(int(getattr(config, "degree", 3)))
            elif algo_key == "logistic":
                self.dbl_log_c.setValue(float(getattr(config, "c", 1.0)))
                i = self.combo_log_penalty.findData(getattr(config, "penalty", "l2"))
                if i >= 0:
                    self.combo_log_penalty.setCurrentIndex(i)
                self.spin_log_iter.setValue(int(getattr(config, "max_iter", 300)))
            elif algo_key == "nb":
                self.dbl_nb_smooth.setValue(float(getattr(config, "var_smoothing", 1e-9)))
            elif algo_key == "lda":
                i = self.combo_lda_shrink.findData(getattr(config, "shrinkage", "auto"))
                if i >= 0:
                    self.combo_lda_shrink.setCurrentIndex(i)
            elif algo_key == "mlp":
                self.spin_mlp_h.setValue(int(getattr(config, "hidden_units", 16)))
                self.dbl_mlp_lr.setValue(float(getattr(config, "learning_rate_init", 0.01)))
                self.dbl_mlp_alpha.setValue(float(getattr(config, "alpha", 0.0001)))
                self.spin_mlp_iter.setValue(int(getattr(config, "max_iter", 200)))
                i = self.combo_mlp_act.findData(getattr(config, "activation", "relu"))
                if i >= 0:
                    self.combo_mlp_act.setCurrentIndex(i)
            elif algo_key == "ridge":
                self.dbl_ridge_a.setValue(float(getattr(config, "alpha", 1.0)))
            elif algo_key == "sgd":
                self.dbl_sgd_a.setValue(float(getattr(config, "alpha", 0.0001)))
                self.spin_sgd_iter.setValue(int(getattr(config, "max_iter", 500)))
                i = self.combo_sgd_penalty.findData(getattr(config, "penalty", "l2"))
                if i >= 0:
                    self.combo_sgd_penalty.setCurrentIndex(i)
            elif algo_key == "nearest_centroid":
                i = self.combo_nc_m.findData(getattr(config, "metric", "euclidean"))
                if i >= 0:
                    self.combo_nc_m.setCurrentIndex(i)
            elif algo_key == "qda":
                self.dbl_qda_reg.setValue(float(getattr(config, "reg_param", 0.1)))
            elif algo_key == "extra_trees":
                self.spin_et_n.setValue(int(getattr(config, "n_estimators", 5)))
                self.spin_et_depth.setValue(int(getattr(config, "max_depth", 4)))
                self.spin_et_minleaf.setValue(int(getattr(config, "min_samples_leaf", 1)))
                i = self.combo_et_crit.findData(getattr(config, "criterion", "gini"))
                if i >= 0:
                    self.combo_et_crit.setCurrentIndex(i)
            elif algo_key == "adaboost":
                self.spin_ada_n.setValue(int(getattr(config, "n_estimators", 5)))
                self.dbl_ada_lr.setValue(float(getattr(config, "learning_rate", 0.5)))
        except Exception:
            pass

    def start_training(self) -> None:
        counts = count_user_spell_samples(self.dataset_dir)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Chưa đủ dữ liệu",
                f"Hiện chỉ có {len(counts)} thần chú trong dataset/spells/.\n\n"
                "Cần ít nhất 2 lớp cử chỉ (ví dụ Lumos và Nox) để máy học có thể phân loại.",
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
        self.btn_train.setText("Đang huấn luyện...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        self._current_worker = MlLabTrainWorker(
            dataset_root=self.dataset_dir,
            algo=algo,
            config=config,
            feature_config=feat_cfg,
            val_fraction=0.2,
            augment_multiplier=3 if self.chk_augment.isChecked() else 1,
        )
        self._current_worker.sig_progress.connect(lambda pct, msg: self.progress_bar.setValue(pct))
        self._current_worker.sig_finished.connect(self._on_training_finished)
        self._current_worker.sig_error.connect(self._on_training_error)
        self._current_worker.start()

    def _on_training_finished(self, result: TrainClassicResult) -> None:
        self.btn_train.setEnabled(True)
        self.btn_train.setText("Huấn luyện & đánh giá")
        self.progress_bar.setVisible(False)
        self._last_result = result
        self.btn_flash_direct.setVisible(True)
        self.btn_model_card.setVisible(True)
        self.class_breakdown.set_result(result)
        self.misclass_widget.set_result(result)

        # Visualizer
        self.canvas.set_data(result.pca_result, result.class_names)
        self.cm_widget.set_results(
            cm=result.confusion_matrix,
            class_names=result.class_names,
            val_acc=result.val_accuracy,
            train_acc=result.train_accuracy,
            cv_mean=result.cv_mean,
            cv_std=result.cv_std,
        )

        # AI Coach: chẩn đoán & lời khuyên tự động
        self.advice_card.set_result(result)

        # Math dissection
        if result.algo in ("tree", "forest", "gbdt", "extra_trees", "adaboost"):
            self.tree_vis.setVisible(True)
            self.weights_vis.setVisible(False)
            if result.algo == "forest":
                model_to_show = result.model.estimators_[0]
            elif result.algo == "gbdt":
                model_to_show = result.model.estimators_[0, 0] if hasattr(result.model, "estimators_") else result.model
            elif result.algo == "adaboost":
                model_to_show = result.model.estimators_[0]
            else:
                model_to_show = result.model
            self.tree_vis.set_tree_model(
                model_to_show,
                [friendly_feature_name(f) for f in result.feature_names],
                result.class_names,
            )
        elif result.algo in ("logistic", "svm", "lda", "ridge", "sgd"):
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "coef_"):
                self.weights_vis.set_weights(
                    result.model.coef_,
                    [friendly_feature_name(f) for f in result.feature_names],
                    result.class_names,
                )
        elif result.algo == "nearest_centroid":
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "centroids_"):
                self.weights_vis.set_weights(
                    result.model.centroids_,
                    [friendly_feature_name(f) for f in result.feature_names],
                    result.class_names,
                )
        elif result.algo == "qda":
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "means_"):
                self.weights_vis.set_weights(
                    result.model.means_,
                    [friendly_feature_name(f) for f in result.feature_names],
                    result.class_names,
                )
        elif result.algo in ("logistic", "svm", "lda"):
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "coef_"):
                self.weights_vis.set_weights(
                result.model.coef_,
                [friendly_feature_name(f) for f in result.feature_names],
                result.class_names,
            )
        elif result.algo == "mlp":
            self.tree_vis.setVisible(False)
            self.weights_vis.setVisible(True)
            if hasattr(result.model, "coefs_"):
                self.weights_vis.set_weights(
                    result.model.coefs_[0].T,
                    [friendly_feature_name(f) for f in result.feature_names],
                    [f"Nơ-ron {i}" for i in range(result.model.coefs_[0].shape[1])],
                )
        else:
            self.tree_vis.setVisible(True)
            self.weights_vis.setVisible(False)

        self.sig_model_trained.emit(result)

    def _on_training_error(self, msg: str) -> None:
        self.btn_train.setEnabled(True)
        self.btn_train.setText("Huấn luyện & đánh giá")
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Lỗi huấn luyện", f"Không thể hoàn tất huấn luyện:\n{msg}")

    def _open_model_card(self) -> None:
        if not self._last_result:
            return
        dlg = ModelCardDialog(self._last_result, self)
        dlg.exec()

    def _open_flash_dialog(self) -> None:
        if not self._last_result:
            return
        dlg = FlashDialog(self._last_result, self)
        dlg.exec()

"""
ml_lab/ui/tabs/tab_simulator_export.py — Tab 5: Giả Lập What-If, Giải Thích SHAP & Xuất Mã C/C++.

Cho phép:
1. Thử nghiệm trực quan các đặc trưng ảo bằng thanh trượt What-If.
2. Giải thích đóng góp từng đặc trưng (SHAP / Feature Attribution Waterfall).
3. Xuất và xem trước mã nguồn C++ thuần zero-malloc tương thích ESP32.
4. Nạp code trực tiếp 1-click vào ESP32.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.data.feature_analysis import compute_local_feature_contributions
from ml_lab.ui.widgets.flash_dialog import FlashDialog


class TabSimulatorExport(QWidget):
    """
    Tab Giả Lập What-If, Giải Thích SHAP & Nạp Code ESP32.
    """

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self.c_exporter = CCodeExporter()
        self._current_result: TrainClassicResult | None = None
        self._sim_sliders: list[QSlider] = []
        self._sim_labels: list[QLabel] = []

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: What-If Interactive Simulator & SHAP ──────
        left_box = QFrame()
        left_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        l_layout = QVBoxLayout(left_box)

        lbl_sim_t = QLabel("🎮 GIẢ LẬP ĐẶC TRƯNG ẢO (WHAT-IF SIMULATOR)")
        lbl_sim_t.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        l_layout.addWidget(lbl_sim_t)

        # Live Outcome Card
        self.outcome_card = QFrame()
        self.outcome_card.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        oc_layout = QVBoxLayout(self.outcome_card)
        oc_layout.setSpacing(2)

        lbl_o_tag = QLabel("DỰ ĐOÁN TỨC THỜI:")
        lbl_o_tag.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b;")
        self.lbl_pred_class = QLabel("CHƯA CÓ MODEL")
        self.lbl_pred_class.setStyleSheet("font-size: 18px; font-weight: 800; color: #007aff;")
        self.lbl_pred_conf = QLabel("Độ tin cậy: --%")
        self.lbl_pred_conf.setStyleSheet("font-size: 11px; font-weight: 600; color: #166534;")

        oc_layout.addWidget(lbl_o_tag)
        oc_layout.addWidget(self.lbl_pred_class)
        oc_layout.addWidget(self.lbl_pred_conf)
        l_layout.addWidget(self.outcome_card)

        # Sliders Area
        lbl_adj = QLabel("Kéo thanh trượt để thay đổi giá trị đặc trưng:")
        lbl_adj.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500;")
        l_layout.addWidget(lbl_adj)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.slider_container = QWidget()
        self.slider_layout = QVBoxLayout(self.slider_container)
        self.slider_layout.setSpacing(6)
        scroll.setWidget(self.slider_container)
        l_layout.addWidget(scroll, stretch=1)

        # SHAP Attribution Table
        lbl_shap = QLabel("🔍 TẠI SAO MÁY ĐOÁN NHƯ VẬY? (SHAP ATTRIBUTION):")
        lbl_shap.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff; margin-top: 6px;")
        l_layout.addWidget(lbl_shap)

        self.table_shap = QTableWidget()
        self.table_shap.setColumnCount(3)
        self.table_shap.setHorizontalHeaderLabels(["Đặc Trưng", "Đóng Góp", "Tác Động"])
        self.table_shap.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_shap.verticalHeader().setVisible(False)
        self.table_shap.setStyleSheet("QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; }")
        l_layout.addWidget(self.table_shap, stretch=1)

        splitter.addWidget(left_box)

        # ── Right: C++ Exporter & 1-Click Flasher ────────────
        right_box = QFrame()
        right_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        r_layout = QVBoxLayout(right_box)

        top_r_row = QHBoxLayout()
        lbl_code_t = QLabel("🚀 XUẤT MÃ NGUỒN C++ & NẠP FIRMWARE ESP32")
        lbl_code_t.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        top_r_row.addWidget(lbl_code_t)
        top_r_row.addStretch()

        btn_copy = QPushButton("📋 Copy Code")
        btn_copy.setStyleSheet("padding: 5px 10px; font-size: 11px; font-weight: 600; border-radius: 5px; background: #f8fafc; border: 1px solid #cbd5e1;")
        btn_copy.clicked.connect(self._copy_current_code)
        top_r_row.addWidget(btn_copy)

        self.btn_flash = QPushButton("🔥 Nạp Code Sang ESP32 (1-Click)")
        self.btn_flash.setStyleSheet(
            "QPushButton { background: #34c759; color: white; font-weight: 700; font-size: 11px; padding: 6px 14px; border-radius: 6px; border: none; } "
            "QPushButton:hover { background: #2fb34f; }"
        )
        self.btn_flash.clicked.connect(self._open_flash_dialog)
        top_r_row.addWidget(self.btn_flash)

        r_layout.addLayout(top_r_row)

        self.code_tabs = QTabWidget()
        self.code_tabs.setStyleSheet("QTabBar::tab { font-weight: 600; padding: 6px 12px; }")

        # Tab 1: C++ Source
        self.cc_code_edit = QTextEdit()
        self.cc_code_edit.setReadOnly(True)
        self.cc_code_edit.setFont(QFont("Consolas", 10))
        self.cc_code_edit.setStyleSheet(
            "background-color: #18181b; color: #d4d4d8; border-radius: 6px; padding: 10px; border: 1px solid #27272a;"
        )
        self.code_tabs.addTab(self.cc_code_edit, "📄 model_classic.cc (C++ Logic)")

        # Tab 2: Header
        self.h_code_edit = QTextEdit()
        self.h_code_edit.setReadOnly(True)
        self.h_code_edit.setFont(QFont("Consolas", 10))
        self.h_code_edit.setStyleSheet(
            "background-color: #18181b; color: #d4d4d8; border-radius: 6px; padding: 10px; border: 1px solid #27272a;"
        )
        self.code_tabs.addTab(self.h_code_edit, "📄 model_classic.h (Header)")

        # Tab 3: ESP32 main.cpp reference
        self.main_cpp_edit = QTextEdit()
        self.main_cpp_edit.setReadOnly(True)
        self.main_cpp_edit.setFont(QFont("Consolas", 10))
        self.main_cpp_edit.setStyleSheet(
            "background-color: #18181b; color: #d4d4d8; border-radius: 6px; padding: 10px; border: 1px solid #27272a;"
        )
        self._load_main_cpp_reference()
        self.code_tabs.addTab(self.main_cpp_edit, "🚀 esp32_classic_ml/main/main.cpp")

        r_layout.addWidget(self.code_tabs, stretch=1)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

    def set_trained_model(self, result: TrainClassicResult) -> None:
        self._current_result = result
        self._rebuild_simulator_sliders()
        self._update_code_views()
        self._run_live_simulation()

    def _rebuild_simulator_sliders(self) -> None:
        while self.slider_layout.count():
            item = self.slider_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    c2 = item.layout().takeAt(0)
                    if c2.widget():
                        c2.widget().deleteLater()

        self._sim_sliders.clear()
        self._sim_labels.clear()

        if not self._current_result:
            return

        features = self._current_result.feature_names[:8]
        for f_idx, feat_name in enumerate(features):
            row = QHBoxLayout()
            lbl = QLabel(feat_name)
            lbl.setStyleSheet("font-size: 11px; font-weight: 500;")
            
            val_lbl = QLabel("0.00")
            val_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #007aff;")
            val_lbl.setFixedWidth(40)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-300, 300)
            slider.setValue(0)
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(f"{v/100.0:.2f}"))
            slider.valueChanged.connect(self._run_live_simulation)

            row.addWidget(lbl, stretch=1)
            row.addWidget(slider, stretch=2)
            row.addWidget(val_lbl)

            self.slider_layout.addLayout(row)
            self._sim_sliders.append(slider)
            self._sim_labels.append(val_lbl)

    def _run_live_simulation(self) -> None:
        if not self._current_result or not self._sim_sliders:
            return

        n_feats = len(self._current_result.feature_names)
        feat_vector = np.zeros(n_feats, dtype=np.float32)

        for i, slider in enumerate(self._sim_sliders):
            if i < n_feats:
                feat_vector[i] = slider.value() / 100.0

        model = self._current_result.model
        scaler = self._current_result.scaler

        X_in = scaler.transform(feat_vector.reshape(1, -1)) if scaler else feat_vector.reshape(1, -1)
        pred = model.predict(X_in)[0]

        cls_names = self._current_result.class_names
        pred_name = cls_names[pred] if pred < len(cls_names) else f"Class {pred}"

        conf = 100.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_in)[0]
            conf = float(np.max(probs)) * 100.0

        self.lbl_pred_class.setText(pred_name)
        self.lbl_pred_conf.setText(f"Độ tin cậy: {conf:.1f}%")

        # Cập nhật SHAP waterfall table
        attribs = compute_local_feature_contributions(
            model=model,
            scaler=scaler,
            raw_sample=feat_vector,
            feature_names=self._current_result.feature_names,
            algo=self._current_result.algo,
            top_k=5,
        )
        self.table_shap.setRowCount(len(attribs))
        for r_idx, at in enumerate(attribs):
            self.table_shap.setItem(r_idx, 0, QTableWidgetItem(at["name"]))
            
            c_item = QTableWidgetItem(f"{at['contribution']:+.3f}")
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if at["contribution"] >= 0:
                c_item.setForeground(QColor(22, 101, 52))
            else:
                c_item.setForeground(QColor(225, 29, 72))
            self.table_shap.setItem(r_idx, 1, c_item)

            self.table_shap.setItem(r_idx, 2, QTableWidgetItem(at["impact"]))

    def _update_code_views(self) -> None:
        if not self._current_result:
            return
        h_code = self.c_exporter.generate_header_string(self._current_result)
        cc_code = self.c_exporter.generate_source_string(self._current_result)
        self.h_code_edit.setPlainText(h_code)
        self.cc_code_edit.setPlainText(cc_code)

    def _load_main_cpp_reference(self) -> None:
        main_cpp_path = Path("esp32_classic_ml/main/main.cpp")
        if main_cpp_path.exists():
            try:
                self.main_cpp_edit.setPlainText(main_cpp_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _copy_current_code(self) -> None:
        curr = self.code_tabs.currentWidget()
        if isinstance(curr, QTextEdit):
            curr.selectAll()
            curr.copy()
            QMessageBox.information(self, "Đã Sao Chép", "Đã copy mã nguồn vào Clipboard!")

    def _open_flash_dialog(self) -> None:
        if not self._current_result:
            QMessageBox.warning(self, "Chưa Có Model", "Vui lòng huấn luyện mô hình trước khi nạp code.")
            return

        dlg = FlashDialog(self._current_result, self)
        dlg.exec()

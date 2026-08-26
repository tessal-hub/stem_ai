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
    QApplication,
    QComboBox,
    QFileDialog,
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
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.experiment_store import ExperimentStore
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.data.feature_analysis import compute_local_feature_contributions
from ml_lab.ui.friendly_terms import friendly_feature_name
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
        left_box.setStyleSheet(ls.card())
        l_layout = QVBoxLayout(left_box)

        lbl_sim_t = QLabel("THỬ NGHIỆM NHANH: MÁY SẼ ĐOÁN GÌ?")
        lbl_sim_t.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_sim_t)

        # Live Outcome Card
        self.outcome_card = QFrame()
        self.outcome_card.setStyleSheet(f".QFrame {{ background: {ls.SURFACE_SUNK}; border: none; border-radius: {ls.RADIUS_MD}px; padding: {ls.SP_3}px; }}")
        oc_layout = QVBoxLayout(self.outcome_card)
        oc_layout.setSpacing(2)

        lbl_o_tag = QLabel("KẾT LUẬN CỦA MÁY:")
        lbl_o_tag.setStyleSheet("font-size: 11px; font-weight: 700; color: #5b6b7f;; border: none; background: transparent;")
        self.lbl_pred_class = QLabel("CHƯA CÓ MÔ HÌNH")
        self.lbl_pred_class.setStyleSheet(ls.font(20, 800) + f"color: {ls.ACCENT};; border: none; background: transparent;")
        self.lbl_pred_conf = QLabel("Mức chắc chắn: --%")
        self.lbl_pred_conf.setStyleSheet("font-size: 11px; font-weight: 600; color: #166534;; border: none; background: transparent;")

        oc_layout.addWidget(lbl_o_tag)
        oc_layout.addWidget(self.lbl_pred_class)
        oc_layout.addWidget(self.lbl_pred_conf)
        l_layout.addWidget(self.outcome_card)

        # Sliders Area
        lbl_adj = QLabel("Kéo các thanh để giả lập giá trị đo được — máy sẽ đoán lại ngay:")
        lbl_adj.setStyleSheet("font-size: 11px; color: #5b6b7f; font-weight: 500;; border: none; background: transparent;")
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
        lbl_shap = QLabel("VÌ SAO MÁY QUYẾT ĐỊNH NHƯ VẬY?")
        lbl_shap.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_shap)

        self.table_shap = QTableWidget()
        self.table_shap.setColumnCount(3)
        self.table_shap.setHorizontalHeaderLabels(["Đặc trưng", "Đóng góp", "Nghĩa là"])
        self.table_shap.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_shap.verticalHeader().setVisible(False)
        self.table_shap.setStyleSheet(ls.DATA_TABLE)
        l_layout.addWidget(self.table_shap, stretch=1)

        splitter.addWidget(left_box)

        # ── Right: C++ Exporter & 1-Click Flasher ────────────
        right_box = QFrame()
        right_box.setStyleSheet(ls.card())
        r_layout = QVBoxLayout(right_box)

        top_r_row = QHBoxLayout()
        lbl_code_t = QLabel("XUẤT MÃ C++ & NẠP LÊN WAND")
        lbl_code_t.setStyleSheet(ls.section_label())
        top_r_row.addWidget(lbl_code_t)
        top_r_row.addStretch()

        btn_copy = QPushButton("Copy mã")
        btn_copy.setStyleSheet(ls.BTN_SECONDARY)
        btn_copy.clicked.connect(self._copy_current_code)
        top_r_row.addWidget(btn_copy)

        btn_save = QPushButton("Lưu mã ra file")
        btn_save.setToolTip("Lưu model_classic.h & model_classic.cc ra thư mục tùy chọn")
        btn_save.setStyleSheet(ls.BTN_SECONDARY)
        btn_save.clicked.connect(self._save_code_to_files)
        top_r_row.addWidget(btn_save)

        self.btn_flash = QPushButton("Nạp lên wand")
        self.btn_flash.setStyleSheet(ls.BTN_SUCCESS)
        self.btn_flash.clicked.connect(self._open_flash_dialog)
        top_r_row.addWidget(self.btn_flash)

        r_layout.addLayout(top_r_row)

        # Mã C++ được tạo tự động theo mô hình — xem đầy đủ bằng "Lưu mã ra file"
        code_note = QLabel(
            "Mô hình huấn luyện xong sẽ được tự động chuyển thành 2 file C++ "
            "(model_classic.h + model_classic.cc) sẵn sàng biên dịch. "
            "Dùng “Lưu mã ra file” hoặc “Copy mã” để xem và mang đi nơi khác."
        )
        code_note.setWordWrap(True)
        code_note.setStyleSheet(ls.note_box(ls.ACCENT))
        r_layout.addWidget(code_note)

        # Tóm tắt mô hình hiện tại
        self.lbl_model_summary = QLabel("Chưa có mô hình nào — hãy huấn luyện ở tab 2.")
        self.lbl_model_summary.setWordWrap(True)
        self.lbl_model_summary.setStyleSheet(
            ls.font(ls.FS_BODY, 600) + f"color: {ls.BODY}; border: none; background: transparent;"
        )
        r_layout.addWidget(self.lbl_model_summary)

        # Chọn file + trình xem mã C++ sinh tự động
        self.code_file_combo = QComboBox()
        self.code_file_combo.setStyleSheet(ls.INPUT_COMBO)
        self.code_file_combo.addItem("model_classic.cc", "cc")
        self.code_file_combo.addItem("model_classic.h", "h")
        self.code_file_combo.setEnabled(False)
        self.code_file_combo.currentIndexChanged.connect(self._refresh_code_view)
        r_layout.addWidget(self.code_file_combo)

        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(QFont("Consolas", 10))
        self.code_view.setStyleSheet(ls.TERMINAL)
        self.code_view.setPlainText(
            "// Chưa có mô hình — hãy huấn luyện ở tab 2.\n"
            "// Mã C++ (model_classic.cc / .h) sẽ được sinh tự động tại đây.\n"
        )
        r_layout.addWidget(self.code_view, stretch=1)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

    def set_trained_model(self, result: TrainClassicResult) -> None:
        self._current_result = result
        self._rebuild_simulator_sliders()
        self._update_code_views()
        self._run_live_simulation()
        self.lbl_empty_code.setVisible(False)

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
            lbl = QLabel(friendly_feature_name(feat_name))
            lbl.setToolTip(f"Mã kỹ thuật: {feat_name}")
            lbl.setStyleSheet("font-size: 11px; font-weight: 500;; border: none; background: transparent;")
            
            val_lbl = QLabel("0.00")
            val_lbl.setStyleSheet(ls.slider_value_label())
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
            item_feat = QTableWidgetItem(friendly_feature_name(at["name"]))
            item_feat.setToolTip(at["name"])
            self.table_shap.setItem(r_idx, 0, item_feat)
            
            c_item = QTableWidgetItem(f"{at['contribution']:+.3f}")
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if at["contribution"] >= 0:
                c_item.setForeground(QColor(ls.SUCCESS_TEXT))
            else:
                c_item.setForeground(QColor(ls.DANGER))
            self.table_shap.setItem(r_idx, 1, c_item)

            self.table_shap.setItem(r_idx, 2, QTableWidgetItem(at["impact"]))

    def _update_code_views(self) -> None:
        if not self._current_result:
            return
        # Sinh mã C++ cho viewer + Copy/Lưu
        self._cached_h_code = self.c_exporter.generate_header_string(self._current_result)
        self._cached_cc_code = self.c_exporter.generate_source_string(self._current_result)
        self.code_file_combo.setEnabled(True)
        r = self._current_result
        self.lbl_model_summary.setText(
            f"Mô hình hiện tại: {r.algo_name} — đoán đúng {r.val_accuracy*100:.1f}% trên dữ liệu mới. "
            f"Thần chú: {', '.join(r.class_names)}."
        )
        self._refresh_code_view()

    def _refresh_code_view(self) -> None:
        want_h = self.code_file_combo.currentData() == "h"
        code = self._cached_h_code if want_h else self._cached_cc_code
        self.code_view.setPlainText(code or "// Chưa có mã — huấn luyện ở tab 2 trước.")

    def _copy_current_code(self) -> None:
        if not getattr(self, "_cached_cc_code", None):
            QMessageBox.warning(self, "Chưa Có Mã", "Hãy huấn luyện mô hình ở tab 2 trước khi copy mã.")
            return
        if self.code_file_combo.currentData() == "h":
            QApplication.clipboard().setText(self._cached_h_code)
            QMessageBox.information(self, "Đã Sao Chép", "Đã copy model_classic.h vào Clipboard!")
        else:
            QApplication.clipboard().setText(self._cached_cc_code)
            QMessageBox.information(self, "Đã Sao Chép", "Đã copy model_classic.cc vào Clipboard!")

    def _save_code_to_files(self) -> None:
        if not self._current_result:
            QMessageBox.warning(self, "Chưa Có Model", "Vui lòng huấn luyện mô hình trước khi xuất mã nguồn.")
            return
        algo_clean = self._current_result.algo
        default_dir = str(ExperimentStore().exports_dir)
        target_dir = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Lưu Mã Nguồn C++", default_dir)
        if not target_dir:
            return
        try:
            h_path = Path(target_dir) / f"model_classic_{algo_clean}.h"
            cc_path = Path(target_dir) / f"model_classic_{algo_clean}.cc"
            h_path.write_text(self.c_exporter.generate_header_string(self._current_result), encoding="utf-8")
            cc_path.write_text(self.c_exporter.generate_source_string(self._current_result), encoding="utf-8")
            QMessageBox.information(
                self,
                "Đã Lưu Mã Nguồn",
                f"Đã lưu 2 file C++ sẵn sàng biên dịch:\n• {h_path.name}\n• {cc_path.name}\n\nTại: {target_dir}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu mã nguồn: {exc}")

    def _open_flash_dialog(self) -> None:
        if not self._current_result:
            QMessageBox.warning(self, "Chưa Có Model", "Vui lòng huấn luyện mô hình trước khi nạp code.")
            return

        dlg = FlashDialog(self._current_result, self)
        dlg.exec()

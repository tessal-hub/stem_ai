"""
ml_lab/ui/tabs/tab_simulator_export.py — Tab 5: Giả Lập What-If, Giải Thích SHAP & Xuất Mã C/C++.

Cho phép:
1. Thử nghiệm trực quan các đặc trưng ảo bằng thanh trượt What-If.
2. Giải thích đóng góp từng đặc trưng (SHAP / Feature Attribution Waterfall).
3. Xuất và xem trước mã nguồn C++ thuần zero-malloc tương thích ESP32.
4. Nạp firmware ESP32 đã build sau khi đồng bộ model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import Qt, QTimer
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ui.layout_utils import scroll_panel
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
        self._cached_h_code: str = ""
        self._cached_cc_code: str = ""
        self._sim_timer = QTimer(self)
        self._sim_timer.setSingleShot(True)
        self._sim_timer.setInterval(120)
        self._sim_timer.timeout.connect(self._run_live_simulation)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        main_layout.setSpacing(ls.SP_3)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        # ── Left: What-If Interactive Simulator & SHAP ──────
        left_box = QFrame()
        left_box.setObjectName("SimLeft")
        left_box.setStyleSheet(ls.card(pad=ls.SP_3))
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        l_layout.setSpacing(ls.SP_2)

        lbl_sim_t = QLabel("Thử nghiệm nhanh: máy sẽ đoán gì?")
        lbl_sim_t.setStyleSheet(ls.chart_title())
        l_layout.addWidget(lbl_sim_t)

        # Live Outcome Card
        self.outcome_card = QFrame()
        self.outcome_card.setStyleSheet(f".QFrame {{ background: {ls.SURFACE_SUNK}; border: none; border-radius: {ls.RADIUS_MD}px; padding: {ls.SP_3}px; }}")
        oc_layout = QVBoxLayout(self.outcome_card)
        oc_layout.setSpacing(2)

        lbl_o_tag = QLabel("KẾT LUẬN CỦA MÁY:")
        lbl_o_tag.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; border: none; background: transparent;")
        self.lbl_pred_class = QLabel("CHƯA CÓ MÔ HÌNH")
        self.lbl_pred_class.setStyleSheet(ls.font(20, 800) + f"color: {ls.ACCENT}; border: none; background: transparent;")
        self.lbl_pred_conf = QLabel("Mức chắc chắn: --%")
        self.lbl_pred_conf.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.SUCCESS_TEXT}; border: none; background: transparent;")

        oc_layout.addWidget(lbl_o_tag)
        oc_layout.addWidget(self.lbl_pred_class)
        oc_layout.addWidget(self.lbl_pred_conf)
        l_layout.addWidget(self.outcome_card)

        # Sliders Area
        lbl_adj = QLabel("Kéo các thanh để giả lập giá trị đo (GIẢ LẬP — kẹp trong phạm vi train, không phải cử chỉ thật):")
        lbl_adj.setWordWrap(True)
        lbl_adj.setStyleSheet(ls.font(ls.FS_CAPTION, 500) + f"color: {ls.MUTED}; border: none; background: transparent;")
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
        lbl_shap = QLabel("Vì sao máy quyết định như vậy?")
        lbl_shap.setStyleSheet(ls.chart_title())
        l_layout.addWidget(lbl_shap)

        self.table_shap = QTableWidget()
        self.table_shap.setColumnCount(3)
        self.table_shap.setHorizontalHeaderLabels(["Đặc trưng", "Đóng góp", "Nghĩa là"])
        self.table_shap.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_shap.verticalHeader().setVisible(False)
        self.table_shap.setStyleSheet(ls.DATA_TABLE)
        l_layout.addWidget(self.table_shap, stretch=1)

        splitter.addWidget(scroll_panel(left_box))

        # ── Right: C++ Exporter & ESP32 Flasher ─────────────
        right_box = QFrame()
        right_box.setObjectName("SimRight")
        right_box.setStyleSheet(ls.card(pad=ls.SP_3))
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        r_layout.setSpacing(ls.SP_2)

        top_r_row = QHBoxLayout()
        lbl_code_t = QLabel("Xuất mã C++ & nạp lên wand")
        lbl_code_t.setStyleSheet(ls.chart_title())
        r_layout.addWidget(lbl_code_t)
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
        self.btn_flash.setToolTip("Sau khi xuất model, chạy idf.py build trong esp32_classic_ml rồi mới nạp.")
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

        splitter.addWidget(scroll_panel(right_box))
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

        self._configure_accessibility(btn_copy, btn_save)

    def _configure_accessibility(self, btn_copy: QPushButton, btn_save: QPushButton) -> None:
        self.table_shap.setAccessibleName("Bảng giải thích mức độ đóng góp của từng đặc trưng SHAP")
        btn_copy.setAccessibleName("Sao chép mã nguồn C++ vào clipboard")
        btn_save.setAccessibleName("Lưu các file mã nguồn C++ ra đĩa")
        self.btn_flash.setAccessibleName("Nạp mô hình vừa huấn luyện lên đũa thần ESP32")
        self.code_file_combo.setAccessibleName("Chọn xem file header hoặc file implementation C++")
        self.code_view.setAccessibleName("Khung xem mã nguồn C++ được sinh tự động")

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

        means = self._current_result.feature_means
        features = self._current_result.feature_names[:8]
        ranges = self._feature_ranges(len(features))
        for f_idx, feat_name in enumerate(features):
            lo, hi = ranges[f_idx]
            baseline = means[f_idx] if len(means) == len(self._current_result.feature_names) else (lo + hi) / 2
            baseline = min(hi, max(lo, baseline))
            row = QHBoxLayout()
            friendly = friendly_feature_name(feat_name)
            # Harden: elide tên dài, giữ tooltip mã gốc + phạm vi train
            lbl = QLabel(friendly[:28] + "…" if len(friendly) > 28 else friendly)
            lbl.setToolTip(f"{friendly}\nMã kỹ thuật: {feat_name}\nPhạm vi train: [{lo:.2f}, {hi:.2f}]")
            lbl.setStyleSheet(ls.font(ls.FS_CAPTION, 500) + "border: none; background: transparent;")
            lbl.setWordWrap(True)

            val_lbl = QLabel(f"{baseline:.2f}")
            val_lbl.setStyleSheet(ls.slider_value_label())
            val_lbl.setMinimumWidth(48)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 1000)
            slider.setValue(round((baseline - lo) * 1000 / (hi - lo)) if hi > lo else 0)
            slider.setEnabled(hi > lo)
            slider.setMinimumHeight(28)
            slider.setAccessibleName(f"Thử giá trị {friendly}")
            slider.setProperty("feat_lo", float(lo))
            slider.setProperty("feat_hi", float(hi))
            slider.valueChanged.connect(
                lambda v, l=val_lbl, s=slider: l.setText(f"{s.property('feat_lo') + (s.property('feat_hi') - s.property('feat_lo')) * v / 1000:.2f}")
            )
            # Debounce 120ms: kéo slider không spam predict + SHAP
            slider.valueChanged.connect(self._schedule_live_simulation)

            row.addWidget(lbl, stretch=1)
            row.addWidget(slider, stretch=2)
            row.addWidget(val_lbl)

            self.slider_layout.addLayout(row)
            self._sim_sliders.append(slider)
            self._sim_labels.append(val_lbl)

    def _feature_ranges(self, n: int) -> list[tuple[float, float]]:
        """Phạm vi từng đặc trưng quan sát trong tập train."""
        result = self._current_result
        ranges = getattr(result, "feature_ranges", ())
        if len(ranges) >= n:
            return ranges[:n]
        scaler = getattr(result, "scaler", None)
        means = getattr(scaler, "mean_", None)
        scales = getattr(scaler, "scale_", None)
        if means is not None and scales is not None:
            return [
                (float(means[i]) - 3 * float(scales[i]), float(means[i]) + 3 * float(scales[i]))
                for i in range(n)
            ]
        return [(-3.0, 3.0)] * n

    def _schedule_live_simulation(self) -> None:
        if not self._sim_timer.isActive():
            self._sim_timer.start()

    def _slider_to_value(self, slider: QSlider) -> float:
        lo = float(slider.property("feat_lo") or 0.0)
        hi = float(slider.property("feat_hi") or 0.0)
        if hi <= lo:
            return lo
        return lo + (hi - lo) * slider.value() / 1000.0

    def _run_live_simulation(self) -> None:
        if not self._current_result or not self._sim_sliders:
            return

        try:
            n_feats = len(self._current_result.feature_names)
            means = self._current_result.feature_means
            if len(means) == n_feats:
                feat_vector = np.asarray(means, dtype=np.float32)
            else:
                scaler_mean = getattr(self._current_result.scaler, "mean_", None)
                feat_vector = (
                    np.asarray(scaler_mean, dtype=np.float32)
                    if scaler_mean is not None and len(scaler_mean) == n_feats
                    else np.zeros(n_feats, dtype=np.float32)
                )

            for i, slider in enumerate(self._sim_sliders):
                if i < n_feats:
                    feat_vector[i] = self._slider_to_value(slider)

            model = self._current_result.model
            scaler = self._current_result.scaler
            if model is None:
                return

            try:
                X_in = scaler.transform(feat_vector.reshape(1, -1)) if scaler is not None else feat_vector.reshape(1, -1)
            except Exception:
                self.lbl_pred_class.setText("Đặc trưng chưa khớp mô hình")
                return
            try:
                pred = int(model.predict(X_in)[0])
            except Exception:
                self.lbl_pred_class.setText("Không dự đoán được (sai shape)")
                return

            cls_names = self._current_result.class_names
            pred_name = cls_names[pred] if 0 <= pred < len(cls_names) else f"Class {pred}"

            conf = 100.0
            try:
                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(X_in)[0]
                    conf = float(np.max(probs)) * 100.0
            except Exception:
                pass

            self.lbl_pred_class.setText(pred_name)
            self.lbl_pred_conf.setText(f"Độ tin cậy: {conf:.1f}% · GIẢ LẬP")

            # Cập nhật SHAP waterfall table
            try:
                attribs = compute_local_feature_contributions(
                    model=model,
                    scaler=scaler,
                    raw_sample=feat_vector,
                    feature_names=self._current_result.feature_names,
                    algo=self._current_result.algo,
                    top_k=5,
                )
            except Exception:
                return
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
        except Exception:
            return

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
        code = getattr(self, "_cached_h_code", "") if want_h else getattr(self, "_cached_cc_code", "")
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

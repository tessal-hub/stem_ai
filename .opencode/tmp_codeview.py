# -*- coding: utf-8 -*-
from pathlib import Path

def apply(path, pairs, must=True):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if new in s:
            continue
        if old in s:
            s = s.replace(old, new)
        else:
            missed.append(old[:70])
    p.write_text(s, encoding="utf-8")
    print(f"{path}: {len(missed)} missed")
    for m in missed:
        print("   MISS:", m)
    return missed

missed = []

# ── A. Tab 5: code viewer ─────────────────────────────────────────────
missed += apply("ml_lab/ui/tabs/tab_simulator_export.py", [
    # import QComboBox
    ("from PyQt6.QtWidgets import (\n    QApplication,\n    QFileDialog,",
     "from PyQt6.QtWidgets import (\n    QApplication,\n    QComboBox,\n    QFileDialog,"),
    # bỏ empty label, thay bằng combo + viewer
    ('''        # Vùng trống căn giữa khi chưa có mô hình
        self.lbl_empty_code = QLabel(
            "Sau khi huấn luyện ở tab 2, mã C++ của mô hình\\n"
            "sẽ được tạo tự động tại đây — sẵn sàng biên dịch."
        )
        self.lbl_empty_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_code.setStyleSheet(
            f"{ls.font(ls.FS_BODY)} color: {ls.FAINT}; border: none; background: transparent;"
        )
        r_layout.addWidget(self.lbl_empty_code, stretch=1)

        r_layout.addStretch()''',
     '''        # Chọn file + trình xem mã C++ sinh tự động
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
            "// Chưa có mô hình — hãy huấn luyện ở tab 2.\\n"
            "// Mã C++ (model_classic.cc / .h) sẽ được sinh tự động tại đây.\\n"
        )
        r_layout.addWidget(self.code_view, stretch=1)'''),
    # set_trained_model: bỏ hide empty label
    ('''        self._run_live_simulation()
        self.lbl_empty_code.setVisible(False)''',
     '''        self._run_live_simulation()'''),
    # _update_code_views: refresh viewer
    ('''    def _update_code_views(self) -> None:
        if not self._current_result:
            return
        # Sinh trước mã C++ để Copy/Lưu dùng ngay (không hiển thị raw code trên UI)
        self._cached_h_code = self.c_exporter.generate_header_string(self._current_result)
        self._cached_cc_code = self.c_exporter.generate_source_string(self._current_result)
        r = self._current_result
        self.lbl_model_summary.setText(
            f"Mô hình hiện tại: {r.algo_name} — đoán đúng {r.val_accuracy*100:.1f}% trên dữ liệu mới. "
            f"Thần chú: {', '.join(r.class_names)}."
        )''',
     '''    def _update_code_views(self) -> None:
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
        self.code_view.setPlainText(code or "// Chưa có mã — huấn luyện ở tab 2 trước.")'''),
    # copy theo file đang chọn
    ('''    def _copy_current_code(self) -> None:
        if not getattr(self, "_cached_cc_code", None):
            QMessageBox.warning(self, "Chưa Có Mã", "Hãy huấn luyện mô hình ở tab 2 trước khi copy mã.")
            return
        QApplication.clipboard().setText(self._cached_cc_code)
        QMessageBox.information(self, "Đã Sao Chép", "Đã copy model_classic.cc vào Clipboard!")''',
     '''    def _copy_current_code(self) -> None:
        if not getattr(self, "_cached_cc_code", None):
            QMessageBox.warning(self, "Chưa Có Mã", "Hãy huấn luyện mô hình ở tab 2 trước khi copy mã.")
            return
        if self.code_file_combo.currentData() == "h":
            QApplication.clipboard().setText(self._cached_h_code)
            QMessageBox.information(self, "Đã Sao Chép", "Đã copy model_classic.h vào Clipboard!")
        else:
            QApplication.clipboard().setText(self._cached_cc_code)
            QMessageBox.information(self, "Đã Sao Chép", "Đã copy model_classic.cc vào Clipboard!")'''),
])

print("MISSED TOTAL:", len(missed))

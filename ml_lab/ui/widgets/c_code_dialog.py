"""
ml_lab/ui/widgets/c_code_dialog.py — Hộp thoại xem trước mã nguồn C và hướng dẫn nhúng.

Cung cấp trình xem mã nguồn C99, thống kê dòng lệnh, copy nhanh và hướng dẫn nhúng ESP32 / Arduino.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CCodeViewerDialog(QDialog):
    """
    Hộp thoại xem trước mã nguồn C99 độc lập và tài liệu tích hợp firmware.
    """

    def __init__(self, c_code: str, title: str = "Mô hình C99", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Mã Nguồn C Thuần — {title}")
        self.resize(850, 620)
        self._c_code = c_code

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        lbl_title = QLabel(f"📄 Header C99 Độc Lập: model_classic.h ({title})")
        lbl_title.setStyleSheet("font-weight: 700; font-size: 15px; color: #007aff;")
        lbl_hint = QLabel("Zero dependencies. Chuẩn ANSI C99. Tương thích trực tiếp ESP-IDF, Arduino, STM32.")
        lbl_hint.setStyleSheet("color: #6b7280; font-size: 12px;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_hint)
        header_layout.addLayout(title_vbox, stretch=1)

        # Stats Badge
        lines_count = len(c_code.splitlines())
        lbl_stats = QLabel(f"📊 {lines_count} dòng mã C")
        lbl_stats.setStyleSheet("font-weight: 600; padding: 4px 10px; border-radius: 6px; background: rgba(0, 122, 255, 0.1); color: #007aff; font-size: 11px;")
        header_layout.addWidget(lbl_stats)

        layout.addLayout(header_layout)

        # ── Tabs ────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { font-weight: 600; padding: 8px 16px; }")

        # Tab 1: C Code Viewer
        code_widget = QWidget()
        code_vbox = QVBoxLayout(code_widget)
        code_vbox.setContentsMargins(0, 8, 0, 0)
        self.code_edit = QTextEdit()
        self.code_edit.setReadOnly(True)
        self.code_edit.setFont(QFont("Consolas", 10))
        self.code_edit.setPlainText(c_code)
        self.code_edit.setStyleSheet(
            "background-color: #1e1e24; color: #d4d4d8; border-radius: 6px; padding: 12px; border: 1px solid #2e2e38;"
        )
        code_vbox.addWidget(self.code_edit)
        tabs.addTab(code_widget, "📄 Mã Nguồn C (model_classic.h)")

        # Tab 2: Integration Guide
        guide_widget = QWidget()
        guide_vbox = QVBoxLayout(guide_widget)
        guide_vbox.setContentsMargins(0, 8, 0, 0)
        guide_edit = QTextEdit()
        guide_edit.setReadOnly(True)
        guide_edit.setFont(QFont("Consolas", 10))
        guide_edit.setPlainText(self._get_integration_guide(title))
        guide_edit.setStyleSheet(
            "background-color: #1e1e24; color: #d4d4d8; border-radius: 6px; padding: 12px; border: 1px solid #2e2e38;"
        )
        guide_vbox.addWidget(guide_edit)
        tabs.addTab(guide_widget, "🚀 Hướng Dẫn Tích Hợp Firmware")

        layout.addWidget(tabs, stretch=1)

        # ── Bottom Action Buttons ───────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_copy = QPushButton("📋 Sao Chép (Copy Code)")
        self.btn_copy.setStyleSheet("font-weight: 600; padding: 8px 16px; border-radius: 6px; background: #007aff; color: white;")
        self.btn_copy.clicked.connect(self._copy_code)

        self.btn_save = QPushButton("💾 Lưu File (model_classic.h)")
        self.btn_save.setStyleSheet("font-weight: 600; padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; background: white;")
        self.btn_save.clicked.connect(self._save_code)

        btn_close = QPushButton("Đóng")
        btn_close.setStyleSheet("padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db;")
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _copy_code(self) -> None:
        self.code_edit.selectAll()
        self.code_edit.copy()
        self.btn_copy.setText("✅ Đã Sao Chép!")
        QTimer.singleShot(2000, lambda: self.btn_copy.setText("📋 Sao Chép (Copy Code)"))

    def _save_code(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file C Header", "model_classic.h", "C Header (*.h);;All Files (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._c_code)
                QMessageBox.information(self, "Thành Công", f"Đã lưu file thành công tại:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {exc}")

    def _get_integration_guide(self, title: str) -> str:
        return f"""/*
 * ============================================================================
 * HƯỚNG DẪN TÍCH HỢP MODEL {title.upper()} VÀO FIRMWARE ESP32 / ARDUINO
 * ============================================================================
 *
 * 1. ĐẶT FILE:
 *    - Chép file 'model_classic.h' vào thư mục project Arduino hoặc thư mục 'main/' trong ESP-IDF.
 *
 * 2. CÁCH GỌI SUY LUẬN (INFERENCE):
 *
 *    #include "model_classic.h"
 *
 *    void loop() {{
 *        // 1. Trích xuất vector đặc trưng từ mảng buffer IMU 6 trục (64 mẫu)
 *        float raw_features[CLASSIC_NUM_FEATURES];
 *        extract_classic_features(imu_buffer, 64, raw_features);
 *
 *        // 2. Chạy dự đoán phân loại
 *        float confidence = 0.0f;
 *        int predicted_class = classic_predict(raw_features, &confidence);
 *
 *        // 3. Lấy tên cử chỉ và xử lý logic
 *        const char* spell_name = classic_get_class_name(predicted_class);
 *        if (confidence >= 0.70f) {{
 *            printf("Phep thuat thi trien: %s (Do tin cay: %.1f%%)\\n", spell_name, confidence * 100.0f);
 *        }}
 *    }}
 *
 * 3. ĐẶC ĐIỂM BỘ NHỚ:
 *    - Toàn bộ hằng số mô hình được lưu trong Flash (PROGMEM / Flash ROM), không chiếm RAM heap.
 *    - RAM thực thi cực thấp (<1KB), không có cấp phát động (Zero malloc).
 */"""

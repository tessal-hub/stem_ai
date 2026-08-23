"""
ml_lab/ui/widgets/flash_dialog.py — Hộp thoại Nạp Code 1-Click Sang ESP32 Cho ML Lab.

Giao diện chuyên nghiệp cho phép học sinh nạp mã nguồn thuật toán vào board ESP32 chỉ bằng 1 nút bấm:
- Tự động quét và chọn cổng COM
- Hiện chi tiết chip ESP32 (MAC, Flash, Core)
- Thanh tiến trình % thời gian thực
- Terminal log trực quan
"""

from __future__ import annotations

from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ml_lab.core.esp32_flasher import Esp32FlashWorker, list_serial_ports
from ml_lab.core.pipeline import TrainClassicResult


class FlashDialog(QDialog):
    """
    Hộp thoại Nạp Code 1-Click Trực Tiếp Sang ESP32.
    """

    def __init__(self, result: TrainClassicResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result = result
        self._worker: Esp32FlashWorker | None = None

        self.setWindowTitle("⚡ Nạp Mã Nguồn Trực Tiếp Vào ESP32 (1-Click Flasher)")
        self.resize(750, 520)
        self._init_ui()
        self.refresh_ports()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header Card ─────────────────────────────────────
        head_box = QFrame()
        head_box.setStyleSheet("background: rgba(0, 122, 255, 0.08); border-radius: 8px; padding: 10px 14px;")
        h_layout = QHBoxLayout(head_box)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        lbl_title = QLabel(f"⚡ NẠP MÔ HÌNH: {self.result.algo_name.upper()}")
        lbl_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #007aff;")
        lbl_sub = QLabel(f"Phép thuật: {', '.join(self.result.class_names)} • Độ chính xác: {self.result.val_accuracy*100:.1f}%")
        lbl_sub.setStyleSheet("font-size: 11px; color: #4b5563;")
        info_vbox.addWidget(lbl_title)
        info_vbox.addWidget(lbl_sub)
        h_layout.addLayout(info_vbox, stretch=1)
        layout.addWidget(head_box)

        # ── Port Selector Card ──────────────────────────────
        port_box = QFrame()
        port_box.setStyleSheet("background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;")
        p_layout = QHBoxLayout(port_box)
        p_layout.setSpacing(10)

        lbl_port = QLabel("🔌 Cổng ESP32 (COM Port):")
        lbl_port.setStyleSheet("font-weight: 700; font-size: 12px;")
        p_layout.addWidget(lbl_port)

        self.combo_ports = QComboBox()
        self.combo_ports.setStyleSheet("padding: 6px; font-weight: 600; border: 1px solid #d1d5db; border-radius: 6px;")
        p_layout.addWidget(self.combo_ports, stretch=1)

        btn_rescan = QPushButton("🔄 Quét lại")
        btn_rescan.setStyleSheet("padding: 6px 12px; font-weight: 600; border-radius: 6px; background: #f3f4f6; border: 1px solid #d1d5db;")
        btn_rescan.clicked.connect(self.refresh_ports)
        p_layout.addWidget(btn_rescan)

        self.btn_flash = QPushButton("🔥 BẮT ĐẦU NẠP CODE (1-CLICK)")
        self.btn_flash.setStyleSheet(
            "padding: 8px 18px; font-weight: 800; font-size: 12px; border-radius: 6px; background: #34c759; color: white;"
        )
        self.btn_flash.clicked.connect(self.start_flash)
        p_layout.addWidget(self.btn_flash)

        layout.addWidget(port_box)

        # ── Chip Info Badge ─────────────────────────────────
        self.lbl_chip_badge = QLabel("📟 Chưa phát hiện board. Vui lòng chọn cổng và bấm Nạp Code.")
        self.lbl_chip_badge.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500; padding: 0 4px;")
        layout.addWidget(self.lbl_chip_badge)

        # ── Real-time Terminal Log ──────────────────────────
        lbl_log = QLabel("📄 TIẾN TRÌNH & NHẬT KÝ NẠP FLASH (REAL-TIME LOG):")
        lbl_log.setStyleSheet("font-weight: 700; font-size: 11px; color: #4b5563;")
        layout.addWidget(lbl_log)

        self.term_edit = QTextEdit()
        self.term_edit.setReadOnly(True)
        self.term_edit.setFont(QFont("Consolas", 10))
        self.term_edit.setStyleSheet(
            "background-color: #1a1a1f; color: #38bdf8; border-radius: 6px; padding: 10px; border: 1px solid #2e2e38;"
        )
        layout.addWidget(self.term_edit, stretch=1)

        # ── Progress Bar & Status ───────────────────────────
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet("font-weight: 600; font-size: 11px; color: #007aff;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #e5e7eb; border-radius: 4px; } "
            "QProgressBar::chunk { background-color: #34c759; border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        # ── Bottom Action Buttons ───────────────────────────
        bot_layout = QHBoxLayout()
        bot_layout.addStretch()

        self.btn_close = QPushButton("Đóng")
        self.btn_close.setStyleSheet("padding: 8px 18px; font-weight: 600; border-radius: 6px; background: #f3f4f6; border: 1px solid #d1d5db;")
        self.btn_close.clicked.connect(self.accept)
        bot_layout.addWidget(self.btn_close)

        layout.addLayout(bot_layout)

    def refresh_ports(self) -> None:
        self.combo_ports.clear()
        ports = list_serial_ports()
        if not ports:
            self.combo_ports.addItem("Không tìm thấy cổng Serial nào", "")
            self.btn_flash.setEnabled(False)
        else:
            for dev, desc in ports:
                self.combo_ports.addItem(f"{dev} ({desc})", dev)
            self.btn_flash.setEnabled(True)

    def start_flash(self) -> None:
        port = self.combo_ports.currentData()
        if not port:
            self.term_edit.append("[LỖI] Vui lòng chọn cổng COM kết nối với ESP32.")
            return

        self.btn_flash.setEnabled(False)
        self.btn_flash.setText("⏳ Đang Nạp...")
        self.progress_bar.setValue(5)
        self.term_edit.clear()

        self._worker = Esp32FlashWorker(port=port, result=self.result)
        self._worker.log_msg.connect(self.term_edit.append)
        self._worker.sig_progress.connect(self.progress_bar.setValue)
        self._worker.sig_status.connect(self.lbl_status.setText)
        self._worker.sig_chip_info.connect(lambda info: self.lbl_chip_badge.setText(f"📟 [CHIP DETECTED] {info}"))
        self._worker.sig_finished.connect(self._on_flash_finished)
        self._worker.start()

    def _on_flash_finished(self, success: bool, msg: str) -> None:
        self.btn_flash.setEnabled(True)
        self.btn_flash.setText("🔥 BẮT ĐẦU NẠP CODE (1-CLICK)")
        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("✅ Nạp thành công 100%!")
        else:
            self.lbl_status.setText(f"❌ {msg}")

    def closeEvent(self, event: Any) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        super().closeEvent(event)

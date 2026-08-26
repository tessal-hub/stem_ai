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

import ml_lab.ui.lab_style as ls
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

        self.setWindowTitle("Nạp mô hình vào ESP32")
        self.resize(750, 520)
        self._init_ui()
        self.refresh_ports()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header Card ─────────────────────────────────────
        head_box = QFrame()
        head_box.setStyleSheet(f".QFrame {{ background: {ls.ACCENT_TINT_STRONG}; border: none; border-radius: {ls.RADIUS_MD}px; padding: 10px 14px; }}")
        h_layout = QHBoxLayout(head_box)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        lbl_title = QLabel(f"NẠP MÔ HÌNH: {self.result.algo_name.upper()}")
        lbl_title.setStyleSheet(f"{ls.font(ls.FS_SECTION, 800)} color: {ls.ACCENT}; border: none; background: transparent;")
        lbl_sub = QLabel(f"Phép thuật: {', '.join(self.result.class_names)} • Độ chính xác: {self.result.val_accuracy*100:.1f}%")
        lbl_sub.setStyleSheet(f"{ls.font(ls.FS_CAPTION)} color: {ls.MUTED}; border: none; background: transparent;")
        info_vbox.addWidget(lbl_title)
        info_vbox.addWidget(lbl_sub)
        h_layout.addLayout(info_vbox, stretch=1)
        layout.addWidget(head_box)

        # ── Port Selector Card ──────────────────────────────
        port_box = QFrame()
        port_box.setStyleSheet(ls.card())
        p_layout = QHBoxLayout(port_box)
        p_layout.setSpacing(10)

        lbl_port = QLabel("Cổng ESP32 (COM):")
        lbl_port.setStyleSheet(f"{ls.font(ls.FS_BODY, 700)} border: none; background: transparent;")
        p_layout.addWidget(lbl_port)

        self.combo_ports = QComboBox()
        self.combo_ports.setStyleSheet(ls.INPUT_COMBO)
        p_layout.addWidget(self.combo_ports, stretch=1)

        btn_rescan = QPushButton("Quét lại")
        btn_rescan.setStyleSheet(ls.BTN_SECONDARY)
        btn_rescan.clicked.connect(self.refresh_ports)
        p_layout.addWidget(btn_rescan)

        self.btn_flash = QPushButton("BẮT ĐẦU NẠP")
        self.btn_flash.setStyleSheet(
            f"padding: 8px 18px; font-weight: 800; font-size: 12px; border-radius: 6px; background: {ls.SUCCESS}; color: white;"
        )
        self.btn_flash.clicked.connect(self.start_flash)
        p_layout.addWidget(self.btn_flash)

        layout.addWidget(port_box)

        # ── Chip Info Badge ─────────────────────────────────
        self.lbl_chip_badge = QLabel("Chưa phát hiện board — chọn cổng rồi bấm nạp.")
        self.lbl_chip_badge.setStyleSheet(f"{ls.font(ls.FS_CAPTION, 500)} color: {ls.MUTED}; padding: 0 4px; border: none; background: transparent;")
        layout.addWidget(self.lbl_chip_badge)

        # ── Real-time Terminal Log ──────────────────────────
        lbl_log = QLabel("TIẾN TRÌNH & NHẬT KÝ NẠP")
        lbl_log.setStyleSheet(ls.section_label())
        layout.addWidget(lbl_log)

        self.term_edit = QTextEdit()
        self.term_edit.setReadOnly(True)
        self.term_edit.setFont(QFont("Consolas", 10))
        self.term_edit.setStyleSheet(ls.TERMINAL)
        layout.addWidget(self.term_edit, stretch=1)

        # ── Progress Bar & Status ───────────────────────────
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet(f"{ls.font(ls.FS_CAPTION, 600)} color: {ls.ACCENT}; border: none; background: transparent;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(ls.PROGRESS_BAR)
        layout.addWidget(self.progress_bar)

        # ── Bottom Action Buttons ───────────────────────────
        bot_layout = QHBoxLayout()
        bot_layout.addStretch()

        self.btn_close = QPushButton("Đóng")
        self.btn_close.setStyleSheet(ls.BTN_SECONDARY)
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
        self.btn_flash.setText("Đang nạp...")
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
        self.btn_flash.setText("BẮT ĐẦU NẠP")
        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("✅ Nạp thành công 100%!")
        else:
            self.lbl_status.setText(f"❌ {msg}")

    def closeEvent(self, event: Any) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        super().closeEvent(event)

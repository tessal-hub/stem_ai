"""Firmware flash control panel."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ui.tokens import (
    PROGRESS_H,
    STYLE_BTN_OUTLINE,
    STYLE_BTN_PRIMARY,
    STYLE_PROGRESS,
    TEXT_MUTED,
)
from ui.wand_panels.shared import make_button, make_card, make_section_label


class WandFlashPanel(QWidget):
    """Panel that owns compile/upload controls and flash progress state."""

    sig_compile_clicked = pyqtSignal()
    sig_upload_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._connect_internal_signals()

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        self.progress_bar.setValue(max(0, min(100, percentage)))
        if status_text:
            self.lbl_flash_status.setText(f"● {status_text}")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(make_section_label("FIRMWARE FLASHER"))

        card, card_layout = make_card()

        btn_row = QHBoxLayout()
        self.btn_compile = make_button("COMPILE", STYLE_BTN_OUTLINE)
        self.btn_flash = make_button("FLASH ESP32", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_compile)
        btn_row.addWidget(self.btn_flash)
        card_layout.addLayout(btn_row)

        self.lbl_flash_status = QLabel("● Ready to compile")
        self.lbl_flash_status.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 800;"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(PROGRESS_H)
        self.progress_bar.setValue(0)

        card_layout.addWidget(self.lbl_flash_status)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)

    def _connect_internal_signals(self) -> None:
        self.btn_compile.clicked.connect(self.sig_compile_clicked.emit)
        self.btn_flash.clicked.connect(self.sig_upload_clicked.emit)

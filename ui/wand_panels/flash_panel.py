"""Model building control panel for .tflite and .cc outputs."""

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
    """Panel that owns build/upload controls and flash progress state."""

    sig_build_tflite_clicked = pyqtSignal()
    sig_build_cc_clicked = pyqtSignal()
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
        layout.setSpacing(4)

        title = make_section_label("MODEL BUILDING")
        title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-weight: 900; font-size: 11px; letter-spacing: 1px;"
        )
        layout.addWidget(title)

        card, card_layout = make_card(margins=(16, 14, 16, 14), spacing=14)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_build_tflite = make_button("BUILD .TFLITE", STYLE_BTN_OUTLINE, height=38)
        self.btn_build_cc = make_button("BUILD .CC", STYLE_BTN_PRIMARY, height=38)
        # Legacy aliases kept for existing access paths.
        self.btn_compile = self.btn_build_cc
        self.btn_flash = self.btn_build_tflite
        btn_row.addWidget(self.btn_build_tflite)
        btn_row.addWidget(self.btn_build_cc)
        card_layout.addLayout(btn_row)

        self.lbl_flash_status = QLabel("● Ready to build model")
        self.lbl_flash_status.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 800;"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(max(PROGRESS_H, 14))
        self.progress_bar.setValue(0)

        card_layout.addWidget(self.lbl_flash_status)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)

    def _connect_internal_signals(self) -> None:
        self.btn_build_tflite.clicked.connect(self.sig_build_tflite_clicked.emit)
        self.btn_build_cc.clicked.connect(self.sig_build_cc_clicked.emit)

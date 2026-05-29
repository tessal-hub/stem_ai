"""
ui/wand_panels/flash_panel.py — Panel điều khiển Build & Flash cho Wand.

Quản lý việc chuyển đổi mô hình TFLite, tạo file header C++ (.cc) 
và nạp dữ liệu/mô hình vào đũa phép Magic Wand.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ui.i18n_bridge import tr_ui
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_MD, SPACING_SM, SPACING_XS
from ui.tokens import (
    BTN_H,
    INPUT_RADIUS,
    PROGRESS_H,
)
from .shared import make_button, make_card, make_section_label


class WandFlashPanel(QWidget):
    """
    Panel điều khiển quá trình xây dựng và nạp mô hình TinyML.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_build_tflite_clicked = pyqtSignal()
    sig_build_cc_clicked = pyqtSignal()
    sig_upload_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()
        self._init_signals()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_XS)

        self._title_lbl = make_section_label(tr_ui("wand_section_model"))
        self._title_lbl.setProperty("type", "settings_section_label")
        layout.addWidget(self._title_lbl)

        card, card_layout = make_card(
            margins=(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE),
            spacing=SPACING_MD,
        )

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(SPACING_SM)
        self.btn_build_tflite = make_button(tr_ui("wand_build_tflite"), "outline", height=BTN_H)
        self.btn_build_cc = make_button(tr_ui("wand_build_cc"), "outline", height=BTN_H)
        self.btn_upload = make_button(tr_ui("wand_upload_model"), "primary", height=BTN_H)
        
        btn_layout.addWidget(self.btn_build_tflite)
        btn_layout.addWidget(self.btn_build_cc)
        btn_layout.addWidget(self.btn_upload)
        card_layout.addLayout(btn_layout)

        self.lbl_flash_status = QLabel(tr_ui("wand_flash_ready"))
        self.lbl_flash_status.setProperty("type", "wand_flash_status")
        self.lbl_flash_status.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(PROGRESS_H)
        self.progress_bar.setValue(0)

        card_layout.addWidget(self.lbl_flash_status)
        card_layout.addWidget(self.progress_bar)
        layout.addWidget(card)

    def _init_signals(self) -> None:
        """Kết nối signal/slot nội bộ."""
        self.btn_build_tflite.clicked.connect(self.sig_build_tflite_clicked.emit)
        self.btn_build_cc.clicked.connect(self.sig_build_cc_clicked.emit)
        self.btn_upload.clicked.connect(self.sig_upload_clicked.emit)

    # ── Public methods ──────────────────────────

    def apply_ui_language(self) -> None:
        """Làm mới văn bản khi ngôn ngữ ứng dụng thay đổi."""
        self._title_lbl.setText(tr_ui("wand_section_model"))
        self.btn_build_tflite.setText(tr_ui("wand_build_tflite"))
        self.btn_build_cc.setText(tr_ui("wand_build_cc"))
        self.btn_upload.setText(tr_ui("wand_upload_model"))

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        """Cập nhật tiến trình nạp firmware."""
        self.progress_bar.setValue(max(0, min(100, percentage)))
        if status_text:
            self.lbl_flash_status.setText(f"● {status_text}")

    def refresh_styles(self) -> None:
        """Làm mới style theo theme hiện tại."""
        self.lbl_flash_status.setProperty("status", "accent")
        self.lbl_flash_status.style().unpolish(self.lbl_flash_status)
        self.lbl_flash_status.style().polish(self.lbl_flash_status)

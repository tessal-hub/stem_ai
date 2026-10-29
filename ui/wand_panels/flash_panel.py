"""
ui/wand_panels/flash_panel.py — Panel điều khiển Build & Flash cho Wand.

Quản lý việc chuyển đổi mô hình TFLite, tạo file header C++ (.cc) 
và nạp dữ liệu/mô hình vào đũa phép Magic Wand.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ui.i18n_bridge import tr_ui
from ui.component_factory import make_card, make_outline_button, make_primary_button, make_section_label
from ui.tokens import (BTN_H, MARGIN_COMFORTABLE, PROGRESS_H, SPACING_MD,
                       SPACING_SM, SPACING_XS)



class WandFlashPanel(QWidget):
    """
    Panel điều khiển quá trình xây dựng và nạp mô hình TinyML.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_build_firmware_clicked = pyqtSignal()
    sig_upload_clicked = pyqtSignal()
    sig_similarity_clicked = pyqtSignal()
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()

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
            margins=(16, 14, 16, 14),
            spacing=SPACING_SM,
        )

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(SPACING_SM)

        # Firmware install buttons (Data collection & Base AI)
        fw_btn_layout = QHBoxLayout()
        fw_btn_layout.setSpacing(8)
        self.btn_flash_collect = make_outline_button(tr_ui("btn_flash_data", default="Cài đặt FW thu thập"), height=BTN_H)
        self.btn_flash_collect.setToolTip(tr_ui("fw_desc_data", default="Nạp firmware thu thập dữ liệu cảm biến"))
        self.btn_flash_ai = make_outline_button(tr_ui("btn_flash_ai", default="Cài đặt FW AI"), height=BTN_H)
        self.btn_flash_ai.setToolTip(tr_ui("fw_desc_inference", default="Nạp firmware động cơ nhận diện AI"))
        fw_btn_layout.addWidget(self.btn_flash_collect, stretch=1)
        fw_btn_layout.addWidget(self.btn_flash_ai, stretch=1)
        btn_layout.addLayout(fw_btn_layout)

        self.btn_similarity = make_outline_button(tr_ui("wand_btn_similarity", default="Ma trận tương đồng"), height=BTN_H)
        self.btn_build_firmware = make_outline_button(tr_ui("wand_build_firmware"), height=BTN_H)
        self.btn_upload = make_primary_button(tr_ui("wand_upload_model"), height=BTN_H)

        btn_layout.addWidget(self.btn_similarity)
        btn_layout.addWidget(self.btn_build_firmware)
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
        self.btn_flash_collect.clicked.connect(lambda _: self.sig_flash_data_firmware.emit())
        self.btn_flash_ai.clicked.connect(lambda _: self.sig_flash_inference_firmware.emit())
        self.btn_similarity.clicked.connect(lambda _: self.sig_similarity_clicked.emit())
        self.btn_build_firmware.clicked.connect(lambda _: self.sig_build_firmware_clicked.emit())
        self.btn_upload.clicked.connect(lambda _: self.sig_upload_clicked.emit())

    # ── Public methods ──────────────────────────

    def apply_ui_language(self) -> None:
        """Làm mới văn bản khi ngôn ngữ ứng dụng thay đổi."""
        self._title_lbl.setText(tr_ui("wand_section_model"))
        self.btn_flash_collect.setText(tr_ui("btn_flash_data", default="Cài đặt FW thu thập"))
        self.btn_flash_collect.setToolTip(tr_ui("fw_desc_data", default="Nạp firmware thu thập dữ liệu cảm biến"))
        self.btn_flash_ai.setText(tr_ui("btn_flash_ai", default="Cài đặt FW AI"))
        self.btn_flash_ai.setToolTip(tr_ui("fw_desc_inference", default="Nạp firmware động cơ nhận diện AI"))
        self.btn_similarity.setText(tr_ui("wand_btn_similarity", default="Ma trận tương đồng"))
        self.btn_build_firmware.setText(tr_ui("wand_build_firmware"))
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

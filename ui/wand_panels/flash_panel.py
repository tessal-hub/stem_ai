"""Panel điều khiển build model .tflite và .cc cho firmware."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ui.tokens import (
    BTN_H,
    INPUT_RADIUS,
    PROGRESS_H,
    STYLE_HOME_SECTION_SUBTITLE,
    STYLE_BTN_OUTLINE,
    STYLE_BTN_PRIMARY,
    STYLE_PROGRESS,
    STYLE_WAND_FLASH_STATUS,
)
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_MD, SPACING_XS
from ui.wand_panels.shared import make_button, make_card, make_section_label
from ui.i18n_bridge import tr_ui


class WandFlashPanel(QWidget):
    """Panel chứa các nút build model và thanh tiến trình flash."""

    sig_build_tflite_clicked = pyqtSignal()
    sig_build_cc_clicked = pyqtSignal()
    sig_upload_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()
        self._init_signals()

    def apply_ui_language(self) -> None:
        self._title_lbl.setText(tr_ui("wand_section_model"))
        self.btn_build_tflite.setText(tr_ui("wand_build_tflite"))
        self.btn_build_cc.setText(tr_ui("wand_build_cc"))
        self.btn_upload.setText(tr_ui("wand_upload_model"))

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        """Cập nhật thanh tiến trình và nhãn trạng thái.

        Args:
            percentage: Phần trăm hoàn thành (0–100).
            status_text: Thông báo trạng thái kèm theo.
        """
        self.progress_bar.setValue(max(0, min(100, percentage)))
        if status_text:
            self.lbl_flash_status.setText(f"● {status_text}")

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        from logic.theme_manager import theme_manager
        p = theme_manager.get_palette()
        self.lbl_flash_status.setStyleSheet(f"color: {p.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {p.SURFACE_TERTIARY}; border: none; border-radius: {INPUT_RADIUS}; text-align: center; color: transparent; }}
            QProgressBar::chunk {{ background-color: {p.PRIMARY}; border-radius: {INPUT_RADIUS}; }}
        """)

    def _init_ui(self) -> None:
        """Xây dựng layout gồm nút build và thanh tiến trình."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_XS)

        title = make_section_label(tr_ui("wand_section_model"))
        self._title_lbl = title
        title.setStyleSheet(STYLE_HOME_SECTION_SUBTITLE)
        layout.addWidget(title)

        card, card_layout = make_card(
            margins=(
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
            ),
            spacing=SPACING_MD,
        )

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING_MD)
        self.btn_build_tflite = make_button(tr_ui("wand_build_tflite"), STYLE_BTN_OUTLINE, height=BTN_H)
        self.btn_build_cc = make_button(tr_ui("wand_build_cc"), STYLE_BTN_OUTLINE, height=BTN_H)
        self.btn_upload = make_button(tr_ui("wand_upload_model"), STYLE_BTN_PRIMARY, height=BTN_H)
        
        # Legacy aliases kept for existing access paths.
        self.btn_compile = self.btn_build_cc
        self.btn_flash = self.btn_upload  # Flash usually means the final step
        
        btn_row.addWidget(self.btn_build_tflite)
        btn_row.addWidget(self.btn_build_cc)
        btn_row.addWidget(self.btn_upload)
        card_layout.addLayout(btn_row)

        self.lbl_flash_status = QLabel(tr_ui("wand_flash_ready"))
        self.lbl_flash_status.setStyleSheet(STYLE_WAND_FLASH_STATUS)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(PROGRESS_H)
        self.progress_bar.setValue(0)

        card_layout.addWidget(self.lbl_flash_status)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot nội bộ."""
        self.btn_build_tflite.clicked.connect(self.sig_build_tflite_clicked.emit)
        self.btn_build_cc.clicked.connect(self.sig_build_cc_clicked.emit)
        self.btn_upload.clicked.connect(self.sig_upload_clicked.emit)

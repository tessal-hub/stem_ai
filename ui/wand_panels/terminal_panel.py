"""
ui/wand_panels/terminal_panel.py — Panel terminal hiển thị log từ Wand.

Cung cấp giao diện hiển thị dữ liệu văn bản nhận được từ cổng Serial/UDP.
Sử dụng cơ chế đệm (buffering) để tối ưu hiệu suất hiển thị khi dữ liệu đến nhanh.
"""

from __future__ import annotations

import collections

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.i18n_bridge import tr_ui
from ui.modern_layout import SPACING_SM
from ui.terminal_widget import TerminalWidget
from ui.tokens import BTN_SMALL_H

from .shared import make_section_label

# Tần suất làm mới terminal (ms)
_FLUSH_INTERVAL_MS = 100


class WandTerminalPanel(QWidget):
    """
    Panel hiển thị nhật ký (log) và phản hồi từ thiết bị phần cứng.
    """

    sig_clear_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._pending_lines = collections.deque()
        self._flush_timer = QTimer(self)

        self._init_ui()
        self._init_signals()
        self._start_timer()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện terminal (Requirement 4)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        header = QHBoxLayout()
        self._term_header = make_section_label(tr_ui("wand_section_terminal"))
        header.addWidget(self._term_header)
        header.addStretch()

        self.btn_term_clear = QPushButton(tr_ui("wand_clear"))
        self.btn_term_clear.setProperty("type", "small")
        self.btn_term_clear.setMinimumHeight(BTN_SMALL_H)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_term_clear.setProperty("status", "accent")
        header.addWidget(self.btn_term_clear)

        layout.addLayout(header)

        # Requirement 4: UART Terminal style
        self.terminal_output = TerminalWidget(max_lines=1000, read_only=True)
        self.terminal_output.setMinimumHeight(200)
        self.terminal_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.terminal_output.setPlainText(">> WAND TERMINAL INITIALIZED...\n>> WAITING FOR DATA...")
        layout.addWidget(self.terminal_output, stretch=1)

    def _init_signals(self) -> None:
        """Kết nối các signal nội bộ."""
        self.btn_term_clear.clicked.connect(self._on_btn_clear_clicked)
        self._flush_timer.timeout.connect(self._flush_pending)

    # ── Public methods ──────────────────────────

    def append_terminal_text(self, text: str) -> None:
        """Thêm văn bản vào hàng đợi hiển thị."""
        self._pending_lines.append(text)

    def apply_ui_language(self) -> None:
        """Làm mới văn bản khi đổi ngôn ngữ."""
        self._term_header.setText(tr_ui("wand_section_terminal"))
        self.btn_term_clear.setText(tr_ui("wand_clear"))

    def refresh_styles(self) -> None:
        """Làm mới style theo theme hiện tại."""
        # Theme handling is mostly done via inline stylesheet for Requirement 4

    # ── Private methods ─────────────────────────

    def _start_timer(self) -> None:
        """Khởi động timer cập nhật định kỳ."""
        self._flush_timer.start(_FLUSH_INTERVAL_MS)

    def _flush_pending(self) -> None:
        """Ghi dữ liệu từ hàng đợi vào widget hiển thị."""
        if not self._pending_lines:
            return
        batch = "\n".join(self._pending_lines)
        self._pending_lines.clear()
        self.terminal_output.append_line(batch)

    # ── Slots ───────────────────────────────────

    def _on_btn_clear_clicked(self) -> None:
        """Xử lý sự kiện xóa sạch terminal."""
        self._pending_lines.clear()
        self.terminal_output.clear()
        self.sig_clear_requested.emit()

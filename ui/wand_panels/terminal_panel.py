"""Panel terminal UART hiển thị dữ liệu telemetry từ wand."""

from __future__ import annotations

import collections

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.modern_layout import SPACING_SM
from ui.terminal_widget import TerminalWidget
from ui.tokens import (
    BTN_SMALL_H,
    STYLE_BTN_SMALL,
    STYLE_TERMINAL,
    TERM_MIN_H,
    WAND_TERMINAL_MIN_H,
)
from ui.wand_panels.shared import make_section_label
from ui.i18n_bridge import tr_ui

# Flush buffered terminal lines at most this often (ms).
# 100 ms → ≤10 DOM updates/s regardless of how fast lines arrive (~50 Hz).
_FLUSH_INTERVAL_MS = 100


class WandTerminalPanel(QWidget):
    """Panel terminal UART hiển thị và quản lý output của wand.

    Dòng thêm qua ``append_terminal_text`` được buffer trong deque nội bộ
    và flush vào widget theo QTimer tần suất ``_FLUSH_INTERVAL_MS``.
    Giới hạn DOM layout tối đa ≤10 batch update mỗi giây dù serial phát ~50 Hz.
    """

    sig_clear_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._pending_lines: collections.deque[str] = collections.deque()
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(_FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush_pending)
        self._flush_timer.start()
        self._init_ui()
        self._init_signals()

    def append_terminal_text(self, text: str) -> None:
        """Buffer *text* để chuyển vào terminal widget theo batch.

        Args:
            text: Nội dung cần hiển thị.
        """
        self._pending_lines.append(text)

    def _flush_pending(self) -> None:
        """Drain buffer và ghi vào terminal widget một lần để giảm reflow."""
        if not self._pending_lines:
            return
        # Join all queued lines into a single append call to minimise DOM reflows.
        batch = "\n".join(self._pending_lines)
        self._pending_lines.clear()
        self.terminal_output.append_line(batch)

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        from logic.theme_manager import theme_manager
        p = theme_manager.get_palette()
        self.terminal_output.setStyleSheet(f"""
            QTextEdit {{ background-color: {p.SURFACE_TERTIARY}; color: {p.TEXT_PRIMARY}; border: 1px solid {p.BORDER}; border-radius: 8px; padding: 12px; font-family: 'Geist Mono'; }}
        """)
        self.btn_term_clear.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: 1px solid {p.BORDER}; border-radius: 14px; color: {p.TEXT_SECONDARY}; padding: 0 16px; font-size: 11px; font-weight: 700; }}
            QPushButton:hover {{ background-color: {p.HOVER_BG}; color: {p.TEXT_PRIMARY}; }}
        """)

    def _init_ui(self) -> None:
        """Xây dựng layout gồm header và terminal output."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        header = QHBoxLayout()
        self._term_header = make_section_label(tr_ui("wand_section_terminal"))
        header.addWidget(self._term_header)
        header.addStretch()

        self.btn_term_clear = QPushButton(tr_ui("wand_clear"))
        self.btn_term_clear.setStyleSheet(STYLE_BTN_SMALL)
        self.btn_term_clear.setMinimumHeight(BTN_SMALL_H)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.btn_term_clear)

        layout.addLayout(header)

        self.terminal_output = TerminalWidget(max_lines=1000, read_only=True)
        self.terminal_output.setStyleSheet(STYLE_TERMINAL)
        self.terminal_output.setMinimumHeight(max(TERM_MIN_H, WAND_TERMINAL_MIN_H))

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.terminal_output.setFont(font)
        self.terminal_output.setPlainText(
            ">> WAND TERMINAL INITIALIZED...\n>> WAITING FOR DATA..."
        )

        layout.addWidget(self.terminal_output, stretch=1)

    def apply_ui_language(self) -> None:
        self._term_header.setText(tr_ui("wand_section_terminal"))
        self.btn_term_clear.setText(tr_ui("wand_clear"))

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot nội bộ."""
        self.btn_term_clear.clicked.connect(self._on_btn_clear_clicked)

    def _on_btn_clear_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Clear terminal."""
        self._pending_lines.clear()
        self.terminal_output.clear()
        self.sig_clear_requested.emit()

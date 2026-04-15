"""UART terminal panel for wand telemetry output."""

from __future__ import annotations

import collections

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.terminal_widget import TerminalWidget
from ui.tokens import STYLE_BTN_SMALL, STYLE_TERMINAL, TERM_MIN_H
from ui.wand_panels.shared import make_section_label

# Flush buffered terminal lines at most this often (ms).
# 100 ms → ≤10 DOM updates/s regardless of how fast lines arrive (~50 Hz).
_FLUSH_INTERVAL_MS = 100


class WandTerminalPanel(QWidget):
    """Panel that owns terminal rendering and clear interaction.

    Lines appended via ``append_terminal_text`` are held in an internal deque
    and flushed to the visible widget by a QTimer at ``_FLUSH_INTERVAL_MS``
    intervals.  This caps DOM layout work at ≤10 batched updates per second
    even when the serial worker emits at ~50 Hz.
    """

    sig_clear_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._pending_lines: collections.deque[str] = collections.deque()
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(_FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush_pending)
        self._flush_timer.start()
        self._build_ui()
        self._connect_internal_signals()

    def append_terminal_text(self, text: str) -> None:
        """Buffer *text* for batched delivery to the terminal widget."""
        self._pending_lines.append(text)

    def _flush_pending(self) -> None:
        """Drain the pending-lines buffer into the terminal widget in one batch."""
        if not self._pending_lines:
            return
        # Join all queued lines into a single append call to minimise DOM reflows.
        batch = "\n".join(self._pending_lines)
        self._pending_lines.clear()
        self.terminal_output.append_line(batch)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(make_section_label("UART TERMINAL"))
        header.addStretch()

        self.btn_term_clear = QPushButton("CLEAR")
        self.btn_term_clear.setStyleSheet(STYLE_BTN_SMALL)
        self.btn_term_clear.setMinimumHeight(30)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.btn_term_clear)

        layout.addLayout(header)

        self.terminal_output = TerminalWidget(max_lines=1000, read_only=True)
        self.terminal_output.setStyleSheet(STYLE_TERMINAL)
        self.terminal_output.setMinimumHeight(max(TERM_MIN_H, 210))

        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.terminal_output.setFont(font)
        self.terminal_output.setPlainText(
            ">> WAND TERMINAL INITIALIZED...\n>> WAITING FOR DATA..."
        )

        layout.addWidget(self.terminal_output, stretch=1)

    def _connect_internal_signals(self) -> None:
        self.btn_term_clear.clicked.connect(self._on_clear_clicked)

    def _on_clear_clicked(self) -> None:
        self._pending_lines.clear()
        self.terminal_output.clear()
        self.sig_clear_requested.emit()

"""UART terminal panel for wand telemetry output."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.terminal_widget import TerminalWidget
from ui.tokens import STYLE_BTN_SMALL, STYLE_TERMINAL, TERM_MIN_H
from ui.wand_panels.shared import make_section_label


class WandTerminalPanel(QWidget):
    """Panel that owns terminal rendering and clear interaction."""

    sig_clear_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._connect_internal_signals()

    def append_terminal_text(self, text: str) -> None:
        self.terminal_output.append_line(text)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(make_section_label("UART TERMINAL"))
        header.addStretch()

        self.btn_term_clear = QPushButton("CLEAR")
        self.btn_term_clear.setStyleSheet(STYLE_BTN_SMALL)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.btn_term_clear)

        layout.addLayout(header)

        self.terminal_output = TerminalWidget(max_lines=1000, read_only=True)
        self.terminal_output.setStyleSheet(STYLE_TERMINAL)
        self.terminal_output.setMinimumHeight(TERM_MIN_H)

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
        self.terminal_output.clear()
        self.sig_clear_requested.emit()

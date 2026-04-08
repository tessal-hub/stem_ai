"""Shared terminal widget with append, autoscroll, and line capping."""
from __future__ import annotations

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QFrame, QTextEdit


class TerminalWidget(QTextEdit):
    """Reusable terminal-style text output widget."""

    def __init__(self, *, max_lines: int = 1000, read_only: bool = True) -> None:
        super().__init__()
        self._max_lines = max(1, max_lines)
        self.setReadOnly(read_only)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)

    def append_line(self, text: str, *, strip_right: bool = False) -> None:
        """Append one line, keep autoscroll, and cap total line count."""
        payload = text.rstrip() if strip_right else text
        self.append(payload)
        self._cap_lines()
        self._scroll_to_bottom()

    def _cap_lines(self) -> None:
        """Trim oldest lines to keep document size bounded."""
        doc = self.document()
        overflow = doc.blockCount() - self._max_lines
        while overflow > 0:
            first = doc.firstBlock()
            if not first.isValid():
                break
            cursor = QTextCursor(first)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
            overflow -= 1

    def _scroll_to_bottom(self) -> None:
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

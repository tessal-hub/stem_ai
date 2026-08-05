"""Widget terminal tái sử dụng với append, autoscroll, và giới hạn số dòng hiệu năng cao."""
from __future__ import annotations

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QFrame, QTextEdit


class TerminalWidget(QTextEdit):
    """Widget hiển thị output kiểu terminal, tái sử dụng được."""

    def __init__(self, *, max_lines: int = 1000, read_only: bool = True) -> None:
        super().__init__()
        self._max_lines = max(1, max_lines)
        self.setReadOnly(read_only)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)

    def append_line(self, text: str, *, strip_right: bool = False) -> None:
        """Append one line or batch, keep autoscroll, and cap total line count efficiently."""
        if not text:
            return
        payload = text.rstrip() if strip_right else text
        self.append(payload)
        self._cap_lines()
        self._scroll_to_bottom()

    def _cap_lines(self) -> None:
        """Trim oldest lines to keep document size bounded efficiently using C++ bulk block move."""
        doc = self.document()
        overflow = doc.blockCount() - self._max_lines
        if overflow <= 0:
            return
        self.setUpdatesEnabled(False)
        try:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor, overflow)
            cursor.removeSelectedText()
        finally:
            self.setUpdatesEnabled(True)

    def _scroll_to_bottom(self) -> None:
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

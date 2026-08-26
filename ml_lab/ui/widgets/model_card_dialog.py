"""
ml_lab/ui/widgets/model_card_dialog.py — Hộp thoại Hồ sơ mô hình (Model Card).

Xem trước hồ sơ tự sinh của mô hình vừa huấn luyện: làm gì, chính xác từng lớp,
KHI NÀO KHÔNG NÊN TIN. Xuất PDF (nộp bài), lưu Markdown hoặc copy.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ml_lab.core.model_card import build_model_card_html, build_model_card_markdown
from ml_lab.core.pipeline import TrainClassicResult


class ModelCardDialog(QDialog):
    """Xem trước + xuất Hồ sơ mô hình (PDF / Markdown / Copy)."""

    def __init__(self, result: TrainClassicResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result = result
        self._markdown = build_model_card_markdown(result)
        self._html = build_model_card_html(result)

        self.setWindowTitle(f"Hồ sơ mô hình — {result.algo_name}")
        self.resize(720, 760)
        self.setStyleSheet(f"background: {ls.BG_APP}; color: {ls.INK};")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        lbl_note = QLabel(
            "Hồ sơ này mô tả mô hình làm gì, mạnh/yếu ở đâu và khi nào KHÔNG nên tin nó. "
            "Nộp kèm bài nộp hoặc lưu lại làm portfolio."
        )
        lbl_note.setWordWrap(True)
        lbl_note.setStyleSheet(ls.note_box(ls.ACCENT))
        layout.addWidget(lbl_note)

        self.preview = QTextBrowser()
        self.preview.setHtml(self._html)
        self.preview.setStyleSheet(
            f"QTextBrowser {{ background: {ls.SURFACE}; color: {ls.INK}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_MD}px; padding: 12px; }}"
        )
        layout.addWidget(self.preview, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_copy = QPushButton("Copy nội dung")
        btn_copy.setStyleSheet(ls.BTN_SECONDARY)
        btn_copy.clicked.connect(self._copy_markdown)
        btn_row.addWidget(btn_copy)

        btn_md = QPushButton("Lưu Markdown")
        btn_md.setStyleSheet(ls.BTN_SECONDARY)
        btn_md.clicked.connect(self._save_markdown)
        btn_row.addWidget(btn_md)

        btn_pdf = QPushButton("Lưu PDF")
        btn_pdf.setStyleSheet(ls.BTN_PRIMARY)
        btn_pdf.clicked.connect(self._save_pdf)
        btn_row.addWidget(btn_pdf)

        btn_close = QPushButton("Đóng")
        btn_close.setStyleSheet(ls.BTN_SECONDARY)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    # ── actions ──────────────────────────────────────────────────────────

    def _default_stem(self) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return f"model_card_{self.result.algo}_{ts}"

    def _copy_markdown(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._markdown)
        QMessageBox.information(self, "Đã sao chép", "Đã copy hồ sơ (Markdown) vào Clipboard!")

    def _save_markdown(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu hồ sơ mô hình (Markdown)", self._default_stem() + ".md",
            "Markdown (*.md);;Text (*.txt);;All Files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self._markdown, encoding="utf-8")
            QMessageBox.information(self, "Đã lưu", f"Đã lưu hồ sơ:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {exc}")

    def _save_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu hồ sơ mô hình (PDF)", self._default_stem() + ".pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._html)
            # PyQt6: phương thức in tên là `print` (không phải print_)
            getattr(doc, "print")(printer)
            QMessageBox.information(self, "Đã lưu", f"Đã lưu hồ sơ PDF:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất PDF: {exc}")

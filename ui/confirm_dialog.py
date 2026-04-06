"""Reusable confirmation dialog for destructive actions."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton, QVBoxLayout

from ui.mac_material import apply_soft_shadow
from ui.tokens import (
    ACCENT,
    ACCENT_TEXT,
    BG_WHITE,
    BORDER,
    DANGER,
    TEXT_BODY,
    TEXT_MUTED,
)


class ConfirmDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        danger: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("ConfirmDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TEXT_BODY}; font-size: 15px; font-weight: 700;"
        )
        body_label = QLabel(message)
        body_label.setWordWrap(True)
        body_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; line-height: 1.35;"
        )

        button_box = QDialogButtonBox()
        self.cancel_button = QPushButton(cancel_text)
        self.confirm_button = QPushButton(confirm_text)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setFixedHeight(30)
        self.confirm_button.setFixedHeight(30)
        self.cancel_button.setStyleSheet(
            f"background-color: {BG_WHITE}; color: {TEXT_BODY}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px 12px;"
        )
        if danger:
            self.confirm_button.setStyleSheet(
                f"background-color: {DANGER}; color: {ACCENT_TEXT}; border: none; border-radius: 8px; padding: 4px 12px;"
            )
        else:
            self.confirm_button.setStyleSheet(
                f"background-color: {ACCENT}; color: {ACCENT_TEXT}; border: none; border-radius: 8px; padding: 4px 12px;"
            )

        button_box.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        button_box.addButton(self.confirm_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addWidget(button_box)

        self.setStyleSheet(
            f"QDialog#ConfirmDialog {{ background-color: {BG_WHITE}; border: 1px solid {BORDER}; border-radius: 14px; }}"
        )
        apply_soft_shadow(self)


def confirm_destructive(
    parent,
    *,
    title: str,
    message: str,
    confirm_text: str,
    cancel_text: str = "Cancel",
) -> bool:
    dialog = ConfirmDialog(
        parent,
        title=title,
        message=message,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        danger=True,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted

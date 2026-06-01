"""Dialog xác nhận tái sử dụng cho các thao tác phá hủy dữ liệu."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QPushButton,
                             QVBoxLayout)


class ConfirmDialog(QDialog):
    """Hộp thoại xác nhận cho các hành động phá hủy hoặc quan trọng."""

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
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setProperty("type", "dialog_title")

        body_label = QLabel(message)
        body_label.setWordWrap(True)
        body_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_label.setProperty("type", "dialog_body")

        button_box = QDialogButtonBox()
        self.cancel_button = QPushButton(cancel_text)
        self.confirm_button = QPushButton(confirm_text)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setFixedHeight(36)
        self.confirm_button.setFixedHeight(36)

        self.cancel_button.setProperty("type", "outline")
        if danger:
            self.confirm_button.setProperty("type", "danger")
        else:
            self.confirm_button.setProperty("type", "primary")

        button_box.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        button_box.addButton(self.confirm_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addWidget(button_box)


def confirm_destructive(
    parent,
    *,
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
) -> bool:
    """Hiển thị dialog xác nhận và trả về True nếu người dùng đồng ý."""
    dialog = ConfirmDialog(
        parent,
        title=title,
        message=message,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        danger=True,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted

"""Shared presenter for serial/bluetooth connection status widgets."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QLabel, QPushButton

from ui.tokens import DANGER, STATUS_LABEL_STYLE_TEMPLATE, SUCCESS


@dataclass(frozen=True)
class ConnectionStatusPresenter:
    """Apply a consistent connected/disconnected presentation state."""

    connected_color: str = SUCCESS
    disconnected_color: str = DANGER

    def apply(
        self,
        *,
        status_label: QLabel,
        connect_btn: QPushButton,
        scan_btn: QPushButton,
        connected: bool,
        device_label: str,
    ) -> None:
        if connected:
            status_label.setText(f"● CONNECTED: {device_label}")
            status_label.setStyleSheet(
                STATUS_LABEL_STYLE_TEMPLATE.format(color=self.connected_color)
            )
            connect_btn.setText("DISCONNECT")
            scan_btn.setEnabled(False)
            return

        status_label.setText("● DISCONNECTED")
        status_label.setStyleSheet(
            STATUS_LABEL_STYLE_TEMPLATE.format(color=self.disconnected_color)
        )
        connect_btn.setText("CONNECT")
        scan_btn.setEnabled(True)

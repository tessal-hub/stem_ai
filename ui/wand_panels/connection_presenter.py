"""Presenter dùng chung cho trạng thái kết nối serial/bluetooth."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QLabel, QPushButton

from ui.i18n_bridge import tr_ui
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
            label = str(device_label).strip().upper()
            if label:
                status_label.setText(tr_ui("wand_status_connected_port", port=label))
            else:
                status_label.setText(tr_ui("wand_status_connected"))
            status_label.setStyleSheet(
                STATUS_LABEL_STYLE_TEMPLATE.format(color=self.connected_color)
            )
            connect_btn.setText(tr_ui("wand_disconnect"))
            scan_btn.setEnabled(False)
            return

        status_label.setText(tr_ui("wand_status_disconnected"))
        status_label.setStyleSheet(
            STATUS_LABEL_STYLE_TEMPLATE.format(color=self.disconnected_color)
        )
        connect_btn.setText(tr_ui("wand_connect"))
        scan_btn.setEnabled(True)

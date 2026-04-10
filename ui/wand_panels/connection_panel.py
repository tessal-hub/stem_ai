"""Connection panel for serial and bluetooth controls."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.tokens import (
    DANGER,
    STATUS_LABEL_STYLE_TEMPLATE,
    STYLE_BTN_OUTLINE,
    STYLE_BTN_PRIMARY,
    STYLE_WAND_COMBO,
    TEXT_BODY,
)
from ui.wand_panels.connection_presenter import ConnectionStatusPresenter
from ui.wand_panels.shared import make_button, make_card, make_section_label


class WandConnectionPanel(QWidget):
    """Combined serial and bluetooth connection control panel."""

    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    sig_bt_scan = pyqtSignal()
    sig_bt_connect = pyqtSignal(str)
    sig_bt_disconnect = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._serial_connected = False
        self._bt_connected = False
        self._status_presenter = ConnectionStatusPresenter()

        self._build_ui()
        self._connect_internal_signals()

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        self._serial_connected = connected
        self._status_presenter.apply(
            status_label=self.lbl_serial_status,
            connect_btn=self.btn_serial_connect,
            scan_btn=self.btn_serial_scan,
            connected=connected,
            device_label=port_name,
        )

    def update_serial_port_list(self, ports: list[str]) -> None:
        self.combo_serial_ports.clear()
        self.combo_serial_ports.addItems(ports)

    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        self._bt_connected = connected
        self._status_presenter.apply(
            status_label=self.lbl_bt_status,
            connect_btn=self.btn_bt_connect,
            scan_btn=self.btn_bt_scan,
            connected=connected,
            device_label=device_name,
        )

    def update_bt_device_list(self, devices: list[str]) -> None:
        self.combo_bt_devices.clear()
        self.combo_bt_devices.addItems(devices)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(make_section_label("CONNECTION"))
        layout.addWidget(self._build_serial_card())
        layout.addWidget(self._build_bt_card())
        layout.addStretch()

    def _build_serial_card(self):
        card, layout = make_card(margins=(12, 12, 12, 12), spacing=8)

        status_row = QHBoxLayout()
        lbl_name = QLabel("SERIAL:")
        lbl_name.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
        self.lbl_serial_status = QLabel("● DISCONNECTED")
        self.lbl_serial_status.setStyleSheet(
            STATUS_LABEL_STYLE_TEMPLATE.format(color=DANGER)
        )
        status_row.addWidget(lbl_name)
        status_row.addStretch()
        status_row.addWidget(self.lbl_serial_status)
        layout.addLayout(status_row)

        self.combo_serial_ports = QComboBox()
        self.combo_serial_ports.setStyleSheet(STYLE_WAND_COMBO)
        self.combo_serial_ports.setMinimumHeight(36)
        layout.addWidget(self.combo_serial_ports)

        btn_row = QHBoxLayout()
        self.btn_serial_scan = make_button("SCAN", STYLE_BTN_OUTLINE)
        self.btn_serial_connect = make_button("CONNECT", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_serial_scan)
        btn_row.addWidget(self.btn_serial_connect)
        layout.addLayout(btn_row)
        return card

    def _build_bt_card(self):
        card, layout = make_card(margins=(12, 12, 12, 12), spacing=8)

        status_row = QHBoxLayout()
        lbl_name = QLabel("BLUETOOTH:")
        lbl_name.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
        self.lbl_bt_status = QLabel("● DISCONNECTED")
        self.lbl_bt_status.setStyleSheet(STATUS_LABEL_STYLE_TEMPLATE.format(color=DANGER))
        status_row.addWidget(lbl_name)
        status_row.addStretch()
        status_row.addWidget(self.lbl_bt_status)
        layout.addLayout(status_row)

        self.combo_bt_devices = QComboBox()
        self.combo_bt_devices.setStyleSheet(STYLE_WAND_COMBO)
        self.combo_bt_devices.setMinimumHeight(36)
        layout.addWidget(self.combo_bt_devices)

        btn_row = QHBoxLayout()
        self.btn_bt_scan = make_button("SCAN", STYLE_BTN_OUTLINE)
        self.btn_bt_connect = make_button("CONNECT", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_bt_scan)
        btn_row.addWidget(self.btn_bt_connect)
        layout.addLayout(btn_row)
        return card

    def _connect_internal_signals(self) -> None:
        self.btn_serial_scan.clicked.connect(self.sig_serial_scan.emit)
        self.btn_serial_connect.clicked.connect(self._on_serial_connect_clicked)

        self.btn_bt_scan.clicked.connect(self.sig_bt_scan.emit)
        self.btn_bt_connect.clicked.connect(self._on_bt_connect_clicked)

    def _on_serial_connect_clicked(self) -> None:
        if self._serial_connected:
            self.sig_serial_disconnect.emit()
            return
        self.sig_serial_connect.emit(self.combo_serial_ports.currentText())

    def _on_bt_connect_clicked(self) -> None:
        if self._bt_connected:
            self.sig_bt_disconnect.emit()
            return
        self.sig_bt_connect.emit(self.combo_bt_devices.currentText())

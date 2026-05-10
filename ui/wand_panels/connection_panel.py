"""Panel điều khiển kết nối serial cho trang Wand."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.tokens import (
    DANGER,
    SETTINGS_INPUT_H,
    STATUS_LABEL_STYLE_TEMPLATE,
    STYLE_BTN_OUTLINE,
    STYLE_BTN_PRIMARY,
    STYLE_SETTINGS_FORM_LABEL,
    STYLE_WAND_COMBO,
)
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_SM
from ui.wand_panels.connection_presenter import ConnectionStatusPresenter
from ui.wand_panels.shared import make_button, make_card, make_section_label


class WandConnectionPanel(QWidget):
    """Panel điều khiển kết nối serial — quét cổng, kết nối, và ngắt."""

    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._serial_connected = False
        self._status_presenter = ConnectionStatusPresenter()

        self._init_ui()
        self._init_signals()

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        """Cập nhật trạng thái kết nối serial trên giao diện.

        Args:
            connected: True nếu đã kết nối.
            port_name: Tên cổng serial đang kết nối.
        """
        self._serial_connected = connected
        self._status_presenter.apply(
            status_label=self.lbl_serial_status,
            connect_btn=self.btn_serial_connect,
            scan_btn=self.btn_serial_scan,
            connected=connected,
            device_label=port_name,
        )

    def update_serial_port_list(self, ports: list[str]) -> None:
        """Cập nhật danh sách cổng serial khả dụng trong dropdown.

        Args:
            ports: Danh sách tên cổng serial.
        """
        self.combo_serial_ports.clear()
        if ports:
            self.combo_serial_ports.addItems(ports)
            self.btn_serial_connect.setEnabled(True)
            return
        self.combo_serial_ports.addItem("No serial ports detected")
        if not self._serial_connected:
            self.btn_serial_connect.setEnabled(False)

    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        """Deprecated no-op: bluetooth feature removed from UI."""
        _ = (connected, device_name)

    def update_bt_device_list(self, devices: list[str]) -> None:
        """Deprecated no-op: bluetooth feature removed from UI."""
        _ = devices

    def _init_ui(self) -> None:
        """Xây dựng layout panel gồm status, dropdown, và các nút."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        layout.addWidget(make_section_label("CONNECTION"))
        layout.addWidget(self._build_serial_card())
        layout.addStretch()

    def _build_serial_card(self) -> QFrame:
        """Tạo card chứa controls kết nối serial."""
        card, layout = make_card(
            margins=(
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
                MARGIN_COMFORTABLE,
            ),
            spacing=SPACING_SM,
        )

        status_row = QHBoxLayout()
        lbl_name = QLabel("SERIAL:")
        lbl_name.setStyleSheet(STYLE_SETTINGS_FORM_LABEL)
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
        self.combo_serial_ports.setMinimumHeight(SETTINGS_INPUT_H)
        self.combo_serial_ports.addItem("No serial ports detected")
        layout.addWidget(self.combo_serial_ports)

        btn_row = QHBoxLayout()
        self.btn_serial_scan = make_button("SCAN", STYLE_BTN_OUTLINE)
        self.btn_serial_connect = make_button("CONNECT", STYLE_BTN_PRIMARY)
        self.btn_serial_connect.setEnabled(False)
        btn_row.addWidget(self.btn_serial_scan)
        btn_row.addWidget(self.btn_serial_connect)
        layout.addLayout(btn_row)
        return card

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot nội bộ."""
        self.btn_serial_scan.clicked.connect(self.sig_serial_scan.emit)
        self.btn_serial_connect.clicked.connect(self._on_btn_serial_connect_clicked)

    def _on_btn_serial_connect_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Connect/Disconnect."""
        if self._serial_connected:
            self.sig_serial_disconnect.emit()
            return
        self.sig_serial_connect.emit(self.combo_serial_ports.currentText())


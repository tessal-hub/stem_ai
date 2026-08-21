"""
ui/wand_panels/connection_panel.py — Panel điều khiển kết nối Serial cho Wand.

Quản lý việc quét các cổng COM, kết nối và ngắt kết nối với đũa phép.
Cung cấp phản hồi trạng thái kết nối trực quan cho người dùng.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel,
                             QVBoxLayout, QWidget)

from ui.i18n_bridge import tr_ui
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_SM
from ui.tokens import SETTINGS_INPUT_H

from .connection_presenter import ConnectionStatusPresenter
from .shared import make_button, make_card, make_section_label


class WandConnectionPanel(QWidget):
    """
    Panel quản lý kết nối phần cứng thông qua cổng Serial.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._serial_connected = False
        self._last_port = ""
        self._current_firmware = "disconnected"
        self._combo_shows_no_ports = True
        self._status_presenter = ConnectionStatusPresenter()

        self._init_ui()
        self._init_signals()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._section_lbl = make_section_label(tr_ui("wand_section_connection"))
        layout.addWidget(self._section_lbl)
        layout.addWidget(self._build_serial_card())

    def _init_signals(self) -> None:
        """Kết nối signal/slot nội bộ."""
        self.btn_serial_scan.clicked.connect(lambda _: self.sig_serial_scan.emit())
        self.btn_serial_connect.clicked.connect(self._on_btn_serial_connect_clicked)

    # ── Public methods ──────────────────────────

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        """Cập nhật trạng thái hiển thị của kết nối."""
        self._serial_connected = connected
        self._last_port = port_name
        self._status_presenter.apply(
            status_label=self.lbl_serial_status,
            connect_btn=self.btn_serial_connect,
            scan_btn=self.btn_serial_scan,
            connected=connected,
            device_label=port_name,
        )
        if not connected:
            self.set_firmware_status("disconnected")

    def set_firmware_status(self, fw_type: str) -> None:
        """Cập nhật trạng thái firmware hiển thị trên panel."""
        self._current_firmware = fw_type
        if not self._serial_connected or fw_type == "disconnected":
            self.lbl_firmware_status.setText(tr_ui("fw_status_disconnected"))
            self.lbl_firmware_status.setProperty("status", "muted")
            self.lbl_firmware_status.setToolTip("")
        elif fw_type == "data":
            self.lbl_firmware_status.setText(f"⚡ {tr_ui('fw_status_data')}")
            self.lbl_firmware_status.setProperty("status", "success")
            self.lbl_firmware_status.setToolTip(tr_ui("fw_desc_data"))
        elif fw_type == "inference":
            self.lbl_firmware_status.setText(f"🧠 {tr_ui('fw_status_inference')}")
            self.lbl_firmware_status.setProperty("status", "accent")
            self.lbl_firmware_status.setToolTip(tr_ui("fw_desc_inference"))
        elif fw_type == "detecting":
            self.lbl_firmware_status.setText(f"🔍 {tr_ui('fw_status_detecting')}")
            self.lbl_firmware_status.setProperty("status", "warning")
            self.lbl_firmware_status.setToolTip(tr_ui("fw_desc_detecting"))
        elif fw_type == "unknown":
            self.lbl_firmware_status.setText(f"❓ {tr_ui('fw_status_unknown')}")
            self.lbl_firmware_status.setProperty("status", "warning")
            self.lbl_firmware_status.setToolTip(tr_ui("fw_desc_unknown"))
        else:
            self.lbl_firmware_status.setText(tr_ui("fw_status_disconnected"))
            self.lbl_firmware_status.setProperty("status", "muted")
            self.lbl_firmware_status.setToolTip("")

        self.lbl_firmware_status.style().unpolish(self.lbl_firmware_status)
        self.lbl_firmware_status.style().polish(self.lbl_firmware_status)

    def update_serial_port_list(self, ports: list[str]) -> None:
        """Cập nhật danh sách cổng COM khả dụng."""
        self.combo_serial_ports.clear()
        if ports:
            self._combo_shows_no_ports = False
            self.combo_serial_ports.addItems(ports)
            self.btn_serial_connect.setEnabled(True)
            return
        self._combo_shows_no_ports = True
        self.combo_serial_ports.addItem(tr_ui("wand_no_ports"))
        if not self._serial_connected:
            self.btn_serial_connect.setEnabled(False)

    def apply_ui_language(self) -> None:
        """Làm mới văn bản khi ngôn ngữ ứng dụng thay đổi."""
        self._section_lbl.setText(tr_ui("wand_section_connection"))
        self._serial_heading.setText(tr_ui("wand_serial"))
        self._fw_heading.setText(tr_ui("fw_label"))
        self.btn_serial_scan.setText(tr_ui("wand_scan"))
        if self._combo_shows_no_ports and self.combo_serial_ports.count() == 1:
            self.combo_serial_ports.setItemText(0, tr_ui("wand_no_ports"))
        self.set_serial_status(self._serial_connected, self._last_port)
        self.set_firmware_status(self._current_firmware)

    def refresh_styles(self) -> None:
        """Làm mới style theo theme hiện tại."""
        self.set_serial_status(self._serial_connected, self.combo_serial_ports.currentText())
        self.set_firmware_status(self._current_firmware)

    # ── Private methods ─────────────────────────

    def _build_serial_card(self) -> QFrame:
        """Xây dựng thẻ chứa các nút điều khiển kết nối."""
        card, layout = make_card(
            margins=(16, 14, 16, 14),
            spacing=SPACING_SM,
        )

        status_row = QHBoxLayout()
        self._serial_heading = QLabel(tr_ui("wand_serial"))
        self._serial_heading.setProperty("type", "settings_form_label")
        self.lbl_serial_status = QLabel(tr_ui("wand_status_disconnected"))
        self.lbl_serial_status.setProperty("type", "status_label")
        self.lbl_serial_status.setProperty("status", "error")
        self.lbl_serial_status.setWordWrap(True)
        status_row.addWidget(self._serial_heading)
        status_row.addStretch()
        status_row.addWidget(self.lbl_serial_status)
        layout.addLayout(status_row)

        fw_row = QHBoxLayout()
        self._fw_heading = QLabel(tr_ui("fw_label"))
        self._fw_heading.setProperty("type", "settings_form_label")
        self.lbl_firmware_status = QLabel(tr_ui("fw_status_disconnected"))
        self.lbl_firmware_status.setProperty("type", "status_label")
        self.lbl_firmware_status.setProperty("status", "muted")
        self.lbl_firmware_status.setWordWrap(True)
        fw_row.addWidget(self._fw_heading)
        fw_row.addStretch()
        fw_row.addWidget(self.lbl_firmware_status)
        layout.addLayout(fw_row)

        self.combo_serial_ports = QComboBox()
        self.combo_serial_ports.setMinimumHeight(SETTINGS_INPUT_H)
        self.combo_serial_ports.addItem(tr_ui("wand_no_ports"))
        layout.addWidget(self.combo_serial_ports)

        btn_row = QHBoxLayout()
        self.btn_serial_scan = make_button(tr_ui("wand_scan"), "outline")
        self.btn_serial_connect = make_button(tr_ui("wand_connect"), "primary")
        self.btn_serial_connect.setEnabled(False)
        btn_row.addWidget(self.btn_serial_scan)
        btn_row.addWidget(self.btn_serial_connect)
        layout.addLayout(btn_row)
        return card

    # ── Slots ───────────────────────────────────

    def _on_btn_serial_connect_clicked(self) -> None:
        """Xử lý sự kiện nhấn nút Kết nối/Ngắt."""
        if self._serial_connected:
            self.sig_serial_disconnect.emit()
        else:
            self.sig_serial_connect.emit(self.combo_serial_ports.currentText())

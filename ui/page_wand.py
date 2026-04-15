"""PageWand compositor for hardware configuration, flashing, and terminal view."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ui.tokens import STYLE_SCROLL_AREA, STYLE_WAND_MAIN_CONTAINER
from ui.wand_panels.connection_panel import WandConnectionPanel
from ui.wand_panels.flash_panel import WandFlashPanel
from ui.wand_panels.spell_payload_panel import WandSpellPayloadPanel
from ui.wand_panels.stats_panel import WandStatsPanel
from ui.wand_panels.terminal_panel import WandTerminalPanel


class PageWand(QWidget):
    # Serial signals
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    # Bluetooth signals
    sig_bt_scan = pyqtSignal()
    sig_bt_connect = pyqtSignal(str)
    sig_bt_disconnect = pyqtSignal()

    # Tool signals
    sig_flash_compile = pyqtSignal(list)
    sig_flash_upload = pyqtSignal()
    sig_term_clear = pyqtSignal()
    sig_train_build_requested = pyqtSignal()
    sig_train_build_tflite_requested = pyqtSignal(list)
    sig_train_build_cc_requested = pyqtSignal(list)

    def __init__(self, data_store) -> None:
        super().__init__()
        self._build_ui()
        self._expose_legacy_attributes()
        self._connect_internal_signals()
        self._configure_accessibility()

        # Populate from DataStore snapshot at startup.
        self.load_spell_payload_list(data_store.spell_counts)
        self.update_esp_stats(data_store.esp32_stats)

    # ------------------------------------------------------------------
    # Public API (preserved)
    # ------------------------------------------------------------------

    def append_terminal_text(self, text: str) -> None:
        self.terminal_panel.append_terminal_text(text)

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        self.flash_panel.update_flash_progress(percentage, status_text)

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        self.connection_panel.set_serial_status(connected, port_name)

    def update_serial_port_list(self, ports: list[str]) -> None:
        self.connection_panel.update_serial_port_list(ports)

    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        self.connection_panel.set_bluetooth_status(connected, device_name)

    def update_bt_device_list(self, devices: list[str]) -> None:
        self.connection_panel.update_bt_device_list(devices)

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        self.stats_panel.update_esp_stats(stats)

    def load_spell_payload_list(self, spell_counts: dict[str, int]) -> None:
        self.stats_panel.update_spell_chart(spell_counts)
        self.payload_panel.load_spell_list(spell_counts)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setFrameShape(QFrame.Shape.NoFrame)
        self.main_container.setFrameShadow(QFrame.Shadow.Plain)
        self.main_container.setStyleSheet(STYLE_WAND_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(12)

        content = QHBoxLayout()
        content.setSpacing(12)

        self.flash_panel = WandFlashPanel()
        self.connection_panel = WandConnectionPanel()
        self.terminal_panel = WandTerminalPanel()
        self.stats_panel = WandStatsPanel()
        self.payload_panel = WandSpellPayloadPanel()

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)
        tools_row.addWidget(self.flash_panel, stretch=1)
        tools_row.addWidget(self.connection_panel, stretch=1)

        left_layout.addLayout(tools_row)
        left_layout.addWidget(self.terminal_panel, stretch=1)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(self.stats_panel, stretch=1)
        right_layout.addWidget(self.payload_panel, stretch=1)

        content.addWidget(left_column, stretch=12)
        content.addWidget(right_column, stretch=10)

        inner.addLayout(content, stretch=1)
        scroll.setWidget(self.main_container)
        outer.addWidget(scroll)

    def _expose_legacy_attributes(self) -> None:
        """Keep historical field access paths stable for handlers/tests."""
        # Serial/Bluetooth controls
        self.combo_serial_ports = self.connection_panel.combo_serial_ports
        self.combo_bt_devices = self.connection_panel.combo_bt_devices
        self.btn_serial_scan = self.connection_panel.btn_serial_scan
        self.btn_serial_connect = self.connection_panel.btn_serial_connect
        self.btn_bt_scan = self.connection_panel.btn_bt_scan
        self.btn_bt_connect = self.connection_panel.btn_bt_connect
        self.lbl_serial_status = self.connection_panel.lbl_serial_status
        self.lbl_bt_status = self.connection_panel.lbl_bt_status

        # Flash controls
        self.btn_build_tflite = self.flash_panel.btn_build_tflite
        self.btn_build_cc = self.flash_panel.btn_build_cc
        self.btn_compile = self.flash_panel.btn_build_cc
        self.btn_flash = self.flash_panel.btn_build_tflite
        self.progress_bar = self.flash_panel.progress_bar
        self.lbl_flash_status = self.flash_panel.lbl_flash_status

        # Terminal controls
        self.btn_term_clear = self.terminal_panel.btn_term_clear
        self.terminal_output = self.terminal_panel.terminal_output

        # Stats/payload widgets
        self.layout_stats = self.stats_panel.layout_stats
        self.stats_plot = self.stats_panel.stats_plot
        self.list_firmware = self.payload_panel.list_firmware
        self.list_selected_spells = self.payload_panel.list_selected_spells
        self.list_available_spells = self.payload_panel.list_available_spells

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_internal_signals(self) -> None:
        self.connection_panel.sig_serial_scan.connect(self.sig_serial_scan.emit)
        self.connection_panel.sig_serial_connect.connect(self.sig_serial_connect.emit)
        self.connection_panel.sig_serial_disconnect.connect(self.sig_serial_disconnect.emit)

        self.connection_panel.sig_bt_scan.connect(self.sig_bt_scan.emit)
        self.connection_panel.sig_bt_connect.connect(self.sig_bt_connect.emit)
        self.connection_panel.sig_bt_disconnect.connect(self.sig_bt_disconnect.emit)

        self.flash_panel.sig_build_tflite_clicked.connect(self._on_build_tflite_clicked)
        self.flash_panel.sig_build_cc_clicked.connect(self._on_build_cc_clicked)

        self.terminal_panel.sig_clear_requested.connect(self.sig_term_clear.emit)

    def _configure_accessibility(self) -> None:
        """Set accessible names and keyboard tab traversal across wand controls."""
        self.combo_serial_ports.setAccessibleName("Serial port list")
        self.btn_serial_scan.setAccessibleName("Scan serial ports")
        self.btn_serial_connect.setAccessibleName("Connect serial")
        self.combo_bt_devices.setAccessibleName("Bluetooth device list")
        self.btn_bt_scan.setAccessibleName("Scan bluetooth devices")
        self.btn_bt_connect.setAccessibleName("Connect bluetooth")
        self.btn_build_tflite.setAccessibleName("Build gesture_model.tflite")
        self.btn_build_cc.setAccessibleName("Build gesture_model.cc")
        self.btn_term_clear.setAccessibleName("Clear wand terminal")
        self.list_selected_spells.setAccessibleName("Selected spells for training")
        self.list_available_spells.setAccessibleName("Available spells for training")

        self.setTabOrder(self.combo_serial_ports, self.btn_serial_scan)
        self.setTabOrder(self.btn_serial_scan, self.btn_serial_connect)
        self.setTabOrder(self.btn_serial_connect, self.combo_bt_devices)
        self.setTabOrder(self.combo_bt_devices, self.btn_bt_scan)
        self.setTabOrder(self.btn_bt_scan, self.btn_bt_connect)
        self.setTabOrder(self.btn_bt_connect, self.btn_build_tflite)
        self.setTabOrder(self.btn_build_tflite, self.btn_build_cc)
        self.setTabOrder(self.btn_build_cc, self.btn_term_clear)
        self.setTabOrder(self.btn_term_clear, self.list_selected_spells)
        self.setTabOrder(self.list_selected_spells, self.list_available_spells)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def _on_compile_clicked(self) -> None:
        self.sig_flash_compile.emit(self.payload_panel.get_checked_spells())

    def _on_build_tflite_clicked(self) -> None:
        selected_spells = self.payload_panel.get_checked_spells()
        self.sig_train_build_tflite_requested.emit(selected_spells)

    def _on_build_cc_clicked(self) -> None:
        selected_spells = self.payload_panel.get_checked_spells()
        self.sig_train_build_cc_requested.emit(selected_spells)

"""
Trang cấu hình phần cứng, flash firmware, và terminal view cho wand.

Tổng hợp các panel con (connection, flash, terminal, stats, payload)
thành một trang quản lý toàn diện cho thiết bị Magic Wand.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_MD, SPACING_LG
from ui.wand_panels.connection_panel import WandConnectionPanel
from ui.wand_panels.flash_panel import WandFlashPanel
from ui.wand_panels.spell_payload_panel import WandSpellPayloadPanel
from ui.wand_panels.stats_panel import WandStatsPanel
from ui.wand_panels.terminal_panel import WandTerminalPanel


class PageWand(QWidget):
    """
    Trang quản lý thiết bị Wand.
    Cung cấp giao diện kết nối serial, build model, terminal UART,
    thống kê dataset, và chọn spell cho firmware.
    """

    # Signal kết nối serial
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    # Signal công cụ build/flash
    sig_flash_compile = pyqtSignal(list)
    sig_flash_upload = pyqtSignal()
    sig_term_clear = pyqtSignal()
    sig_train_build_requested = pyqtSignal()
    sig_train_build_tflite_requested = pyqtSignal(list)
    sig_train_build_cc_requested = pyqtSignal(list)

    def __init__(self, data_store) -> None:
        super().__init__()
        self._init_ui()
        self._expose_legacy_attributes()
        self._init_signals()
        self._configure_accessibility()
        self._load_data(data_store)

    # ------------------------------------------------------------------
    # Khởi tạo giao diện
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Xây dựng layout 2 cột với các panel con."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            MARGIN_COMFORTABLE, MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE, MARGIN_COMFORTABLE,
        )
        outer.setSpacing(SPACING_LG)

        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)

        self.flash_panel = WandFlashPanel()
        self.connection_panel = WandConnectionPanel()
        self.terminal_panel = WandTerminalPanel()
        self.stats_panel = WandStatsPanel()
        self.payload_panel = WandSpellPayloadPanel()

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING_LG)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(SPACING_MD)
        tools_row.addWidget(self.flash_panel, stretch=1)
        tools_row.addWidget(self.connection_panel, stretch=1)

        left_layout.addLayout(tools_row)
        left_layout.addWidget(self.terminal_panel, stretch=1)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(SPACING_LG)
        right_layout.addWidget(self.stats_panel, stretch=1)
        right_layout.addWidget(self.payload_panel, stretch=1)

        content.addWidget(left_column, stretch=12)
        content.addWidget(right_column, stretch=10)

        outer.addLayout(content, stretch=1)

    # ------------------------------------------------------------------
    # Kết nối signal/slot
    # ------------------------------------------------------------------

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal từ các panel con tới signal cấp trang."""
        # Serial panel → page-level signals
        self.connection_panel.sig_serial_scan.connect(self.sig_serial_scan.emit)
        self.connection_panel.sig_serial_connect.connect(self.sig_serial_connect.emit)
        self.connection_panel.sig_serial_disconnect.connect(self.sig_serial_disconnect.emit)

        # Flash panel → slot nội bộ → page-level signals
        self.flash_panel.sig_build_tflite_clicked.connect(self._on_btn_build_tflite_clicked)
        self.flash_panel.sig_build_cc_clicked.connect(self._on_btn_build_cc_clicked)

        # Terminal panel
        self.terminal_panel.sig_clear_requested.connect(self.sig_term_clear.emit)

    # ------------------------------------------------------------------
    # Nạp dữ liệu ban đầu
    # ------------------------------------------------------------------

    def _load_data(self, data_store) -> None:
        """Nạp dữ liệu ban đầu từ DataStore snapshot.

        Args:
            data_store: Đối tượng DataStore chứa spell counts và ESP stats.
        """
        self.load_spell_payload_list(data_store.spell_counts)
        self.update_esp_stats(data_store.esp32_stats)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_terminal_text(self, text: str) -> None:
        """Thêm dòng text vào terminal output.

        Args:
            text: Nội dung cần hiển thị trong terminal.
        """
        self.terminal_panel.append_terminal_text(text)

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        """Cập nhật thanh tiến trình flash.

        Args:
            percentage: Phần trăm hoàn thành (0-100).
            status_text: Thông báo trạng thái kèm theo.
        """
        self.flash_panel.update_flash_progress(percentage, status_text)

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        """Cập nhật trạng thái kết nối serial trên giao diện.

        Args:
            connected: True nếu đã kết nối.
            port_name: Tên cổng serial đang kết nối.
        """
        self.connection_panel.set_serial_status(connected, port_name)

    def update_serial_port_list(self, ports: list[str]) -> None:
        """Cập nhật danh sách cổng serial khả dụng.

        Args:
            ports: Danh sách tên cổng serial.
        """
        self.connection_panel.update_serial_port_list(ports)

    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        """No-op: tính năng bluetooth đã bị loại bỏ khỏi UI."""
        _ = (connected, device_name)

    def update_bt_device_list(self, devices: list[str]) -> None:
        """No-op: tính năng bluetooth đã bị loại bỏ khỏi UI."""
        _ = devices

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        """Cập nhật thống kê phần cứng ESP32.

        Args:
            stats: Dict chứa các thông số (Battery, RAM Free, RSSI...).
        """
        self.stats_panel.update_esp_stats(stats)

    def load_spell_payload_list(self, spell_counts: dict[str, int]) -> None:
        """Nạp danh sách spell vào cả chart thống kê và panel payload.

        Args:
            spell_counts: Dict spell_name → số lượng mẫu.
        """
        self.stats_panel.update_spell_chart(spell_counts)
        self.payload_panel.load_spell_list(spell_counts)

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _expose_legacy_attributes(self) -> None:
        """Giữ ổn định đường dẫn truy cập cũ cho handlers/tests.

        Các alias này đảm bảo code ngoài (Handler, tests) truy cập
        trực tiếp widget con qua tên cũ vẫn hoạt động bình thường.
        """
        # Serial controls
        self.combo_serial_ports = self.connection_panel.combo_serial_ports
        self.btn_serial_scan = self.connection_panel.btn_serial_scan
        self.btn_serial_connect = self.connection_panel.btn_serial_connect
        self.lbl_serial_status = self.connection_panel.lbl_serial_status

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

    def _configure_accessibility(self) -> None:
        """Đặt accessible names và thứ tự tab traversal cho các control."""
        self.combo_serial_ports.setAccessibleName("Serial port list")
        self.btn_serial_scan.setAccessibleName("Scan serial ports")
        self.btn_serial_connect.setAccessibleName("Connect serial")
        self.btn_build_tflite.setAccessibleName("Build gesture_model.tflite")
        self.btn_build_cc.setAccessibleName("Build gesture_model.cc")
        self.btn_term_clear.setAccessibleName("Clear wand terminal")
        self.list_selected_spells.setAccessibleName("Selected spells for training")
        self.list_available_spells.setAccessibleName("Available spells for training")

        self.setTabOrder(self.combo_serial_ports, self.btn_serial_scan)
        self.setTabOrder(self.btn_serial_scan, self.btn_serial_connect)
        self.setTabOrder(self.btn_serial_connect, self.btn_build_tflite)
        self.setTabOrder(self.btn_build_tflite, self.btn_build_cc)
        self.setTabOrder(self.btn_build_cc, self.btn_term_clear)
        self.setTabOrder(self.btn_term_clear, self.list_selected_spells)
        self.setTabOrder(self.list_selected_spells, self.list_available_spells)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_btn_compile_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Compile firmware."""
        self.sig_flash_compile.emit(self.payload_panel.get_checked_spells())

    def _on_btn_build_tflite_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Build .tflite."""
        selected_spells = self.payload_panel.get_checked_spells()
        self.sig_train_build_tflite_requested.emit(selected_spells)

    def _on_btn_build_cc_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Build .cc."""
        selected_spells = self.payload_panel.get_checked_spells()
        self.sig_train_build_cc_requested.emit(selected_spells)

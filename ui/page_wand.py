"""
ui/page_wand.py — Trang cấu hình phần cứng, flash firmware và giám sát wand.

Tổng hợp các panel quản lý kết nối serial, xây dựng mô hình TinyML,
hiển thị terminal UART và thống kê tài nguyên thiết bị.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QGridLayout, QSizePolicy

from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG
from ui.tokens import SPACE_32
from ui.wand_panels.connection_panel import WandConnectionPanel
from ui.wand_panels.flash_panel import WandFlashPanel
from ui.wand_panels.spell_payload_panel import WandSpellPayloadPanel
from ui.wand_panels.stats_panel import WandStatsPanel
from ui.wand_panels.terminal_panel import WandTerminalPanel


class PageWand(QWidget):
    """
    Trang quản lý thiết bị Wand (Đũa phép).
    Điều phối luồng công việc từ kết nối đến nạp firmware.
    """

    # ── Signal điều hướng & Phần cứng ─────────────
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    # ── Signal Build & Flash ──────────────────────
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

    def _init_ui(self) -> None:
        """Khởi tạo giao diện (Requirement 2: 2-column grid, Requirement 10: padding 80px)."""
        layout = QVBoxLayout(self)
        # Requirement 10: padding-bottom 80px
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, 80)
        layout.setSpacing(SPACING_LG)

        # Requirement 2: 2-column layout, gap 32px
        grid = QGridLayout()
        grid.setSpacing(SPACE_32)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Khởi tạo các panel thành phần
        self.flash_panel = WandFlashPanel()
        self.connection_panel = WandConnectionPanel()
        self.terminal_panel = WandTerminalPanel()
        self.stats_panel = WandStatsPanel()
        self.payload_panel = WandSpellPayloadPanel()

        # Cột trái: Setup
        left_col = QVBoxLayout()
        left_col.addWidget(self.connection_panel)
        left_col.addWidget(self.payload_panel, stretch=1)
        grid.addLayout(left_col, 0, 0)

        # Cột phải: Monitoring & Flash
        right_col = QVBoxLayout()
        right_col.addWidget(self.stats_panel)
        right_col.addWidget(self.terminal_panel)
        right_col.addWidget(self.flash_panel)
        grid.addLayout(right_col, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        layout.addLayout(grid, stretch=1)

    def _init_signals(self) -> None:
        """Kết nối các signal từ panel con lên cấp trang."""
        # Kết nối Serial
        self.connection_panel.sig_serial_scan.connect(self.sig_serial_scan.emit)
        self.connection_panel.sig_serial_connect.connect(self.sig_serial_connect.emit)
        self.connection_panel.sig_serial_disconnect.connect(self.sig_serial_disconnect.emit)

        # Thao tác Flash & Build
        self.flash_panel.sig_build_tflite_clicked.connect(self._on_btn_build_tflite_clicked)
        self.flash_panel.sig_build_cc_clicked.connect(self._on_btn_build_cc_clicked)
        self.flash_panel.sig_upload_clicked.connect(self.sig_flash_upload.emit)

        # Terminal
        self.terminal_panel.sig_clear_requested.connect(self.sig_term_clear.emit)

    def _load_data(self, data_store) -> None:
        """Nạp dữ liệu trạng thái ban đầu."""
        self.load_spell_payload_list(data_store.spell_counts)
        self.update_esp_stats(data_store.esp32_stats)

    # ── Public methods ──────────────────────────

    def refresh_styles(self) -> None:
        """Làm mới style cho tất cả các panel con."""
        panels = [self.connection_panel, self.flash_panel, self.terminal_panel, self.stats_panel, self.payload_panel]
        for panel in panels:
            if hasattr(panel, "refresh_styles"):
                panel.refresh_styles()

    def append_terminal_text(self, text: str) -> None:
        """Hiển thị nội dung vào terminal output."""
        self.terminal_panel.append_terminal_text(text)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ hiển thị cho toàn trang."""
        self.flash_panel.apply_ui_language()
        self.connection_panel.apply_ui_language()
        self.terminal_panel.apply_ui_language()
        self.stats_panel.apply_ui_language()
        self.payload_panel.apply_ui_language()

    def update_flash_progress(self, percentage: int, status: str = "") -> None:
        """Cập nhật tiến độ nạp firmware."""
        self.flash_panel.update_flash_progress(percentage, status)

    def set_serial_status(self, connected: bool, port: str = "") -> None:
        """Cập nhật trạng thái kết nối cổng COM."""
        self.connection_panel.set_serial_status(connected, port)

    def update_serial_port_list(self, ports: list[str]) -> None:
        """Cập nhật danh sách cổng COM khả dụng."""
        self.connection_panel.update_serial_port_list(ports)

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        """Cập nhật thông số phần cứng ESP32."""
        self.stats_panel.update_esp_stats(stats)

    def load_spell_payload_list(self, counts: dict[str, int]) -> None:
        """Cập nhật danh sách spell vào chart và panel payload."""
        self.stats_panel.update_spell_chart(counts)
        self.payload_panel.load_spell_list(counts)

    # ── Private methods ─────────────────────────

    def _expose_legacy_attributes(self) -> None:
        """Alias cho các thuộc tính cũ để đảm bảo tính tương thích."""
        self.combo_serial_ports = self.connection_panel.combo_serial_ports
        self.btn_serial_scan = self.connection_panel.btn_serial_scan
        self.btn_serial_connect = self.connection_panel.btn_serial_connect
        self.lbl_serial_status = self.connection_panel.lbl_serial_status

        self.btn_build_tflite = self.flash_panel.btn_build_tflite
        self.btn_build_cc = self.flash_panel.btn_build_cc
        self.btn_compile = self.flash_panel.btn_build_cc
        self.btn_flash = self.flash_panel.btn_build_tflite
        self.progress_bar = self.flash_panel.progress_bar
        self.lbl_flash_status = self.flash_panel.lbl_flash_status

        self.btn_term_clear = self.terminal_panel.btn_term_clear
        self.terminal_output = self.terminal_panel.terminal_output

        self.layout_stats = self.stats_panel.layout_stats
        self.stats_plot = self.stats_panel.stats_plot
        self.list_firmware = self.payload_panel.list_firmware
        self.list_selected_spells = self.payload_panel.list_selected_spells
        self.list_available_spells = self.payload_panel.list_available_spells

    def _configure_accessibility(self) -> None:
        """Cấu hình hỗ trợ trợ năng và thứ tự tab."""
        self.combo_serial_ports.setAccessibleName("Danh sách cổng Serial")
        self.btn_serial_scan.setAccessibleName("Quét tìm thiết bị")
        self.setTabOrder(self.combo_serial_ports, self.btn_serial_scan)
        self.setTabOrder(self.btn_serial_scan, self.connection_panel.btn_serial_connect)

    # ── Slots ───────────────────────────────────

    def _on_btn_build_tflite_clicked(self) -> None:
        """Xử lý khi yêu cầu build model .tflite."""
        self.sig_train_build_tflite_requested.emit(self.payload_panel.get_checked_spells())

    def _on_btn_build_cc_clicked(self) -> None:
        """Xử lý khi yêu cầu build file .cc."""
        self.sig_train_build_cc_requested.emit(self.payload_panel.get_checked_spells())

"""
ui/page_wand.py — Trang cấu hình phần cứng, flash firmware và giám sát wand.

Tổng hợp các panel quản lý kết nối serial, xây dựng mô hình TinyML,
hiển thị terminal UART và thống kê tài nguyên thiết bị.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG
from ui.tokens import SPACE_32
from ui.wand_panels.connection_panel import WandConnectionPanel
from ui.wand_panels.flash_panel import WandFlashPanel
from ui.wand_panels.settings_panel import WandSettingsPanel
from ui.wand_panels.spell_payload_panel import WandSpellPayloadPanel
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
    sig_show_similarity_matrix = pyqtSignal()
    sig_term_clear = pyqtSignal()
    sig_train_build_requested = pyqtSignal()
    sig_train_build_firmware_requested = pyqtSignal(list)
    sig_settings_saved = pyqtSignal(dict)

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._init_ui()
        self._expose_legacy_attributes()
        self._init_signals()
        self._configure_accessibility()
        self._load_data(data_store)

    def _init_ui(self) -> None:
        """Khởi tạo giao diện (Requirement 2: 2-column grid, Requirement 10: padding 80px)."""
        layout = QVBoxLayout(self)
        # Bỏ padding-bottom cứng để nội dung được bung hết cỡ
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_LG)

        # Requirement 2: 2-column layout, gap 32px
        grid = QGridLayout()
        grid.setSpacing(SPACE_32)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Khởi tạo các panel thành phần
        self.flash_panel = WandFlashPanel()
        self.connection_panel = WandConnectionPanel()
        self.terminal_panel = WandTerminalPanel()
        self.payload_panel = WandSpellPayloadPanel()
        self.settings_panel = WandSettingsPanel(self.data_store)

        self._left_col = QVBoxLayout()
        self._right_col = QVBoxLayout()
        grid.addLayout(self._left_col, 0, 0)
        grid.addLayout(self._right_col, 0, 1)

        self._rebalance_layout(True)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid, stretch=1)

    def _init_signals(self) -> None:
        """Kết nối các signal từ panel con lên cấp trang."""
        # Kết nối Serial
        self.connection_panel.sig_serial_scan.connect(self.sig_serial_scan.emit)
        self.connection_panel.sig_serial_connect.connect(self.sig_serial_connect.emit)
        self.connection_panel.sig_serial_disconnect.connect(self.sig_serial_disconnect.emit)

        # Thao tác Flash & Build & Similarity
        self.flash_panel.sig_build_firmware_clicked.connect(self._on_btn_build_firmware_clicked)
        self.flash_panel.sig_upload_clicked.connect(self.sig_flash_upload.emit)
        self.flash_panel.sig_similarity_clicked.connect(self.sig_show_similarity_matrix.emit)

        # Cài đặt tích hợp
        self.settings_panel.sig_settings_saved.connect(self.sig_settings_saved.emit)

        # Terminal
        self.terminal_panel.sig_clear_requested.connect(self.sig_term_clear.emit)

    def _load_data(self, data_store) -> None:
        """Nạp dữ liệu trạng thái ban đầu."""
        self.load_spell_payload_list(data_store.spell_counts)

    # ── Public methods ──────────────────────────

    def refresh_styles(self) -> None:
        """Làm mới style cho tất cả các panel con."""
        panels = [self.connection_panel, self.flash_panel, self.terminal_panel, self.payload_panel, getattr(self, "settings_panel", None)]
        for panel in panels:
            if panel and hasattr(panel, "refresh_styles"):
                panel.refresh_styles()

    def append_terminal_text(self, text: str) -> None:
        """Hiển thị nội dung vào terminal output."""
        self.terminal_panel.append_terminal_text(text)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ hiển thị cho toàn trang."""
        self.flash_panel.apply_ui_language()
        self.connection_panel.apply_ui_language()
        self.terminal_panel.apply_ui_language()
        self.payload_panel.apply_ui_language()
        if hasattr(self, "settings_panel"):
            self.settings_panel.apply_ui_language()

    def load_settings(self, config: dict) -> None:
        """Nạp cấu hình cho panel cài đặt tích hợp."""
        if hasattr(self, "settings_panel"):
            self.settings_panel.load_settings(config)

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
        """No-op: ESP32 stats display removed."""
        pass

    def _rebalance_layout(self, advanced: bool) -> None:
        """Tái cân đối các panel giữa 2 cột theo chế độ nâng cao / cơ bản."""
        if not hasattr(self, "_left_col") or not hasattr(self, "_right_col"):
            return

        while self._left_col.count():
            self._left_col.takeAt(0)
        while self._right_col.count():
            self._right_col.takeAt(0)

        if advanced:
            # Chế độ nâng cao: Ẩn settings panel trên Wand (đã có tab Settings riêng)
            if hasattr(self, "settings_panel"):
                self.settings_panel.setVisible(False)
            # Cột trái: Kết nối + Danh sách Spell
            self._left_col.addWidget(self.connection_panel)
            self._left_col.addWidget(self.payload_panel, stretch=1)
            # Cột phải: UART Terminal + Nạp/Flash Firmware
            self._right_col.addWidget(self.terminal_panel, stretch=2)
            self._right_col.addWidget(self.flash_panel, stretch=1)
        else:
            # Chế độ cơ bản (không nâng cao): Gộp Cài đặt & Wand vào một trang
            if hasattr(self, "settings_panel"):
                self.settings_panel.setVisible(True)
            # Cột trái: Kết nối + Nạp/Flash Firmware + Cài đặt Hệ thống & Giao diện
            self._left_col.addWidget(self.connection_panel)
            self._left_col.addWidget(self.flash_panel)
            if hasattr(self, "settings_panel"):
                self._left_col.addWidget(self.settings_panel)
            self._left_col.addStretch()
            # Cột phải: Danh sách Spell bung toàn bộ chiều cao
            self._right_col.addWidget(self.payload_panel, stretch=1)

    def set_advanced_mode(self, enabled: bool) -> None:
        """Bật/tắt chế độ nâng cao (ẩn/hiện panel UART Terminal) và cân bằng lại layout."""
        if hasattr(self, "terminal_panel") and self.terminal_panel:
            self.terminal_panel.setVisible(enabled)
        self._rebalance_layout(enabled)

    def load_spell_payload_list(self, counts: dict[str, int]) -> None:
        """Cập nhật danh sách spell vào chart và panel payload."""
        from logic.dataset_layout import _PRIMITIVE_LOGICAL_NAMES
        
        # Lọc bỏ các primitives để UI không hiển thị
        filtered_counts = {
            k: v for k, v in counts.items() 
            if k not in _PRIMITIVE_LOGICAL_NAMES and "::" not in k and k != "STAND BY" and k != "STAND_BY"
        }
        
        self.payload_panel.load_spell_list(filtered_counts)

    # ── Private methods ─────────────────────────

    def _expose_legacy_attributes(self) -> None:
        """Alias cho các thuộc tính cũ để đảm bảo tính tương thích."""
        self.combo_serial_ports = self.connection_panel.combo_serial_ports
        self.btn_serial_scan = self.connection_panel.btn_serial_scan
        self.btn_serial_connect = self.connection_panel.btn_serial_connect
        self.lbl_serial_status = self.connection_panel.lbl_serial_status

        self.btn_build_firmware = self.flash_panel.btn_build_firmware
        # Alias for backward compatibility if needed:
        self.btn_compile = self.flash_panel.btn_build_firmware
        self.btn_flash = self.flash_panel.btn_upload
        self.progress_bar = self.flash_panel.progress_bar
        self.lbl_flash_status = self.flash_panel.lbl_flash_status

        self.btn_term_clear = self.terminal_panel.btn_term_clear
        self.terminal_output = self.terminal_panel.terminal_output

        self.layout_stats = None
        self.stats_plot = None
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

    def _on_btn_build_firmware_clicked(self) -> None:
        """Xử lý khi yêu cầu build firmware."""
        self.sig_train_build_firmware_requested.emit(self.payload_panel.get_checked_spells())

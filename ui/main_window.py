"""
ui/main_window.py — Cửa sổ chính của ứng dụng STEM Spell Book.

Trách nhiệm:
    - Quản lý navigation giữa các trang thông qua MacShell.
    - Khởi tạo và điều phối các trang giao diện con.
    - Sở hữu UdpWorker để thu thập dữ liệu không dây.
    - Chuyển tiếp dữ liệu từ các nguồn tới DataStore.
"""

from __future__ import annotations

import logging

from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from logic.udp_worker import UdpWorker
from ui.asset_utils import resolve_asset_path
from ui.i18n_bridge import tr_ui
from ui.mac_shell import MacShell
from ui.page_home import PageHome
from ui.page_primitive_collect import PagePrimitiveCollect
from ui.page_record import PageRecord
from ui.page_setting import PageSetting
from ui.page_wand import PageWand

log = logging.getLogger(__name__)

# Các key dùng để trích xuất dữ liệu cảm biến từ payload UDP
_SENSOR_KEYS = ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z")


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng.
    Điều phối luồng dữ liệu và quản lý trạng thái hiển thị các trang.
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self.handler: object | None = None
        self._udp_log_count = 0

        self._init_ui()
        self._init_signals()
        self._load_data()
        self._apply_ui_language()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục widget."""
        self.setWindowTitle("STEM Spell Book")
        self.setWindowIcon(QIcon(resolve_asset_path("assets/icon/cooliocns SVG/Interface/Book_Open.svg")))
        self.resize(1100, 850)
        self.setMinimumSize(1000, 700)

        # 1. Khởi tạo Shell điều hướng
        self.shell = MacShell("STEM Spell Book")
        self.setCentralWidget(self.shell)

        # 2. Khởi tạo các trang nội dung
        self.page_home = PageHome(self.data_store)
        self.page_primitive_collect = PagePrimitiveCollect(self.data_store)
        self.page_record = PageRecord(self.data_store)
        self.page_wand = PageWand(self.data_store)
        self.page_setting = PageSetting(self.data_store)

        self._pages: list[QWidget] = [
            self.page_home,
            self.page_primitive_collect,
            self.page_record,
            self.page_wand,
            self.page_setting,
        ]

        # 3. Quản lý StackedWidget
        self.stack = QStackedWidget()

        for page in self._pages:
            self.stack.addWidget(page)
        self.shell.content_layout.addWidget(self.stack, stretch=1)

        # 4. Worker nền
        self.udp_worker = UdpWorker(port=5555)

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot."""
        # Điều hướng
        self.shell.nav_requested.connect(self._on_shell_nav_requested)

        # Cài đặt
        self.page_setting.sig_settings_saved.connect(self._on_settings_saved)

        # Dữ liệu UDP
        self.udp_worker.sig_data_received.connect(self._on_udp_sensor_dispatch)
        self.udp_worker.sig_status_change.connect(self._on_udp_status_changed)
        self.udp_worker.sig_health_update.connect(self._on_udp_health_updated)

        # Cập nhật từ DataStore
        self.data_store.sig_connection_state_updated.connect(self.page_home.set_connection_status)
        self.data_store.sig_live_buffer_updated.connect(self.page_primitive_collect.update_signal_preview)
        self.data_store.sig_sensor_data_updated.connect(self._on_sensor_data_for_3d)
        if hasattr(self.data_store, "sig_primitive_stats_updated"):
            self.data_store.sig_primitive_stats_updated.connect(self.page_primitive_collect.update_collection_stats)

        # Hệ thống
        locale_manager.language_changed.connect(self._apply_ui_language)
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ DataStore."""
        self._set_page(0)

        settings = self.data_store.get_settings_snapshot()
        show_prim = settings.get("show_primitives_menu", True)
        self.shell.set_nav_item_visible(1, show_prim)

        # Đồng bộ trạng thái kết nối
        is_connected, _ = self.data_store.get_connection_state()
        self.page_home.set_connection_status(is_connected)

        # Cập nhật thống kê dataset ban đầu
        if hasattr(self.data_store, "get_primitive_collection_stats"):
            stats = self.data_store.get_primitive_collection_stats()
            self.page_primitive_collect.update_collection_stats(stats)

        # Khởi động listener UDP
        self.udp_worker.start()

    # ── Public methods ──────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Xử lý khi đóng ứng dụng."""
        log.info("MainWindow: Ứng dụng đang đóng...")
        handler = getattr(self, "handler", None)
        if handler is not None:
            try:
                handler.shutdown()
            except Exception as exc:
                log.warning("MainWindow: Handler shutdown thất bại: %s", exc)

        if self.udp_worker.isRunning():
            self.udp_worker.stop()
        event.accept()

    # ── Private methods ─────────────────────────

    def _set_page(self, index: int) -> None:
        """Chuyển đổi trang hiển thị trên stack."""
        self.stack.setCurrentIndex(index)
        self.shell.set_active_index(index)
        # Refresh primitive stats when user navigates to that page (index 1 is primitives)
        if index == 1 and hasattr(self.data_store, "refresh_primitive_stats"):
            self.data_store.refresh_primitive_stats()

    def _extract_esp_stats(self, data: dict) -> dict[str, str]:
        """Trích xuất và format thông tin ESP32."""
        esp_update: dict[str, str] = {}
        if "battery" in data:
            esp_update["Battery"] = f"{data['battery']}%"
        if "free_ram" in data:
            esp_update["RAM Free"] = f"{data['free_ram']} KB"
        if "rssi" in data:
            esp_update["RSSI"] = f"{data['rssi']} dBm"
        return esp_update

    def _apply_ui_language(self, _lang: str | None = None) -> None:
        """Cập nhật văn bản hiển thị cho toàn bộ UI."""
        self.setWindowTitle(tr_ui("win_title"))
        self.shell.apply_ui_language()
        for page in self._pages:
            if hasattr(page, "apply_ui_language"):
                page.apply_ui_language()

    # ── Slots ───────────────────────────────────

    def _on_shell_nav_requested(self, index: int) -> None:
        """Xử lý khi người dùng chọn menu điều hướng."""
        self._set_page(index)

    def _on_udp_sensor_dispatch(self, data: dict) -> None:
        """Dispatch UDP payload to Handler for standard routing.

        Extracts 6-axis sensor values and hardware stats then delegates
        to Handler, which applies the same guards and routing as serial.
        """
        handler = getattr(self, "handler", None)
        if handler is None:
            return

        sensor_keys = ("accel_x", "accel_y", "accel_z",
                        "gyro_x", "gyro_y", "gyro_z")
        if sensor_keys[0] in data:
            values = [float(data.get(k, 0.0)) for k in sensor_keys]
            handler.on_udp_sensor_data(values)

        esp_update: dict[str, str] = {}
        if "battery" in data:
            esp_update["Battery"] = f"{data['battery']}%"
        if "free_ram" in data:
            esp_update["RAM Free"] = f"{data['free_ram']} KB"
        if "rssi" in data:
            esp_update["RSSI"] = f"{data['rssi']} dBm"
        if esp_update:
            handler.on_udp_esp_stats(esp_update)

        self._udp_log_count += 1
        if self._udp_log_count % 25 == 0:
            self.page_wand.append_terminal_text(f">> UDP: {data}")

    def _on_udp_status_changed(self, active: bool) -> None:
        """Thông báo trạng thái kết nối UDP."""
        if active:
            self.page_wand.append_terminal_text(">> UDP telemetry received.")

    def _on_udp_health_updated(self, health: dict) -> None:
        """Cập nhật sức khỏe kết nối vào DataStore."""
        self.data_store.update_udp_health(health)

    def _on_sensor_data_for_3d(self, buffers: dict) -> None:
        """Cập nhật hướng 3D cho wand viewer."""
        try:
            ax = buffers["ax"][-1] if buffers.get("ax") else 0.0
            ay = buffers["ay"][-1] if buffers.get("ay") else 0.0
            az = buffers["az"][-1] if buffers.get("az") else 1.0
            gx = buffers["gx"][-1] if buffers.get("gx") else 0.0
            gy = buffers["gy"][-1] if buffers.get("gy") else 0.0
            gz = buffers["gz"][-1] if buffers.get("gz") else 0.0
            self.page_home.wand_3d.update_orientation(ax, ay, az, gx, gy, gz)
        except Exception:
            log.debug("MainWindow: Bỏ qua cập nhật 3D", exc_info=True)

    def _on_settings_saved(self, config: dict) -> None:
        """Lưu cấu hình ứng dụng."""
        self.data_store.save_settings(config)
        show_prim = config.get("show_primitives_menu", True)
        self.shell.set_nav_item_visible(1, show_prim)

    def _on_theme_changed(self, theme_name: str) -> None:
        """Làm mới style của tất cả các trang khi theme đổi."""
        log.info("MainWindow: Đang áp dụng theme %s", theme_name)
        for page in self._pages:
            if hasattr(page, "refresh_styles"):
                page.refresh_styles()

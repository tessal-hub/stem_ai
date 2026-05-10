"""
Cửa sổ chính của ứng dụng STEM Spell Book.

Trách nhiệm:
    - Tạo page stack và topbar (MacShell).
    - Sở hữu UdpWorker (nguồn dữ liệu phụ).
    - Chuyển tiếp dữ liệu UDP tới DataStore (cùng pattern với SerialWorker trong Handler).
    KHÔNG xử lý dữ liệu — chỉ chuyển tiếp tới DataStore.
"""

from __future__ import annotations

import logging

from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from ui.mac_shell import MacShell
from ui.asset_utils import resolve_asset_path
from ui.page_home import PageHome
from ui.page_record import PageRecord
from ui.page_statistics import PageStatistics
from ui.page_primitive_collect import PagePrimitiveCollect
from ui.page_wand import PageWand
from ui.page_setting import PageSetting
from logic.udp_worker import UdpWorker

log = logging.getLogger(__name__)

# Các key dùng để trích xuất dữ liệu cảm biến từ payload UDP
_SENSOR_KEYS = ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z")


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng.
    Quản lý navigation giữa các trang, khởi tạo UdpWorker,
    và chuyển tiếp dữ liệu từ các nguồn tới DataStore.
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self.handler: object | None = None
        self._udp_log_count = 0

        self._init_ui()
        self._init_signals()
        self._load_data()

    # ------------------------------------------------------------------
    # Khởi tạo giao diện
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Khởi tạo cửa sổ, tạo các trang và page stack."""
        self.setWindowTitle("STEM Spell Book")
        self.setWindowIcon(QIcon(resolve_asset_path("assets/icon/wand.svg")))
        self.resize(1024, 800)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("QMainWindow { background-color: transparent; }")

        # ── Shell chính ─────────────────────────────────────────────────
        self.shell = MacShell("STEM Spell Book")
        self.setCentralWidget(self.shell)

        # ── Các trang — lưu thành named attrs để truy cập type-safe ────
        self.page_home = PageHome(self.data_store)
        self.page_record = PageRecord(self.data_store)
        self.page_statistics = PageStatistics(self.data_store)
        self.page_primitive_collect = PagePrimitiveCollect(self.data_store)
        self.page_wand = PageWand(self.data_store)
        self.page_setting = PageSetting(self.data_store)

        self._pages: list[QWidget] = [
            self.page_home,
            self.page_record,
            self.page_statistics,
            self.page_primitive_collect,
            self.page_wand,
            self.page_setting,
        ]

        # ── Page stack ──────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")
        for page in self._pages:
            self.stack.addWidget(page)
        self.shell.content_layout.addWidget(self.stack, stretch=1)

        # ── UDP Worker (nguồn dữ liệu phụ) ─────────────────────────────
        self.udp_worker = UdpWorker(port=5555)

    # ------------------------------------------------------------------
    # Kết nối signal/slot
    # ------------------------------------------------------------------

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot của cửa sổ chính."""
        # Navigation
        self.shell.nav_requested.connect(self._on_shell_nav_requested)

        # Settings
        self.page_setting.sig_settings_saved.connect(self._on_settings_saved)

        # UDP Worker
        self.udp_worker.sig_data_received.connect(self._on_udp_data_received)
        self.udp_worker.sig_status_change.connect(self._on_udp_status_changed)
        self.udp_worker.sig_health_update.connect(self._on_udp_health_updated)

        # DataStore → UI
        self.data_store.sig_connection_state_updated.connect(
            self.page_home.set_connection_status
        )
        self.data_store.sig_stats_updated.connect(
            self.page_home.update_manager_stats
        )
        self.data_store.sig_live_features_updated.connect(
            self.page_statistics.update_live_features
        )
        self.data_store.sig_live_buffer_updated.connect(
            self.page_primitive_collect.update_signal_preview
        )
        # Mô phỏng 3D wand: truyền dữ liệu cảm biến real-time tới viewer trang Home
        self.data_store.sig_sensor_data_updated.connect(
            self._on_sensor_data_for_3d
        )

    # ------------------------------------------------------------------
    # Nạp dữ liệu ban đầu
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        """Nạp trạng thái ban đầu và khởi động UDP worker."""
        self._set_page(0)

        # Đồng bộ trạng thái kết nối hiện tại vào UI
        connected, _ = self.data_store.get_connection_state()
        self.page_home.set_connection_status(connected)
        self.page_home.update_manager_stats(self.data_store.system_stats)

        if hasattr(self.data_store, "get_primitive_collection_stats"):
            self.page_primitive_collect.update_collection_stats(
                self.data_store.get_primitive_collection_stats()
            )

        # Khởi động UDP listener
        self.udp_worker.start()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Xử lý sự kiện đóng cửa sổ, dọn dẹp tài nguyên."""
        log.info("Ứng dụng đang đóng.")
        handler = getattr(self, "handler", None)
        if handler is not None:
            try:
                handler.shutdown()
            except Exception as exc:
                log.warning("Handler shutdown trong closeEvent thất bại: %s", exc)
        if self.udp_worker.isRunning():
            self.udp_worker.stop()
        event.accept()

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _set_page(self, index: int) -> None:
        """Chuyển trang hiển thị và cập nhật sidebar active state.

        Args:
            index: Chỉ số trang cần hiển thị.
        """
        self.stack.setCurrentIndex(index)
        self.shell.set_active_index(index)

    def _extract_esp_stats(self, data: dict) -> dict[str, str]:
        """Trích xuất thông tin phần cứng ESP32 từ payload UDP.

        Args:
            data: Payload UDP dạng dict.

        Returns:
            Dict chứa các thông số ESP32 đã format.
        """
        esp_update: dict[str, str] = {}
        if "battery" in data:
            esp_update["Battery"] = f"{data['battery']}%"
        if "free_ram" in data:
            esp_update["RAM Free"] = f"{data['free_ram']} KB"
        if "rssi" in data:
            esp_update["RSSI"] = f"{data['rssi']} dBm"
        return esp_update

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_shell_nav_requested(self, index: int) -> None:
        """Xử lý yêu cầu chuyển trang từ sidebar navigation."""
        self._set_page(index)

    def _on_udp_data_received(self, data: dict) -> None:
        """Chuyển tiếp dữ liệu UDP tới DataStore. Không xử lý tại đây."""
        # Payload cảm biến → DataStore
        if _SENSOR_KEYS[0] in data:
            values = [float(data.get(k, 0.0)) for k in _SENSOR_KEYS]
            self.data_store.update_sensor_data(
                {
                    "ax": values[0],
                    "ay": values[1],
                    "az": values[2],
                    "gx": values[3],
                    "gy": values[4],
                    "gz": values[5],
                }
            )
            if self.page_record.is_live:
                self.data_store.add_live_sample(values)

        # Text thô → terminal wand (throttle để tránh quá tải UI)
        self._udp_log_count += 1
        if self._udp_log_count % 25 == 0:
            self.page_wand.append_terminal_text(f">> UDP: {data}")

        # Thống kê phần cứng → DataStore
        esp_update = self._extract_esp_stats(data)
        if esp_update:
            self.data_store.update_esp_stats(esp_update)

    def _on_udp_status_changed(self, active: bool) -> None:
        """Xử lý thay đổi trạng thái UDP — tách biệt khỏi trạng thái kết nối wand."""
        if active:
            self.page_wand.append_terminal_text(">> UDP telemetry received.")

    def _on_udp_health_updated(self, health: dict) -> None:
        """Cập nhật thống kê sức khỏe kết nối UDP vào DataStore."""
        self.data_store.update_udp_health(health)

    def _on_sensor_data_for_3d(self, buffers: dict) -> None:
        """Truyền mẫu IMU mới nhất tới widget 3D wand trên trang Home."""
        try:
            ax = buffers["ax"][-1] if buffers.get("ax") else 0.0
            ay = buffers["ay"][-1] if buffers.get("ay") else 0.0
            az = buffers["az"][-1] if buffers.get("az") else 1.0
            gx = buffers["gx"][-1] if buffers.get("gx") else 0.0
            gy = buffers["gy"][-1] if buffers.get("gy") else 0.0
            gz = buffers["gz"][-1] if buffers.get("gz") else 0.0
            self.page_home.wand_3d.update_orientation(ax, ay, az, gx, gy, gz)
        except Exception:
            log.debug("Bỏ qua cập nhật hướng 3D", exc_info=True)

    def _on_settings_saved(self, config: dict) -> None:
        """Lưu settings qua DataStore khi người dùng bấm Save."""
        self.data_store.save_settings(config)

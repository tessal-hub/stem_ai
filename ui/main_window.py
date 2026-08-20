"""
ui/main_window.py — Cửa sổ chính của ứng dụng STEM Spell Book.

Trách nhiệm:
    - Quản lý navigation giữa các trang thông qua MacShell.
    - Khởi tạo và điều phối các trang giao diện con (Lazy loading).
    - Sở hữu UdpWorker để thu thập dữ liệu không dây.
    - Chuyển tiếp dữ liệu từ các nguồn tới DataStore.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from logic.udp_worker import UdpWorker
from ui.asset_utils import resolve_asset_path
from ui.i18n_bridge import tr_ui
from config import APP_DATA_DIR
from logic.sound_player import SoundPlayer
from logic.spell_config_store import SpellConfigStore
from ui.mac_shell import MacShell
from ui.page_home import PageHome

log = logging.getLogger(__name__)

# Các key dùng để trích xuất dữ liệu cảm biến từ payload UDP
_SENSOR_KEYS = ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z")


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng.
    Điều phối luồng dữ liệu và quản lý trạng thái hiển thị các trang.
    """

    def __init__(
        self,
        data_store,
        spell_config_store: SpellConfigStore | None = None,
        sound_player: SoundPlayer | None = None,
    ) -> None:
        super().__init__()
        self.data_store = data_store
        self.spell_config_store = spell_config_store or SpellConfigStore(APP_DATA_DIR)
        self.sound_player = sound_player or SoundPlayer(self.spell_config_store)
        self.handler: object | None = None
        self._udp_log_count = 0

        self._page_home = PageHome(self.data_store, spell_config_store=self.spell_config_store)
        self._page_primitive_collect = None
        self._page_record = None
        self._page_wand = None
        self._page_setting = None

        self._init_ui()
        self._init_signals()
        self._load_data()
        self._apply_ui_language()

        # Asynchronously preload secondary pages in idle background time
        QTimer.singleShot(100, self._preload_secondary_pages)
        # Tự động mở Hướng Dẫn cho người mới ở lần khởi động đầu tiên
        QTimer.singleShot(400, self._check_first_run_guide)

    def _check_first_run_guide(self) -> None:
        """Tự động mở Hướng Dẫn cho người dùng mới khi lần đầu mở app."""
        try:
            settings = self.data_store.get_settings_snapshot()
            has_seen = settings.get("has_seen_beginner_guide", False)
            if not has_seen:
                self.data_store.save_settings({"has_seen_beginner_guide": True})
                if hasattr(self, "shell") and hasattr(self.shell, "_open_beginner_guide"):
                    self.shell._open_beginner_guide()
        except Exception as exc:
            log.warning("MainWindow: Check first-run guide encountered error: %s", exc)

    @property
    def page_home(self) -> PageHome:
        return self._page_home

    @property
    def page_primitive_collect(self):
        if self._page_primitive_collect is None:
            from ui.page_primitive_collect import PagePrimitiveCollect
            self._page_primitive_collect = PagePrimitiveCollect(self.data_store)
            self._page_primitive_collect.update_collection_stats(
                self.data_store.get_primitive_collection_stats()
            )
            adv = self._is_advanced_mode()
            self._page_primitive_collect.set_advanced_mode(adv)
            self._replace_stack_page(1, self._page_primitive_collect)
        return self._page_primitive_collect

    @property
    def page_record(self):
        if self._page_record is None:
            from ui.page_record import PageRecord
            self._page_record = PageRecord(
                self.data_store,
                spell_config_store=self.spell_config_store,
                sound_player=self.sound_player,
            )
            self._replace_stack_page(2, self._page_record)
        return self._page_record

    @property
    def page_wand(self):
        if self._page_wand is None:
            from ui.page_wand import PageWand
            self._page_wand = PageWand(self.data_store)
            self._page_wand.sig_settings_saved.connect(self._on_settings_saved)
            adv = self._is_advanced_mode()
            self._page_wand.set_advanced_mode(adv)
            self._replace_stack_page(3, self._page_wand)
        return self._page_wand

    @property
    def page_setting(self):
        if self._page_setting is None:
            from ui.page_setting import PageSetting
            self._page_setting = PageSetting(self.data_store)
            self._page_setting.sig_settings_saved.connect(self._on_settings_saved)
            adv = self._is_advanced_mode()
            self._page_setting.set_advanced_mode(adv)
            self._replace_stack_page(4, self._page_setting)
        return self._page_setting

    def _is_advanced_mode(self) -> bool:
        settings = self.data_store.get_settings_snapshot()
        return bool(settings.get("advanced_mode", settings.get("show_primitives_menu", True)))

    @property
    def _pages(self) -> list[QWidget]:
        pages = [self._page_home]
        for p in (self._page_primitive_collect, self._page_record, self._page_wand, self._page_setting):
            if p is not None:
                pages.append(p)
        return pages

    def _replace_stack_page(self, index: int, widget: QWidget) -> None:
        old = self.stack.widget(index)
        self.stack.removeWidget(old)
        if old is not None:
            old.deleteLater()
        self.stack.insertWidget(index, widget)

    def _preload_secondary_pages(self) -> None:
        """Nạp không đồng bộ các trang phụ ở background idle."""
        try:
            _ = self.page_primitive_collect
            _ = self.page_record
            _ = self.page_wand
            _ = self.page_setting
        except Exception as exc:
            log.warning("MainWindow: Preload secondary pages encountered error: %s", exc)

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục widget."""
        self.setWindowTitle("STEM Spell Book")
        self.setWindowIcon(QIcon(resolve_asset_path("assets/icon/cooliocns SVG/Interface/Book_Open.svg")))
        self.resize(1100, 850)
        self.setMinimumSize(1000, 700)

        # 1. Khởi tạo Shell điều hướng
        self.shell = MacShell("STEM Spell Book")
        self.setCentralWidget(self.shell)

        # 2. Quản lý StackedWidget với page_home + 4 placeholder
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_home)
        for _ in range(4):
            placeholder = QWidget()
            self.stack.addWidget(placeholder)

        self.shell.content_layout.addWidget(self.stack, stretch=1)

        # 3. Worker nền
        self.udp_worker = UdpWorker(port=5555)

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot."""
        # Điều hướng
        self.shell.nav_requested.connect(self._on_shell_nav_requested)

        # Dữ liệu UDP
        self.udp_worker.sig_data_received.connect(self._on_udp_sensor_dispatch, type=Qt.ConnectionType.QueuedConnection)
        self.udp_worker.sig_status_change.connect(self._on_udp_status_changed, type=Qt.ConnectionType.QueuedConnection)
        self.udp_worker.sig_health_update.connect(self._on_udp_health_updated, type=Qt.ConnectionType.QueuedConnection)

        # Cập nhật từ DataStore
        self.data_store.sig_connection_state_updated.connect(self._page_home.set_connection_status)
        self.data_store.sig_primitive_stats_updated.connect(self._on_primitive_stats_updated)

        # Hệ thống
        locale_manager.language_changed.connect(self._apply_ui_language)
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_primitive_stats_updated(self, stats: dict) -> None:
        if self._page_primitive_collect is not None:
            self._page_primitive_collect.update_collection_stats(stats)

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ DataStore."""
        self._set_page(0)

        adv_mode = self._is_advanced_mode()
        self.shell.set_nav_item_visible(1, adv_mode)
        self.shell.set_nav_item_visible(4, adv_mode)

        # Đồng bộ trạng thái kết nối
        is_connected, _ = self.data_store.get_connection_state()
        self._page_home.set_connection_status(is_connected)

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
        """Chuyển đổi trang hiển thị trên stack (trigger lazy load nếu cần)."""
        if index == 1:
            _ = self.page_primitive_collect
        elif index == 2:
            _ = self.page_record
        elif index == 3:
            _ = self.page_wand
        elif index == 4:
            _ = self.page_setting

        self.stack.setCurrentIndex(index)
        self.shell.set_active_index(index)
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
        """Dispatch UDP payload to Handler for standard routing."""
        handler = getattr(self, "handler", None)
        if handler is None:
            return

        sensor_keys = ("accel_x", "accel_y", "accel_z",
                        "gyro_x", "gyro_y", "gyro_z")
        if sensor_keys[0] in data:
            values = [float(data.get(k, 0.0)) for k in sensor_keys]
            handler.on_udp_sensor_data(values)

        esp_update = self._extract_esp_stats(data)
        if esp_update:
            handler.on_udp_esp_stats(esp_update)

        self._udp_log_count += 1
        if self._udp_log_count % 25 == 0 and self._page_wand is not None:
            self.page_wand.append_terminal_text(f">> UDP: {data}")

    def _on_udp_status_changed(self, active: bool) -> None:
        """Thông báo trạng thái kết nối UDP."""
        if active and self._page_wand is not None:
            self.page_wand.append_terminal_text(">> UDP telemetry received.")

    def _on_udp_health_updated(self, health: dict) -> None:
        """Cập nhật sức khỏe kết nối vào DataStore."""
        self.data_store.update_udp_health(health)

    def _on_settings_saved(self, config: dict) -> None:
        """Lưu cấu hình ứng dụng."""
        self.data_store.save_settings(config)
        adv_mode = config.get("advanced_mode", config.get("show_primitives_menu", True))
        self.shell.set_nav_item_visible(1, adv_mode)
        self.shell.set_nav_item_visible(4, adv_mode)

        # Nếu đang ở tab bị ẩn thì tự động chuyển về Wand (tab 3)
        if not adv_mode and self.shell._active_index in (1, 4):
            self.shell.set_active_index(3)
            self._set_page(3)

        if self._page_wand is not None:
            self._page_wand.set_advanced_mode(adv_mode)
            self._page_wand.load_settings(config)
        if self._page_setting is not None:
            self._page_setting.set_advanced_mode(adv_mode)
            self._page_setting.load_settings(config)
        if self._page_primitive_collect is not None:
            self._page_primitive_collect.set_advanced_mode(adv_mode)

    def _on_theme_changed(self, theme_name: str) -> None:
        """Làm mới style của tất cả các trang và shell khi theme đổi."""
        log.info("MainWindow: Đang áp dụng theme %s", theme_name)
        from PyQt6.QtWidgets import QApplication
        from theme import get_modern_stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_modern_stylesheet(theme_name))
        if hasattr(self, "shell") and hasattr(self.shell, "refresh_styles"):
            self.shell.refresh_styles()
        for page in self._pages:
            if hasattr(page, "refresh_styles"):
                page.refresh_styles()

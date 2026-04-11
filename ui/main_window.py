"""
main_window.py — Application shell.

Responsibilities:
    - Creates the page stack and topbar.
    - Owns the UdpWorker (secondary data source).
    - Routes UDP data to DataStore (same pattern as SerialWorker in Handler).
    MUST NOT do any data processing — just relay to DataStore.
"""

from __future__ import annotations

import logging

from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from ui.mac_shell        import MacShell
from ui.page_home        import PageHome
from ui.page_record      import PageRecord
from ui.page_statistics  import PageStatistics
from ui.page_wand        import PageWand
from ui.page_setting     import PageSetting
from logic.udp_worker    import UdpWorker

log = logging.getLogger(__name__)

# Keys used to extract normalised sensor data from a UDP payload.
_SENSOR_KEYS = ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z")


class MainWindow(QMainWindow):
    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store

        self.setWindowTitle("STEM Spell Book")
        self.setWindowIcon(QIcon("assets/icon/wand.svg"))
        self.resize(1024, 800)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("QMainWindow { background-color: transparent; }")

        # ── Central shell ───────────────────────────────────────────────
        self.shell = MacShell("STEM Spell Book")
        self.setCentralWidget(self.shell)

        # ── Pages — stored as named attrs for type-safe access ───────────
        self.page_home       = PageHome(self.data_store)
        self.page_record     = PageRecord(self.data_store)
        self.page_statistics = PageStatistics(self.data_store)
        self.page_wand       = PageWand(self.data_store)
        self.page_setting    = PageSetting(self.data_store)

        self._pages: list[QWidget] = [
            self.page_home,
            self.page_record,
            self.page_statistics,
            self.page_wand,
            self.page_setting,
        ]

        # ── Page stack ───────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")
        for page in self._pages:
            self.stack.addWidget(page)
        self.shell.content_layout.addWidget(self.stack, stretch=1)
        self.shell.nav_requested.connect(self._set_page)

        self._set_page(0)
        self.page_setting.sig_settings_saved.connect(self._on_settings_saved)

        # ── UDP Worker (secondary data source) ───────────────────────────
        self.udp_worker = UdpWorker(port=5555)
        self.udp_worker.sig_data_received.connect(self._on_udp_data)
        self.udp_worker.sig_status_change.connect(self._on_udp_status_change)
        self.udp_worker.sig_health_update.connect(self._on_udp_health_update)
        self.udp_worker.start()

        self.data_store.sig_connection_state_updated.connect(self.page_home.set_connection_status)
        self.data_store.sig_stats_updated.connect(self.page_home.update_manager_stats)
        self.data_store.sig_live_features_updated.connect(self.page_statistics.update_live_features)
        connected, _ = self.data_store.get_connection_state()
        self.page_home.set_connection_status(connected)
        self.page_home.update_manager_stats(self.data_store.system_stats)
        self._udp_log_count = 0

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_udp_data(self, data: dict) -> None:
        """Route incoming UDP JSON to DataStore. No processing here."""
        # Sensor payload → DataStore
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

        # Raw text → Wand terminal (throttled)
        self._udp_log_count += 1
        if self._udp_log_count % 25 == 0:
            self.page_wand.append_terminal_text(f">> UDP: {data}")

        # Hardware stats → DataStore
        esp_update: dict[str, str] = {}
        if "battery" in data:
            esp_update["Battery"] = f"{data['battery']}%"
        if "free_ram" in data:
            esp_update["RAM Free"] = f"{data['free_ram']} KB"
        if "rssi" in data:
            esp_update["RSSI"] = f"{data['rssi']} dBm"
        if esp_update:
            self.data_store.update_esp_stats(esp_update)

    def _on_udp_status_change(self, active: bool) -> None:
        """Keep UDP telemetry separate from wand connection state."""
        if active:
            self.page_wand.append_terminal_text(">> UDP telemetry received.")

    def _on_udp_health_update(self, health: dict) -> None:
        self.data_store.update_udp_health(health)

    def _on_settings_saved(self, config: dict) -> None:
        """Persist settings through DataStore-owned settings store."""
        self.data_store.save_settings(config)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        log.info("Application closing.")
        if self.udp_worker.isRunning():
            self.udp_worker.stop()
        event.accept()

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.shell.set_active_index(index)
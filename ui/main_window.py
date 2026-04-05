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
from PyQt6.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.top_bar          import Topbar, C_PAGE_BG
from ui.page_home        import PageHome
from ui.page_record      import PageRecord
from ui.page_statistics  import PageStatistics
from ui.page_wand        import PageWand
from ui.page_setting     import PageSetting
from logic.udp_worker    import UdpWorker

log = logging.getLogger(__name__)

# Shared page stylesheet — all pages inherit this base.
_PAGE_STYLE = f"""
    QWidget {{
        background-color: {C_PAGE_BG};
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
    QLabel {{ color: #333333; }}
"""

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
        self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")

        # ── Central widget ───────────────────────────────────────────────
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Topbar ───────────────────────────────────────────────────────
        self.topbar = Topbar(self.data_store)

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
        self.stack.setStyleSheet(
            "QStackedWidget { border: none; background: transparent; }"
        )
        for page in self._pages:
            page.setStyleSheet(_PAGE_STYLE)
            self.stack.addWidget(page)

        # ── Assemble ─────────────────────────────────────────────────────
        root_layout.addWidget(self.topbar)
        root_layout.addWidget(self.stack, stretch=1)

        self.topbar.nav_requested.connect(self.stack.setCurrentIndex)

        # ── UDP Worker (secondary data source) ───────────────────────────
        self.udp_worker = UdpWorker(port=5555)
        self.udp_worker.sig_data_received.connect(self._on_udp_data)
        self.udp_worker.sig_status_change.connect(self.page_home.set_connection_status)
        self.udp_worker.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_udp_data(self, data: dict) -> None:
        """Route incoming UDP JSON to DataStore. No processing here."""
        # Sensor payload → DataStore
        if _SENSOR_KEYS[0] in data:
            values = [float(data.get(k, 0)) for k in _SENSOR_KEYS]
            self.data_store.add_sensor_data(values)

        # Raw text → Wand terminal
        self.page_wand.append_terminal_text(f">> UDP: {data}")

        # Hardware stats → DataStore
        esp_update: dict[str, str] = {}
        if "battery" in data:
            esp_update["Battery"] = f"{data['battery']}%"
        if "free_ram" in data:
            esp_update["RAM Free"] = f"{data['free_ram']} KB"
        if esp_update:
            self.data_store.update_esp_stats(esp_update)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        log.info("Application closing.")
        if self.udp_worker.isRunning():
            self.udp_worker.stop()
        event.accept()
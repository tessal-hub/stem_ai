"""
main_window.py — Application shell.

Responsibilities:
    - Creates the page stack and topbar.
    - Owns the UdpWorker (secondary data source).
    - Routes UDP data to DataStore (same pattern as SerialWorker in Handler).
    MUST NOT do any data processing — just relay to DataStore.
"""

from __future__ import annotations

from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.top_bar import Topbar, C_PAGE_BG
from ui.page_home       import PageHome
from ui.page_record     import PageRecord
from ui.page_statistics import PageStatistics
from ui.page_wand       import PageWand
from ui.page_setting    import PageSetting
from logic.udp_worker   import UdpWorker


# Shared page stylesheet — all pages inherit this base.
_PAGE_STYLE = f"""
    QWidget {{
        background-color: {C_PAGE_BG};
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
    QLabel {{
        color: #333333;
    }}
"""


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

        # ── Page stack ───────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(
            "QStackedWidget { border: none; background: transparent; }"
        )

        # Pages are stored in order matching Topbar.MENUS
        self._pages: list[QWidget] = [
            PageHome(self.data_store),
            PageRecord(self.data_store),
            PageStatistics(self.data_store),
            PageWand(self.data_store),
            PageSetting(self.data_store),
        ]
        for page in self._pages:
            page.setStyleSheet(_PAGE_STYLE)
            self.stack.addWidget(page)

        # ── Assemble ─────────────────────────────────────────────────────
        root_layout.addWidget(self.topbar)
        root_layout.addWidget(self.stack, stretch=1)

        self.topbar.nav_requested.connect(self.stack.setCurrentIndex)

        # ── UDP Worker (secondary data source) ───────────────────────────
        # Routes data through DataStore just like SerialWorker does via Handler.
        self.udp_worker = UdpWorker(port=5555)
        self.udp_worker.sig_data_received.connect(self._on_udp_data)
        self.udp_worker.sig_status_change.connect(self.page_home.set_connection_status)
        self.udp_worker.start()

    def _on_udp_data(self, data: dict) -> None:
        """Route incoming UDP JSON to DataStore. No processing here."""
        # Build a 6-element normalized list if sensor keys are present
        if "accel_x" in data:
            values = [
                float(data.get("accel_x", 0)),
                float(data.get("accel_y", 0)),
                float(data.get("accel_z", 0)),
                float(data.get("gyro_x", 0)),
                float(data.get("gyro_y", 0)),
                float(data.get("gyro_z", 0)),
            ]
            self.data_store.add_sensor_data(values)

        # Route raw text to Wand terminal
        self.page_wand.append_terminal_text(f">> UDP: {data}")

        # Update ESP32 hardware stats if present
        if "battery" in data:
            self.data_store.update_esp_stats({"Battery": f"{data['battery']}%"})
        if "free_ram" in data:
            self.data_store.update_esp_stats({"RAM Free": f"{data['free_ram']} KB"})

    # Named convenience properties
    @property
    def page_home(self)       -> PageHome:       return self._pages[0]  # type: ignore[return-value]
    @property
    def page_record(self)     -> PageRecord:     return self._pages[1]  # type: ignore[return-value]
    @property
    def page_statistics(self) -> PageStatistics: return self._pages[2]  # type: ignore[return-value]
    @property
    def page_wand(self)       -> PageWand:       return self._pages[3]  # type: ignore[return-value]
    @property
    def page_setting(self)    -> PageSetting:    return self._pages[4]  # type: ignore[return-value]

    def closeEvent(self, event: QCloseEvent) -> None:
        print("Application is closing…")

        if hasattr(self, 'udp_worker') and self.udp_worker.isRunning():
            self.udp_worker.stop()

        event.accept()
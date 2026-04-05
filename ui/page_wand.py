"""PageWand — Hardware configuration, flashing, and terminal view."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .common_design_tokens import (
    ACCENT, ACCENT_DARK, ACCENT_TEXT,
    BG_LIGHT, BG_WHITE,
    BORDER, BORDER_MID,
    DANGER,
    HOVER_BG,
    PROGRESS_H, BTN_H, TERM_MIN_H,
    RARITY_NONE, RARITY_COM, RARITY_UNC, RARITY_RARE, RARITY_EPIC,
    SUCCESS,
    TERM_BG, TERM_FG,
    TEXT_BODY, TEXT_MUTED,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RarityTier:
    min_count: int
    label:     str
    color:     str


RARITY_TIERS: tuple[RarityTier, ...] = (
    RarityTier(0,   "UNLEARNED", RARITY_NONE),
    RarityTier(10,  "COMMON",    RARITY_COM),
    RarityTier(20,  "UNCOMMON",  RARITY_UNC),
    RarityTier(50,  "RARE",      RARITY_RARE),
    RarityTier(100, "EPIC",      RARITY_EPIC),
)

# ---------------------------------------------------------------------------
# Style constants (module-private)
# ---------------------------------------------------------------------------

_STYLE_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {BG_LIGHT};
        border: 1px solid {BORDER};
        border-top: none;
        border-bottom-left-radius: 14px;
        border-bottom-right-radius: 14px;
    }}
"""
_STYLE_CARD = f"""
    #CardFrame {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
"""
_STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_MID};
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 6px 12px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""
_STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 6px 12px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {BORDER_MID}; color: {TEXT_MUTED}; }}
"""
_STYLE_BTN_SMALL = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {TEXT_MUTED};
        border: 1px solid {BORDER_MID};
        border-radius: 5px;
        font-size: 9px;
        font-weight: bold;
        padding: 2px 8px;
    }}
    QPushButton:hover {{
        background-color: {HOVER_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
"""
_STYLE_TERMINAL = f"""
    QTextEdit {{
        background-color: {TERM_BG};
        color: {TERM_FG};
        border: none;
        border-radius: 8px;
        padding: 10px;
    }}
"""
_STYLE_COMBO = f"""
    QComboBox {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER_MID};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_BODY};
        font-weight: bold;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; }}
"""
_STYLE_PROGRESS = f"""
    QProgressBar {{
        border: 1px solid {BORDER_MID};
        border-radius: 4px;
        text-align: center;
        color: {TEXT_BODY};
        font-weight: bold;
        font-size: 10px;
        background-color: {BG_WHITE};
    }}
    QProgressBar::chunk {{ background-color: {SUCCESS}; border-radius: 3px; }}
"""
_STYLE_LIST = f"""
    QListWidget {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        outline: 0;
    }}
    QListWidget::item {{
        border-bottom: 1px solid {BORDER};
        min-height: 44px;
    }}
    QListWidget::item:hover {{ background-color: {HOVER_BG}; }}
"""
_STYLE_CHECKBOX = f"""
    QCheckBox {{
        color: {TEXT_BODY};
        font-weight: bold;
        font-size: 13px;
    }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 4px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER_MID};
        border-radius: 4px;
    }}
"""
_STYLE_RARITY_BADGE = """
    QLabel {{
        background-color: {color};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 4px 10px;
        font-weight: 900;
        font-size: 10px;
        letter-spacing: 1px;
    }}
"""

_STATUS_STYLE = "color: {color}; font-weight: 800; font-size: 11px;"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _clear_layout(layout: QLayout | None) -> None:
    """Recursively remove and schedule deletion for all items in *layout*."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        if (widget := item.widget()) is not None:
            widget.deleteLater()
        elif (child := item.layout()) is not None:
            _clear_layout(child)
            child.deleteLater()


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class PageWand(QWidget):
    # Serial signals
    sig_serial_scan       = pyqtSignal()
    sig_serial_connect    = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()

    # Bluetooth signals
    sig_bt_scan           = pyqtSignal()
    sig_bt_connect        = pyqtSignal(str)
    sig_bt_disconnect     = pyqtSignal()

    # Tool signals
    sig_flash_compile     = pyqtSignal(list)
    sig_flash_upload      = pyqtSignal()
    sig_term_clear        = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()

        # Connection state flags — source of truth, not button text.
        self._serial_connected = False
        self._bt_connected     = False

        # Maps spell name → checkbox widget only (count is consumed at build time).
        self._spell_checkboxes: dict[str, QCheckBox] = {}

        self._build_ui()
        self._connect_internal_signals()

        # Populate from DataStore snapshot at startup.
        self.load_spell_payload_list(data_store.spell_counts)
        self.update_esp_stats(data_store.esp32_stats)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_terminal_text(self, text: str) -> None:
        self.terminal_output.append(text)
        sb = self.terminal_output.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        self.progress_bar.setValue(max(0, min(100, percentage)))
        if status_text:
            self.lbl_flash_status.setText(f"● {status_text}")

    # ── Serial UI updaters ────────────────────────────────────────────

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        self._serial_connected = connected
        self._set_connection_ui(
            status_label=self.lbl_serial_status,
            connect_btn=self.btn_serial_connect,
            scan_btn=self.btn_serial_scan,
            connected=connected,
            device_label=port_name,
        )

    def update_serial_port_list(self, ports: list[str]) -> None:
        self.combo_serial_ports.clear()
        self.combo_serial_ports.addItems(ports)

    # ── Bluetooth UI updaters ─────────────────────────────────────────

    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        self._bt_connected = connected
        self._set_connection_ui(
            status_label=self.lbl_bt_status,
            connect_btn=self.btn_bt_connect,
            scan_btn=self.btn_bt_scan,
            connected=connected,
            device_label=device_name,
        )

    def update_bt_device_list(self, devices: list[str]) -> None:
        self.combo_bt_devices.clear()
        self.combo_bt_devices.addItems(devices)

    # ── Hardware stats ────────────────────────────────────────────────

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        _clear_layout(self.layout_stats)
        if not stats:
            lbl = QLabel("Awaiting connection…")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-style: italic;")
            self.layout_stats.addWidget(lbl)
            return
        for key, val in stats.items():
            lbl = QLabel(f"■  {key}: {val}")
            lbl.setStyleSheet(f"color: {TEXT_BODY}; font-size: 11px; font-weight: 600;")
            self.layout_stats.addWidget(lbl)

    # ── Spell list ────────────────────────────────────────────────────

    def load_spell_payload_list(self, spell_counts: dict[str, int]) -> None:
        """Refresh both the bar chart and the payload checkbox list."""
        self._update_spell_chart(spell_counts)
        self._update_spell_list(spell_counts)

    # ------------------------------------------------------------------
    # Private helpers — shared logic
    # ------------------------------------------------------------------

    @staticmethod
    def _set_connection_ui(
        status_label: QLabel,
        connect_btn: QPushButton,
        scan_btn: QPushButton,
        connected: bool,
        device_label: str,
    ) -> None:
        """Update status label, connect button text, and scan button state."""
        if connected:
            status_label.setText(f"● CONNECTED: {device_label}")
            status_label.setStyleSheet(_STATUS_STYLE.format(color=SUCCESS))
            connect_btn.setText("DISCONNECT")
            scan_btn.setEnabled(False)
        else:
            status_label.setText("● DISCONNECTED")
            status_label.setStyleSheet(_STATUS_STYLE.format(color=DANGER))
            connect_btn.setText("CONNECT")
            scan_btn.setEnabled(True)

    def _update_spell_chart(self, spell_counts: dict[str, int]) -> None:
        self.stats_plot.clear()

        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_left   = self.stats_plot.getAxis("left")
        ax_left.setPen(TEXT_MUTED)
        ax_bottom.setPen(TEXT_MUTED)

        spells = list(spell_counts.keys())
        counts = list(spell_counts.values())

        if spells:
            bar = pg.BarGraphItem(
                x=np.arange(len(spells)),
                height=counts,
                width=0.6,
                brush=pg.mkBrush(ACCENT),
            )
            self.stats_plot.addItem(bar)
            ax_bottom.setTicks([list(enumerate(spells))])
        else:
            bar = pg.BarGraphItem(x=[0], height=[0], width=0.6, brush=pg.mkBrush(BORDER_MID))
            self.stats_plot.addItem(bar)
            self.stats_plot.setYRange(0, 10)
            ax_bottom.setTicks([[(0, "No data yet")]])

    def _update_spell_list(self, spell_counts: dict[str, int]) -> None:
        self.list_firmware.clear()
        self._spell_checkboxes.clear()

        for name, count in spell_counts.items():
            item   = QListWidgetItem(self.list_firmware)
            widget = QWidget()
            widget.setStyleSheet("background: transparent;")
            row    = QHBoxLayout(widget)
            row.setContentsMargins(12, 4, 12, 4)

            chk = QCheckBox(name)
            chk.setStyleSheet(_STYLE_CHECKBOX)
            self._spell_checkboxes[name] = chk

            rarity = self._resolve_rarity(count)
            badge  = self._make_rarity_badge(rarity.label, rarity.color)

            row.addWidget(chk)
            row.addStretch()
            row.addWidget(badge)

            item.setSizeHint(widget.sizeHint())
            self.list_firmware.setItemWidget(item, widget)

    def _get_checked_spells(self) -> list[str]:
        return [name for name, chk in self._spell_checkboxes.items() if chk.isChecked()]

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(_STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(20, 20, 20, 20)
        inner.setSpacing(16)

        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._build_left_column(),  stretch=12)
        content.addWidget(self._build_right_column(), stretch=10)
        inner.addLayout(content, stretch=1)

        outer.addWidget(self.main_container)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)

        # Flash sub-column
        flash_w = QWidget()
        flash_l = QVBoxLayout(flash_w)
        flash_l.setContentsMargins(0, 0, 0, 0)
        flash_l.setSpacing(8)
        flash_l.addWidget(self._make_section_label("FIRMWARE FLASHER"))
        flash_l.addWidget(self._build_flash_card())
        tools_row.addWidget(flash_w, stretch=1)

        # Connections sub-column
        conn_w = QWidget()
        conn_l = QVBoxLayout(conn_w)
        conn_l.setContentsMargins(0, 0, 0, 0)
        conn_l.setSpacing(8)
        conn_l.addWidget(self._make_section_label("CONNECTION"))
        conn_l.addWidget(self._build_serial_card())
        conn_l.addWidget(self._build_bt_card())
        conn_l.addStretch()
        tools_row.addWidget(conn_w, stretch=1)

        layout.addLayout(tools_row)

        # Terminal header row
        term_row = QHBoxLayout()
        term_row.addWidget(self._make_section_label("UART TERMINAL"))
        term_row.addStretch()
        self.btn_term_clear = QPushButton("CLEAR")
        self.btn_term_clear.setStyleSheet(_STYLE_BTN_SMALL)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        term_row.addWidget(self.btn_term_clear)
        layout.addLayout(term_row)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet(_STYLE_TERMINAL)
        self.terminal_output.setMinimumHeight(TERM_MIN_H)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.terminal_output.setFont(font)
        self.terminal_output.setPlainText(
            ">> WAND TERMINAL INITIALIZED…\n>> WAITING FOR DATA…"
        )
        layout.addWidget(self.terminal_output, stretch=1)

        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._make_section_label("DATASET STATISTICS"))
        layout.addWidget(self._build_stats_graph_card(), stretch=1)

        layout.addWidget(self._make_section_label("FIRMWARE PAYLOAD"))
        self.list_firmware = QListWidget()
        self.list_firmware.setStyleSheet(_STYLE_LIST)
        self.list_firmware.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_firmware, stretch=1)

        return widget

    def _build_flash_card(self) -> QFrame:
        card, layout = self._make_card()

        btn_row = QHBoxLayout()
        self.btn_compile = self._make_btn("COMPILE",     _STYLE_BTN_OUTLINE)
        self.btn_flash   = self._make_btn("FLASH ESP32", _STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_compile)
        btn_row.addWidget(self.btn_flash)
        layout.addLayout(btn_row)

        self.lbl_flash_status = QLabel("● Ready to compile")
        self.lbl_flash_status.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 800;"
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(_STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(PROGRESS_H)
        self.progress_bar.setValue(0)

        layout.addWidget(self.lbl_flash_status)
        layout.addWidget(self.progress_bar)
        return card

    def _build_serial_card(self) -> QFrame:
        card, layout = self._make_card(margins=(12, 12, 12, 12), spacing=8)

        status_row = QHBoxLayout()
        lbl_name = QLabel("SERIAL:")
        lbl_name.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
        self.lbl_serial_status = QLabel("● DISCONNECTED")
        self.lbl_serial_status.setStyleSheet(_STATUS_STYLE.format(color=DANGER))
        status_row.addWidget(lbl_name)
        status_row.addStretch()
        status_row.addWidget(self.lbl_serial_status)
        layout.addLayout(status_row)

        self.combo_serial_ports = QComboBox()
        self.combo_serial_ports.setStyleSheet(_STYLE_COMBO)
        layout.addWidget(self.combo_serial_ports)

        btn_row = QHBoxLayout()
        self.btn_serial_scan    = self._make_btn("SCAN",    _STYLE_BTN_OUTLINE)
        self.btn_serial_connect = self._make_btn("CONNECT", _STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_serial_scan)
        btn_row.addWidget(self.btn_serial_connect)
        layout.addLayout(btn_row)
        return card

    def _build_bt_card(self) -> QFrame:
        card, layout = self._make_card(margins=(12, 12, 12, 12), spacing=8)

        status_row = QHBoxLayout()
        lbl_name = QLabel("BLUETOOTH:")
        lbl_name.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
        self.lbl_bt_status = QLabel("● DISCONNECTED")
        self.lbl_bt_status.setStyleSheet(_STATUS_STYLE.format(color=DANGER))
        status_row.addWidget(lbl_name)
        status_row.addStretch()
        status_row.addWidget(self.lbl_bt_status)
        layout.addLayout(status_row)

        self.combo_bt_devices = QComboBox()
        self.combo_bt_devices.setStyleSheet(_STYLE_COMBO)
        layout.addWidget(self.combo_bt_devices)

        btn_row = QHBoxLayout()
        self.btn_bt_scan    = self._make_btn("SCAN",    _STYLE_BTN_OUTLINE)
        self.btn_bt_connect = self._make_btn("CONNECT", _STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_bt_scan)
        btn_row.addWidget(self.btn_bt_connect)
        layout.addLayout(btn_row)
        return card

    def _build_stats_graph_card(self) -> QFrame:
        card, layout = self._make_card()

        self.layout_stats = QHBoxLayout()
        layout.addLayout(self.layout_stats)

        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setBackground(BG_WHITE)
        self.stats_plot.setMouseEnabled(x=False, y=False)
        self.stats_plot.hideButtons()
        self.stats_plot.showGrid(x=False, y=True, alpha=0.3)

        ax_bottom = self.stats_plot.getAxis("bottom")
        ax_bottom.setPen(TEXT_MUTED)
        ax_bottom.setTextPen(TEXT_BODY)
        ax_bottom.setStyle(tickTextOffset=8)
        self.stats_plot.getAxis("left").setPen(TEXT_MUTED)
        self.stats_plot.getAxis("left").setTextPen(TEXT_BODY)

        layout.addWidget(self.stats_plot, stretch=1)
        return card

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_internal_signals(self) -> None:
        self.btn_term_clear.clicked.connect(self._on_term_clear_clicked)

        self.btn_serial_scan.clicked.connect(self.sig_serial_scan.emit)
        self.btn_serial_connect.clicked.connect(self._on_serial_connect_clicked)

        self.btn_bt_scan.clicked.connect(self.sig_bt_scan.emit)
        self.btn_bt_connect.clicked.connect(self._on_bt_connect_clicked)

        self.btn_compile.clicked.connect(self._on_compile_clicked)
        self.btn_flash.clicked.connect(self.sig_flash_upload.emit)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def _on_term_clear_clicked(self) -> None:
        self.terminal_output.clear()
        self.sig_term_clear.emit()

    def _on_serial_connect_clicked(self) -> None:
        if self._serial_connected:
            self.sig_serial_disconnect.emit()
        else:
            self.sig_serial_connect.emit(self.combo_serial_ports.currentText())

    def _on_bt_connect_clicked(self) -> None:
        if self._bt_connected:
            self.sig_bt_disconnect.emit()
        else:
            self.sig_bt_connect.emit(self.combo_bt_devices.currentText())

    def _on_compile_clicked(self) -> None:
        self.sig_flash_compile.emit(self._get_checked_spells())

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_card(
        margins: tuple[int, int, int, int] = (16, 16, 16, 16),
        spacing: int = 12,
    ) -> tuple[QFrame, QVBoxLayout]:
        """Return a styled card frame together with its configured layout."""
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(_STYLE_CARD)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        return frame, layout

    @staticmethod
    def _make_btn(label: str, style: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(BTN_H)
        btn.setStyleSheet(style)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 900; font-size: 13px; letter-spacing: 1px;"
        )
        return lbl

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(_STYLE_RARITY_BADGE.format(color=color))
        return lbl

    @staticmethod
    def _resolve_rarity(count: int) -> RarityTier:
        """Return the highest tier whose min_count does not exceed *count*."""
        return max(
            (tier for tier in RARITY_TIERS if count >= tier.min_count),
            key=lambda t: t.min_count,
            default=RARITY_TIERS[0],
        )
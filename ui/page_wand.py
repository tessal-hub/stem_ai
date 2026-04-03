"""PageWand — Hardware configuration, flashing, and terminal view."""
from __future__ import annotations
from dataclasses import dataclass
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLayout, 
    QListWidget, QListWidgetItem, QProgressBar, QPushButton, QTextEdit, 
    QVBoxLayout, QWidget
)
import pyqtgraph as pg
import numpy as np

class Colors:
    ACCENT       = "#ff3366"      # Standardized pink accent
    ACCENT_DARK  = "#e62e5c"
    ACCENT_TEXT  = "#ffffff"
    BG_DARK      = "#111827"
    BG_LIGHT     = "#f3f4f6"
    BG_WHITE     = "#ffffff"
    BORDER       = "#e5e7eb"
    BORDER_MID   = "#d1d5db"
    TEXT_BODY    = "#1f2937"
    TEXT_MUTED   = "#6b7280"
    HOVER_BG     = "#fce7ec"
    SUCCESS      = "#10b981"
    DANGER       = "#ef4444"
    TERM_FG      = "#10b981"
    TERM_BG      = "#0d1117"
    RARITY_NONE  = "#9ca3af"
    RARITY_COM   = "#10b981"
    RARITY_UNC   = "#3b82f6"
    RARITY_RARE  = "#8b5cf6"
    RARITY_EPIC  = "#f59e0b"

class Sizes:
    TERM_MIN_H   = 160         
    TERM_MAX_H   = 800         
    BTN_H        = 40
    PROGRESS_H   = 12

@dataclass(frozen=True)
class RarityTier:
    min_count: int
    label:     str
    color:     str

RARITY_TIERS: tuple[RarityTier, ...] = (
    RarityTier(0,   "UNLEARNED", Colors.RARITY_NONE),
    RarityTier(10,  "COMMON",    Colors.RARITY_COM),
    RarityTier(20,  "UNCOMMON",  Colors.RARITY_UNC),
    RarityTier(50,  "RARE",      Colors.RARITY_RARE),
    RarityTier(100, "EPIC",      Colors.RARITY_EPIC),
)

STYLE_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {Colors.BG_LIGHT};
        border: 1px solid {Colors.BORDER};
        border-top: none;
        border-bottom-left-radius: 14px;
        border-bottom-right-radius: 14px;
    }}
"""
STYLE_CARD = f"""
    #CardFrame {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER};
        border-radius: 12px;
    }}
"""
STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {Colors.BG_WHITE};
        color: {Colors.TEXT_BODY};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 6px 12px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background-color: {Colors.HOVER_BG};
        border-color: {Colors.ACCENT};
        color: {Colors.ACCENT};
    }}
"""
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {Colors.ACCENT};
        color: {Colors.ACCENT_TEXT};
        border: none;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
        padding: 6px 12px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{ background-color: {Colors.ACCENT_DARK}; }}
    QPushButton:disabled {{ background-color: {Colors.BORDER_MID}; color: {Colors.TEXT_MUTED}; }}
"""
STYLE_BTN_SMALL = f"""
    QPushButton {{
        background-color: {Colors.BG_WHITE};
        color: {Colors.TEXT_MUTED};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 5px;
        font-size: 9px;
        font-weight: bold;
        padding: 2px 8px;
    }}
    QPushButton:hover {{
        background-color: {Colors.HOVER_BG};
        border-color: {Colors.ACCENT};
        color: {Colors.ACCENT};
    }}
"""
STYLE_TERMINAL = f"""
    QTextEdit {{
        background-color: {Colors.TERM_BG};
        color: {Colors.TERM_FG};
        border: none;
        border-radius: 8px;
        padding: 10px;
    }}
"""
STYLE_COMBO = f"""
    QComboBox {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 8px;
        padding: 6px 10px;
        color: {Colors.TEXT_BODY};
        font-weight: bold;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; }}
"""
STYLE_PROGRESS = f"""
    QProgressBar {{
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 4px;
        text-align: center;
        color: {Colors.TEXT_BODY};
        font-weight: bold;
        font-size: 10px;
        background-color: {Colors.BG_WHITE};
    }}
    QProgressBar::chunk {{ background-color: {Colors.SUCCESS}; border-radius: 3px; }}
"""
STYLE_LIST = f"""
    QListWidget {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER};
        border-radius: 12px;
        outline: 0;
    }}
    QListWidget::item {{
        border-bottom: 1px solid {Colors.BORDER};
        min-height: 44px; 
    }}
    QListWidget::item:hover {{ background-color: {Colors.HOVER_BG}; }}
"""
STYLE_CHECKBOX = f"""
    QCheckBox {{
        color: {Colors.TEXT_BODY};
        font-weight: bold;
        font-size: 13px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {Colors.ACCENT};
        border: 1px solid {Colors.ACCENT};
        border-radius: 4px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 4px;
    }}
"""
STYLE_RARITY_BADGE = """
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

def clear_layout(layout: QLayout | None) -> None:
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0)
        if item is None: continue
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                clear_layout(child)
                child.deleteLater()

class PageWand(QWidget):
    # Serial Signals
    sig_serial_scan       = pyqtSignal()
    sig_serial_connect    = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()
    
    # Bluetooth Signals
    sig_bt_scan           = pyqtSignal()
    sig_bt_connect        = pyqtSignal(str)
    sig_bt_disconnect     = pyqtSignal()
    
    # Tool Signals
    sig_flash_compile     = pyqtSignal(list)
    sig_flash_upload      = pyqtSignal()
    sig_term_clear        = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self._available_checkboxes: dict[str, tuple[QCheckBox, int]] = {}

        self._build_ui()
        self._connect_internal_signals()

        # Initial display from DataStore (read-only snapshot at startup)
        self.load_spell_payload_list(data_store.spell_counts)
        self.update_esp_stats(data_store.esp32_stats)

    def append_terminal_text(self, text: str) -> None:
        self.terminal_output.append(text)
        sb = self.terminal_output.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        self.progress_bar.setValue(max(0, min(100, percentage)))
        if status_text:
            self.lbl_flash_status.setText(f"● {status_text}")

    # --- SERIAL UI UPDATERS ---
    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        if connected:
            self.lbl_serial_status.setText(f"● CONNECTED: {port_name}")
            self.lbl_serial_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: 800; font-size: 11px;")
            self.btn_serial_connect.setText("DISCONNECT")
            self.btn_serial_scan.setEnabled(False)
        else:
            self.lbl_serial_status.setText("● DISCONNECTED")
            self.lbl_serial_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: 800; font-size: 11px;")
            self.btn_serial_connect.setText("CONNECT")
            self.btn_serial_scan.setEnabled(True)

    def update_serial_port_list(self, ports: list[str]) -> None:
        self.combo_serial_ports.clear()
        self.combo_serial_ports.addItems(ports)

    # --- BLUETOOTH UI UPDATERS ---
    def set_bluetooth_status(self, connected: bool, device_name: str = "") -> None:
        if connected:
            self.lbl_bt_status.setText(f"● CONNECTED: {device_name}")
            self.lbl_bt_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: 800; font-size: 11px;")
            self.btn_bt_connect.setText("DISCONNECT")
            self.btn_bt_scan.setEnabled(False)
        else:
            self.lbl_bt_status.setText("● DISCONNECTED")
            self.lbl_bt_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: 800; font-size: 11px;")
            self.btn_bt_connect.setText("CONNECT")
            self.btn_bt_scan.setEnabled(True)

    def update_bt_device_list(self, devices: list[str]) -> None:
        self.combo_bt_devices.clear()
        self.combo_bt_devices.addItems(devices)

    def update_esp_stats(self, stats: dict[str, str]) -> None:
        clear_layout(self.layout_stats)
        if not stats:
            lbl = QLabel("Awaiting connection...")
            lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; font-style: italic;")
            self.layout_stats.addWidget(lbl)
            return

        for key, val in stats.items():
            lbl = QLabel(f"■  {key}: {val}")
            lbl.setStyleSheet(f"color: {Colors.TEXT_BODY}; font-size: 11px; font-weight: 600;")
            self.layout_stats.addWidget(lbl)

    def load_spell_payload_list(self, spell_counts: dict[str, int]) -> None:
        """Update both checkboxes and the statistics bar chart."""
        self.list_firmware.clear()
        self._available_checkboxes.clear()

        # 1. Plot the bar graph
        spells = list(spell_counts.keys())
        counts = list(spell_counts.values())
        
        self.stats_plot.clear()
        
        ax_bottom = self.stats_plot.getAxis('bottom')
        ax_left = self.stats_plot.getAxis('left')
        ax_left.setPen(Colors.TEXT_MUTED)
        ax_bottom.setPen(Colors.TEXT_MUTED)

        if not spells:
            bg = pg.BarGraphItem(x=[0], height=[0], width=0.6, brush=pg.mkBrush(Colors.BORDER_MID))
            self.stats_plot.addItem(bg)
            self.stats_plot.setYRange(0, 10)
            ax_bottom.setTicks([[(0, "No data yet")]])
        else:
            bg = pg.BarGraphItem(x=np.arange(len(spells)), height=counts, width=0.6, brush=pg.mkBrush(Colors.ACCENT))
            self.stats_plot.addItem(bg)
            ax_bottom.setTicks([list(enumerate(spells))])

        # 2. Update Payload Spells list
        for name, count in spell_counts.items():
            item = QListWidgetItem(self.list_firmware)
            widget = QWidget()
            widget.setStyleSheet("background: transparent;")
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(12, 4, 12, 4)

            chk = QCheckBox(name)
            chk.setStyleSheet(STYLE_CHECKBOX)
            self._available_checkboxes[name] = (chk, count)

            rarity = self._resolve_rarity(count)
            badge = self._make_rarity_badge(rarity.label, rarity.color)

            layout.addWidget(chk)
            layout.addStretch()
            layout.addWidget(badge)

            item.setSizeHint(widget.sizeHint())
            self.list_firmware.setItemWidget(item, widget)

    # ── UI Construction ──────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(20, 20, 20, 20)
        inner.setSpacing(16)

        # 2-Column Core Layout
        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._build_left_column(), stretch=12) # Slightly wider left
        content.addWidget(self._build_right_column(), stretch=10)
        
        inner.addLayout(content, stretch=1)
        outer.addWidget(self.main_container)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Tools Row (Flash + Connections)
        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)

        # Flash Card
        flash_w = QWidget()
        flash_l = QVBoxLayout(flash_w)
        flash_l.setContentsMargins(0,0,0,0)
        flash_l.setSpacing(8)
        flash_l.addWidget(self._make_section_label("FIRMWARE FLASHER"))
        flash_l.addWidget(self._build_flash_card())
        tools_row.addWidget(flash_w, stretch=1)

        # Connections Column (Serial + BT)
        conn_w = QWidget()
        conn_l = QVBoxLayout(conn_w)
        conn_l.setContentsMargins(0,0,0,0)
        conn_l.setSpacing(8)
        
        conn_l.addWidget(self._make_section_label("CONNECTION"))
        conn_l.addWidget(self._build_serial_card())
        conn_l.addWidget(self._build_bt_card())
        conn_l.addStretch()
        tools_row.addWidget(conn_w, stretch=1)

        layout.addLayout(tools_row)

        # UART Terminal
        term_label_row = QHBoxLayout()
        term_label_row.addWidget(self._make_section_label("UART TERMINAL"))
        term_label_row.addStretch()
        self.btn_term_clear = QPushButton("CLEAR")
        self.btn_term_clear.setStyleSheet(STYLE_BTN_SMALL)
        self.btn_term_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        term_label_row.addWidget(self.btn_term_clear)
        layout.addLayout(term_label_row)

        term = QTextEdit()
        term.setReadOnly(True)
        term.setStyleSheet(STYLE_TERMINAL)
        term.setMinimumHeight(Sizes.TERM_MIN_H)
        
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        term.setFont(font)
        term.setPlainText(">> WAND TERMINAL INITIALIZED...\n>> WAITING FOR DATA...")
        self.terminal_output = term
        
        layout.addWidget(term, stretch=1)
        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Dataset Statistics (Graph + ESP Stats)
        layout.addWidget(self._make_section_label("DATASET STATISTICS"))
        layout.addWidget(self._build_stats_graph_card(), stretch=1)

        # Available Spells Checkboxes
        layout.addWidget(self._make_section_label("FIRMWARE PAYLOAD"))
        self.list_firmware = QListWidget()
        self.list_firmware.setStyleSheet(STYLE_LIST)
        self.list_firmware.setSelectionMode(QListWidget.SelectionMode.NoSelection) 
        layout.addWidget(self.list_firmware, stretch=1)

        return widget

    def _build_flash_card(self) -> QFrame:
        card = self._make_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        btn_row = QHBoxLayout()
        self.btn_compile = self._make_btn("COMPILE", STYLE_BTN_OUTLINE)
        self.btn_flash   = self._make_btn("FLASH ESP32", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_compile)
        btn_row.addWidget(self.btn_flash)
        layout.addLayout(btn_row)

        self.lbl_flash_status = QLabel("● Ready to compile")
        self.lbl_flash_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; font-weight: 800;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(Sizes.PROGRESS_H)
        self.progress_bar.setValue(0)

        layout.addWidget(self.lbl_flash_status)
        layout.addWidget(self.progress_bar)
        return card

    def _build_serial_card(self) -> QFrame:
        card = self._make_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.lbl_serial_status = QLabel("● DISCONNECTED")
        self.lbl_serial_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: 800; font-size: 11px;")
        status_row.addWidget(QLabel("SERIAL:", styleSheet=f"color: {Colors.TEXT_BODY}; font-weight: bold; font-size: 11px;"))
        status_row.addStretch()
        status_row.addWidget(self.lbl_serial_status)
        layout.addLayout(status_row)

        self.combo_serial_ports = QComboBox()
        self.combo_serial_ports.setStyleSheet(STYLE_COMBO)
        layout.addWidget(self.combo_serial_ports)

        btn_row = QHBoxLayout()
        self.btn_serial_scan    = self._make_btn("SCAN",    STYLE_BTN_OUTLINE)
        self.btn_serial_connect = self._make_btn("CONNECT", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_serial_scan)
        btn_row.addWidget(self.btn_serial_connect)
        layout.addLayout(btn_row)
        return card

    def _build_bt_card(self) -> QFrame:
        card = self._make_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.lbl_bt_status = QLabel("● DISCONNECTED")
        self.lbl_bt_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: 800; font-size: 11px;")
        status_row.addWidget(QLabel("BLUETOOTH:", styleSheet=f"color: {Colors.TEXT_BODY}; font-weight: bold; font-size: 11px;"))
        status_row.addStretch()
        status_row.addWidget(self.lbl_bt_status)
        layout.addLayout(status_row)

        self.combo_bt_devices = QComboBox()
        self.combo_bt_devices.setStyleSheet(STYLE_COMBO)
        layout.addWidget(self.combo_bt_devices)

        btn_row = QHBoxLayout()
        self.btn_bt_scan    = self._make_btn("SCAN",    STYLE_BTN_OUTLINE)
        self.btn_bt_connect = self._make_btn("CONNECT", STYLE_BTN_PRIMARY)
        btn_row.addWidget(self.btn_bt_scan)
        btn_row.addWidget(self.btn_bt_connect)
        layout.addLayout(btn_row)
        return card

    def _build_stats_graph_card(self) -> QFrame:
        card = self._make_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Top row: Hardware ESP Status (Optional info text)
        self.layout_stats = QHBoxLayout()
        layout.addLayout(self.layout_stats)

        # Graph Plot Widget
        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setBackground(Colors.BG_WHITE)
        self.stats_plot.setMouseEnabled(x=False, y=False)
        self.stats_plot.hideButtons()
        self.stats_plot.showGrid(x=False, y=True, alpha=0.3)
        
        # Clean axes
        ax_bottom = self.stats_plot.getAxis('bottom')
        ax_bottom.setPen(Colors.TEXT_MUTED)
        ax_bottom.setTextPen(Colors.TEXT_BODY)
        ax_bottom.setStyle(tickTextOffset=8)
        
        ax_left = self.stats_plot.getAxis('left')
        ax_left.setPen(Colors.TEXT_MUTED)
        ax_left.setTextPen(Colors.TEXT_BODY)
        
        layout.addWidget(self.stats_plot, stretch=1)
        return card

    @staticmethod
    def _make_card_frame() -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_CARD)
        return frame

    @staticmethod
    def _make_btn(label: str, style: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(Sizes.BTN_H)
        btn.setStyleSheet(style)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_BODY}; font-weight: 900; font-size: 13px; letter-spacing: 1px;")
        return lbl

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(STYLE_RARITY_BADGE.format(color=color))
        return lbl

    @staticmethod
    def _resolve_rarity(count: int) -> RarityTier:
        result = RARITY_TIERS[0]
        for tier in RARITY_TIERS:
            if count >= tier.min_count:
                result = tier
        return result

    def _connect_internal_signals(self) -> None:
        self.btn_term_clear.clicked.connect(self.terminal_output.clear)
        self.btn_term_clear.clicked.connect(lambda checked: self.sig_term_clear.emit())
        
        # Connect Serial buttons
        self.btn_serial_scan.clicked.connect(lambda checked: self.sig_serial_scan.emit())
        self.btn_serial_connect.clicked.connect(self._on_serial_connect_clicked)
        
        # Connect BT buttons
        self.btn_bt_scan.clicked.connect(lambda checked: self.sig_bt_scan.emit())
        self.btn_bt_connect.clicked.connect(self._on_bt_connect_clicked)
        
        # Connect Flash buttons
        self.btn_compile.clicked.connect(self._on_compile_clicked)
        self.btn_flash.clicked.connect(lambda checked: self.sig_flash_upload.emit())

    def _on_serial_connect_clicked(self) -> None:
        if self.btn_serial_connect.text() == "CONNECT":
            self.sig_serial_connect.emit(self.combo_serial_ports.currentText())
        else:
            self.sig_serial_disconnect.emit()

    def _on_bt_connect_clicked(self) -> None:
        if self.btn_bt_connect.text() == "CONNECT":
            self.sig_bt_connect.emit(self.combo_bt_devices.currentText())
        else:
            self.sig_bt_disconnect.emit()

    def _on_compile_clicked(self) -> None:
        self.sig_flash_compile.emit(self._get_checked_spells())

    def _get_checked_spells(self) -> list[str]:
        return [name for name, (chk, _) in self._available_checkboxes.items() if chk.isChecked()]
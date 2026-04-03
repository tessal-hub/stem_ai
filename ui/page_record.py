"""
PageRecord — Timeline and recording view with LIVE Plotting, 3D Wand, & Snipping.

Architecture compliance (SKILL.md §2A):
    - This file is PURE VIEW. No data processing, no direct DataStore calls.
    - Receives plot data via update_plot_data(buffer_snapshot) called by Handler.
    - Emits sig_data_cropped(list, str) with 6D data + spell name for Handler to save.
    - Emits sig_spell_selected(str) when user clicks a spell.
    - MUST NOT import anything from /logic.
"""
from __future__ import annotations
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)


class Colors:
    ACCENT       = "#ff3366"
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
    WARNING      = "#f59e0b"
    GRAPH_LINE_1 = "#00d4ff"
    GRAPH_LINE_2 = "#00ff88"
    CROP_REGION  = "#ff336644"


class Sizes:
    BTN_H       = 44          # Tăng kích thước nút
    RIGHT_MAX_W = 320


# ── Stylesheets ─────────────────────────────────────────────────────────

STYLE_MAIN_CONTAINER = (
    f"#MainBox {{ background-color: {Colors.BG_WHITE}; "
    f"border: 1px solid {Colors.BORDER}; border-top: none; "
    f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
)
STYLE_CARD = (
    f"#CardFrame {{ background-color: {Colors.BG_LIGHT}; "
    f"border: none; border-radius: 8px; }}"
)
STYLE_BTN_BASE = (
    f"QPushButton {{ background-color: {Colors.BG_WHITE}; "
    f"border: 1px solid {Colors.BORDER_MID}; border-radius: 8px; "
    f"font-size: 13px; font-weight: bold; padding: 8px 12px; "
    f"min-width: 70px; }} "
    f"QPushButton:hover {{ background-color: {Colors.HOVER_BG}; "
    f"border-color: {Colors.ACCENT}; }}"
)
STYLE_BTN_START = STYLE_BTN_BASE + f" QPushButton {{ color: {Colors.SUCCESS}; }}"
STYLE_BTN_STOP  = STYLE_BTN_BASE + f" QPushButton {{ color: {Colors.DANGER};  }}"
STYLE_BTN_SNIP  = (
    STYLE_BTN_BASE +
    f" QPushButton {{ color: {Colors.ACCENT}; background-color: {Colors.HOVER_BG}; "
    f"border-color: {Colors.ACCENT}; }}"
)
STYLE_BTN_BACK  = STYLE_BTN_BASE + f" QPushButton {{ color: {Colors.TEXT_BODY}; }}"
STYLE_LIST = (
    f"QListWidget {{ background-color: {Colors.BG_LIGHT}; border: none; "
    f"border-radius: 8px; outline: 0; }} "
    f"QListWidget::item {{ padding: 12px; border-bottom: 1px solid {Colors.BORDER}; "
    f"color: {Colors.TEXT_BODY}; font-weight: 500; }} "
    f"QListWidget::item:selected {{ background-color: {Colors.ACCENT}; "
    f"color: {Colors.ACCENT_TEXT}; border-radius: 6px; }} "
    f"QListWidget::item:hover:!selected {{ background-color: {Colors.HOVER_BG}; "
    f"border-radius: 6px; }}"
)
STYLE_CHECKBOX = (
    f"QCheckBox {{ color: {Colors.TEXT_BODY}; font-weight: bold; font-size: 11px; }} "
    f"QCheckBox::indicator:checked {{ background-color: {Colors.ACCENT}; "
    f"border: 1px solid {Colors.ACCENT}; border-radius: 3px; }}"
)
STYLE_COMBO = (
    f"QComboBox {{ background-color: {Colors.BG_WHITE}; "
    f"border: 1px solid {Colors.BORDER_MID}; border-radius: 6px; "
    f"padding: 6px 10px; color: {Colors.TEXT_BODY}; "
    f"font-weight: bold; font-size: 12px; min-height: 28px; }} "
    f"QComboBox::drop-down {{ border: none; }}"
)


# ════════════════════════════════════════════════════════════════════════
#  PageRecord
# ════════════════════════════════════════════════════════════════════════

class PageRecord(QWidget):
    """Recording page: live plots, 3D wand, snip tool, spell library."""

    # ── Outbound signals (consumed by Handler) ──────────────────────────
    sig_start_record   = pyqtSignal()
    sig_stop_record    = pyqtSignal()
    sig_snip_record    = pyqtSignal()
    sig_sample_opened  = pyqtSignal(str)
    sig_sample_deleted = pyqtSignal(str)
    sig_data_cropped   = pyqtSignal(list, str)  # (6D data, spell_name)
    sig_spell_selected = pyqtSignal(str)        # spell name when user clicks

    # Widget type hints
    btn_start: QPushButton
    btn_stop:  QPushButton
    btn_snip:  QPushButton

    def __init__(self, data_store) -> None:
        super().__init__()
        # Initial spell list (read-only snapshot at startup)
        self._initial_spell_list = data_store.get_spell_list()

        self.is_live: bool = True
        self.current_spell_name: str = ""

        # Latest buffer snapshot received from DataStore via Handler signal
        self._plot_buffer: list[list[float]] = []

        self._build_ui()
        self._setup_plots()
        self._connect_internal_signals()

        # Populate spell combo and list
        self.load_spell_list(self._initial_spell_list)

    # ── Public methods (called by Handler via signals/slots) ────────────

    def update_plot_data(self, buffer_snapshot: list) -> None:
        """Receive latest sensor buffer snapshot from DataStore signal."""
        if self.is_live:
            self._plot_buffer = buffer_snapshot

    def set_wand_ready(self, is_ready: bool) -> None:
        if is_ready:
            self.lbl_wand_status.setText("● WAND IS READY")
            self.lbl_wand_status.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: bold; font-size: 12px;"
            )
        else:
            self.lbl_wand_status.setText("● WAND NOT READY")
            self.lbl_wand_status.setStyleSheet(
                f"color: {Colors.DANGER}; font-weight: bold; font-size: 12px;"
            )

    def set_recording_state(self, recording: bool) -> None:
        self.btn_start.setEnabled(not recording)
        self.btn_stop.setEnabled(recording)
        status = "● RECORDING" if recording else "● WAND IS READY"
        color  = Colors.ACCENT if recording else Colors.SUCCESS
        self.lbl_wand_status.setText(status)
        self.lbl_wand_status.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
        )

    def set_save_status(self, spell_name: str) -> None:
        """Visual feedback after a successful crop-save."""
        self.lbl_wand_status.setText(f"✔ SAVED TO {spell_name}")
        self.lbl_wand_status.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-weight: bold; font-size: 12px;"
        )

    def load_spell_list(self, spells: list[str]) -> None:
        self.spell_list.clear()
        self.spell_list.addItems(spells)
        # Also update the spell combo box
        current_text = self.combo_spell.currentText()
        self.combo_spell.clear()
        self.combo_spell.addItems(spells)
        if current_text:
            idx = self.combo_spell.findText(current_text)
            if idx >= 0:
                self.combo_spell.setCurrentIndex(idx)

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        self.current_spell_name = spell_name
        self.lbl_current_spell.setText(f"SAMPLES: {spell_name}")
        self.sample_list.clear()
        self.sample_list.addItems(samples)
        self.stacked_spells.setCurrentIndex(1)

    # ── Plot Setup & Rendering ──────────────────────────────────────────

    def _setup_plots(self) -> None:
        for plot in [self.graph1, self.graph2]:
            plot.setBackground(Colors.BG_DARK)
            plot.showGrid(x=True, y=True, alpha=0.1)
            plot.getAxis("left").setPen(Colors.TEXT_MUTED)
            plot.getAxis("bottom").setPen(Colors.TEXT_MUTED)
            plot.setMenuEnabled(False)
            plot.setMouseEnabled(x=False, y=True)

        # Graph 1: Motion (aX + gX overlaid)
        self.curve_ax = self.graph1.plot(pen=pg.mkPen(Colors.GRAPH_LINE_1, width=2))
        self.curve_gx = self.graph1.plot(pen=pg.mkPen(Colors.GRAPH_LINE_2, width=2))

        # Graph 2: Reserved for MIC (future feature)
        self.curve_mic = self.graph2.plot(pen=pg.mkPen(Colors.WARNING, width=2))

        # Crop region overlay on graph1 — LARGER handles for easier drag
        self.crop_region = pg.LinearRegionItem(
            [30, 120],
            brush=Colors.CROP_REGION,
        )
        self.crop_region.setZValue(10)
        # Make handles bigger and more visible
        for handle in self.crop_region.lines:
            handle.setPen(pg.mkPen(Colors.ACCENT, width=3))
            handle.setHoverPen(pg.mkPen("#ffffff", width=4))
        self.crop_region.hide()
        self.graph1.addItem(self.crop_region)

    def _render_plots(self) -> None:
        """Timer callback (~60 FPS). Pure display — no data processing."""
        if not self._plot_buffer:
            return

        if self.is_live:
            # Extract columns for plotting (view-only, no mutation)
            ax_data = [row[0] for row in self._plot_buffer]
            gx_data = [row[3] for row in self._plot_buffer]

            if self.graph1.isVisible():
                self.curve_ax.setData(ax_data)
                self.curve_gx.setData(gx_data)



    # ── Toolbar Actions ─────────────────────────────────────────────────

    def _on_start(self) -> None:
        """START: Resume live plotting, hide crop region."""
        self.is_live = True
        self.crop_region.hide()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snip.setEnabled(False)
        self.lbl_wand_status.setText("● PLOTTING LIVE DATA")
        self.lbl_wand_status.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-weight: bold; font-size: 12px;"
        )
        self.sig_start_record.emit()

    def _on_stop(self) -> None:
        """STOP: Freeze plot, show crop region for user to select data."""
        self.is_live = False
        self.crop_region.show()
        # Set region to cover full buffer
        buf_len = len(self._plot_buffer)
        if buf_len > 0:
            self.crop_region.setRegion([0, buf_len])
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(True)
        self.lbl_wand_status.setText("● STOPPED — Drag handles to select data, then SNIP")
        self.lbl_wand_status.setStyleSheet(
            f"color: {Colors.WARNING}; font-weight: bold; font-size: 13px;"
        )
        self.sig_stop_record.emit()

    def _on_snip(self) -> None:
        """SNIP: Cut the selected region and emit with spell name."""
        if not self.crop_region.isVisible():
            return

        # Get spell name from combo
        spell_name = self.combo_spell.currentText().strip()
        if not spell_name:
            self.lbl_wand_status.setText("⚠ Enter a spell name first!")
            self.lbl_wand_status.setStyleSheet(
                f"color: {Colors.DANGER}; font-weight: bold; font-size: 13px;"
            )
            return

        region = self.crop_region.getRegion()
        min_x, max_x = float(region[0]), float(region[1])

        buf = self._plot_buffer
        min_idx = max(0, int(min_x))
        max_idx = min(len(buf), int(max_x))

        if min_idx < max_idx:
            cropped_6d = buf[min_idx:max_idx]
            self.sig_data_cropped.emit(cropped_6d, spell_name)
            self.lbl_wand_status.setText(
                f"✂ Snipped {max_idx - min_idx} samples → {spell_name}"
            )
            self.lbl_wand_status.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: bold; font-size: 13px;"
            )
        else:
            self.lbl_wand_status.setText("⚠ Invalid selection range")
            self.lbl_wand_status.setStyleSheet(
                f"color: {Colors.DANGER}; font-weight: bold; font-size: 13px;"
            )

        self.sig_snip_record.emit()

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(12)

        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=2)
        inner.addLayout(content)
        outer.addWidget(self.main_container)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Status row
        top_row = QHBoxLayout()
        self.lbl_wand_status = QLabel("● WAITING FOR SERIAL")
        self.lbl_wand_status.setStyleSheet(
            f"color: {Colors.WARNING}; font-weight: bold; font-size: 12px;"
        )
        lbl_timeline = self._make_section_label("TIMELINE:")
        lbl_timeline.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self.lbl_wand_status)
        top_row.addWidget(lbl_timeline)
        layout.addLayout(top_row)

        # Graph card
        graph_card = QFrame()
        graph_card.setObjectName("CardFrame")
        graph_card.setStyleSheet(
            f"#CardFrame {{ background-color: {Colors.BG_DARK}; border-radius: 8px; }}"
        )
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(6, 6, 6, 6)
        graph_layout.setSpacing(8)
        self.graph1 = pg.PlotWidget()
        self.graph2 = pg.PlotWidget()
        self.graph2.hide()
        graph_layout.addWidget(self.graph1)
        graph_layout.addWidget(self.graph2)
        layout.addWidget(graph_card, stretch=1)

        # Checkboxes row
        bottom_row = QHBoxLayout()
        self.chk_graph1 = self._make_checkbox("SHOW MOTION (aX, gX)", checked=True)
        self.chk_graph2 = self._make_checkbox("SHOW AUDIO (MIC)", checked=False)
        bottom_row.addWidget(self.chk_graph1)
        bottom_row.addWidget(self.chk_graph2)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(Sizes.RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._make_section_label("TOOLBAR"))

        # ── Controls card ──────────────────────────────────────────
        controls_card = self._make_card_frame()
        ctrl_layout = QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        # Spell name selector (editable combo)
        lbl_spell = QLabel("SPELL LABEL:")
        lbl_spell.setStyleSheet(
            f"color: {Colors.ACCENT}; font-weight: 900; font-size: 11px; "
            f"letter-spacing: 1px;"
        )
        self.combo_spell = QComboBox()
        self.combo_spell.setEditable(True)
        self.combo_spell.setStyleSheet(STYLE_COMBO)
        self.combo_spell.setPlaceholderText("Type or select spell name...")
        ctrl_layout.addWidget(lbl_spell)
        ctrl_layout.addWidget(self.combo_spell)

        # Buttons: START | STOP | SNIP
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_start = self._make_btn("▶ START", STYLE_BTN_START, Sizes.BTN_H)
        self.btn_stop  = self._make_btn("■ STOP",  STYLE_BTN_STOP,  Sizes.BTN_H)
        self.btn_snip  = self._make_btn("✂ SNIP",  STYLE_BTN_SNIP,  Sizes.BTN_H)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(False)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_snip)
        ctrl_layout.addLayout(btn_row)

        # Hint
        lbl_hint = QLabel("START → plot live   |   STOP → freeze & drag   |   SNIP → save")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        ctrl_layout.addWidget(lbl_hint)

        layout.addWidget(controls_card)

        # ── Spell list stack ───────────────────────────────────────
        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_spell_list_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)

        return widget

    def _build_spell_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._make_section_label("SPELL LIBRARY", accent=False))
        self.spell_list = QListWidget()
        self.spell_list.setStyleSheet(STYLE_LIST)
        layout.addWidget(self.spell_list)
        return page

    def _build_sample_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        top_row = QHBoxLayout()
        self.btn_back_spells = self._make_btn("◀ BACK", STYLE_BTN_BACK, 36)
        self.lbl_current_spell = QLabel("SAMPLES: …")
        self.lbl_current_spell.setStyleSheet(
            f"color: {Colors.ACCENT}; font-weight: bold; font-size: 11px;"
        )
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_LIST)
        layout.addWidget(self.sample_list)
        return page

    # ── Internal Signal Wiring ──────────────────────────────────────────

    def _connect_internal_signals(self) -> None:
        # Toolbar buttons
        self.btn_start.clicked.connect(lambda: self._on_start())
        self.btn_stop.clicked.connect(lambda: self._on_stop())
        self.btn_snip.clicked.connect(lambda: self._on_snip())

        # Graph visibility toggles
        self.chk_graph1.toggled.connect(self.graph1.setVisible)
        self.chk_graph2.toggled.connect(self.graph2.setVisible)

        # Spell list navigation
        self.btn_back_spells.clicked.connect(
            lambda: self.stacked_spells.setCurrentIndex(0)
        )
        self.spell_list.itemClicked.connect(
            lambda item: self.sig_spell_selected.emit(item.text())
        )

        # Plot refresh timer — 60 FPS
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._render_plots)
        self._plot_timer.start(16)  # ~60 FPS

    # ── Static helpers ──────────────────────────────────────────────────

    @staticmethod
    def _make_card_frame() -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_CARD)
        return frame

    @staticmethod
    def _make_btn(label: str, style: str, height: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(height)
        btn.setStyleSheet(style)
        return btn

    @staticmethod
    def _make_section_label(text: str, accent: bool = True) -> QLabel:
        lbl = QLabel(text)
        color = Colors.ACCENT if accent else Colors.TEXT_BODY
        lbl.setStyleSheet(
            f"color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
        )
        return lbl

    @staticmethod
    def _make_checkbox(label: str, *, checked: bool = False) -> QCheckBox:
        chk = QCheckBox(label)
        chk.setChecked(checked)
        chk.setStyleSheet(STYLE_CHECKBOX)
        return chk
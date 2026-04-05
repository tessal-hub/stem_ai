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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QTime
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QListWidget, QMessageBox, QPushButton, QLineEdit, QStackedWidget, QVBoxLayout, QWidget,
)
from .common_design_tokens import *


STYLE_MAIN_CONTAINER = (
    f"#MainBox {{ background-color: {BG_WHITE}; "
    f"border: 1px solid {BORDER}; border-top: none; "
    f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
)
STYLE_CARD = (
    f"#CardFrame {{ background-color: {BG_LIGHT}; "
    f"border: none; border-radius: 8px; }}"
)
STYLE_BTN_BASE = (
    f"QPushButton {{ background-color: {BG_WHITE}; "
    f"border: 1px solid {BORDER_MID}; border-radius: 8px; "
    f"font-size: 13px; font-weight: bold; padding: 8px 12px; "
    f"min-width: 70px; }} "
    f"QPushButton:hover {{ background-color: {HOVER_BG}; "
    f"border-color: {ACCENT}; }}"
)
STYLE_BTN_START = STYLE_BTN_BASE + f" QPushButton {{ color: {SUCCESS}; }}"
STYLE_BTN_STOP  = STYLE_BTN_BASE + f" QPushButton {{ color: {DANGER};  }}"
STYLE_BTN_SNIP  = (
    STYLE_BTN_BASE +
    f" QPushButton {{ color: {ACCENT}; background-color: {HOVER_BG}; "
    f"border-color: {ACCENT}; }}"
)
STYLE_BTN_BACK  = STYLE_BTN_BASE + f" QPushButton {{ color: {TEXT_BODY}; }}"
STYLE_LIST = (
    f"QListWidget {{ background-color: {BG_LIGHT}; border: none; "
    f"border-radius: 8px; outline: 0; }} "
    f"QListWidget::item {{ padding: 12px; border-bottom: 1px solid {BORDER}; "
    f"color: {TEXT_BODY}; font-weight: 500; }} "
    f"QListWidget::item:selected {{ background-color: {ACCENT}; "
    f"color: {ACCENT_TEXT}; border-radius: 6px; }} "
    f"QListWidget::item:hover:!selected {{ background-color: {HOVER_BG}; "
    f"border-radius: 6px; }}"
)
STYLE_CHECKBOX = (
    f"QCheckBox {{ color: {TEXT_BODY}; font-weight: bold; font-size: 11px; }} "
    f"QCheckBox::indicator:checked {{ background-color: {ACCENT}; "
    f"border: 1px solid {ACCENT}; border-radius: 3px; }}"
)
STYLE_COMBO = (
    f"QComboBox {{ background-color: {BG_WHITE}; "
    f"border: 1px solid {BORDER_MID}; border-radius: 6px; "
    f"padding: 6px 10px; color: {TEXT_BODY}; "
    f"font-weight: bold; font-size: 12px; min-height: 28px; }} "
    f"QComboBox::drop-down {{ border: none; }}"
)


# ════════════════════════════════════════════════════════════════════════
#  PageRecord
# ════════════════════════════════════════════════════════════════════════

class PageRecord(QWidget):
    """Recording page: live plots, 3D wand, snip tool, spell library."""

    # ── Outbound signals (consumed by Handler) ──────────────────────────
    sig_start_record   = pyqtSignal(str)
    sig_stop_record    = pyqtSignal()
    sig_snip_record    = pyqtSignal()
    sig_sample_opened  = pyqtSignal(str)
    sig_sample_deleted = pyqtSignal(str)
    sig_data_cropped   = pyqtSignal(list, str)  # (6D data, spell_name)
    sig_spell_selected = pyqtSignal(str)        # spell name when user clicks
    sig_spell_deleted  = pyqtSignal(str)        # spell name when user deletes

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

        # Recording timer for duration tracking
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self._update_recording_duration)
        self.recording_start_time = QTime()

        # Latest buffer snapshot received from DataStore via Handler signal
        self._plot_buffer: list[list[float]] = []

        self._build_ui()
        self._setup_plots()
        self._connect_internal_signals()
        
        print("[PageRecord] Initialized - is_live=True, QTimer started for plot rendering")

        # Populate spell combo and list
        self.load_spell_list(self._initial_spell_list)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts for recording actions."""
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_start.isEnabled():
                self._on_start()
        elif event.key() == Qt.Key.Key_T and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_stop.isEnabled():
                self._on_stop()
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_snip.isEnabled():
                self._on_snip()
        else:
            super().keyPressEvent(event)

    # ── Public methods (called by Handler via signals/slots) ────────────

    def update_plot_data(self, buffer_snapshot: list) -> None:
        """Receive latest sensor buffer snapshot from DataStore signal."""
        if self.is_live:
            self._plot_buffer = buffer_snapshot
            if len(buffer_snapshot) > 0:
                print(f"[PageRecord.update_plot_data] Received {len(buffer_snapshot)} samples, latest: {buffer_snapshot[-1]}")

    def set_wand_ready(self, is_ready: bool) -> None:
        if is_ready:
            self.lbl_wand_status.setText("● WAND IS READY")
            self.lbl_wand_status.setStyleSheet(
                f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
            )
        else:
            self.lbl_wand_status.setText("● WAND NOT READY")
            self.lbl_wand_status.setStyleSheet(
                f"color: {DANGER}; font-weight: bold; font-size: 12px;"
            )

    def set_recording_state(self, recording: bool) -> None:
        self.btn_start.setEnabled(not recording)
        self.btn_stop.setEnabled(recording)
        self.edit_action_name.setEnabled(not recording)
        self.combo_spell.setEnabled(not recording)

        status = "● RECORDING" if recording else "● WAND IS READY"
        color = ACCENT if recording else SUCCESS
        self.lbl_wand_status.setText(status)
        self.lbl_wand_status.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
        )

    def _update_recording_duration(self) -> None:
        """Update the recording duration display."""
        if self.recording_timer.isActive():
            elapsed = self.recording_start_time.elapsed()
            minutes = elapsed // 60000
            seconds = (elapsed % 60000) // 1000
            self.lbl_record_duration.setText(f"Duration: {minutes:02d}:{seconds:02d}")

    def update_record_count(self, count: int) -> None:
        """Update the recording sample count display."""
        if self.is_live:
            self.lbl_record_count.setText(f"Recorded: {count}")
        # When not live, _on_crop_region_changed handles the display

    def set_save_status(self, spell_name: str) -> None:
        """Visual feedback after a successful crop-save."""
        self.lbl_wand_status.setText(f"✔ SAVED TO {spell_name}")
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
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
        print("[PageRecord._setup_plots] Starting plot setup...")
        for plot in [self.graph1, self.graph2]:
            plot.setBackground(BG_DARK)
            plot.showGrid(x=True, y=True, alpha=0.1)
            plot.getAxis("left").setPen(TEXT_MUTED)
            plot.getAxis("bottom").setPen(TEXT_MUTED)
            plot.setMenuEnabled(False)
            plot.setMouseEnabled(x=False, y=True)

        # Graph 1: Acceleration Axes (aX, aY, aZ)
        self.curve_ax = self.graph1.plot(pen=pg.mkPen("#ff5555", width=2), name="aX")   # Red
        self.curve_ay = self.graph1.plot(pen=pg.mkPen("#55ff55", width=2), name="aY")   # Green
        self.curve_az = self.graph1.plot(pen=pg.mkPen("#5555ff", width=2), name="aZ")   # Blue

        # Graph 2: Gyroscope Axes (gX, gY, gZ)
        self.curve_gx = self.graph2.plot(pen=pg.mkPen("#ff00ff", width=2), name="gX")   # Magenta
        self.curve_gy = self.graph2.plot(pen=pg.mkPen("#00ffff", width=2), name="gY")   # Cyan
        self.curve_gz = self.graph2.plot(pen=pg.mkPen("#ffff00", width=2), name="gZ")   # Yellow

        print(f"[PageRecord._setup_plots] Created 6 curves: ax={self.curve_ax}, ay={self.curve_ay}, az={self.curve_az}, gx={self.curve_gx}, gy={self.curve_gy}, gz={self.curve_gz}")

        # Add legend to both graphs
        self.graph1.addLegend()
        self.graph2.addLegend()
        
        # Set Y-axis labels
        self.graph1.setLabel('left', 'Acceleration (g)', color=TEXT_BODY)
        self.graph1.setLabel('bottom', 'Time (samples)', color=TEXT_BODY)
        self.graph2.setLabel('left', 'Gyroscope (rad/s)', color=TEXT_BODY)
        self.graph2.setLabel('bottom', 'Time (samples)', color=TEXT_BODY)

        # Crop region overlay on graph1 — LARGER handles for easier drag
        self.crop_region = pg.LinearRegionItem(
            [30, 120],
            brush=CROP_REGION,
        )
        self.crop_region.setZValue(10)
        # Make handles bigger and more visible
        for handle in self.crop_region.lines:
            handle.setPen(pg.mkPen(ACCENT, width=3))
            handle.setHoverPen(pg.mkPen("#ffffff", width=4))
        self.crop_region.hide()
        self.crop_region.sigRegionChanged.connect(self._on_crop_region_changed)
        self.graph1.addItem(self.crop_region)
        print("[PageRecord._setup_plots] Plot setup complete!")

    def _on_crop_region_changed(self) -> None:
        """Update the sample count display when crop region changes."""
        if not self.crop_region.isVisible():
            return
        
        region = self.crop_region.getRegion()
        min_x = int(region[0])
        max_x = int(region[1])
        sample_count = max(0, max_x - min_x)
        
        self.lbl_record_count.setText(f"Selected: {sample_count} samples")

    def _render_plots(self) -> None:
        """Timer callback (~60 FPS). Pure display — no data processing."""
        if not self._plot_buffer or len(self._plot_buffer) == 0:
            return  # Guard against empty buffer

        if not self.is_live:
            return  # Guard: only render during live recording

        try:
            # Extract all 6 columns for plotting (view-only, no mutation)
            # Buffer format: [ax, ay, az, gx, gy, gz]
            ax_data = [row[0] for row in self._plot_buffer]
            ay_data = [row[1] for row in self._plot_buffer]
            az_data = [row[2] for row in self._plot_buffer]
            gx_data = [row[3] for row in self._plot_buffer]
            gy_data = [row[4] for row in self._plot_buffer]
            gz_data = [row[5] for row in self._plot_buffer]

            # Update accel curves (graph1)
            if self.graph1.isVisible() and len(ax_data) > 0:
                self.curve_ax.setData(ax_data)
                self.curve_ay.setData(ay_data)
                self.curve_az.setData(az_data)

            # Update gyro curves (graph2)
            if self.graph2.isVisible() and len(gx_data) > 0:
                self.curve_gx.setData(gx_data)
                self.curve_gy.setData(gy_data)
                self.curve_gz.setData(gz_data)
            
            if len(self._plot_buffer) % 50 == 0:  # Print every 50 samples (~1 second)
                print(f"[PageRecord._render_plots] Rendering {len(self._plot_buffer)} samples")
        except Exception as e:
            print(f"[ERROR] _render_plots failed: {type(e).__name__}: {e}")



    # ── Toolbar Actions ─────────────────────────────────────────────────

    def _on_start(self) -> None:
        """START: Begin recording and send command to device."""
        label_name = self.edit_action_name.text().strip() or self.combo_spell.currentText().strip()
        if not label_name:
            self.lbl_wand_status.setText("⚠ Enter action name first")
            self.lbl_wand_status.setStyleSheet(
                f"color: {DANGER}; font-weight: bold; font-size: 13px;"
            )
            return

        self.is_live = True
        self.crop_region.hide()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snip.setEnabled(False)
        self.edit_action_name.setEnabled(False)
        self.combo_spell.setEnabled(False)
        self.lbl_wand_status.setText("● RECORDING DATA")
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
        )
        
        # Start recording timer
        self.recording_start_time.start()
        self.recording_timer.start(1000)  # Update every second
        
        self.sig_start_record.emit(label_name)

    def _on_stop(self) -> None:
        """STOP: cease recording buffer and finalize file."""
        self.is_live = False
        self.crop_region.show()
        
        # Auto-select a reasonable crop region (last 2 seconds of data, or full if shorter)
        buf_len = len(self._plot_buffer)
        if buf_len > 0:
            # Aim for last 2 seconds (assuming 50Hz = 100 samples/second)
            crop_start = max(0, buf_len - 200)
            self.crop_region.setRegion([crop_start, buf_len])
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(True)
        self.edit_action_name.setEnabled(True)
        self.combo_spell.setEnabled(True)

        self.lbl_wand_status.setText("● RECORDING STOPPED - Select region to snip")
        self.lbl_wand_status.setStyleSheet(
            f"color: {WARNING}; font-weight: bold; font-size: 13px;"
        )
        
        # Stop recording timer
        self.recording_timer.stop()
        self.lbl_record_duration.setText("Duration: 00:00")
        
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
                f"color: {DANGER}; font-weight: bold; font-size: 13px;"
            )
            return

        region = self.crop_region.getRegion()
        if len(region) < 2:
            self.lbl_wand_status.setText("⚠ Invalid crop region")
            self.lbl_wand_status.setStyleSheet(
                f"color: {DANGER}; font-weight: bold; font-size: 13px;"
            )
            return

        def _to_float(val):
            if isinstance(val, (list, tuple)) and val:
                val = val[0]
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                elif isinstance(val, str) and val.replace('.', '').replace('-', '').isdigit():
                    return float(val)
                else:
                    return 0.0
            except Exception:
                return 0.0

        min_x = _to_float(region[0])
        max_x = _to_float(region[1])

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
                f"color: {SUCCESS}; font-weight: bold; font-size: 13px;"
            )
        else:
            self.lbl_wand_status.setText("⚠ Invalid selection range")
            self.lbl_wand_status.setStyleSheet(
                f"color: {DANGER}; font-weight: bold; font-size: 13px;"
            )

        self.sig_snip_record.emit()

    def _zoom_in(self) -> None:
        """Zoom in on both plots."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().scaleBy((0.8, 0.8))

    def _zoom_out(self) -> None:
        """Zoom out on both plots."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().scaleBy((1.25, 1.25))

    def _zoom_fit(self) -> None:
        """Fit both plots to show all data."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().autoRange()

    def _on_delete_spell(self) -> None:
        """Handle spell deletion with 2-step verification."""
        # Get selected spell
        current_item = self.spell_list.currentItem()
        if not current_item:
            QMessageBox.critical(self, "No Selection", "Please select a spell to delete from the list.")
            return

        spell_name = current_item.text()
        
        # First confirmation dialog
        reply1 = QMessageBox.question(
            self, 
            "Delete Spell - Step 1", 
            f"Are you sure you want to delete the spell '{spell_name}'?\n\n"
            "This will permanently remove all training samples for this spell.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply1 != QMessageBox.StandardButton.Yes:
            return
            
        # Second confirmation dialog
        reply2 = QMessageBox.warning(
            self, 
            "Delete Spell - Step 2", 
            f"FINAL CONFIRMATION:\n\n"
            f"You are about to delete '{spell_name}' and ALL its training data.\n\n"
            "This action CANNOT be undone!\n\n"
            "Click YES to confirm deletion:",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply2 == QMessageBox.StandardButton.Yes:
            self.sig_spell_deleted.emit(spell_name)

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
            f"color: {WARNING}; font-weight: bold; font-size: 12px;"
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
            f"#CardFrame {{ background-color: {BG_DARK}; border-radius: 8px; }}"
        )
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(6, 6, 6, 6)
        graph_layout.setSpacing(8)
        self.graph1 = pg.PlotWidget()
        self.graph2 = pg.PlotWidget()
        graph_layout.addWidget(self.graph1)
        graph_layout.addWidget(self.graph2, stretch=1)
        layout.addWidget(graph_card, stretch=1)

        # Checkboxes row
        bottom_row = QHBoxLayout()
        self.chk_graph1 = self._make_checkbox("SHOW ACCEL (aX, aY, aZ)", checked=True)
        self.chk_graph2 = self._make_checkbox("SHOW GYRO (gX, gY, gZ)", checked=True)
        
        # Add zoom controls
        self.btn_zoom_in = self._make_btn("🔍+", STYLE_BTN_BASE, 32)
        self.btn_zoom_out = self._make_btn("🔍-", STYLE_BTN_BASE, 32)
        self.btn_zoom_fit = self._make_btn("🔍□", STYLE_BTN_BASE, 32)
        self.btn_zoom_in.setToolTip("Zoom in on plots")
        self.btn_zoom_out.setToolTip("Zoom out on plots")
        self.btn_zoom_fit.setToolTip("Fit plots to data")
        
        bottom_row.addWidget(self.chk_graph1)
        bottom_row.addWidget(self.chk_graph2)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_zoom_in)
        bottom_row.addWidget(self.btn_zoom_out)
        bottom_row.addWidget(self.btn_zoom_fit)
        layout.addLayout(bottom_row)

        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._make_section_label("TOOLBAR"))

        # Action Name / Record Counter
        lbl_action = QLabel("ACTION NAME:")
        lbl_action.setStyleSheet(
            f"color: {ACCENT}; font-weight: 900; font-size: 11px; letter-spacing: 1px;"
        )
        self.edit_action_name = QLineEdit()
        self.edit_action_name.setStyleSheet(STYLE_COMBO)
        self.edit_action_name.setPlaceholderText("Type a spell/action name...")

        self.lbl_record_count = QLabel("Recorded: 0")
        self.lbl_record_count.setStyleSheet(
            f"color: {TEXT_MUTED}; font-weight: 800; font-size: 11px;"
        )
        
        # Add recording duration display
        self.lbl_record_duration = QLabel("Duration: 00:00")
        self.lbl_record_duration.setStyleSheet(
            f"color: {TEXT_MUTED}; font-weight: 800; font-size: 11px;"
        )

        layout.addWidget(lbl_action)
        layout.addWidget(self.edit_action_name)
        layout.addWidget(self.lbl_record_count)
        layout.addWidget(self.lbl_record_duration)

        # ── Controls card ──────────────────────────────────────────
        controls_card = self._make_card_frame()
        ctrl_layout = QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        # Spell name selector (editable combo)
        lbl_spell = QLabel("SPELL LABEL:")
        lbl_spell.setStyleSheet(
            f"color: {ACCENT}; font-weight: 900; font-size: 11px; "
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
        self.btn_start = self._make_btn("▶ START", STYLE_BTN_START, BTN_H)
        self.btn_stop  = self._make_btn("■ STOP",  STYLE_BTN_STOP,  BTN_H)
        self.btn_snip  = self._make_btn("✂ SNIP",  STYLE_BTN_SNIP,  BTN_H)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(False)
        
        # Add tooltips for better UX
        self.btn_start.setToolTip("Start recording sensor data for the selected spell")
        self.btn_stop.setToolTip("Stop recording and enable cropping/snipping")
        self.btn_snip.setToolTip("Save the selected region as a training sample")
        
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_snip)
        ctrl_layout.addLayout(btn_row)

        # Hint
        lbl_hint = QLabel("START → plot live (Ctrl+S)  |  STOP → freeze & drag (Ctrl+T)  |  SNIP → save (Ctrl+X)")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
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
        
        # Spell list
        self.spell_list = QListWidget()
        self.spell_list.setStyleSheet(STYLE_LIST)
        layout.addWidget(self.spell_list)
        
        # Delete button at bottom
        self.btn_delete_spell = self._make_btn("DELETE SPELL", STYLE_BTN_BASE + f" QPushButton {{ color: {DANGER}; }}", 36)
        self.btn_delete_spell.setToolTip("Delete selected spell")
        layout.addWidget(self.btn_delete_spell)
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
            f"color: {ACCENT}; font-weight: bold; font-size: 11px;"
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
        
        # Zoom controls
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)

        # Spell list navigation
        self.btn_back_spells.clicked.connect(
            lambda: self.stacked_spells.setCurrentIndex(0)
        )
        self.spell_list.itemClicked.connect(
            lambda item: self.sig_spell_selected.emit(item.text())
        )
        self.btn_delete_spell.clicked.connect(self._on_delete_spell)

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
        color = ACCENT if accent else TEXT_BODY
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
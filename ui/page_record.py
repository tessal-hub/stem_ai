"""
PageRecord — Timeline and recording view with LIVE Plotting, 3D Wand, & Snipping.

Architecture compliance (SKILL.md §2A):
    - This file is PURE VIEW. No data processing, no direct DataStore calls.
    - Receives plot data via update_plot_data(buffer_snapshot) called by Handler.
    - Emits sig_data_cropped(list, str, str) with 6D data + spell name + tag for Handler to save.
    - Emits sig_spell_selected(str) when user clicks a spell.
    - MUST NOT import anything from /logic.
"""
from __future__ import annotations
import logging
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QTime
from PyQt6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QListWidget, QMessageBox, QPushButton, QLineEdit, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)
from ui.tokens import (
    # Colors, Sizes
    BG_WHITE, BG_LIGHT, BG_DARK, BORDER, BORDER_MID, TEXT_BODY, TEXT_MUTED, ACCENT, ACCENT_TEXT, 
    HOVER_BG, SUCCESS, DANGER, WARNING, BTN_H, RIGHT_MAX_W, CROP_REGION,
    PLOT_AX_COLOR, PLOT_AY_COLOR, PLOT_AZ_COLOR,
    PLOT_GX_COLOR, PLOT_GY_COLOR, PLOT_GZ_COLOR, PLOT_HANDLE_HOVER_COLOR,
    # Styles (page-specific)
    STYLE_RECORD_MAIN_CONTAINER,
    STYLE_RECORD_GRAPH_CARD,
    STYLE_BTN_BASE,
    STYLE_BTN_START,
    STYLE_BTN_STOP,
    STYLE_BTN_SNIP,
    STYLE_BTN_BACK,
    STYLE_RECORD_LIST,
    STYLE_RECORD_COMBO,
)
from ui.component_factory import (
    make_card_frame,
    make_button,
    make_section_label,
    make_checkbox,
    make_hint,
)
from ui.confirm_dialog import confirm_destructive
from ui.mac_material import apply_soft_shadow
from ui.modern_layout import (
    create_modern_card,
    add_card_shadow,
    MARGIN_COMFORTABLE,
    MARGIN_STANDARD,
    SPACING_MD,
    SPACING_LG,
    SPACING_SM,
)

log = logging.getLogger(__name__)


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
    sig_data_cropped   = pyqtSignal(list, str, str)  # (6D data, spell_name, tag)
    sig_spell_selected = pyqtSignal(str)        # spell name when user clicks
    sig_spell_deleted  = pyqtSignal(str)        # spell name when user deletes
    sig_clear_buffer   = pyqtSignal()           # clear recorded samples
    sig_export_csv     = pyqtSignal()           # export samples to CSV

    # Widget type hints
    btn_start: QPushButton
    btn_stop:  QPushButton
    btn_snip:  QPushButton

    def __init__(self, data_store) -> None:
        super().__init__()
        self.store = data_store
        # Initial spell list (read-only snapshot at startup)
        self._initial_spell_list = data_store.get_spell_list()

        self.is_live: bool = True
        self.current_spell_name: str = ""

        # Recording timer for duration tracking
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self._update_recording_duration)
        self.recording_start_time = QTime()

        self._build_ui()
        self._setup_plots()
        self._connect_internal_signals()
        self._configure_accessibility()
        
        log.debug("[PageRecord] Initialized - is_live=True, QTimer started for plot rendering")

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
            if len(buffer_snapshot) > 0:
                log.debug(
                    "[PageRecord.update_plot_data] Received %d samples, latest: %s",
                    len(buffer_snapshot),
                    buffer_snapshot[-1],
                )

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
        self.combo_spell.setEnabled(not recording)
        self.edit_tag.setEnabled(not recording)

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
            self.lbl_record_duration.setText(f"{minutes:02d}:{seconds:02d}")

    def update_record_count(self, count: int) -> None:
        """Update the recording sample count display."""
        if self.is_live:
            self.lbl_record_count.setText(str(count))
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
        log.debug("[PageRecord._setup_plots] Starting plot setup...")
        for plot in [self.graph1, self.graph2]:
            plot.setBackground(BG_DARK)
            plot.showGrid(x=True, y=True, alpha=0.1)
            plot.getAxis("left").setPen(TEXT_MUTED)
            plot.getAxis("bottom").setPen(TEXT_MUTED)
            plot.setMenuEnabled(False)
            plot.setMouseEnabled(x=False, y=True)
            plot_item = plot.getPlotItem()
            plot_item.setClipToView(True)
            plot_item.setDownsampling(auto=True, mode="peak")

        # Graph 1: Acceleration Axes (aX, aY, aZ)
        self.curve_ax = self.graph1.plot(pen=pg.mkPen(PLOT_AX_COLOR, width=2), name="aX")
        self.curve_ay = self.graph1.plot(pen=pg.mkPen(PLOT_AY_COLOR, width=2), name="aY")
        self.curve_az = self.graph1.plot(pen=pg.mkPen(PLOT_AZ_COLOR, width=2), name="aZ")

        # Graph 2: Gyroscope Axes (gX, gY, gZ)
        self.curve_gx = self.graph2.plot(pen=pg.mkPen(PLOT_GX_COLOR, width=2), name="gX")
        self.curve_gy = self.graph2.plot(pen=pg.mkPen(PLOT_GY_COLOR, width=2), name="gY")
        self.curve_gz = self.graph2.plot(pen=pg.mkPen(PLOT_GZ_COLOR, width=2), name="gZ")

        log.debug(
            "[PageRecord._setup_plots] Created 6 curves: ax=%s, ay=%s, az=%s, gx=%s, gy=%s, gz=%s",
            self.curve_ax,
            self.curve_ay,
            self.curve_az,
            self.curve_gx,
            self.curve_gy,
            self.curve_gz,
        )

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
            handle.setHoverPen(pg.mkPen(PLOT_HANDLE_HOVER_COLOR, width=4))
        self.crop_region.hide()
        self.crop_region.sigRegionChanged.connect(self._on_crop_region_changed)
        self.graph1.addItem(self.crop_region)
        log.debug("[PageRecord._setup_plots] Plot setup complete!")

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
        """Timer callback (~30 FPS). Pure display — no data processing.

        Uses numpy column-slicing instead of per-column list comprehensions to
        extract the six signal axes from the snapshot in a single pass.  The
        widget visibility guard ensures no work is done when the page is hidden.
        """
        # Skip rendering when this widget is not visible (e.g. user is on a
        # different page) to avoid doing unnecessary GPU/CPU work.
        if not self.isVisible():
            return

        if not self.is_live:
            return  # Guard: only render during live recording

        plot_buffer = self.store.get_live_buffer_snapshot()
        if not plot_buffer:
            return  # Guard against empty buffer

        try:
            # Single numpy conversion — avoids 6× list comprehensions over
            # potentially 500 rows (≈30 000 Python object accesses/second at 60 fps).
            arr = np.asarray(plot_buffer, dtype=np.float32)
            if arr.ndim != 2 or arr.shape[1] < 6:
                return

            # Update accel curves (graph1)
            if self.graph1.isVisible():
                self.curve_ax.setData(arr[:, 0])
                self.curve_ay.setData(arr[:, 1])
                self.curve_az.setData(arr[:, 2])

            # Update gyro curves (graph2)
            if self.graph2.isVisible():
                self.curve_gx.setData(arr[:, 3])
                self.curve_gy.setData(arr[:, 4])
                self.curve_gz.setData(arr[:, 5])

            if len(plot_buffer) % 50 == 0:  # Print every 50 samples (~1 second)
                log.debug("[PageRecord._render_plots] Rendering %d samples", len(plot_buffer))
        except Exception as e:
            log.warning("_render_plots failed: %s: %s", type(e).__name__, e)



    # ── Toolbar Actions ─────────────────────────────────────────────────

    def _on_start(self) -> None:
        """START: Begin recording and send command to device."""
        spell_name = self.combo_spell.currentText().strip()
        if not spell_name:
            self.lbl_wand_status.setText("⚠ Select a spell first")
            self.lbl_wand_status.setStyleSheet(
                f"color: {DANGER}; font-weight: bold; font-size: 13px;"
            )
            return

        self.is_live = True
        self.crop_region.hide()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snip.setEnabled(False)
        self.combo_spell.setEnabled(False)
        self.lbl_wand_status.setText("● RECORDING DATA")
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
        )
        
        # Start recording timer
        self.recording_start_time.start()
        self.recording_timer.start(1000)  # Update every second
        
        self.sig_start_record.emit(spell_name)

    def _on_stop(self) -> None:
        """STOP: cease recording buffer and finalize file."""
        self.is_live = False
        self.crop_region.show()
        
        # Auto-select a reasonable crop region (last 2 seconds of data, or full if shorter)
        buf_len = len(self.store.get_live_buffer_snapshot())
        if buf_len > 0:
            # Aim for last 2 seconds (assuming 50Hz = 100 samples/second)
            crop_start = max(0, buf_len - 200)
            self.crop_region.setRegion([crop_start, buf_len])
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(True)
        self.combo_spell.setEnabled(True)

        self.lbl_wand_status.setText("● RECORDING STOPPED - Select region to snip")
        self.lbl_wand_status.setStyleSheet(
            f"color: {WARNING}; font-weight: bold; font-size: 13px;"
        )
        
        # Stop recording timer
        self.recording_timer.stop()
        self.lbl_record_duration.setText("00:00")
        
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

        buf = self.store.get_live_buffer_snapshot()
        min_idx = max(0, int(min_x))
        max_idx = min(len(buf), int(max_x))

        if min_idx < max_idx:
            cropped_6d = buf[min_idx:max_idx]
            tag = self.edit_tag.text().strip()
            self.sig_data_cropped.emit(cropped_6d, spell_name, tag)
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

    def _on_clear_samples(self) -> None:
        """Clear all recorded samples from current buffer."""
        if not confirm_destructive(
            self,
            title="Clear Recorded Samples",
            message="Clear all currently recorded samples?\n\nThis action cannot be undone.",
            confirm_text="Clear All",
            cancel_text="Keep Samples",
        ):
            return
        
        # Emit signal to Handler for actual clearing
        self.sig_clear_buffer.emit()
        # Update UI
        self.lbl_record_count.setText("0")
        self.crop_region.setRegion([30, 120])
        self.is_live = True
        self.crop_region.hide()
        self.lbl_wand_status.setText("✔ Recording buffer cleared")
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
        )

    def _on_export_csv(self) -> None:
        """Export current recorded samples to CSV file."""
        buf = self.store.get_live_buffer_snapshot()
        if not buf or len(buf) == 0:
            self.lbl_wand_status.setText("⚠ No samples to export")
            self.lbl_wand_status.setStyleSheet(
                f"color: {WARNING}; font-weight: bold; font-size: 12px;"
            )
            return
        
        # Emit signal to Handler for actual export
        self.sig_export_csv.emit()
        sample_count = len(buf)
        self.lbl_wand_status.setText(f"💾 Exporting {sample_count} samples...")
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
        )
        self.lbl_wand_status.setStyleSheet(
            f"color: {SUCCESS}; font-weight: bold; font-size: 12px;"
        )

    def _on_spell_list_clicked(self, item) -> None:
        """Handle spell list item click: auto-select spell in combo and emit signal."""
        spell_name = item.text()
        # Auto-select in combo box
        idx = self.combo_spell.findText(spell_name)
        if idx >= 0:
            self.combo_spell.setCurrentIndex(idx)
        # Emit signal for handler
        self.sig_spell_selected.emit(spell_name)

    def _on_delete_spell(self) -> None:
        """Handle spell deletion with 2-step verification."""
        # Get selected spell
        current_item = self.spell_list.currentItem()
        if not current_item:
            QMessageBox.critical(self, "No Selection", "Please select a spell to delete from the list.")
            return

        spell_name = current_item.text()
        
        # First confirmation dialog
        if not confirm_destructive(
            self,
            title="Delete Spell - Step 1",
            message=(
                f"Delete the spell '{spell_name}' and its training samples?\n\n"
                "This removes the item from the visible library and prepares the final check."
            ),
            confirm_text="Continue",
            cancel_text="Keep Spell",
        ):
            return

        if confirm_destructive(
            self,
            title="Delete Spell - Step 2",
            message=(
                f"Final check: delete '{spell_name}' and all training data?\n\n"
                "This action cannot be recovered."
            ),
            confirm_text="Delete Spell",
            cancel_text="Cancel",
        ):
            self.sig_spell_deleted.emit(spell_name)

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setFrameShape(QFrame.Shape.NoFrame)
        self.main_container.setFrameShadow(QFrame.Shadow.Plain)
        self.main_container.setStyleSheet(STYLE_RECORD_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        # Use modern breathing room: 16px margins and 12px spacing
        inner.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        inner.setSpacing(SPACING_LG)

        content = QHBoxLayout()
        # Increased spacing between columns
        content.setSpacing(SPACING_LG)
        content.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=2)
        inner.addLayout(content)
        outer.addWidget(self.main_container)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        # Status row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(SPACING_MD)
        self.lbl_wand_status = QLabel("● WAITING FOR SERIAL")
        self.lbl_wand_status.setStyleSheet(
            f"color: {WARNING}; font-weight: bold; font-size: 12px;"
        )
        lbl_timeline = make_section_label("TIMELINE:", accent_color=ACCENT)
        lbl_timeline.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self.lbl_wand_status)
        top_row.addWidget(lbl_timeline)
        layout.addLayout(top_row)

        # Graph card - modern card with shadow
        graph_card = QFrame()
        graph_card.setObjectName("CardFrame")
        graph_card.setStyleSheet(STYLE_RECORD_GRAPH_CARD)
        # Add drop shadow for elevation
        add_card_shadow(graph_card, blur_radius=16, offset_y=4, color="rgba(0, 0, 0, 0.12)")
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD)
        graph_layout.setSpacing(SPACING_MD)
        self.graph1 = pg.PlotWidget()
        self.graph2 = pg.PlotWidget()
        self.graph1.setMinimumHeight(150)
        self.graph2.setMinimumHeight(150)
        graph_layout.addWidget(self.graph1)
        graph_layout.addWidget(self.graph2, stretch=1)
        layout.addWidget(graph_card, stretch=1)

        # Checkboxes row
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(SPACING_MD)
        self.chk_graph1 = make_checkbox("SHOW ACCEL (aX, aY, aZ)", checked=True)
        self.chk_graph2 = make_checkbox("SHOW GYRO (gX, gY, gZ)", checked=True)
        
        # Add zoom controls
        self.btn_zoom_in = make_button("🔍+", STYLE_BTN_BASE, 32)
        self.btn_zoom_out = make_button("🔍-", STYLE_BTN_BASE, 32)
        self.btn_zoom_fit = make_button("🔍□", STYLE_BTN_BASE, 32)
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
        widget.setMaximumWidth(min(RIGHT_MAX_W, 280))
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        layout.addWidget(make_section_label("TOOLBAR", accent_color=ACCENT))

        # Details card with modern shadow
        detail_card = make_card_frame()
        add_card_shadow(detail_card, blur_radius=12, offset_y=3, color="rgba(0, 0, 0, 0.10)")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        detail_layout.setSpacing(SPACING_MD)

        detail_form = QFormLayout()
        detail_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        detail_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        detail_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        detail_form.setHorizontalSpacing(SPACING_SM)
        detail_form.setVerticalSpacing(SPACING_SM)

        self.combo_spell = QComboBox()
        self.combo_spell.setEditable(True)
        self.combo_spell.setStyleSheet(STYLE_RECORD_COMBO)
        self.combo_spell.setPlaceholderText("Type or select spell name...")
        self.combo_spell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.edit_tag = QLineEdit()
        self.edit_tag.setStyleSheet(STYLE_RECORD_COMBO)
        self.edit_tag.setPlaceholderText("e.g., Walking / Idle")
        self.edit_tag.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lbl_spell = QLabel("Spell label:")
        lbl_spell.setStyleSheet(f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;")
        lbl_tag = QLabel("Tag:")
        lbl_tag.setStyleSheet(f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;")

        detail_form.addRow(lbl_spell, self.combo_spell)
        detail_form.addRow(lbl_tag, self.edit_tag)
        detail_layout.addLayout(detail_form)

        count_grid = QGridLayout()
        count_grid.setHorizontalSpacing(SPACING_MD)
        count_grid.setVerticalSpacing(SPACING_SM)
        count_grid.addWidget(make_hint("Recorded", color=TEXT_MUTED), 0, 0)
        count_grid.addWidget(make_hint("Duration", color=TEXT_MUTED), 0, 1)

        self.lbl_record_count = QLabel("0")
        self.lbl_record_count.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 800; font-size: 16px;"
        )

        self.lbl_record_duration = QLabel("00:00")
        self.lbl_record_duration.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 800; font-size: 16px;"
        )
        count_grid.addWidget(self.lbl_record_count, 1, 0)
        count_grid.addWidget(self.lbl_record_duration, 1, 1)
        detail_layout.addLayout(count_grid)
        layout.addWidget(detail_card)

        # ── Controls card with modern shadow ─────────────────────
        controls_card = make_card_frame()
        add_card_shadow(controls_card, blur_radius=12, offset_y=3, color="rgba(0, 0, 0, 0.10)")
        ctrl_layout = QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        ctrl_layout.setSpacing(SPACING_MD)

        # Buttons: START | STOP | SNIP
        btn_row = QGridLayout()
        btn_row.setHorizontalSpacing(SPACING_SM)
        btn_row.setVerticalSpacing(SPACING_SM)
        self.btn_start = make_button("▶ START", STYLE_BTN_START, BTN_H)
        self.btn_stop  = make_button("■ STOP",  STYLE_BTN_STOP,  BTN_H)
        self.btn_snip  = make_button("✌ SNIP",  STYLE_BTN_SNIP,  BTN_H)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(False)
        
        # Add tooltips for better UX (include keyboard shortcuts)
        self.btn_start.setToolTip("Start recording sensor data (Ctrl+S)")
        self.btn_stop.setToolTip("Stop recording and enable snipping (Ctrl+T)")
        self.btn_snip.setToolTip("Save selected region as a training sample (Ctrl+X)")
        
        btn_row.addWidget(self.btn_start, 0, 0)
        btn_row.addWidget(self.btn_stop, 0, 1)
        btn_row.addWidget(self.btn_snip, 0, 2)
        ctrl_layout.addLayout(btn_row)

        # Hint
        lbl_hint = make_hint("START -> plot live (Ctrl+S)  |  STOP -> freeze & drag (Ctrl+T)  |  SNIP -> save (Ctrl+X)")
        ctrl_layout.addWidget(lbl_hint)

        layout.addWidget(controls_card)

        # ── Batch operations card with modern shadow ───────────────────
        batch_card = make_card_frame()
        add_card_shadow(batch_card, blur_radius=12, offset_y=3, color="rgba(0, 0, 0, 0.10)")
        batch_layout = QVBoxLayout(batch_card)
        batch_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        batch_layout.setSpacing(SPACING_MD)

        batch_layout.addWidget(make_section_label("BATCH OPERATIONS", accent_color=TEXT_BODY))

        batch_btn_row = QGridLayout()
        batch_btn_row.setHorizontalSpacing(SPACING_SM)
        batch_btn_row.setVerticalSpacing(SPACING_SM)

        self.btn_clear_samples = make_button(
            "🗑 CLEAR", 
            STYLE_BTN_BASE + f" QPushButton {{ color: {DANGER}; }}", 
            32
        )
        self.btn_clear_samples.setToolTip("Clear all currently recorded samples")

        self.btn_export_csv = make_button("💾 EXPORT", STYLE_BTN_BASE, 32)
        self.btn_export_csv.setToolTip("Export recorded samples as CSV")

        batch_btn_row.addWidget(self.btn_clear_samples, 0, 0)
        batch_btn_row.addWidget(self.btn_export_csv, 0, 1)
        batch_layout.addLayout(batch_btn_row)

        layout.addWidget(batch_card)

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
        layout.setSpacing(SPACING_MD)
        layout.addWidget(make_section_label("SPELL LIBRARY", accent_color=TEXT_BODY))
        
        # Spell list
        self.spell_list = QListWidget()
        self.spell_list.setStyleSheet(STYLE_RECORD_LIST)
        layout.addWidget(self.spell_list)
        
        # Delete button at bottom
        self.btn_delete_spell = make_button("DELETE SPELL", STYLE_BTN_BASE + f" QPushButton {{ color: {DANGER}; }}", 36)
        self.btn_delete_spell.setToolTip("Delete selected spell")
        layout.addWidget(self.btn_delete_spell)
        return page

    def _build_sample_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(SPACING_SM)
        self.btn_back_spells = make_button("◀ BACK", STYLE_BTN_BACK, 36)
        self.lbl_current_spell = QLabel("SAMPLES: …")
        self.lbl_current_spell.setStyleSheet(
            f"color: {ACCENT}; font-weight: bold; font-size: 11px;"
        )
        self.lbl_current_spell.setWordWrap(True)
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_RECORD_LIST)
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

        # Batch operations
        self.btn_clear_samples.clicked.connect(self._on_clear_samples)
        self.btn_export_csv.clicked.connect(self._on_export_csv)

        # Spell list navigation
        self.btn_back_spells.clicked.connect(
            lambda: self.stacked_spells.setCurrentIndex(0)
        )
        self.spell_list.itemClicked.connect(self._on_spell_list_clicked)
        self.btn_delete_spell.clicked.connect(self._on_delete_spell)

        # Plot refresh timer — throttled for high-throughput stability
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._render_plots)
        self._plot_timer.start(33)  # ~30 FPS

    def _configure_accessibility(self) -> None:
        """Set keyboard traversal and accessibility names for core controls."""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.graph1.setAccessibleName("Accelerometer live plot (aX, aY, aZ)")
        self.graph2.setAccessibleName("Gyroscope live plot (gX, gY, gZ)")
        self.lbl_wand_status.setAccessibleName("Recording status")
        self.lbl_wand_status.setAccessibleDescription(
            "Dynamic status indicator showing current recording or connection state"
        )
        self.combo_spell.setAccessibleName("Spell label selector")
        self.edit_tag.setAccessibleName("Optional tag label")
        self.btn_start.setAccessibleName("Start recording (Ctrl+S)")
        self.btn_stop.setAccessibleName("Stop recording (Ctrl+T)")
        self.btn_snip.setAccessibleName("Snip selected range (Ctrl+X)")
        self.btn_zoom_in.setAccessibleName("Zoom in timeline")
        self.btn_zoom_out.setAccessibleName("Zoom out timeline")
        self.btn_zoom_fit.setAccessibleName("Fit timeline to data")
        self.spell_list.setAccessibleName("Spell list")
        self.btn_delete_spell.setAccessibleName("Delete spell")
        self.btn_back_spells.setAccessibleName("Back to spell list")
        self.sample_list.setAccessibleName("Sample list")
        self.btn_clear_samples.setAccessibleName("Clear recorded samples")
        self.btn_export_csv.setAccessibleName("Export samples to CSV file")

        self.setTabOrder(self.combo_spell, self.edit_tag)
        self.setTabOrder(self.edit_tag, self.btn_start)
        self.setTabOrder(self.btn_start, self.btn_stop)
        self.setTabOrder(self.btn_stop, self.btn_snip)
        self.setTabOrder(self.btn_snip, self.btn_zoom_in)
        self.setTabOrder(self.btn_zoom_in, self.btn_zoom_out)
        self.setTabOrder(self.btn_zoom_out, self.btn_zoom_fit)
        self.setTabOrder(self.btn_zoom_fit, self.btn_clear_samples)
        self.setTabOrder(self.btn_clear_samples, self.btn_export_csv)
        self.setTabOrder(self.btn_export_csv, self.spell_list)
        self.setTabOrder(self.spell_list, self.btn_delete_spell)
        self.setTabOrder(self.btn_delete_spell, self.btn_back_spells)
        self.setTabOrder(self.btn_back_spells, self.sample_list)

    # ── Static helpers ──────────────────────────────────────────────────


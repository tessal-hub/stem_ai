"""
PageRecord — Timeline and recording view with LIVE Plotting, 3D Wand, & Snipping.

Architecture compliance (docs/01_ARCHITECTURE/OVERVIEW.md and docs/06_CONTRACTS/UI_CONTRACTS.md):
    - This file is PURE VIEW. No data processing, no direct DataStore calls.
    - Receives plot data via update_plot_data(buffer_snapshot) called by Handler.
    - Emits sig_data_cropped(list, str) with 6D data + spell name for Handler to save.
    - Emits sig_spell_selected(str) when user clicks a spell.
    - MUST NOT import anything from /logic.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QTime, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import numpy as np
import pyqtgraph as pg

from constants import canonical_system_spell, is_system_spell
from ui.component_factory import (
    make_button,
    make_checkbox,
    make_card_frame,
    make_hint,
    make_section_label,
)
from ui.color_utils import readable_text_on
from ui.confirm_dialog import confirm_destructive
from ui.i18n_bridge import tr_ui
from ui.mac_material import apply_soft_shadow
from ui.modern_layout import (
    MARGIN_COMFORTABLE,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
)
from ui.tokens import (
    ACCENT,
    BTN_H,
    CROP_REGION,
    DANGER,
    PLOT_AX_COLOR,
    PLOT_AY_COLOR,
    PLOT_AZ_COLOR,
    PLOT_GX_COLOR,
    PLOT_GY_COLOR,
    PLOT_GZ_COLOR,
    PLOT_HANDLE_HOVER_COLOR,
    RECORD_GRAPH_MIN_H,
    RECORD_LIST_MIN_H,
    RIGHT_MAX_W,
    SPELL_BTN_H,
    STYLE_BTN_BACK,
    STYLE_BTN_BASE,
    STYLE_BTN_DANGER_OUTLINE,
    STYLE_BTN_SNIP,
    STYLE_BTN_START,
    STYLE_BTN_STOP,
    STYLE_RECORD_COMBO,
    STYLE_RECORD_CURRENT_SPELL,
    STYLE_RECORD_FIELD_LABEL,
    STYLE_RECORD_GRAPH_CARD,
    STYLE_RECORD_LIST,
    STYLE_RECORD_MAIN_CONTAINER,
    STYLE_RECORD_METRIC_VALUE,
    STYLE_RECORD_STATUS_TEMPLATE,
    SUCCESS,
    TEXT_BODY,
    TEXT_MUTED,
    WARNING,
)
from logic.theme_manager import theme_manager

log = logging.getLogger(__name__)

_EMPTY_SPELL_LIST = "__STEM_EMPTY_SPELL_LIST__"
_RECORDING_TIMER_INTERVAL_MS = 1000
_PLOT_TIMER_INTERVAL_MS = 33
_DEFAULT_CROP_REGION_START = 30
_DEFAULT_CROP_REGION_END = 120
_AUTO_CROP_TAIL_SAMPLE_COUNT = 200


# ════════════════════════════════════════════════════════════════════════
#  PageRecord
# ════════════════════════════════════════════════════════════════════════

class PageRecord(QWidget):
    """Trang thu thập mẫu cử chỉ — vẽ đồ thị IMU reаl-time, snip và lưu mẫu."""

    # ── Outbound signals (consumed by Handler) ──────────────────────────
    sig_start_record   = pyqtSignal(str)
    sig_stop_record    = pyqtSignal()
    sig_snip_record    = pyqtSignal()
    sig_sample_opened  = pyqtSignal(str)
    sig_sample_deleted = pyqtSignal(str)
    sig_delete_latest_sample = pyqtSignal(str)  # spell name
    sig_data_cropped   = pyqtSignal(list, str)  # (6D data, spell_name)
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
        # Initial spell-count snapshot at startup for static list rendering.
        self._initial_spell_counts = dict(getattr(data_store, "spell_counts", {}))

        self.is_live: bool = True
        self.current_spell_name: str = ""
        self._sample_list_empty_sentinel = "__STEM_EMPTY_SAMPLES__"

        # Recording timer for duration tracking
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self._update_recording_duration)
        self.recording_start_time = QTime()

        self._init_ui()
        self._setup_plots()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

        log.debug("[PageRecord] Khởi tạo xong - is_live=True, QTimer render plot đang chạy")

    def keyPressEvent(self, event) -> None:
        """Xử lý phím tắt bàn phím cho các thao tác recording."""
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_start.isEnabled():
                self._on_btn_start_clicked()
        elif event.key() == Qt.Key.Key_T and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_stop.isEnabled():
                self._on_btn_stop_clicked()
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_snip.isEnabled():
                self._on_btn_snip_clicked()
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
            self.lbl_wand_status.setText(tr_ui('record_ready'))
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
            )
        else:
            self.lbl_wand_status.setText(tr_ui('record_not_ready'))
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=DANGER)
            )

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        # Update Plot Styles
        for plot in [self.graph1, self.graph2]:
            plot.setBackground("transparent")
            plot.getAxis("left").setPen(p.TEXT_TERTIARY)
            plot.getAxis("bottom").setPen(p.TEXT_TERTIARY)
        # Update Library
        self.spell_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; color: {p.TEXT_PRIMARY}; }}
            QListWidget::item {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 8px; margin-bottom: 4px; padding: 10px; }}
            QListWidget::item:selected {{ background-color: {p.PRIMARY}; color: {p.SURFACE_PRIMARY}; border: none; }}
        """)

    def set_recording_state(self, recording: bool) -> None:
        self.btn_start.setEnabled(not recording)
        self.btn_stop.setEnabled(recording)
        self.combo_spell.setEnabled(not recording)
        if hasattr(self, "btn_delete_latest_sample"):
            self.btn_delete_latest_sample.setEnabled(not recording)

        status = tr_ui('record_recording_short') if recording else tr_ui('record_ready')
        color = ACCENT if recording else SUCCESS
        self.lbl_wand_status.setText(status)
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=color)
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
        self.lbl_wand_status.setText(tr_ui('record_status_saved', name=spell_name))
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
        )

    def load_spell_list(self, spells: list[str] | dict[str, int]) -> None:
        if isinstance(spells, dict):
            spell_counts = {
                str(name): int(count)
                for name, count in spells.items()
                if str(name).strip()
            }
        else:
            spell_counts = {
                str(name): int(getattr(self.store, "spell_counts", {}).get(str(name), 0))
                for name in spells
                if str(name).strip()
            }

        spell_names = list(spell_counts.keys())

        self.spell_list.clear()
        if spell_names:
            for spell_name in spell_names:
                count = spell_counts.get(spell_name, 0)
                item = QListWidgetItem(f"{spell_name} ({count})")
                item.setData(Qt.ItemDataRole.UserRole, spell_name)
                self.spell_list.addItem(item)
        else:
            empty_item = QListWidgetItem(tr_ui("record_list_empty"))
            empty_item.setData(Qt.ItemDataRole.UserRole, _EMPTY_SPELL_LIST)
            self.spell_list.addItem(empty_item)

        # Also update the spell combo box
        current_text = self.combo_spell.currentText()
        self.combo_spell.clear()
        self.combo_spell.addItems(spell_names)
        if current_text:
            idx = self.combo_spell.findText(current_text)
            if idx >= 0:
                self.combo_spell.setCurrentIndex(idx)

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        self.current_spell_name = spell_name
        self.lbl_current_spell.setText(tr_ui("record_spell_samples", name=spell_name))
        self.sample_list.clear()
        if samples:
            self.sample_list.addItems(samples)
        else:
            empty_item = QListWidgetItem(tr_ui("record_sample_empty"))
            empty_item.setData(Qt.ItemDataRole.UserRole, self._sample_list_empty_sentinel)
            self.sample_list.addItem(empty_item)
        self.stacked_spells.setCurrentIndex(1)

    # ── Plot Setup & Rendering ──────────────────────────────────────────

    def _setup_plots(self) -> None:
        log.debug("[PageRecord._setup_plots] Starting plot setup...")
        for plot in [self.graph1, self.graph2]:
            plot.setBackground("transparent")
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
        self.graph1.setLabel("left", tr_ui("record_axis_accel_left"), color=TEXT_BODY)
        self.graph1.setLabel("bottom", tr_ui("record_axis_bottom"), color=TEXT_BODY)
        self.graph2.setLabel("left", tr_ui("record_axis_gyro_left"), color=TEXT_BODY)
        self.graph2.setLabel("bottom", tr_ui("record_axis_bottom"), color=TEXT_BODY)

        # Crop region overlay on graph1 — LARGER handles for easier drag
        self.crop_region = pg.LinearRegionItem(
            [_DEFAULT_CROP_REGION_START, _DEFAULT_CROP_REGION_END],
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
        """Cập nhật số mẫu đang chọn khi vùng crop thay đổi.

        Returns:
            None.
        """
        if not self.crop_region.isVisible():
            return
        
        region = self.crop_region.getRegion()
        min_x = int(region[0])
        max_x = int(region[1])
        sample_count = max(0, max_x - min_x)
        
        self.lbl_record_count.setText(tr_ui("record_selected_samples", n=sample_count))

    def _render_plots(self) -> None:
        """Render đồ thị live theo timer, chỉ xử lý hiển thị và không đổi dữ liệu nguồn.

        Returns:
            None.
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

    def _on_btn_start_clicked(self) -> None:
        """START: Begin recording and send command to device."""
        spell_name = self.combo_spell.currentText().strip()
        if not spell_name:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_select_spell')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=DANGER)
            )
            return

        self.is_live = True
        self.crop_region.hide()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snip.setEnabled(False)
        self.btn_delete_latest_sample.setEnabled(False)
        self.combo_spell.setEnabled(False)
        self.lbl_wand_status.setText(f"● {tr_ui('record_recording')}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
        )
        
        # Start recording timer
        self.recording_start_time.start()
        self.recording_timer.start(_RECORDING_TIMER_INTERVAL_MS)
        
        self.sig_start_record.emit(spell_name)

    def _on_btn_stop_clicked(self) -> None:
        """STOP: cease recording buffer and finalize file."""
        self.is_live = False
        self.crop_region.show()
        
        # Auto-select a reasonable crop region (last 2 seconds of data, or full if shorter)
        buf_len = len(self.store.get_live_buffer_snapshot())
        if buf_len > 0:
            # Aim for last 2 seconds (assuming 50Hz = 100 samples/second)
            crop_start = max(0, buf_len - _AUTO_CROP_TAIL_SAMPLE_COUNT)
            self.crop_region.setRegion([crop_start, buf_len])
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(True)
        self.btn_delete_latest_sample.setEnabled(True)
        self.combo_spell.setEnabled(True)

        self.lbl_wand_status.setText(f"● {tr_ui('record_stopped_snip')}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
        )
        
        # Stop recording timer
        self.recording_timer.stop()
        self.lbl_record_duration.setText("00:00")
        
        self.sig_stop_record.emit()

    def _on_btn_snip_clicked(self) -> None:
        """SNIP: Cut the selected region and emit with spell name."""
        if not self.crop_region.isVisible():
            return

        # Get spell name from combo
        spell_name = self.combo_spell.currentText().strip()
        if not spell_name:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_enter_spell')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=DANGER)
            )
            return

        region = self.crop_region.getRegion()
        if len(region) < 2:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_invalid_crop')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=DANGER)
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
            self.sig_data_cropped.emit(cropped_6d, spell_name)
            self.lbl_wand_status.setText(
                tr_ui("record_snipped", n=max_idx - min_idx, name=spell_name)
            )
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
            )
        else:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_invalid_range')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=DANGER)
            )

        self.sig_snip_record.emit()

    def _on_btn_zoom_in_clicked(self) -> None:
        """Zoom in on both plots."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().scaleBy((0.8, 0.8))

    def _on_btn_zoom_out_clicked(self) -> None:
        """Zoom out on both plots."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().scaleBy((1.25, 1.25))

    def _on_btn_zoom_fit_clicked(self) -> None:
        """Fit both plots to show all data."""
        for plot in [self.graph1, self.graph2]:
            if plot.isVisible():
                plot.getViewBox().autoRange()

    def _on_btn_clear_samples_clicked(self) -> None:
        """Clear all recorded samples from current buffer."""
        if not confirm_destructive(
            self,
            title=tr_ui("record_clear_title"),
            message=tr_ui("record_clear_msg"),
            confirm_text=tr_ui("record_clear_confirm"),
            cancel_text=tr_ui("record_clear_cancel"),
        ):
            return
        
        # Emit signal to Handler for actual clearing
        self.sig_clear_buffer.emit()
        # Update UI
        self.lbl_record_count.setText("0")
        self.crop_region.setRegion([_DEFAULT_CROP_REGION_START, _DEFAULT_CROP_REGION_END])
        self.is_live = True
        self.crop_region.hide()
        self.lbl_wand_status.setText(f"✔ {tr_ui('record_cleared')}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
        )

    def _on_btn_export_csv_clicked(self) -> None:
        """Export current recorded samples to CSV file."""
        buf = self.store.get_live_buffer_snapshot()
        if not buf:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_no_export')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
            )
            return

        self.sig_export_csv.emit()
        self.lbl_wand_status.setText(tr_ui("record_exporting", n=len(buf)))
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
        )

    def _on_btn_delete_latest_sample_clicked(self) -> None:
        """Quick-delete the newest recorded CSV sample for the active spell."""
        spell_name = self.current_spell_name.strip() or self.combo_spell.currentText().strip()
        if not spell_name:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_select_delete_spell')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
            )
            return

        samples = self.store.get_samples_for_spell(spell_name)
        if not samples:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_no_samples_spell', name=spell_name)}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
            )
            return

        self.sig_delete_latest_sample.emit(spell_name)
        self.lbl_wand_status.setText(tr_ui("record_deleting_latest", name=spell_name))
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
        )

    def set_quick_delete_feedback(self, success: bool, message: str) -> None:
        """Display status feedback after quick sample deletion."""
        if success:
            self.lbl_wand_status.setText(f"✔ {tr_ui('record_deleted_latest')}")
            self.lbl_wand_status.setStyleSheet(
                STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS)
            )
            return
        self.lbl_wand_status.setText(f"⚠ {message}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
        )

    def _on_spell_list_item_clicked(self, item) -> None:
        """Handle spell list item click: auto-select spell in combo and emit signal."""
        if item.data(Qt.ItemDataRole.UserRole) == _EMPTY_SPELL_LIST:
            return
        spell_name = str(item.data(Qt.ItemDataRole.UserRole) or item.text())
        if is_system_spell(spell_name):
            self.btn_delete_spell.setToolTip(tr_ui("record_tt_standby"))
        else:
            self.btn_delete_spell.setToolTip(tr_ui("record_tt_delete_spell"))
        # Auto-select in combo box
        idx = self.combo_spell.findText(spell_name)
        if idx >= 0:
            self.combo_spell.setCurrentIndex(idx)
        # Emit signal for handler
        self.sig_spell_selected.emit(spell_name)

    def _on_btn_delete_spell_clicked(self) -> None:
        """Handle spell deletion with 2-step verification."""
        # Get selected spell
        current_item = self.spell_list.currentItem()
        if not current_item:
            QMessageBox.critical(
                self,
                tr_ui("record_no_selection_title"),
                tr_ui("record_no_selection_msg"),
            )
            return

        if current_item.data(Qt.ItemDataRole.UserRole) == _EMPTY_SPELL_LIST:
            return
        spell_name = str(current_item.data(Qt.ItemDataRole.UserRole) or current_item.text())
        if is_system_spell(spell_name):
            self.show_protected_spell_warning(canonical_system_spell(spell_name))
            return
        
        # First confirmation dialog
        if not confirm_destructive(
            self,
            title=tr_ui("record_del_step1_title"),
            message=tr_ui("record_del_step1_msg", name=spell_name),
            confirm_text=tr_ui("record_del_continue"),
            cancel_text=tr_ui("record_del_keep"),
        ):
            return

        if confirm_destructive(
            self,
            title=tr_ui("record_del_step2_title"),
            message=tr_ui("record_del_step2_msg", name=spell_name),
            confirm_text=tr_ui("record_del_final"),
            cancel_text=tr_ui("record_del_abort"),
        ):
            self.sig_spell_deleted.emit(spell_name)

    def _on_btn_back_spells_clicked(self) -> None:
        """Quay về danh sách spell từ trang chi tiết sample."""
        self.stacked_spells.setCurrentIndex(0)

    def show_protected_spell_warning(self, spell_name: str) -> None:
        """Display clear UX feedback when a protected spell deletion is blocked."""
        canonical_name = canonical_system_spell(spell_name)
        QMessageBox.warning(
            self,
            tr_ui("record_protected_title"),
            tr_ui("record_protected_msg", name=canonical_name),
        )
        self.lbl_wand_status.setText(f"⚠ {tr_ui('record_spell_protected', name=canonical_name)}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
        )

    # ── UI Construction ─────────────────────────────────────────────────

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        
        # 1. Update Plot Styles
        for plot in [self.plot_accel, self.plot_gyro]:
            plot.setBackground("transparent")
            plot.getAxis("left").setPen(p.TEXT_TERTIARY)
            plot.getAxis("bottom").setPen(p.TEXT_TERTIARY)
            
        # 2. Update Layout Cards
        self.graph_card.setStyleSheet(f"""
            #VanguardCardOuter {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 24px; }}
            #VanguardCardInner {{ background-color: {p.SURFACE_PRIMARY}; border: none; border-radius: 16px; }}
        """)
        
        # 3. Update Sidebar Library
        self.spell_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; color: {p.TEXT_PRIMARY}; }}
            QListWidget::item {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 8px; margin-bottom: 4px; padding: 10px; }}
            QListWidget::item:selected {{ background-color: {p.PRIMARY}; color: {readable_text_on(p.PRIMARY, dark_text=p.SURFACE_PRIMARY, light_text="#FFFFFF")}; border: none; }}
        """)

    def _init_ui(self) -> None:
        """Xây dựng layout chính gồm 2 cột: plot bên trái, controls bên phải."""
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
        self.lbl_wand_status = QLabel(f"● {tr_ui('record_wait_serial')}")
        self.lbl_wand_status.setStyleSheet(
            STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING)
        )
        self.lbl_timeline = make_section_label(tr_ui("record_timeline"), accent=True)
        self.lbl_timeline.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self.lbl_wand_status)
        top_row.addWidget(self.lbl_timeline)
        layout.addLayout(top_row)

        # Graph card - modern card with shadow
        graph_card = QFrame()
        graph_card.setObjectName("CardFrame")
        graph_card.setStyleSheet(STYLE_RECORD_GRAPH_CARD)
        apply_soft_shadow(graph_card, blur_radius=22, y_offset=4, color="rgba(15, 23, 42, 0.14)")
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
        )
        graph_layout.setSpacing(SPACING_MD)
        self.graph1 = pg.PlotWidget()
        self.graph2 = pg.PlotWidget()
        self.graph1.setMinimumHeight(RECORD_GRAPH_MIN_H)
        self.graph2.setMinimumHeight(RECORD_GRAPH_MIN_H)
        graph_layout.addWidget(self.graph1)
        graph_layout.addWidget(self.graph2, stretch=1)
        layout.addWidget(graph_card, stretch=1)

        # Checkboxes row
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(SPACING_MD)
        self.chk_graph1 = make_checkbox(tr_ui("record_show_accel"), checked=True)
        self.chk_graph2 = make_checkbox(tr_ui("record_show_gyro"), checked=True)
        
        # Add zoom controls
        self.btn_zoom_in = make_button("🔍+", STYLE_BTN_BASE, BTN_H)
        self.btn_zoom_out = make_button("🔍-", STYLE_BTN_BASE, BTN_H)
        self.btn_zoom_fit = make_button("🔍□", STYLE_BTN_BASE, BTN_H)
        self.btn_zoom_in.setToolTip(tr_ui("record_tt_zoom_in"))
        self.btn_zoom_out.setToolTip(tr_ui("record_tt_zoom_out"))
        self.btn_zoom_fit.setToolTip(tr_ui("record_tt_fit"))
        
        bottom_row.addWidget(self.chk_graph1, stretch=1)
        bottom_row.addWidget(self.chk_graph2, stretch=1)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_zoom_in)
        bottom_row.addWidget(self.btn_zoom_out)
        bottom_row.addWidget(self.btn_zoom_fit)
        layout.addLayout(bottom_row)

        return widget

    def _build_right_column(self) -> QWidget:
        """Xây dựng cột phải gồm details, controls, danh sách spell và batch actions."""
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        self._section_toolbar = make_section_label(tr_ui("record_toolbar"), accent=True)
        layout.addWidget(self._section_toolbar)
        layout.addWidget(self._build_detail_card())
        layout.addWidget(self._build_controls_card())

        # ── Spell list stack ───────────────────────────────────────
        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_spell_list_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)

        layout.addWidget(self._build_batch_card())

        return widget

    def _build_detail_card(self) -> QFrame:
        """Xây dựng card chứa spell selector và chỉ số recorded/duration."""
        detail_card = make_card_frame()
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
        self.combo_spell.setPlaceholderText(tr_ui("record_spell_placeholder"))
        self.combo_spell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._lbl_spell = QLabel(tr_ui("record_spell_label"))
        self._lbl_spell.setStyleSheet(STYLE_RECORD_FIELD_LABEL)
        detail_form.addRow(self._lbl_spell, self.combo_spell)
        detail_layout.addLayout(detail_form)

        count_grid = QGridLayout()
        count_grid.setHorizontalSpacing(SPACING_MD)
        count_grid.setVerticalSpacing(SPACING_SM)
        self._hint_recorded = make_hint(tr_ui("record_hint_recorded"), color=TEXT_MUTED)
        self._hint_duration = make_hint(tr_ui("record_hint_duration"), color=TEXT_MUTED)
        count_grid.addWidget(self._hint_recorded, 0, 0)
        count_grid.addWidget(self._hint_duration, 0, 1)

        self.lbl_record_count = QLabel("0")
        self.lbl_record_count.setStyleSheet(STYLE_RECORD_METRIC_VALUE)
        self.lbl_record_duration = QLabel("00:00")
        self.lbl_record_duration.setStyleSheet(STYLE_RECORD_METRIC_VALUE)
        count_grid.addWidget(self.lbl_record_count, 1, 0)
        count_grid.addWidget(self.lbl_record_duration, 1, 1)
        detail_layout.addLayout(count_grid)
        return detail_card

    def _build_controls_card(self) -> QFrame:
        """Xây dựng card chứa nút START/STOP/SNIP và hint thao tác."""
        controls_card = make_card_frame()
        ctrl_layout = QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        ctrl_layout.setSpacing(SPACING_MD)

        btn_row = QGridLayout()
        btn_row.setHorizontalSpacing(SPACING_SM)
        btn_row.setVerticalSpacing(SPACING_SM)
        self.btn_start = make_button(tr_ui("record_btn_start"), STYLE_BTN_START, BTN_H)
        self.btn_stop = make_button(tr_ui("record_btn_stop"), STYLE_BTN_STOP, BTN_H)
        self.btn_snip = make_button(tr_ui("record_btn_snip"), STYLE_BTN_SNIP, BTN_H)
        self.btn_stop.setEnabled(False)
        self.btn_snip.setEnabled(False)
        self.btn_start.setToolTip(tr_ui("record_tt_start"))
        self.btn_stop.setToolTip(tr_ui("record_tt_stop"))
        self.btn_snip.setToolTip(tr_ui("record_tt_snip"))
        btn_row.addWidget(self.btn_start, 0, 0)
        btn_row.addWidget(self.btn_stop, 0, 1)
        btn_row.addWidget(self.btn_snip, 0, 2)
        ctrl_layout.addLayout(btn_row)

        self._hint_controls = make_hint(tr_ui("record_hint_controls"))
        ctrl_layout.addWidget(self._hint_controls)
        return controls_card

    def _build_batch_card(self) -> QFrame:
        """Xây dựng card batch operations: delete latest, clear, export."""
        batch_card = make_card_frame()
        batch_layout = QVBoxLayout(batch_card)
        batch_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        batch_layout.setSpacing(SPACING_MD)

        self._section_batch = make_section_label(tr_ui("record_batch"), accent=False)
        batch_layout.addWidget(self._section_batch)

        batch_btn_row = QGridLayout()
        batch_btn_row.setHorizontalSpacing(SPACING_SM)
        batch_btn_row.setVerticalSpacing(SPACING_SM)
        self.btn_clear_samples = make_button(tr_ui("record_btn_clear"), STYLE_BTN_DANGER_OUTLINE, BTN_H)
        self.btn_clear_samples.setToolTip(tr_ui("record_tt_clear"))
        self.btn_export_csv = make_button(tr_ui("record_btn_export"), STYLE_BTN_BASE, BTN_H)
        self.btn_export_csv.setToolTip(tr_ui("record_tt_export"))
        self.btn_delete_latest_sample = make_button(
            tr_ui("record_btn_delete_latest"),
            STYLE_BTN_DANGER_OUTLINE,
            BTN_H,
        )
        self.btn_delete_latest_sample.setToolTip(tr_ui("record_tt_delete_latest"))
        batch_btn_row.addWidget(self.btn_delete_latest_sample, 0, 0)
        batch_btn_row.addWidget(self.btn_clear_samples, 0, 1)
        batch_btn_row.addWidget(self.btn_export_csv, 0, 2)
        batch_layout.addLayout(batch_btn_row)
        return batch_card

    def _build_spell_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)
        self._section_spell_library = make_section_label(tr_ui("record_spell_list"), accent=False)
        layout.addWidget(self._section_spell_library)
        
        # Spell list
        self.spell_list = QListWidget()
        self.spell_list.setStyleSheet(STYLE_RECORD_LIST)
        self.spell_list.setMinimumHeight(RECORD_LIST_MIN_H)
        layout.addWidget(self.spell_list)
        
        # Delete button at bottom
        self.btn_delete_spell = make_button(
            tr_ui("record_delete_spell_btn"), STYLE_BTN_DANGER_OUTLINE, SPELL_BTN_H
        )
        self.btn_delete_spell.setToolTip(tr_ui("record_tt_delete_spell"))
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
        self.btn_back_spells = make_button(tr_ui("record_btn_back"), STYLE_BTN_BACK, SPELL_BTN_H)
        self.lbl_current_spell = QLabel(tr_ui("record_spell_samples", name="…"))
        self.lbl_current_spell.setStyleSheet(
            STYLE_RECORD_CURRENT_SPELL
        )
        self.lbl_current_spell.setWordWrap(True)
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_RECORD_LIST)
        self.sample_list.setMinimumHeight(RECORD_LIST_MIN_H)
        layout.addWidget(self.sample_list)
        return page

    # ── Internal Signal Wiring ──────────────────────────────────────────

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot của trang recording."""
        # Toolbar buttons
        self.btn_start.clicked.connect(self._on_btn_start_clicked)
        self.btn_stop.clicked.connect(self._on_btn_stop_clicked)
        self.btn_snip.clicked.connect(self._on_btn_snip_clicked)

        # Graph visibility toggles
        self.chk_graph1.toggled.connect(self.graph1.setVisible)
        self.chk_graph2.toggled.connect(self.graph2.setVisible)
        
        # Zoom controls
        self.btn_zoom_in.clicked.connect(self._on_btn_zoom_in_clicked)
        self.btn_zoom_out.clicked.connect(self._on_btn_zoom_out_clicked)
        self.btn_zoom_fit.clicked.connect(self._on_btn_zoom_fit_clicked)

        # Batch operations
        self.btn_delete_latest_sample.clicked.connect(self._on_btn_delete_latest_sample_clicked)
        self.btn_clear_samples.clicked.connect(self._on_btn_clear_samples_clicked)
        self.btn_export_csv.clicked.connect(self._on_btn_export_csv_clicked)

        # Spell list navigation
        self.btn_back_spells.clicked.connect(self._on_btn_back_spells_clicked)
        self.spell_list.itemClicked.connect(self._on_spell_list_item_clicked)
        self.btn_delete_spell.clicked.connect(self._on_btn_delete_spell_clicked)

        # Plot refresh timer — throttled for high-throughput stability
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._render_plots)
        self._plot_timer.start(_PLOT_TIMER_INTERVAL_MS)

    def apply_ui_language(self) -> None:
        """Refresh visible strings after app language change."""
        self.lbl_timeline.setText(tr_ui("record_timeline"))
        self._section_toolbar.setText(tr_ui("record_toolbar"))
        self._lbl_spell.setText(tr_ui("record_spell_label"))
        self.combo_spell.setPlaceholderText(tr_ui("record_spell_placeholder"))
        self._hint_recorded.setText(tr_ui("record_hint_recorded"))
        self._hint_duration.setText(tr_ui("record_hint_duration"))
        self.chk_graph1.setText(tr_ui("record_show_accel"))
        self.chk_graph2.setText(tr_ui("record_show_gyro"))
        self.btn_zoom_in.setToolTip(tr_ui("record_tt_zoom_in"))
        self.btn_zoom_out.setToolTip(tr_ui("record_tt_zoom_out"))
        self.btn_zoom_fit.setToolTip(tr_ui("record_tt_fit"))
        self.btn_start.setText(tr_ui("record_btn_start"))
        self.btn_stop.setText(tr_ui("record_btn_stop"))
        self.btn_snip.setText(tr_ui("record_btn_snip"))
        self.btn_start.setToolTip(tr_ui("record_tt_start"))
        self.btn_stop.setToolTip(tr_ui("record_tt_stop"))
        self.btn_snip.setToolTip(tr_ui("record_tt_snip"))
        self._hint_controls.setText(tr_ui("record_hint_controls"))
        self._section_batch.setText(tr_ui("record_batch"))
        self.btn_clear_samples.setText(tr_ui("record_btn_clear"))
        self.btn_clear_samples.setToolTip(tr_ui("record_tt_clear"))
        self.btn_export_csv.setText(tr_ui("record_btn_export"))
        self.btn_export_csv.setToolTip(tr_ui("record_tt_export"))
        self.btn_delete_latest_sample.setText(tr_ui("record_btn_delete_latest"))
        self.btn_delete_latest_sample.setToolTip(tr_ui("record_tt_delete_latest"))
        self._section_spell_library.setText(tr_ui("record_spell_list"))
        self.btn_delete_spell.setText(tr_ui("record_delete_spell_btn"))
        self.btn_delete_spell.setToolTip(tr_ui("record_tt_delete_spell"))
        self.btn_back_spells.setText(tr_ui("record_btn_back"))
        self.graph1.setLabel("left", tr_ui("record_axis_accel_left"), color=TEXT_BODY)
        self.graph1.setLabel("bottom", tr_ui("record_axis_bottom"), color=TEXT_BODY)
        self.graph2.setLabel("left", tr_ui("record_axis_gyro_left"), color=TEXT_BODY)
        self.graph2.setLabel("bottom", tr_ui("record_axis_bottom"), color=TEXT_BODY)
        for i in range(self.spell_list.count()):
            it = self.spell_list.item(i)
            if it is not None and it.data(Qt.ItemDataRole.UserRole) == _EMPTY_SPELL_LIST:
                it.setText(tr_ui("record_list_empty"))
                break
        for i in range(self.sample_list.count()):
            it = self.sample_list.item(i)
            if it is not None and it.data(Qt.ItemDataRole.UserRole) == self._sample_list_empty_sentinel:
                it.setText(tr_ui("record_sample_empty"))
                break
        if self.current_spell_name:
            self.lbl_current_spell.setText(tr_ui("record_spell_samples", name=self.current_spell_name))

    def _configure_accessibility(self) -> None:
        """Đặt accessible names và thứ tự tab traversal cho các control."""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.graph1.setAccessibleName("Accelerometer live plot (aX, aY, aZ)")
        self.graph2.setAccessibleName("Gyroscope live plot (gX, gY, gZ)")
        self.lbl_wand_status.setAccessibleName("Recording status")
        self.lbl_wand_status.setAccessibleDescription(
            "Dynamic status indicator showing current recording or connection state"
        )
        self.combo_spell.setAccessibleName("Spell label selector")
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
        self.btn_delete_latest_sample.setAccessibleName("Quick delete latest sample")
        self.btn_clear_samples.setAccessibleName("Clear recorded samples")
        self.btn_export_csv.setAccessibleName("Export samples to CSV file")

        self.setTabOrder(self.combo_spell, self.btn_start)
        self.setTabOrder(self.btn_start, self.btn_stop)
        self.setTabOrder(self.btn_stop, self.btn_snip)
        self.setTabOrder(self.btn_snip, self.btn_zoom_in)
        self.setTabOrder(self.btn_zoom_in, self.btn_zoom_out)
        self.setTabOrder(self.btn_zoom_out, self.btn_zoom_fit)
        self.setTabOrder(self.btn_zoom_fit, self.btn_delete_latest_sample)
        self.setTabOrder(self.btn_delete_latest_sample, self.btn_clear_samples)
        self.setTabOrder(self.btn_clear_samples, self.btn_export_csv)
        self.setTabOrder(self.btn_export_csv, self.spell_list)
        self.setTabOrder(self.spell_list, self.btn_delete_spell)
        self.setTabOrder(self.btn_delete_spell, self.btn_back_spells)
        self.setTabOrder(self.btn_back_spells, self.sample_list)

    # ── Load initial data ────────────────────────────────────────────────

    def _load_data(self) -> None:
        """Nạp danh sách spell ban đầu vào combo và list."""
        self.load_spell_list(self._initial_spell_counts)

    # ── Static helpers ──────────────────────────────────────────────────


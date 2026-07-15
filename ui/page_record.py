"""
ui/page_record.py — Trang thu thập và xử lý mẫu cử chỉ thời gian thực.

Cung cấp giao diện trực quan hóa dữ liệu IMU, cho phép người dùng ghi lại,
cắt (snip) và lưu trữ các mẫu cử chỉ vào dataset.
"""

from __future__ import annotations

import logging

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QElapsedTimer, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (QComboBox, QFormLayout, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressBar, QSizePolicy,
                             QStackedWidget, QVBoxLayout, QWidget)

from constants import is_system_spell
from logic.dataset_layout import _PRIMITIVE_LOGICAL_NAMES, folder_name_match_key
from logic.theme_manager import theme_manager
from ui.component_factory import (IconButton, make_button, make_card,
                                  make_checkbox, make_empty_state_card,
                                  make_hint, make_section_label)
from ui.confirm_dialog import confirm_destructive
from ui.i18n_bridge import tr_ui
from ui.modern_layout import (MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD,
                              SPACING_SM)
from ui.tokens import (ACCENT, BTN_H, CROP_REGION, DANGER, PLOT_AX_COLOR,
                       PLOT_AY_COLOR, PLOT_AZ_COLOR, PLOT_GX_COLOR,
                       PLOT_GY_COLOR, PLOT_GZ_COLOR, PLOT_HANDLE_HOVER_COLOR,
                       RECORD_GRAPH_MIN_H, RIGHT_MAX_W, RIGHT_MIN_W,
                       SPELL_BTN_H, STYLE_BTN_PRIMARY, SUCCESS, TEXT_MUTED,
                       WARNING)

log = logging.getLogger(__name__)

# Hằng số cấu hình nội bộ
_EMPTY_SPELL_LIST = "__STEM_EMPTY_SPELL_LIST__"
_TIMER_INTERVAL_MS = 1000
_PLOT_REFRESH_MS = 33
_DEFAULT_CROP_START = 30
_DEFAULT_CROP_END = 120
_AUTO_CROP_TAIL = 200


class PageRecord(QWidget):
    """
    Trang thu thập mẫu cử chỉ.
    Tương tác với sensor thông qua Handler và hiển thị đồ thị real-time.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_start_record = pyqtSignal(str)
    sig_stop_record = pyqtSignal()
    sig_snip_record = pyqtSignal()
    sig_sample_opened = pyqtSignal(str)
    sig_sample_deleted = pyqtSignal(str)
    sig_data_cropped = pyqtSignal(list, str)
    sig_spell_selected = pyqtSignal(str)
    sig_spell_deleted = pyqtSignal(str)
    sig_clear_buffer = pyqtSignal()
    sig_export_csv = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.store = data_store
        self._initial_counts = dict(getattr(data_store, "spell_counts", {}))
        self.is_live = True
        self.current_spell_name = ""
        self._sample_sentinel = "__STEM_EMPTY_SAMPLES__"
        self._current_samples: list[str] = []          # filenames in display order
        self._per_sample_scores: dict[str, float] = {} # filename -> score

        self._recording_timer = QTimer()
        self._recording_start_time = QElapsedTimer()
        self._pending_consistency_result: dict | None = None  # cached when UI not on sample page

        self._init_ui()
        self._setup_plots()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục (Requirement 10: padding-bottom 80px)."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")

        inner = QVBoxLayout(self.main_container)
        # Bỏ padding-bottom cứng để nội dung được bung hết cỡ
        inner.setContentsMargins(MARGIN_COMFORTABLE, 18, MARGIN_COMFORTABLE, 18)
        inner.setSpacing(SPACING_LG)

        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)
        content.addWidget(self._build_left_column(), stretch=7)
        content.addWidget(self._build_right_column(), stretch=3)

        inner.addLayout(content)
        outer.addWidget(self.main_container)

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot."""
        self.btn_start.clicked.connect(self._on_btn_start_clicked)
        self.btn_stop.clicked.connect(self._on_btn_stop_clicked)
        self.btn_snip.clicked.connect(self._on_btn_snip_clicked)
        self.btn_zoom_in.clicked.connect(self._on_zoom_in_clicked)
        self.btn_zoom_out.clicked.connect(self._on_zoom_out_clicked)
        self.btn_zoom_fit.clicked.connect(self._on_zoom_fit_clicked)
        self.btn_delete_selected.clicked.connect(self._on_btn_delete_selected_clicked)
        self.btn_clear_samples.clicked.connect(self._on_btn_clear_clicked)
        self.btn_export_csv.clicked.connect(self._on_btn_export_clicked)
        self.btn_back_spells.clicked.connect(self._on_btn_back_clicked)
        self.btn_delete_spell.clicked.connect(self._on_btn_delete_spell_clicked)
        self.spell_list.itemClicked.connect(self._on_spell_item_clicked)
        self.chk_graph1.toggled.connect(self.graph1.setVisible)
        self.chk_graph2.toggled.connect(self.graph2.setVisible)
        self._recording_timer.timeout.connect(self._update_recording_duration)
        self.shortcut_start = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_start.activated.connect(self._trigger_start)

        self.shortcut_stop = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_stop.activated.connect(self._trigger_stop)

        self.shortcut_snip = QShortcut(QKeySequence("Ctrl+X"), self)
        self.shortcut_snip.activated.connect(self._trigger_snip)

        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._render_plots)
        self._plot_timer.start(_PLOT_REFRESH_MS)
        # Show/hide delete button based on list selection
        self.sample_list.itemSelectionChanged.connect(self._on_sample_selection_changed)

    def _trigger_start(self) -> None:
        if self.btn_start.isEnabled():
            self.btn_start.click()

    def _trigger_stop(self) -> None:
        if self.btn_stop.isEnabled():
            self.btn_stop.click()

    def _trigger_snip(self) -> None:
        if self.btn_snip.isEnabled():
            self.btn_snip.click()

    def _load_data(self) -> None:
        """Nạp danh sách spell ban đầu."""
        self.load_spell_list(self._initial_counts)

    # ── Public methods ──────────────────────────

    def set_wand_ready(self, is_ready: bool) -> None:
        """Cập nhật trạng thái sẵn sàng của thiết bị."""
        if is_ready:
            self.lbl_wand_status.setText(tr_ui('record_ready'))
            self.lbl_wand_status.setProperty("status", "success")
        else:
            self.lbl_wand_status.setText(tr_ui('record_not_ready'))
            self.lbl_wand_status.setProperty("status", "error")
        self.lbl_wand_status.style().unpolish(self.lbl_wand_status)
        self.lbl_wand_status.style().polish(self.lbl_wand_status)

    def set_recording_state(self, recording: bool) -> None:
        """Thiết lập trạng thái UI khi đang ghi dữ liệu."""
        self.btn_start.setEnabled(not recording)
        self.btn_stop.setEnabled(recording)
        self.combo_spell.setEnabled(not recording)
        self.btn_delete_selected.setEnabled(not recording)

        status = tr_ui('record_recording_short') if recording else tr_ui('record_ready')
        self.lbl_wand_status.setText(status)
        self.lbl_wand_status.setProperty("status", "accent" if recording else "success")
        self.lbl_wand_status.style().unpolish(self.lbl_wand_status)
        self.lbl_wand_status.style().polish(self.lbl_wand_status)

    def load_spell_list(self, spells: list[str] | dict[str, int], consistencies: dict[str, float | str] = None) -> None:
        """Nạp và hiển thị danh sách các câu thần chú (Requirement 3: Empty State)."""
        self._current_consistencies = consistencies or {}
        if isinstance(spells, dict):
            self._current_spell_counts = {str(k): int(v) for k, v in spells.items() if str(k).strip()}
        else:
            self._current_spell_counts = {str(s): int(getattr(self.store, "spell_counts", {}).get(str(s), 0))
                            for s in spells if str(s).strip()}

        self._refresh_spell_list()

    def _refresh_spell_list(self) -> None:
        if not hasattr(self, "_current_spell_counts"):
            return

        spell_counts = self._current_spell_counts
        names = sorted(list(spell_counts.keys()))
        display_names = [n for n in names if "::" not in n]

        self.spell_list.clear()
        if display_names:
            self.spell_stack.setCurrentIndex(0)
            
            for name in display_names:
                normalized = folder_name_match_key(name)
                is_prim = normalized in {folder_name_match_key(p) for p in _PRIMITIVE_LOGICAL_NAMES}
                
                if is_prim:
                    continue
                
                is_registered = name in getattr(self.store, "registered_prototypes", set())
                suffix = " [Ready]" if is_registered else ""
                
                # Hiển thị độ đồng nhất hoặc gợi ý hành động ngay trên danh sách chính
                consistency = getattr(self, "_current_consistencies", {}).get(name)
                score_suffix = ""
                if consistency == "no_encoder":
                    score_suffix = " - Yêu cầu train Encoder"
                elif consistency == "need_samples":
                    score_suffix = " - Cần >= 2 mẫu"
                elif isinstance(consistency, float):
                    score_suffix = f" - Độ đồng nhất: {int(consistency * 100)}%"
                
                item = QListWidgetItem(f"{name} ({spell_counts[name]}){suffix}{score_suffix}")
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.spell_list.addItem(item)
        else:
            # Requirement 3: Empty State
            self.spell_stack.setCurrentIndex(1)

        filtered_names = sorted(list({
            n for n in display_names 
            if folder_name_match_key(n) not in {folder_name_match_key(p) for p in _PRIMITIVE_LOGICAL_NAMES}
        }))
        self._update_combo_box(filtered_names)

    def _on_filter_changed(self) -> None:
        self._refresh_spell_list()

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        """Hiển thị danh sách mẫu cho một câu thần chú cụ thể."""
        self.current_spell_name = spell_name
        self._current_samples = list(samples)
        self.lbl_current_spell.setText(tr_ui("record_spell_samples", name=spell_name))
        self.sample_list.clear()
        if samples:
            self.sample_stack.setCurrentIndex(0)
            scores = self._per_sample_scores
            for fname in samples:
                score = scores.get(fname)
                if score is None:
                    text = fname
                    item = QListWidgetItem(text)
                elif score >= 0.85:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(SUCCESS))
                elif score >= 0.70:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(WARNING))
                else:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(DANGER))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.sample_list.addItem(item)
        else:
            self.sample_stack.setCurrentIndex(1)
        self.stacked_spells.setCurrentIndex(1)
        # Apply any consistency result that arrived while we were on page 0
        if self._pending_consistency_result is not None:
            pending = self._pending_consistency_result
            self._pending_consistency_result = None
            self.update_consistency_display(pending)

    def update_consistency_display(self, result: dict) -> None:
        """Đập kết quả từ analyze_spell_samples vào UI consistency section."""
        # Cache result unconditionally so it survives a page switch
        self._pending_consistency_result = result

        # Chỉ render khi đang ở trang sample list
        if self.stacked_spells.currentIndex() != 1:
            return

        n = result.get("n_samples", 0)
        overall = result.get("overall_consistency")
        rec = result.get("recommendation", "")
        per_scores = result.get("per_sample_scores", [])
        ready = result.get("ready_to_register", False)

        # Update recommendation label
        self.lbl_consistency.setVisible(True)
        self.lbl_consistency.setText(rec)

        # Update progress bar
        if overall is not None:
            pct = int(overall * 100)
            self.consistency_bar.setValue(pct)
            self.consistency_bar.setFormat(f"Độ đồng nhất: {pct}%")
            self.consistency_bar.setVisible(True)
            if pct >= 85:
                bar_color = SUCCESS
            elif pct >= 70:
                bar_color = WARNING
            else:
                bar_color = DANGER
            self.consistency_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {bar_color}; }}"
                "QProgressBar { border-radius: 4px; background: #E5E5EA; text-align: center; }"
            )
        else:
            # n < 3: show dot-progress so user sees how many samples remain
            n_samples = result.get("n_samples", 0)
            filled = "●" * min(n_samples, 3)
            empty  = "○" * max(0, 3 - n_samples)
            self.consistency_bar.setValue(0)
            self.consistency_bar.setFormat(f"Thu mẫu: {filled}{empty}  ({n_samples}/3)")
            self.consistency_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #8E8E93; }"
                "QProgressBar { border-radius: 4px; background: #E5E5EA; text-align: center; color: #3a3a3c; }"
            )
            self.consistency_bar.setVisible(True)


        # Map per_sample_scores to filenames
        self._per_sample_scores = {}
        for i, fname in enumerate(self._current_samples):
            if i < len(per_scores):
                self._per_sample_scores[fname] = per_scores[i]

        # Re-render sample list with colors
        samples_snapshot = list(self._current_samples)
        if samples_snapshot:
            self.sample_list.clear()
            for fname in samples_snapshot:
                score = self._per_sample_scores.get(fname)
                if score is None:
                    item = QListWidgetItem(fname)
                elif score >= 0.85:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(SUCCESS))
                elif score >= 0.70:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(WARNING))
                else:
                    item = QListWidgetItem(f"{fname}  [{int(score*100)}%]")
                    item.setForeground(QColor(DANGER))
                    font = item.font(); font.setBold(True); item.setFont(font)
                self.sample_list.addItem(item)

        # Highlight worst outlier row in the list (already colored by score)
        worst_idx = result.get("worst_sample_idx")
        if worst_idx is not None and worst_idx < len(self._current_samples):
            item = self.sample_list.item(worst_idx)
            if item:
                item.setToolTip(
                    f"⚠️ Mẫu có điểm thấp nhất trong tập — cân nhắc xóa để cải thiện độ đồng nhất."
                )

    def on_spell_registered(self, spell_name: str) -> None:
        """Được gọi sau khi handler đăng ký prototype thành công."""
        self.lbl_consistency.setText(
            f"✅ '{spell_name}' đã đăng ký. Hiển thị [Ready] trong danh sách."
        )
        self.consistency_bar.setVisible(False)
        self._per_sample_scores = {}

    def set_consistency_score(self, score: float | str | None) -> None:
        """Legacy fallback — vẫn giữ để tương thích ngược."""
        # update_consistency_display đã xử lý đầy đủ hơn; method này không làm gì
        pass

    def refresh_styles(self) -> None:
        """Làm mới giao diện theo theme hiện tại."""
        p = theme_manager.get_palette()
        for g in [self.graph1, self.graph2]:
            g.setBackground("transparent")
            g.getAxis("left").setPen(p.TEXT_TERTIARY)
            g.getAxis("bottom").setPen(p.TEXT_TERTIARY)

    # ── Private methods ─────────────────────────

    def _setup_plots(self) -> None:
        """Cấu hình các đối tượng đồ thị pyqtgraph."""
        for plot in [self.graph1, self.graph2]:
            plot.setBackground("transparent")
            plot.showGrid(x=True, y=True, alpha=0.1)
            plot.getAxis("left").setPen(TEXT_MUTED)
            plot.getAxis("bottom").setPen(TEXT_MUTED)
            plot.setMenuEnabled(False)
            plot.setMouseEnabled(x=False, y=True)
            plot.getPlotItem().setClipToView(True)
            plot.getPlotItem().setDownsampling(auto=True, mode="peak")

        self.curve_ax = self.graph1.plot(pen=pg.mkPen(PLOT_AX_COLOR, width=2), name="aX")
        self.curve_ay = self.graph1.plot(pen=pg.mkPen(PLOT_AY_COLOR, width=2), name="aY")
        self.curve_az = self.graph1.plot(pen=pg.mkPen(PLOT_AZ_COLOR, width=2), name="aZ")
        self.curve_gx = self.graph2.plot(pen=pg.mkPen(PLOT_GX_COLOR, width=2), name="gX")
        self.curve_gy = self.graph2.plot(pen=pg.mkPen(PLOT_GY_COLOR, width=2), name="gY")
        self.curve_gz = self.graph2.plot(pen=pg.mkPen(PLOT_GZ_COLOR, width=2), name="gZ")

        self.graph1.addLegend()
        self.graph2.addLegend()
        self._add_crop_overlay()

    def _add_crop_overlay(self) -> None:
        """Thêm vùng chọn (crop) vào đồ thị gia tốc."""
        self.crop_region = pg.LinearRegionItem([_DEFAULT_CROP_START, _DEFAULT_CROP_END], brush=CROP_REGION)
        self.crop_region.setZValue(10)
        for handle in self.crop_region.lines:
            handle.setPen(pg.mkPen(ACCENT, width=3))
            handle.setHoverPen(pg.mkPen(PLOT_HANDLE_HOVER_COLOR, width=4))
        self.crop_region.hide()
        self.crop_region.sigRegionChanged.connect(self._on_crop_region_changed)
        self.graph1.addItem(self.crop_region)

    def _render_plots(self) -> None:
        """Vẽ dữ liệu cảm biến thời gian thực."""
        if not self.isVisible() or not self.is_live:
            return

        buf = self.store.get_live_buffer_snapshot()
        if not buf:
            return

        try:
            arr = np.asarray(buf, dtype=np.float32)
            if arr.ndim == 2 and arr.shape[1] >= 6:
                self.curve_ax.setData(arr[:, 0])
                self.curve_ay.setData(arr[:, 1])
                self.curve_az.setData(arr[:, 2])
                self.curve_gx.setData(arr[:, 3])
                self.curve_gy.setData(arr[:, 4])
                self.curve_gz.setData(arr[:, 5])
        except Exception as exc:
            log.warning("PageRecord: Render plots failed: %s", exc)

    def _build_left_column(self) -> QWidget:
        """Xây dựng cột chứa đồ thị."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        self.lbl_wand_status = QLabel(f"● {tr_ui('record_wait_serial')}")
        self.lbl_wand_status.setProperty("type", "status_label")
        self.lbl_wand_status.setProperty("status", "warning")
        self.lbl_timeline = make_section_label(tr_ui("record_timeline"), accent=True)
        self.lbl_timeline.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.lbl_wand_status)
        header.addWidget(self.lbl_timeline)
        layout.addLayout(header)

        card, card_layout = make_card(margins=(20, 20, 20, 20), spacing=SPACING_MD)

        self.graph1 = pg.PlotWidget()
        self.graph2 = pg.PlotWidget()
        self.graph1.setMinimumHeight(RECORD_GRAPH_MIN_H)
        self.graph2.setMinimumHeight(RECORD_GRAPH_MIN_H)
        card_layout.addWidget(self.graph1)
        card_layout.addWidget(self.graph2, stretch=1)
        layout.addWidget(card, stretch=1)

        layout.addLayout(self._build_left_controls())
        return widget

    def _build_left_controls(self) -> QHBoxLayout:
        """Các nút điều khiển đồ thị."""
        row = QHBoxLayout()
        self.chk_graph1 = make_checkbox(tr_ui("record_show_accel"), checked=True)
        self.chk_graph2 = make_checkbox(tr_ui("record_show_gyro"), checked=True)

        self.btn_zoom_in = IconButton("assets/icon/cooliocns SVG/Interface/Magnifying_Glass_Plus.svg", height=BTN_H)
        self.btn_zoom_out = IconButton("assets/icon/cooliocns SVG/Interface/Magnifying_Glass_Minus.svg", height=BTN_H)
        self.btn_zoom_fit = IconButton("assets/icon/cooliocns SVG/Arrow/Expand.svg", height=BTN_H)

        row.addWidget(self.chk_graph1, stretch=1)
        row.addWidget(self.chk_graph2, stretch=1)
        row.addStretch()
        row.addWidget(self.btn_zoom_in)
        row.addWidget(self.btn_zoom_out)
        row.addWidget(self.btn_zoom_fit)
        return row

    def _build_right_column(self) -> QWidget:
        """Xây dựng cột chứa workflow điều khiển."""
        widget = QWidget()
        widget.setMinimumWidth(RIGHT_MIN_W)
        widget.setMaximumWidth(RIGHT_MAX_W)
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(make_section_label(tr_ui("record_toolbar"), accent=True))
        layout.addWidget(self._build_detail_card())
        layout.addWidget(self._build_controls_card())

        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_spell_list_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)

        layout.addWidget(self._build_batch_card())
        return widget

    def _build_detail_card(self) -> QFrame:
        """Card chọn câu thần chú và thông số ghi."""
        card, layout = make_card(margins=(10, 10, 10, 10), spacing=SPACING_SM)

        form = QFormLayout()
        self.combo_spell = QComboBox()
        self.combo_spell.setEditable(True)
        self.combo_spell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lbl = QLabel(tr_ui("record_spell_label"))
        lbl.setProperty("type", "record_field_label")
        form.addRow(lbl, self.combo_spell)
        layout.addLayout(form)

        stats = QGridLayout()
        self.lbl_record_count = QLabel("0")
        self.lbl_record_count.setProperty("type", "record_metric_value")
        self.lbl_record_duration = QLabel("00:00")
        self.lbl_record_duration.setProperty("type", "record_metric_value")
        stats.addWidget(make_hint(tr_ui("record_hint_recorded")), 0, 0)
        stats.addWidget(make_hint(tr_ui("record_hint_duration")), 0, 1)
        stats.addWidget(self.lbl_record_count, 1, 0)
        stats.addWidget(self.lbl_record_duration, 1, 1)
        layout.addLayout(stats)
        return card

    def _build_controls_card(self) -> QFrame:
        """Card chứa các nút tác vụ ghi (Start/Stop/Snip)."""
        card, layout = make_card(margins=(10, 10, 10, 10), spacing=SPACING_SM)

        # Sắp xếp nút Start/Stop cạnh nhau, Snip chiếm trọn hàng để dễ thao tác
        row1 = QHBoxLayout()
        self.btn_start = make_button(tr_ui("record_btn_start"), "start", BTN_H)
        self.btn_stop = make_button(tr_ui("record_btn_stop"), "stop", BTN_H)
        self.btn_stop.setEnabled(False)
        row1.addWidget(self.btn_start)
        row1.addWidget(self.btn_stop)
        layout.addLayout(row1)

        self.btn_snip = make_button(tr_ui("record_btn_snip"), "snip", BTN_H)
        self.btn_snip.setEnabled(False)
        layout.addWidget(self.btn_snip)

        hint = make_hint(tr_ui("record_hint_controls"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return card

    def _build_batch_card(self) -> QFrame:
        """Card tác vụ hàng loạt — 3 nút xếp ngang."""
        card, layout = make_card(margins=(8, 8, 8, 8), spacing=SPACING_SM)
        layout.addWidget(make_section_label(tr_ui("record_batch"), accent=False))

        row = QHBoxLayout()
        row.setSpacing(SPACING_SM)

        self.btn_delete_selected = make_button(
            "🗑 Xóa đã chọn", "danger_outline", BTN_H
        )
        self.btn_delete_selected.setEnabled(False)
        self.btn_delete_selected.setToolTip("Chọn một hoặc nhiều mẫu trong danh sách rồi nhấn nút này để xóa.")
        self.btn_clear_samples = make_button(
            tr_ui("record_btn_clear"), "danger_outline", BTN_H
        )
        self.btn_export_csv = make_button(
            tr_ui("record_btn_export"), "base", BTN_H
        )

        row.addWidget(self.btn_delete_selected, stretch=1)
        row.addWidget(self.btn_clear_samples, stretch=1)
        row.addWidget(self.btn_export_csv, stretch=1)
        layout.addLayout(row)
        return card

    def _build_spell_list_page(self) -> QWidget:
        """Trang hiển thị danh sách câu thần chú (Requirement 3: Empty State)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)
        layout.addWidget(make_section_label(tr_ui("record_spell_list"), accent=False))

        self.spell_stack = QStackedWidget()

        # Thư viện thực
        lib_page = QWidget()
        lib_lay = QVBoxLayout(lib_page)
        lib_lay.setContentsMargins(0, 0, 0, 0)
        lib_lay.setSpacing(SPACING_SM)

        self.spell_list = QListWidget()
        lib_lay.addWidget(self.spell_list)
        self.spell_list.setProperty("type", "record_list")
        self.btn_delete_spell = make_button(tr_ui("record_delete_spell_btn"), "danger_outline", SPELL_BTN_H)
        lib_lay.addWidget(self.btn_delete_spell)

        self.spell_stack.addWidget(lib_page)

        # Requirement 3: Empty state
        empty_card, _ = self._make_empty_state()
        self.spell_stack.addWidget(empty_card)

        layout.addWidget(self.spell_stack)
        return page

    def _build_sample_list_page(self) -> QWidget:
        """Trang hiển thị danh sách mẫu đã thu thập."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)
        top = QHBoxLayout()
        self.btn_back_spells = make_button(tr_ui("record_btn_back"), "back", SPELL_BTN_H)
        self.lbl_current_spell = QLabel("…")
        self.lbl_current_spell.setProperty("type", "record_current_spell")
        self.lbl_current_spell.setWordWrap(True)
        top.addWidget(self.btn_back_spells)
        top.addWidget(self.lbl_current_spell)
        layout.addLayout(top)

        self.lbl_consistency = QLabel("")
        self.lbl_consistency.setWordWrap(True)
        self.lbl_consistency.setStyleSheet("margin: 5px 0px; font-size: 13px;")
        layout.addWidget(self.lbl_consistency)

        self.sample_list = QListWidget()
        self.sample_list.setProperty("type", "record_list")
        self.sample_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.sample_stack = QStackedWidget()
        self.sample_stack.addWidget(self.sample_list)
        empty_card, _ = make_empty_state_card()
        self.sample_stack.addWidget(empty_card)
        layout.addWidget(self.sample_stack)

        # ── Consistency Analysis section ─────────────────────
        self.consistency_bar = QProgressBar()
        self.consistency_bar.setRange(0, 100)
        self.consistency_bar.setValue(0)
        self.consistency_bar.setTextVisible(True)
        self.consistency_bar.setFixedHeight(18)
        self.consistency_bar.setVisible(False)
        layout.addWidget(self.consistency_bar)

        return page

    def _make_empty_state(self) -> tuple[QFrame, QVBoxLayout]:
        """Requirement 3: Centered empty state with icon."""
        return make_empty_state_card()

    def _update_combo_box(self, names: list[str]) -> None:
        """Cập nhật dữ liệu cho combo box chọn spell."""
        curr = self.combo_spell.currentText()
        self.combo_spell.clear()
        self.combo_spell.addItems(names)
        if curr:
            idx = self.combo_spell.findText(curr)
            if idx >= 0:
                self.combo_spell.setCurrentIndex(idx)

    def _configure_accessibility(self) -> None:
        """Cấu hình các thuộc tính trợ năng."""
        self.btn_start.setAccessibleName("Bắt đầu ghi cử chỉ")
        self.btn_stop.setAccessibleName("Dừng ghi cử chỉ")
        self.btn_snip.setAccessibleName("Cắt vùng chọn làm mẫu")
        self.setTabOrder(self.combo_spell, self.btn_start)
        self.setTabOrder(self.btn_start, self.btn_stop)
        self.setTabOrder(self.btn_stop, self.btn_snip)

    # ── Slots ───────────────────────────────────

    def _on_btn_start_clicked(self) -> None:
        """Bắt đầu quá trình ghi dữ liệu."""
        spell = self.combo_spell.currentText().strip()
        if not spell:
            self.lbl_wand_status.setText(f"⚠ {tr_ui('record_select_spell')}")
            return
        self.is_live = True
        self.btn_snip.setEnabled(False)
        self.crop_region.hide()
        self.set_recording_state(True)
        self._recording_start_time.start()
        self._recording_timer.start(_TIMER_INTERVAL_MS)
        self.sig_start_record.emit(spell)

    def _on_btn_stop_clicked(self) -> None:
        """Dừng quá trình ghi và hiển thị vùng chọn snip."""
        self.is_live = False
        self.set_recording_state(False)
        self.btn_snip.setEnabled(True)
        self.crop_region.show()
        buf_len = len(self.store.get_live_buffer_snapshot())
        if buf_len > 0:
            start = max(0, buf_len - _AUTO_CROP_TAIL)
            self.crop_region.setRegion([start, buf_len])
        self._recording_timer.stop()
        self.lbl_record_duration.setText("00:00")
        self.sig_stop_record.emit()

    def _on_btn_snip_clicked(self) -> None:
        """Cắt vùng dữ liệu đã chọn và gửi signal lưu trữ."""
        if not self.crop_region.isVisible():
            return
        spell = self.combo_spell.currentText().strip()
        region = self.crop_region.getRegion()
        buf = self.store.get_live_buffer_snapshot()
        idx_min, idx_max = max(0, int(region[0])), min(len(buf), int(region[1]))
        if idx_min < idx_max:
            self.sig_data_cropped.emit(buf[idx_min:idx_max], spell)
            self.lbl_wand_status.setText(tr_ui("record_snipped", n=idx_max-idx_min, name=spell))
        self.sig_snip_record.emit()

    def _on_crop_region_changed(self) -> None:
        """Cập nhật số mẫu đang được chọn trong vùng snip."""
        if not self.crop_region.isVisible():
            return
        r = self.crop_region.getRegion()
        n = max(0, int(r[1]) - int(r[0]))
        self.lbl_record_count.setText(tr_ui("record_selected_samples", n=n))

    def _update_recording_duration(self) -> None:
        """Cập nhật thời gian đã ghi trên giao diện."""
        if self._recording_timer.isActive():
            ms = self._recording_start_time.elapsed()
            self.lbl_record_duration.setText(f"{ms//60000:02d}:{(ms % 60000)//1000:02d}")

    def _on_zoom_in_clicked(self) -> None:
        for g in [self.graph1, self.graph2]:
            g.getViewBox().scaleBy((0.8, 0.8))

    def _on_zoom_out_clicked(self) -> None:
        for g in [self.graph1, self.graph2]:
            g.getViewBox().scaleBy((1.25, 1.25))

    def _on_zoom_fit_clicked(self) -> None:
        for g in [self.graph1, self.graph2]:
            g.getViewBox().autoRange()

    def _on_btn_clear_clicked(self) -> None:
        """Xóa sạch bộ đệm dữ liệu tạm thời."""
        if confirm_destructive(self, title=tr_ui("record_clear_title"), message=tr_ui("record_clear_msg")):
            self.sig_clear_buffer.emit()
            self.lbl_record_count.setText("0")
            self.is_live = True
            self.crop_region.hide()

    def _on_btn_export_clicked(self) -> None:
        """Xuất dữ liệu thô ra file CSV."""
        if self.store.get_live_buffer_snapshot():
            self.sig_export_csv.emit()

    def _on_sample_selection_changed(self) -> None:
        """Bật/tắt nút xóa theo số mẫu đang được chọn."""
        n = len(self.sample_list.selectedItems())
        self.btn_delete_selected.setEnabled(n > 0)
        if n == 0:
            self.btn_delete_selected.setText("🗑 Xóa đã chọn")
        elif n == 1:
            self.btn_delete_selected.setText("🗑 Xóa 1 mẫu")
        else:
            self.btn_delete_selected.setText(f"🗑 Xóa {n} mẫu")

    def _on_btn_delete_selected_clicked(self) -> None:
        """Xóa các mẫu đang được chọn trong sample_list."""
        spell = self.current_spell_name
        if not spell:
            return
        selected_items = self.sample_list.selectedItems()
        if not selected_items:
            return

        # Strip score annotation to get bare filename
        fnames = [item.text().split("  [")[0].strip() for item in selected_items]
        n = len(fnames)
        label = f"'{fnames[0]}'" if n == 1 else f"{n} mẫu"

        if not confirm_destructive(
            self,
            title=f"Xóa {label}",
            message=f"Xóa {label} khỏi spell '{spell}'?\nHành động này không thể hoàn tác."
        ):
            return

        from pathlib import Path
        from logic.dataset_layout import storage_dirs_for_spell
        dataset_root = Path(self.store.dataset_dir)
        dirs = storage_dirs_for_spell(dataset_root, spell)
        deleted = 0
        for fname in fnames:
            for d in dirs:
                fpath = d / fname
                if fpath.exists():
                    try:
                        fpath.unlink()
                        deleted += 1
                    except Exception as exc:
                        log.error("Delete sample '%s' failed: %s", fname, exc)
                    break  # found in this dir, no need to check others

        if deleted:
            self.btn_delete_selected.setText("🗑 Xóa đã chọn")
            self.btn_delete_selected.setEnabled(False)
            samples = self.store.get_samples_for_spell(spell)
            self.load_samples_for_spell(spell, samples)
            self.store.refresh_database(force=True)

    def _on_spell_item_clicked(self, item: QListWidgetItem) -> None:
        """Khi chọn một spell từ danh sách thư viện."""
        name = item.data(Qt.ItemDataRole.UserRole)
        if name != _EMPTY_SPELL_LIST:
            idx = self.combo_spell.findText(name)
            if idx >= 0:
                self.combo_spell.setCurrentIndex(idx)
            self.sig_spell_selected.emit(name)

    def _on_btn_delete_spell_clicked(self) -> None:
        """Xóa vĩnh viễn một câu thần chú cùng toàn bộ dataset của nó."""
        item = self.spell_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) == _EMPTY_SPELL_LIST:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if is_system_spell(name):
            QMessageBox.warning(self, tr_ui("record_protected_title"), tr_ui("record_protected_msg", name=name))
            return
        if confirm_destructive(self, title=tr_ui("record_del_step1_title"), message=tr_ui("record_del_step1_msg", name=name)):
            if confirm_destructive(self, title=tr_ui("record_del_step2_title"), message=tr_ui("record_del_step2_msg", name=name)):
                self.sig_spell_deleted.emit(name)

    def _on_btn_back_clicked(self) -> None:
        """Quay lại danh sách câu thần chú."""
        self.current_spell_name = ""
        self.lbl_consistency.setText("")
        self.lbl_consistency.setVisible(False)
        self._pending_consistency_result = None  # discard stale analysis from previous spell
        self.stacked_spells.setCurrentIndex(0)

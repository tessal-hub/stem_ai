from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.component_factory import make_button, make_card_frame, make_hint, make_section_label
from ui.layout_utils import clear_layout
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from ui.tokens import (
    ACCENT_TEXT,
    BG_DARK,
    BTN_H,
    DANGER,
    PLOT_AX_COLOR,
    PLOT_AY_COLOR,
    PLOT_AZ_COLOR,
    PLOT_GX_COLOR,
    PLOT_GY_COLOR,
    PLOT_GZ_COLOR,
    RIGHT_MAX_W,
    STYLE_BTN_BASE,
    STYLE_BTN_PRIMARY,
    STYLE_BTN_SNIP,
    STYLE_BTN_START,
    STYLE_BTN_STOP,
    STYLE_RECORD_FIELD_LABEL,
    STYLE_RECORD_MAIN_CONTAINER,
    STYLE_RECORD_STATUS_TEMPLATE,
    STYLE_SCROLL_AREA,
    STYLE_STATISTICS_CARD,
    STYLE_STATISTICS_MAIN_CONTAINER,
    STYLE_TRANSPARENT_WIDGET,
    SUCCESS,
    TEXT_BODY,
    TEXT_MUTED,
    WARNING,
    APP_FONT_STACK,
    TITLE_FONT_STACK,
    CARD_RADIUS,
    BTN_RADIUS,
    INPUT_RADIUS,
)

from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from logic.primitive_i18n import get_primitive_catalog
from ui.i18n_bridge import tr_ui

def get_style_group_done():
    return (
        f"QPushButton {{ background-color: {SUCCESS}; color: {ACCENT_TEXT}; border: none; border-radius: {BTN_RADIUS}; "
        f"font-family: {APP_FONT_STACK}; font-size: 11px; font-weight: 700; padding: 5px 10px; }}"
        f" QPushButton:hover {{ background-color: {SUCCESS}; color: {ACCENT_TEXT}; }}"
    )


class PagePrimitiveCollect(QWidget):
    """
    Trang thu thập cử chỉ nguyên thủy — tạo training data cho encoder model.
    """

    sig_start_collection = pyqtSignal(str, str)  # (gesture_name, group_name)
    sig_stop_collection = pyqtSignal()
    sig_capture_collection = pyqtSignal(str, str)  # (gesture_name, group_name)
    sig_train_encoder_requested = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.store = data_store
        self._selected_gesture: str | None = None
        self._selected_group: str | None = None
        self._collecting = False
        self._capture_ready = False
        self._catalog = get_primitive_catalog(locale_manager.current_language)
        self._stats = {name: 0 for name in self._catalog}
        self._card_widgets: dict[str, dict] = {}

        self._init_ui()
        self._setup_plot()
        self._load_data()

    def apply_ui_language(self) -> None:
        """Reload primitive catalog for locale and rebuild gesture cards."""
        prev = dict(self._stats)
        self._catalog = get_primitive_catalog(locale_manager.current_language)
        self._stats = {name: int(prev.get(name, 0)) for name in self._catalog}
        self._rebuild_cards()
        self.update_collection_stats(self._stats)
        self._sec_preview.setText(tr_ui("primitive_signal_preview"))
        self._sec_quality.setText(tr_ui("primitive_quality"))
        self._lbl_q_samples.setText(tr_ui("primitive_lbl_samples"))
        self._lbl_q_duration.setText(tr_ui("primitive_lbl_duration"))
        self._lbl_q_motion.setText(tr_ui("primitive_lbl_motion"))
        self._lbl_q_clip.setText(tr_ui("primitive_lbl_clipping"))
        self.quality_score.setFormat(tr_ui("primitive_quality_bar"))
        self._sec_encoder.setText(tr_ui("primitive_encoder"))
        self.btn_train_encoder.setText(tr_ui("primitive_btn_train"))
        self._lbl_ratio_title.setText(tr_ui("primitive_lbl_distance_ratio"))
        self._lbl_f5_title.setText(tr_ui("primitive_lbl_fewshot_5"))
        self._lbl_f10_title.setText(tr_ui("primitive_lbl_fewshot_10"))
        self.btn_start_collect.setText(tr_ui("record_btn_start"))
        self.btn_stop_collect.setText(tr_ui("record_btn_stop"))
        self.btn_capture_collect.setText(tr_ui("primitive_btn_capture"))
        self.btn_start_collect.setToolTip(tr_ui("record_tt_start"))
        self.btn_stop_collect.setToolTip(tr_ui("record_tt_stop"))
        self.btn_capture_collect.setToolTip(tr_ui("record_tt_snip"))
        self.lbl_instruction.setText(tr_ui("primitive_flow_hint"))
        self.reset_quality_evaluation(collecting=self._collecting)
        if self._selected_gesture and self._selected_group:
            self._set_instruction_for_selection()

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        
        # 1. Update Plot Styles
        self.preview_plot.setBackground("transparent")
        self.preview_plot.getAxis("left").setPen(p.TEXT_TERTIARY)
        self.preview_plot.getAxis("bottom").setPen(p.TEXT_TERTIARY)
        
        # 2. Update Cards
        for card in [self.preview_card, self.quality_card, self.train_card]:
            card.setStyleSheet(f"""
                #VanguardCardOuter {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: {CARD_RADIUS}; }}
                #VanguardCardInner {{ background-color: {p.SURFACE_PRIMARY}; border: none; border-radius: calc({CARD_RADIUS} - 4px); }}
            """)
            
        # 3. Update Quality evaluation styles
        self.lbl_quality_samples.setStyleSheet(f"color: {p.TEXT_PRIMARY}; font-family: {APP_FONT_STACK};")
        self.lbl_quality_duration.setStyleSheet(f"color: {p.TEXT_PRIMARY}; font-family: {APP_FONT_STACK};")
        self.lbl_quality_motion.setStyleSheet(f"color: {p.TEXT_PRIMARY}; font-family: {APP_FONT_STACK};")
        self.lbl_quality_clipping.setStyleSheet(f"color: {p.TEXT_PRIMARY}; font-family: {APP_FONT_STACK};")
        
        # 4. Update Gesture Cards
        self._rebuild_cards()

    def _init_ui(self) -> None:
        """Xây dựng layout chính gồm 2 cột: gesture cards và controls/plot."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)

        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)
        content.addWidget(self._build_left_column(), stretch=3)
        content.addWidget(self._build_right_column(), stretch=2)
        outer.addLayout(content)
        
        self.refresh_styles()

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        from ui.component_factory import make_card
        
        # Preview Card
        self.preview_card, preview_layout = make_card()
        self.preview_card.setObjectName("VanguardCardOuter")
        self._sec_preview = make_section_label(tr_ui("primitive_signal_preview"), accent=True)
        preview_layout.addWidget(self._sec_preview)

        self.preview_plot = pg.PlotWidget()
        self.preview_plot.setMinimumHeight(320)
        preview_layout.addWidget(self.preview_plot)
        layout.addWidget(self.preview_card, stretch=3)

        # Quality Card
        self.quality_card, quality_layout = make_card()
        self._sec_quality = make_section_label(tr_ui("primitive_quality"), accent=True)
        quality_layout.addWidget(self._sec_quality)

        self.lbl_quality_status = QLabel(tr_ui("primitive_quality_none"))
        quality_layout.addWidget(self.lbl_quality_status)

        self.quality_score = QProgressBar()
        self.quality_score.setRange(0, 100)
        self.quality_score.setValue(0)
        self.quality_score.setFixedHeight(12)
        self.quality_score.setStyleSheet(f"QProgressBar {{ background-color: {theme_manager.get_palette().SURFACE_TERTIARY}; border: none; border-radius: {INPUT_RADIUS}; }} QProgressBar::chunk {{ background-color: {theme_manager.get_palette().PRIMARY}; border-radius: {INPUT_RADIUS}; }}")
        quality_layout.addWidget(self.quality_score)

        quality_grid = QGridLayout()
        quality_grid.setHorizontalSpacing(SPACING_MD)
        quality_grid.setVerticalSpacing(SPACING_SM)

        self._lbl_q_samples = QLabel(tr_ui("primitive_lbl_samples"))
        self.lbl_quality_samples = QLabel("--")

        self._lbl_q_duration = QLabel(tr_ui("primitive_lbl_duration"))
        self.lbl_quality_duration = QLabel("--")

        self._lbl_q_motion = QLabel(tr_ui("primitive_lbl_motion"))
        self.lbl_quality_motion = QLabel("--")

        self._lbl_q_clip = QLabel(tr_ui("primitive_lbl_clipping"))
        self.lbl_quality_clipping = QLabel("--")

        quality_grid.addWidget(self._lbl_q_samples, 0, 0)
        quality_grid.addWidget(self.lbl_quality_samples, 0, 1)
        quality_grid.addWidget(self._lbl_q_duration, 1, 0)
        quality_grid.addWidget(self.lbl_quality_duration, 1, 1)
        quality_grid.addWidget(self._lbl_q_motion, 2, 0)
        quality_grid.addWidget(self.lbl_quality_motion, 2, 1)
        quality_grid.addWidget(self._lbl_q_clip, 3, 0)
        quality_grid.addWidget(self.lbl_quality_clipping, 3, 1)
        quality_layout.addLayout(quality_grid)

        self.lbl_quality_notes = make_hint(tr_ui("primitive_quality_hint_start"))
        quality_layout.addWidget(self.lbl_quality_notes)
        layout.addWidget(self.quality_card, stretch=2)

        # Train Card
        self.train_card, train_layout = make_card()
        self._sec_encoder = make_section_label(tr_ui("primitive_encoder"), accent=True)
        train_layout.addWidget(self._sec_encoder)

        self.encoder_progress = QProgressBar()
        self.encoder_progress.setRange(0, 100)
        self.encoder_progress.setValue(0)
        self.encoder_progress.setFixedHeight(12)
        self.encoder_progress.setStyleSheet(f"QProgressBar {{ background-color: {theme_manager.get_palette().SURFACE_TERTIARY}; border: none; border-radius: {INPUT_RADIUS}; }} QProgressBar::chunk {{ background-color: {theme_manager.get_palette().PRIMARY}; border-radius: {INPUT_RADIUS}; }}")
        train_layout.addWidget(self.encoder_progress)

        self.lbl_encoder_status = QLabel(tr_ui("primitive_encoder_not_ready"))
        train_layout.addWidget(self.lbl_encoder_status)

        self.btn_train_encoder = make_button(tr_ui("primitive_btn_train"), style=STYLE_BTN_PRIMARY, height=BTN_H)
        self.btn_train_encoder.setEnabled(False)
        train_layout.addWidget(self.btn_train_encoder)

        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(SPACING_MD)
        metrics_grid.setVerticalSpacing(SPACING_SM)

        self._lbl_ratio_title = QLabel(tr_ui("primitive_lbl_distance_ratio"))
        self.lbl_distance_ratio = QLabel("--")
        self._lbl_f5_title = QLabel(tr_ui("primitive_lbl_fewshot_5"))
        self.lbl_fewshot_5 = QLabel("--")
        self._lbl_f10_title = QLabel(tr_ui("primitive_lbl_fewshot_10"))
        self.lbl_fewshot_10 = QLabel("--")

        metrics_grid.addWidget(self._lbl_ratio_title, 0, 0)
        metrics_grid.addWidget(self.lbl_distance_ratio, 0, 1)
        metrics_grid.addWidget(self._lbl_f5_title, 1, 0)
        metrics_grid.addWidget(self.lbl_fewshot_5, 1, 1)
        metrics_grid.addWidget(self._lbl_f10_title, 2, 0)
        metrics_grid.addWidget(self.lbl_fewshot_10, 2, 1)
        train_layout.addLayout(metrics_grid)

        layout.addWidget(self.train_card, stretch=2)
        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)
        scroll_content = QWidget()
        scroll_content.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        self.cards_layout = QVBoxLayout(scroll_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(SPACING_SM)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(SPACING_SM)
        self.btn_start_collect = make_button(tr_ui("record_btn_start"), STYLE_BTN_START, BTN_H)
        self.btn_stop_collect = make_button(tr_ui("record_btn_stop"), STYLE_BTN_STOP, BTN_H)
        self.btn_capture_collect = make_button(tr_ui("primitive_btn_capture"), STYLE_BTN_SNIP, BTN_H)
        self.btn_stop_collect.setEnabled(False)
        self.btn_capture_collect.setEnabled(False)
        self.btn_start_collect.clicked.connect(self._on_start_clicked)
        self.btn_stop_collect.clicked.connect(self._on_stop_clicked)
        self.btn_capture_collect.clicked.connect(self._on_capture_clicked)
        self.btn_start_collect.setToolTip(tr_ui("record_tt_start"))
        self.btn_stop_collect.setToolTip(tr_ui("record_tt_stop"))
        self.btn_capture_collect.setToolTip(tr_ui("record_tt_snip"))
        actions.addWidget(self.btn_start_collect)
        actions.addWidget(self.btn_stop_collect)
        actions.addWidget(self.btn_capture_collect)
        layout.addLayout(actions)

        self.lbl_instruction = make_hint(tr_ui("primitive_flow_hint"))
        layout.addWidget(self.lbl_instruction)

        self._rebuild_cards()
        return widget

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu và làm mới trạng thái nút."""
        self.update_collection_stats(self._stats)
        self._refresh_action_buttons()

    def _setup_plot(self) -> None:
        """Cấu hình PyQtGraph plot cho signal preview."""
        self.preview_plot.setBackground(BG_DARK)
        self.preview_plot.showGrid(x=True, y=True, alpha=0.15)
        self.preview_plot.setMenuEnabled(False)
        self.preview_plot.setMouseEnabled(x=False, y=True)
        self.preview_plot.getAxis("left").setPen(TEXT_MUTED)
        self.preview_plot.getAxis("bottom").setPen(TEXT_MUTED)

        self.curve_ax = self.preview_plot.plot(pen=pg.mkPen(PLOT_AX_COLOR, width=2), name="ax")
        self.curve_ay = self.preview_plot.plot(pen=pg.mkPen(PLOT_AY_COLOR, width=2), name="ay")
        self.curve_az = self.preview_plot.plot(pen=pg.mkPen(PLOT_AZ_COLOR, width=2), name="az")
        self.curve_gx = self.preview_plot.plot(pen=pg.mkPen(PLOT_GX_COLOR, width=2), name="gx")
        self.curve_gy = self.preview_plot.plot(pen=pg.mkPen(PLOT_GY_COLOR, width=2), name="gy")
        self.curve_gz = self.preview_plot.plot(pen=pg.mkPen(PLOT_GZ_COLOR, width=2), name="gz")
        self.preview_plot.addLegend()

    def _resolve_sample_rate_hz(self) -> float:
        if not hasattr(self.store, "get_settings_snapshot"):
            return 50.0
        settings = self.store.get_settings_snapshot()
        raw_rate = str(settings.get("sample_rate", "50"))
        digits = "".join(ch for ch in raw_rate if ch.isdigit())
        try:
            return max(1.0, float(digits))
        except ValueError:
            return 50.0

    def reset_quality_evaluation(self, *, collecting: bool = False) -> None:
        self.quality_score.setValue(0)
        self.lbl_quality_samples.setText("--")
        self.lbl_quality_duration.setText("--")
        self.lbl_quality_motion.setText("--")
        self.lbl_quality_clipping.setText("--")
        if collecting:
            self.lbl_quality_status.setText(tr_ui("primitive_collecting"))
            self.lbl_quality_notes.setText(tr_ui("primitive_collecting_hint"))
        else:
            self.lbl_quality_status.setText(tr_ui("primitive_quality_none"))
            self.lbl_quality_notes.setText(tr_ui("primitive_quality_hint_start"))
        self.lbl_quality_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=TEXT_MUTED))

    def update_quality_assessment(self, buffer_snapshot: list) -> None:
        if not buffer_snapshot:
            self.reset_quality_evaluation(collecting=False)
            return

        arr = np.asarray(buffer_snapshot, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] < 6:
            self.reset_quality_evaluation(collecting=False)
            return

        sample_count = int(arr.shape[0])
        sample_rate = self._resolve_sample_rate_hz()
        duration_sec = sample_count / sample_rate

        accel_mag = np.linalg.norm(arr[:, :3], axis=1)
        gyro_mag = np.linalg.norm(arr[:, 3:6], axis=1)
        accel_span = float(np.percentile(accel_mag, 95) - np.percentile(accel_mag, 5))
        gyro_span = float(np.percentile(gyro_mag, 95) - np.percentile(gyro_mag, 5))
        clip_ratio = float(np.mean(np.abs(arr) >= 0.98))

        sample_score = min(1.0, sample_count / 80.0)
        if duration_sec < 0.4:
            duration_score = max(0.0, duration_sec / 0.4)
        elif duration_sec > 3.5:
            duration_score = max(0.0, 1.0 - ((duration_sec - 3.5) / 3.5))
        else:
            duration_score = 1.0
        motion_score = min(1.0, ((accel_span / 0.45) + (gyro_span / 1.2)) * 0.5)
        clip_score = max(0.0, 1.0 - (clip_ratio * 3.0))

        overall_score = int(
            round(
                100.0
                * (
                    (0.35 * sample_score)
                    + (0.25 * duration_score)
                    + (0.25 * motion_score)
                    + (0.15 * clip_score)
                )
            )
        )
        overall_score = max(0, min(100, overall_score))

        if overall_score >= 80:
            quality_text = tr_ui("primitive_q_tier_high")
            quality_color = SUCCESS
        elif overall_score >= 60:
            quality_text = tr_ui("primitive_q_tier_mid")
            quality_color = WARNING
        else:
            quality_text = tr_ui("primitive_q_tier_low")
            quality_color = DANGER

        notes: list[str] = []
        if sample_count < 40:
            notes.append(tr_ui("primitive_note_short_samples"))
        if duration_sec < 0.5:
            notes.append(tr_ui("primitive_note_short_dur"))
        if motion_score < 0.35:
            notes.append(tr_ui("primitive_note_low_motion"))
        if clip_ratio > 0.12:
            notes.append(tr_ui("primitive_note_clipping"))
        if not notes:
            notes.append(tr_ui("primitive_note_ok"))

        self.quality_score.setValue(overall_score)
        self.lbl_quality_samples.setText(str(sample_count))
        self.lbl_quality_duration.setText(f"{duration_sec:.2f}s")
        self.lbl_quality_motion.setText(f"{int(round(motion_score * 100.0))}%")
        self.lbl_quality_clipping.setText(f"{clip_ratio * 100.0:.1f}%")
        self.lbl_quality_status.setText(f"{quality_text} ({overall_score}/100)")
        self.lbl_quality_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=quality_color))
        self.lbl_quality_notes.setText(" | ".join(notes))

    def _rebuild_cards(self) -> None:
        clear_layout(self.cards_layout)
        self._card_widgets.clear()
        for gesture_name, info in self._catalog.items():
            card = QFrame()
            card.setObjectName("CardFrame")
            card.setStyleSheet(STYLE_STATISTICS_CARD)
            card.installEventFilter(self)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
            card_layout.setSpacing(SPACING_SM)

            title = QLabel(gesture_name)
            title.setStyleSheet(f"{STYLE_RECORD_FIELD_LABEL} font-size: 13px; font-weight: 700; color: {theme_manager.get_palette().TEXT_PRIMARY};")
            desc = QLabel(info["description"])
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-family: {APP_FONT_STACK};")

            progress = QProgressBar()
            progress.setRange(0, int(info["target_samples"]))
            progress.setValue(0)
            progress.setFixedHeight(8)
            progress.setFormat(f"%v/{int(info['target_samples'])}")
            progress.setStyleSheet(f"QProgressBar {{ background-color: {theme_manager.get_palette().SURFACE_TERTIARY}; border: none; border-radius: {INPUT_RADIUS}; }} QProgressBar::chunk {{ background-color: {theme_manager.get_palette().PRIMARY}; border-radius: {INPUT_RADIUS}; }}")

            groups_grid = QGridLayout()
            groups_grid.setHorizontalSpacing(SPACING_SM)
            groups_grid.setVerticalSpacing(SPACING_SM)
            group_buttons: dict[str, QWidget] = {}
            for idx, (group_name, group_info) in enumerate(info["groups"].items()):
                group_btn = make_button(
                    f"{group_name[0]}: 0/{int(group_info['count'])}",
                    STYLE_BTN_BASE,
                    BTN_H,
                )
                group_btn.clicked.connect(
                    lambda _checked=False, g=gesture_name, gr=group_name: self._on_group_selected(g, gr)
                )
                groups_grid.addWidget(group_btn, 0, idx)
                group_buttons[group_name] = group_btn

            card_layout.addWidget(title)
            card_layout.addWidget(desc)
            card_layout.addWidget(progress)
            card_layout.addLayout(groups_grid)
            self.cards_layout.addWidget(card)

            self._card_widgets[gesture_name] = {
                "card": card,
                "progress": progress,
                "groups": group_buttons,
            }
            card.setProperty("gesture_name", gesture_name)

        self.cards_layout.addStretch()

    def _on_group_selected(self, gesture_name: str, group_name: str) -> None:
        if self._collecting or self._capture_ready:
            return
        self._selected_gesture = gesture_name
        self._selected_group = group_name
        self._set_instruction_for_selection()
        self._refresh_group_button_styles()
        self._refresh_action_buttons()

    def _on_start_clicked(self) -> None:
        if not self._selected_gesture or not self._selected_group:
            return
        self._capture_ready = False
        self._refresh_action_buttons()
        self.sig_start_collection.emit(self._selected_gesture, self._selected_group)

    def _on_stop_clicked(self) -> None:
        if self._collecting:
            self.sig_stop_collection.emit()

    def _on_capture_clicked(self) -> None:
        if not self._selected_gesture or not self._selected_group or not self._capture_ready:
            return
        self._capture_ready = False
        self._refresh_action_buttons()
        self.sig_capture_collection.emit(self._selected_gesture, self._selected_group)

    def _refresh_action_buttons(self) -> None:
        can_start = bool(self._selected_gesture and self._selected_group and not self._collecting)
        self.btn_start_collect.setEnabled(can_start)
        self.btn_stop_collect.setEnabled(self._collecting)
        self.btn_capture_collect.setEnabled(
            bool(
                self._capture_ready
                and not self._collecting
                and self._selected_gesture
                and self._selected_group
            )
        )

    def _refresh_group_button_styles(self) -> None:
        for gesture_name, widgets in self._card_widgets.items():
            for group_name, button in widgets["groups"].items():
                is_selected = (gesture_name == self._selected_gesture and group_name == self._selected_group)
                if is_selected:
                    button.setStyleSheet(STYLE_BTN_PRIMARY)
                else:
                    button.setStyleSheet(STYLE_BTN_BASE)

    def _set_instruction_for_selection(self) -> None:
        if not self._selected_gesture or not self._selected_group:
            self.lbl_instruction.setText("Chọn gesture và group để bắt đầu.")
            return
        instruction = self._catalog[self._selected_gesture]["groups"][self._selected_group]["instruction"]
        self.lbl_instruction.setText(f"[{self._selected_gesture} / {self._selected_group}] {instruction}")

    def _compute_group_counts(self, gesture_name: str, total_count: int) -> dict[str, int]:
        result: dict[str, int] = {}
        remaining = int(total_count)
        for group_name, group_info in self._catalog[gesture_name]["groups"].items():
            target = int(group_info["count"])
            current = max(0, min(target, remaining))
            result[group_name] = current
            remaining -= current
        return result

    def _auto_select_next_group_if_completed(self) -> None:
        if self._collecting or not self._selected_gesture or not self._selected_group:
            return
        total = int(self._stats.get(self._selected_gesture, 0))
        group_counts = self._compute_group_counts(self._selected_gesture, total)
        groups = list(self._catalog[self._selected_gesture]["groups"].items())
        for idx, (group_name, group_info) in enumerate(groups):
            if group_name != self._selected_group:
                continue
            if group_counts.get(group_name, 0) < int(group_info["count"]):
                return
            next_idx = idx + 1
            if next_idx < len(groups):
                self._selected_group = groups[next_idx][0]
                self._set_instruction_for_selection()
                self._refresh_group_button_styles()
            return

    # ── Inbound methods (called by Handler/MainWindow) ───────────────────────

    def set_collection_state(self, collecting: bool) -> None:
        self._collecting = bool(collecting)
        if self._collecting:
            self._capture_ready = False
            self.reset_quality_evaluation(collecting=True)
        self._refresh_action_buttons()
        for gesture_name, widgets in self._card_widgets.items():
            for group_name, button in widgets["groups"].items():
                if self._collecting and (gesture_name != self._selected_gesture or group_name != self._selected_group):
                    button.setEnabled(False)
                else:
                    button.setEnabled(True)

    def set_capture_ready(self, ready: bool) -> None:
        self._capture_ready = bool(
            ready and not self._collecting and self._selected_gesture and self._selected_group
        )
        if self._capture_ready:
            self.lbl_encoder_status.setText("Đã dừng thu. Bấm CAPTURE để lưu mẫu primitive.")
            self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING))
        self._refresh_action_buttons()

    def on_capture_saved(self, success: bool, message: str) -> None:
        if success:
            self.lbl_encoder_status.setText("Đã CAPTURE mẫu primitive.")
            self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS))
            self._capture_ready = False
        else:
            self.lbl_encoder_status.setText(f"CAPTURE thất bại: {message}")
            self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING))
            self._capture_ready = True
        self._refresh_action_buttons()

    def update_signal_preview(self, buffer_snapshot: list) -> None:
        if not buffer_snapshot:
            return
        arr = np.asarray(buffer_snapshot, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] < 6:
            return
        self.curve_ax.setData(arr[:, 0])
        self.curve_ay.setData(arr[:, 1])
        self.curve_az.setData(arr[:, 2])
        self.curve_gx.setData(arr[:, 3])
        self.curve_gy.setData(arr[:, 4])
        self.curve_gz.setData(arr[:, 5])
        self.update_quality_assessment(buffer_snapshot)

    def on_encoder_training_status(self, message: str) -> None:
        self.lbl_encoder_status.setText(message)
        self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=TEXT_BODY))

    def on_encoder_training_progress(self, value: int) -> None:
        self.encoder_progress.setValue(max(0, min(100, int(value))))

    def on_encoder_training_finished(self, success: bool, message: str) -> None:
        if success:
            self.lbl_encoder_status.setText("Encoder training hoàn tất")
            self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=SUCCESS))
            self._apply_metrics_from_summary(message)
        else:
            self.lbl_encoder_status.setText(f"Encoder training thất bại: {message}")
            self.lbl_encoder_status.setStyleSheet(STYLE_RECORD_STATUS_TEMPLATE.format(color=WARNING))

    def update_collection_stats(self, stats: dict) -> None:
        normalized_stats = {}
        for gesture_name in self._catalog:
            normalized_stats[gesture_name] = int(stats.get(gesture_name, 0))
        self._stats = normalized_stats

        ready_for_training = 0
        for gesture_name, widgets in self._card_widgets.items():
            total = int(self._stats.get(gesture_name, 0))
            target = int(self._catalog[gesture_name]["target_samples"])
            widgets["progress"].setValue(max(0, min(target, total)))

            group_counts = self._compute_group_counts(gesture_name, total)
            for group_name, button in widgets["groups"].items():
                group_target = int(self._catalog[gesture_name]["groups"][group_name]["count"])
                group_count = int(group_counts.get(group_name, 0))
                button.setText(f"{group_name[0]}: {group_count}/{group_target}")
                if group_count >= group_target:
                    button.setStyleSheet(get_style_group_done())
                elif gesture_name == self._selected_gesture and group_name == self._selected_group:
                    button.setStyleSheet(STYLE_BTN_PRIMARY)
                else:
                    button.setStyleSheet(STYLE_BTN_BASE)

            if total >= 100:
                ready_for_training += 1

        self.btn_train_encoder.setEnabled(ready_for_training >= 6 and not self._collecting)
        self._auto_select_next_group_if_completed()

    @staticmethod
    def _extract_metric(message: str, key: str) -> float | None:
        marker = f"{key}="
        start = message.find(marker)
        if start < 0:
            return None
        start += len(marker)
        end = start
        while end < len(message):
            char = message[end]
            if char.isdigit() or char == ".":
                end += 1
                continue
            break
        if end <= start:
            return None
        try:
            return float(message[start:end])
        except ValueError:
            return None

    def _apply_metrics_from_summary(self, message: str) -> None:
        metrics = {
            "distance_ratio": self.lbl_distance_ratio,
            "fewshot5": self.lbl_fewshot_5,
            "fewshot10": self.lbl_fewshot_10,
        }
        for key, target in metrics.items():
            value = self._extract_metric(message, key)
            if value is None:
                continue
            if key.startswith("fewshot"):
                target.setText(f"{value * 100.0:.1f}%")
            else:
                target.setText(f"{value:.4f}")

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_start_collect.isEnabled():
                self._on_start_clicked()
                return
        elif event.key() == Qt.Key.Key_T and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_stop_collect.isEnabled():
                self._on_stop_clicked()
                return
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.btn_capture_collect.isEnabled():
                self._on_capture_clicked()
                return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Enter and isinstance(watched, QFrame):
            gesture_name = watched.property("gesture_name")
            if isinstance(gesture_name, str):
                if self._selected_gesture == gesture_name and self._selected_group:
                    self._set_instruction_for_selection()
                else:
                    groups = self._catalog[gesture_name]["groups"]
                    first_group = next(iter(groups.keys()))
                    instruction = groups[first_group]["instruction"]
                    self.lbl_instruction.setText(f"[{gesture_name} / {first_group}] {instruction}")
        return super().eventFilter(watched, event)

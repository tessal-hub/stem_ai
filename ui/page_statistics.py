"""
Trang thống kê — phân bố dữ liệu spell, chỉ số mastery, và FFT features.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from ui.tokens import (
    # Colors
    TEXT_BODY,
    TEXT_MUTED,
    WAND_ACCENT,
    # Sizes
    BTN_H,
    RIGHT_MAX_W,
    STATISTICS_FFT_MIN_H,
    STATISTICS_SAMPLE_LIST_MIN_H,
    # Styles
    STYLE_STATISTICS_CARD,
    STYLE_SCROLL_AREA,
    STYLE_STATISTICS_BTN_BACK,
    STYLE_STATISTICS_LIST,
    STYLE_STATISTICS_CURRENT_SPELL,
    STYLE_STATISTICS_INFO_LABEL,
    STYLE_STATISTICS_META_LABEL,
    STYLE_TRANSPARENT_WIDGET,
)
from logic.rarity_utils import resolve_rarity
from ui.mac_material import apply_soft_shadow
from logic.theme_manager import theme_manager
from ui.component_factory import (
    make_card_count_label,
    make_card_name_label,
    make_empty_state_card,
    make_error_state_card,
    make_graph_placeholder,
    make_outline_button,
    make_primary_button,
    make_rarity_badge_statistics,
    make_section_label,
)
from ui.layout_utils import clear_layout
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from ui.i18n_bridge import tr_ui


class ClickableFrame(QFrame):
    """QFrame hỗ trợ click — phát signal clicked khi người dùng nhấp chuột."""

    clicked = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class PageStatistics(QWidget):
    """
    Trang thống kê dữ liệu.
    Hiển thị phân bố spell, chỉ số mastery, live FFT features,
    và danh sách sample cho mỗi spell.
    """

    sig_spell_selected = pyqtSignal(str)
    sig_sample_opened = pyqtSignal(str)
    sig_train_build_requested = pyqtSignal()
    sig_health_audit_requested = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._spell_cards_layout: QVBoxLayout | None = None
        self._last_features: dict = {}

        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def apply_ui_language(self) -> None:
        """Re-apply FFT / feature strings after locale change."""
        self.fft_placeholder.setText(tr_ui("stats_fft_wait_features"))
        self.fft_plot.setLabel("left", tr_ui("stats_plot_fft_mag"), color=TEXT_MUTED)
        self.fft_plot.setLabel("bottom", tr_ui("stats_plot_freq"), color=TEXT_MUTED)
        self.update_live_features(self._last_features)

    def update_live_features(self, features: dict) -> None:
        self._last_features = dict(features) if features else {}
        if not features:
            self.lbl_accel_stats.setText(tr_ui("stats_placeholder_accel"))
            self.lbl_gyro_stats.setText(tr_ui("stats_placeholder_gyro"))
            self.lbl_dominant_freq.setText(tr_ui("stats_dominant_wait"))
            self.fft_stack.setCurrentWidget(self.fft_placeholder)
            return

        self.lbl_accel_stats.setText(
            tr_ui(
                "stats_accel_tpl",
                m=features.get("accel_mean", 0.0),
                v=features.get("accel_var", 0.0),
                r=features.get("accel_rms", 0.0),
            )
        )
        self.lbl_gyro_stats.setText(
            tr_ui(
                "stats_gyro_tpl",
                m=features.get("gyro_mean", 0.0),
                v=features.get("gyro_var", 0.0),
                r=features.get("gyro_rms", 0.0),
            )
        )

        freqs = features.get("fft_freqs")
        mags = features.get("fft_mags")
        if freqs and mags and len(freqs) == len(mags):
            self.fft_curve.setData(freqs, mags)
            # Find and display dominant frequency
            try:
                max_idx = mags.index(max(mags))
                dominant_freq = freqs[max_idx]
                self.lbl_dominant_freq.setText(tr_ui("stats_dominant_hz", f=dominant_freq))
            except (ValueError, IndexError):
                self.lbl_dominant_freq.setText(tr_ui("stats_dominant_na"))
            self.fft_stack.setCurrentWidget(self.fft_plot)
            return

        self.lbl_dominant_freq.setText(tr_ui("stats_fft_unavailable"))
        self.fft_stack.setCurrentWidget(self.fft_placeholder)

    def update_spell_stats(self, spell_counts: dict[str, int]) -> None:
        # FIX: Gán vào biến local để Pylance xác nhận không bị đổi thành None giữa chừng
        target_layout = self._spell_cards_layout
        if target_layout is None: return
        
        clear_layout(target_layout)

        sorted_spells = sorted(spell_counts.items(), key=lambda x: x[1], reverse=True)
        if not sorted_spells:
            self.mastery_stack.setCurrentWidget(self.mastery_empty_state)
            self.lbl_total_samples.setText(tr_ui("stats_total_samples", n=0))
            self.lbl_total_spells.setText(tr_ui("stats_active_spells", n=0))
            return

        self.mastery_stack.setCurrentWidget(self.mastery_scroll)
        for spell_name, count in sorted_spells:
            card = self._make_spell_card(spell_name, count)
            card.clicked.connect(lambda checked=False, s=spell_name: self.sig_spell_selected.emit(s))
            target_layout.addWidget(card)
            
        target_layout.addStretch()
        total = sum(spell_counts.values())
        self.lbl_total_samples.setText(tr_ui("stats_total_samples", n=total))
        self.lbl_total_spells.setText(tr_ui("stats_active_spells", n=len(spell_counts)))

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        self.lbl_current_spell.setText(tr_ui("record_spell_samples", name=spell_name))
        self.sample_list.clear()
        if samples:
            self.sample_list.addItems(samples)
        else:
            self.sample_list.addItem(tr_ui("stats_no_samples_line"))
        self.stacked_spells.setCurrentIndex(1)

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        
        # 1. Update Cards
        for card in [self.feature_card, self.model_card, self.graph_card, self.mastery_box]:
            card.setStyleSheet(f"""
                #VanguardCardOuter {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 24px; }}
                #VanguardCardInner {{ background-color: {p.SURFACE_PRIMARY}; border: none; border-radius: 16px; }}
            """)
        
        # 2. Update Plots
        for plot in [self.fft_plot]:
            plot.setBackground("transparent")
            plot.getAxis("left").setPen(p.TEXT_TERTIARY)
            plot.getAxis("bottom").setPen(p.TEXT_TERTIARY)
            
        # 3. Update Lists
        self.sample_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; color: {p.TEXT_PRIMARY}; }}
            QListWidget::item {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 12px; margin-bottom: 8px; padding: 12px; }}
            QListWidget::item:selected {{ background-color: {p.PRIMARY}; color: {p.SURFACE_PRIMARY}; border: none; }}
        """)
        
        # 4. Update Mastery Spells
        self.update_spell_stats(self.data_store.spell_counts)

    def _init_ui(self) -> None:
        """Xây dựng layout chính gồm 2 cột: spell cards và features."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)
        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=3)
        outer.addLayout(content)
        
        self.refresh_styles()

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)

        from ui.component_factory import make_card
        
        # Stats Summary
        top_row = QHBoxLayout()
        top_row.setSpacing(SPACING_MD)
        self.lbl_total_samples = make_section_label("TOTAL SAMPLES: 0", accent=False)
        self.lbl_total_spells  = make_section_label("ACTIVE SPELLS: 0",  accent=False)
        top_row.addWidget(self.lbl_total_samples)
        top_row.addWidget(self.lbl_total_spells)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Feature Card
        self.feature_card, feature_layout = make_card()
        feature_layout.addWidget(make_section_label("LIVE FEATURES", accent=True))
        self.lbl_accel_stats = QLabel("Accel: mean --  var --  rms --")
        self.lbl_gyro_stats = QLabel("Gyro: mean --  var --  rms --")
        feature_layout.addWidget(self.lbl_accel_stats)
        feature_layout.addWidget(self.lbl_gyro_stats)
        layout.addWidget(self.feature_card)

        # Model Card
        self.model_card, model_layout = make_card()
        model_layout.addWidget(make_section_label("MODEL TRAIN / BUILD", accent=True))
        self.lbl_train_status = QLabel("Train: idle")
        self.lbl_build_status = QLabel("Build: idle")
        self.model_progress = QProgressBar()
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        self.btn_train_build = make_primary_button("TRAIN + BUILD GESTURE MODEL")
        self.btn_health_audit = make_outline_button("RUN DATASET HEALTH AUDIT")
        model_layout.addWidget(self.lbl_train_status)
        model_layout.addWidget(self.lbl_build_status)
        model_layout.addWidget(self.model_progress)
        model_layout.addWidget(self.btn_train_build)
        model_layout.addWidget(self.btn_health_audit)
        layout.addWidget(self.model_card)

        # FFT Card
        self.graph_card, graph_layout = make_card()
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self.fft_stack = QStackedWidget()
        self.fft_placeholder = make_graph_placeholder()
        self.fft_placeholder.setMinimumHeight(STATISTICS_FFT_MIN_H)
        self.fft_stack.addWidget(self.fft_placeholder)
        
        self.fft_plot = pg.PlotWidget()
        self.fft_plot.setBackground("transparent")
        self.fft_plot.showGrid(x=True, y=True, alpha=0.2)
        self.fft_curve = self.fft_plot.plot(pen=pg.mkPen(WAND_ACCENT, width=2))
        self.fft_stack.addWidget(self.fft_plot)
        
        graph_layout.addWidget(make_section_label("FREQUENCY SPECTRUM", accent=True))
        self.lbl_dominant_freq = QLabel("Dominant: -- Hz")
        graph_layout.addWidget(self.lbl_dominant_freq)
        graph_layout.addWidget(self.fft_stack)
        layout.addWidget(self.graph_card, stretch=1)
        
        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)
        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_mastery_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)
        return widget

    def _build_mastery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)
        layout.addWidget(make_section_label("SPELL MASTERY"))
        
        from ui.component_factory import make_card
        self.mastery_box, inner_layout = make_card()
        
        self.mastery_stack = QStackedWidget()
        self.mastery_scroll = QScrollArea()
        self.mastery_scroll.setWidgetResizable(True)
        self.mastery_scroll.setStyleSheet(STYLE_SCROLL_AREA)
        scroll_content = QWidget()
        scroll_content.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        self._spell_cards_layout = QVBoxLayout(scroll_content)
        self._spell_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._spell_cards_layout.setSpacing(SPACING_SM)
        self.mastery_scroll.setWidget(scroll_content)
        self.mastery_stack.addWidget(self.mastery_scroll)
        
        empty_card, _ = make_empty_state_card("No spell data yet", "Capture your first samples in Record.")
        self.mastery_empty_state = empty_card
        self.mastery_stack.addWidget(self.mastery_empty_state)
        
        inner_layout.addWidget(self.mastery_stack)
        layout.addWidget(self.mastery_box)
        return page

    def _build_sample_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)
        top_row = QHBoxLayout()
        self.btn_back_spells = make_outline_button("◀ BACK", BTN_H)
        self.btn_back_spells.setStyleSheet(STYLE_STATISTICS_BTN_BACK)
        self.lbl_current_spell = QLabel("SAMPLES: —")
        self.lbl_current_spell.setStyleSheet(STYLE_STATISTICS_CURRENT_SPELL)
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        top_row.addStretch()
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_STATISTICS_LIST)
        self.sample_list.setMinimumHeight(STATISTICS_SAMPLE_LIST_MIN_H)
        layout.addWidget(self.sample_list)
        return page

    def _make_spell_card(self, spell_name: str, count: int) -> ClickableFrame:
        card = ClickableFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(STYLE_STATISTICS_CARD)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
        )
        info = QVBoxLayout()
        info.addWidget(self._make_card_name_label(spell_name))
        info.addWidget(self._make_card_count_label(count))
        rarity = resolve_rarity(count)
        badge  = self._make_rarity_badge(rarity.label, rarity.color)
        layout.addLayout(info)
        layout.addStretch()
        layout.addWidget(badge)
        return card

    @staticmethod
    def _make_standard_frame() -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_STATISTICS_CARD)
        apply_soft_shadow(frame, blur_radius=20, y_offset=4, color="rgba(15, 23, 42, 0.14)")
        return frame

    @staticmethod
    def _make_section_label(text: str, accent: bool = True) -> QLabel:
        return make_section_label(text, accent=accent)

    @staticmethod
    def _make_graph_placeholder() -> QLabel:
        return make_graph_placeholder()

    @staticmethod
    def _make_card_name_label(name: str) -> QLabel:
        return make_card_name_label(name)

    @staticmethod
    def _make_card_count_label(count: int) -> QLabel:
        return make_card_count_label(count)

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        return make_rarity_badge_statistics(label, color)

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot của trang thống kê."""
        self.btn_back_spells.clicked.connect(lambda checked: self.stacked_spells.setCurrentIndex(0))
        self.sample_list.itemDoubleClicked.connect(lambda item: self.sig_sample_opened.emit(item.text()))
        self.btn_train_build.clicked.connect(self.sig_train_build_requested.emit)
        self.btn_health_audit.clicked.connect(self.sig_health_audit_requested.emit)
        self.sig_spell_selected.connect(
            lambda spell_name: self.load_samples_for_spell(
                spell_name, 
                self.data_store.get_samples_for_spell(spell_name)
            )
        )

    def set_training_state(self, running: bool) -> None:
        self.btn_train_build.setEnabled(not running)
        if running:
            self.model_progress.setValue(0)
            self.lbl_train_status.setText("Train: running...")
            self.lbl_build_status.setText("Build: waiting...")
            self.model_error_state.setVisible(False)

    def update_training_status(self, text: str) -> None:
        msg = text.strip()
        if not msg:
            return
        if "[TRAIN]" in msg:
            self.lbl_train_status.setText(f"Train: {msg.replace('[TRAIN]', '').strip()}")
        elif "[BUILD]" in msg:
            self.lbl_build_status.setText(f"Build: {msg.replace('[BUILD]', '').strip()}")
        elif "[DONE]" in msg:
            self.lbl_build_status.setText("Build: completed")

    def update_training_progress(self, value: int) -> None:
        self.model_progress.setValue(max(0, min(100, int(value))))

    def set_training_finished(self, success: bool, summary: str) -> None:
        self.btn_train_build.setEnabled(True)
        if success:
            self.model_progress.setValue(100)
            self.lbl_train_status.setText("Train: completed")
            self.lbl_build_status.setText(f"Build: {summary}")
            self.model_error_state.setVisible(False)
        else:
            self.lbl_build_status.setText(f"Build: failed - {summary}")
            self.model_error_state.setVisible(True)

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ DataStore vào trang thống kê."""
        self.update_spell_stats(self.data_store.spell_counts)
        self.update_live_features({})

    def _configure_accessibility(self) -> None:
        """Đặt accessible names và thứ tự tab traversal cho các control."""
        self.lbl_total_samples.setAccessibleName("Total samples metric")
        self.lbl_total_spells.setAccessibleName("Active spells metric")
        self.lbl_train_status.setAccessibleName("Model training status")
        self.lbl_build_status.setAccessibleName("Model build status")
        self.lbl_dominant_freq.setAccessibleName("Dominant FFT frequency")
        self.fft_plot.setAccessibleName("Frequency spectrum FFT plot")
        self.model_progress.setAccessibleName("Training progress")
        self.btn_back_spells.setAccessibleName("Back to mastery list")
        self.sample_list.setAccessibleName("Samples for selected spell")
        self.btn_train_build.setAccessibleName("Train and build gesture model")

        self.setTabOrder(self.btn_train_build, self.model_progress)
        self.setTabOrder(self.model_progress, self.btn_back_spells)
        self.setTabOrder(self.btn_back_spells, self.sample_list)
        self.setTabOrder(self.sample_list, self.btn_train_build)

"""
PageStatistics — Data distribution and spell mastery view.
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
    RIGHT_MAX_W,
    # Styles
    STYLE_STATISTICS_MAIN_CONTAINER,
    STYLE_STATISTICS_CARD,
    STYLE_SCROLL_AREA,
    STYLE_STATISTICS_BTN_BACK,
    STYLE_STATISTICS_LIST,
    STYLE_TRANSPARENT_WIDGET,
)
from logic.rarity_utils import resolve_rarity
from ui.component_factory import (
    make_card_count_label,
    make_card_name_label,
    make_graph_placeholder,
    make_rarity_badge_statistics,
    make_section_label,
)
from ui.layout_utils import clear_layout
from ui.mac_material import apply_soft_shadow
from ui.modern_layout import MARGIN_STANDARD, SPACING_MD


class ClickableFrame(QFrame):
    clicked = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class PageStatistics(QWidget):
    sig_spell_selected = pyqtSignal(str)
    sig_sample_opened = pyqtSignal(str)
    sig_train_build_requested = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._spell_cards_layout: QVBoxLayout | None = None

        self._build_ui()
        self._connect_internal_signals()
        self._configure_accessibility()
        self.update_spell_stats(self.data_store.spell_counts)
        self.update_live_features({})

    def update_live_features(self, features: dict) -> None:
        if not features:
            self.lbl_accel_stats.setText("Accel: mean --  var --  rms --")
            self.lbl_gyro_stats.setText("Gyro: mean --  var --  rms --")
            return

        self.lbl_accel_stats.setText(
            "Accel: mean {accel_mean:.3f}  var {accel_var:.3f}  rms {accel_rms:.3f}".format(
                accel_mean=features.get("accel_mean", 0.0),
                accel_var=features.get("accel_var", 0.0),
                accel_rms=features.get("accel_rms", 0.0),
            )
        )
        self.lbl_gyro_stats.setText(
            "Gyro: mean {gyro_mean:.3f}  var {gyro_var:.3f}  rms {gyro_rms:.3f}".format(
                gyro_mean=features.get("gyro_mean", 0.0),
                gyro_var=features.get("gyro_var", 0.0),
                gyro_rms=features.get("gyro_rms", 0.0),
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
                self.lbl_dominant_freq.setText(f"Dominant: {dominant_freq:.1f} Hz")
            except (ValueError, IndexError):
                self.lbl_dominant_freq.setText("Dominant: -- Hz")

    def update_spell_stats(self, spell_counts: dict[str, int]) -> None:
        # FIX: Gán vào biến local để Pylance xác nhận không bị đổi thành None giữa chừng
        target_layout = self._spell_cards_layout
        if target_layout is None: return
        
        clear_layout(target_layout)

        sorted_spells = sorted(spell_counts.items(), key=lambda x: x[1], reverse=True)
        for spell_name, count in sorted_spells:
            card = self._make_spell_card(spell_name, count)
            card.clicked.connect(lambda checked=False, s=spell_name: self.sig_spell_selected.emit(s))
            target_layout.addWidget(card)
            
        target_layout.addStretch()
        total = sum(spell_counts.values())
        self.lbl_total_samples.setText(f"TOTAL SAMPLES: {total}")
        self.lbl_total_spells.setText(f"ACTIVE SPELLS: {len(spell_counts)}")

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        self.lbl_current_spell.setText(f"SAMPLES: {spell_name}")
        self.sample_list.clear()
        self.sample_list.addItems(samples)
        self.stacked_spells.setCurrentIndex(1)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setStyleSheet(STYLE_SCROLL_AREA)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setFrameShape(QFrame.Shape.NoFrame)
        self.main_container.setFrameShadow(QFrame.Shadow.Plain)
        self.main_container.setStyleSheet(STYLE_STATISTICS_MAIN_CONTAINER)
        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD)
        inner.setSpacing(SPACING_MD)
        content = QHBoxLayout()
        content.setSpacing(SPACING_MD)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=3)
        inner.addLayout(content)
        page_scroll.setWidget(self.main_container)
        outer.addWidget(page_scroll)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top_row = QGridLayout()
        top_row.setHorizontalSpacing(12)
        top_row.setVerticalSpacing(4)
        self.lbl_total_samples = self._make_section_label("TOTAL SAMPLES: 0", accent=False)
        self.lbl_total_spells  = self._make_section_label("ACTIVE SPELLS: 0",  accent=False)
        lbl_title = self._make_section_label("DATA DISTRIBUTION")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.lbl_total_samples, 0, 0)
        top_row.addWidget(self.lbl_total_spells, 0, 1)
        top_row.setColumnStretch(2, 1)
        top_row.addWidget(lbl_title, 0, 3)
        layout.addLayout(top_row)

        feature_card = self._make_standard_frame()
        feature_layout = QVBoxLayout(feature_card)
        feature_layout.setContentsMargins(10, 10, 10, 10)
        feature_layout.setSpacing(6)
        feature_layout.addWidget(self._make_section_label("LIVE FEATURES", accent=False))
        self.lbl_accel_stats = QLabel("Accel: mean --  var --  rms --")
        self.lbl_accel_stats.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;"
        )
        self.lbl_gyro_stats = QLabel("Gyro: mean --  var --  rms --")
        self.lbl_gyro_stats.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;"
        )
        feature_layout.addWidget(self.lbl_accel_stats)
        feature_layout.addWidget(self.lbl_gyro_stats)
        layout.addWidget(feature_card)

        model_card = self._make_standard_frame()
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(10, 10, 10, 10)
        model_layout.setSpacing(6)
        model_layout.addWidget(self._make_section_label("MODEL TRAIN / BUILD", accent=False))

        self.lbl_train_status = QLabel("Train: idle")
        self.lbl_train_status.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;"
        )
        self.lbl_build_status = QLabel("Build: idle")
        self.lbl_build_status.setStyleSheet(
            f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;"
        )

        self.model_progress = QProgressBar()
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        self.model_progress.setTextVisible(True)
        self.model_progress.setFormat("%p%")

        self.btn_train_build = QPushButton("TRAIN + BUILD GESTURE MODEL")
        self.btn_train_build.setFixedHeight(34)
        self.btn_train_build.setCursor(Qt.CursorShape.PointingHandCursor)

        model_layout.addWidget(self.lbl_train_status)
        model_layout.addWidget(self.lbl_build_status)
        model_layout.addWidget(self.model_progress)
        model_layout.addWidget(self.btn_train_build)
        layout.addWidget(model_card)

        graph_card = self._make_standard_frame()
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self.fft_plot = pg.PlotWidget()

        # FFT frequency analysis header
        fft_header = QHBoxLayout()
        fft_header.setContentsMargins(10, 8, 10, 0)
        fft_header.addWidget(self._make_section_label("FREQUENCY SPECTRUM", accent=False))
        fft_header.addStretch()
        self.lbl_dominant_freq = QLabel("Dominant: -- Hz")
        self.lbl_dominant_freq.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        fft_header.addWidget(self.lbl_dominant_freq)
        graph_layout.addLayout(fft_header)

        self.fft_plot.setBackground("transparent")
        self.fft_plot.showGrid(x=True, y=True, alpha=0.2)
        self.fft_plot.getAxis("left").setPen(TEXT_MUTED)
        self.fft_plot.getAxis("bottom").setPen(TEXT_MUTED)
        self.fft_plot.setLabel("left", "FFT magnitude", color=TEXT_MUTED)
        self.fft_plot.setLabel("bottom", "Frequency (Hz)", color=TEXT_MUTED)
        self.fft_curve = self.fft_plot.plot(pen=pg.mkPen(WAND_ACCENT, width=2))
        graph_layout.addWidget(self.fft_plot)
        layout.addWidget(graph_card, stretch=1)
        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_mastery_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)
        return widget

    def _build_mastery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._make_section_label("SPELL MASTERY"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)
        scroll_content = QWidget()
        scroll_content.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        self._spell_cards_layout = QVBoxLayout(scroll_content)
        self._spell_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._spell_cards_layout.setSpacing(8)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return page

    def _build_sample_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        top_row = QHBoxLayout()
        self.btn_back_spells = QPushButton("◀ BACK")
        self.btn_back_spells.setFixedHeight(32)
        self.btn_back_spells.setStyleSheet(STYLE_STATISTICS_BTN_BACK)
        self.lbl_current_spell = QLabel("SAMPLES: …")
        self.lbl_current_spell.setStyleSheet(f"color: {WAND_ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        top_row.addStretch()
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_STATISTICS_LIST)
        layout.addWidget(self.sample_list)
        return page

    def _make_spell_card(self, spell_name: str, count: int) -> ClickableFrame:
        card = ClickableFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(STYLE_STATISTICS_CARD)
        apply_soft_shadow(card, blur_radius=16, y_offset=3, color="rgba(0, 0, 0, 0.08)")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
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
        apply_soft_shadow(frame, blur_radius=16, y_offset=3, color="rgba(0, 0, 0, 0.08)")
        return frame

    @staticmethod
    def _make_section_label(text: str, accent: bool = True) -> QLabel:
        color = WAND_ACCENT if accent else TEXT_BODY
        return make_section_label(text, accent_color=color)

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

    def _connect_internal_signals(self) -> None:
        self.btn_back_spells.clicked.connect(lambda checked: self.stacked_spells.setCurrentIndex(0))
        self.sample_list.itemDoubleClicked.connect(lambda item: self.sig_sample_opened.emit(item.text()))
        self.btn_train_build.clicked.connect(self.sig_train_build_requested.emit)
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
        else:
            self.lbl_build_status.setText(f"Build: failed - {summary}")

    def _configure_accessibility(self) -> None:
        """Apply basic screen-reader names and tab traversal for keyboard use."""
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
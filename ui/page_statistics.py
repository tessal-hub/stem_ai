"""
Trang thống kê — phân bố dữ liệu spell, chỉ số mastery, và nhật ký huấn luyện model.
"""

from __future__ import annotations

from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal
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
    QTextEdit,
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
    STYLE_TERMINAL,
    # Geometry & Font
    CARD_RADIUS,
    APP_FONT_STACK,
    TITLE_FONT_STACK,
)
from logic.rarity_utils import resolve_rarity
from ui.mac_material import apply_soft_shadow
from logic.theme_manager import theme_manager
from ui.component_factory import (
    make_card_count_label,
    make_card_name_label,
    make_empty_state_card,
    make_error_state_card,
    make_outline_button,
    make_primary_button,
    make_rarity_badge_statistics,
    make_section_label,
)
from ui.layout_utils import clear_layout
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from ui.modern_layout import create_modern_card, add_card_shadow
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
    Hiển thị phân bố spell, chỉ số mastery, và nhật ký huấn luyện model.
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
        """Reload strings after locale change."""
        self.update_live_features(self._last_features)
        self._sec_preview.setText(tr_ui("stats_live_features"))
        self._sec_model.setText(tr_ui("stats_model_train"))
        self._sec_console.setText(tr_ui("sub_console"))
        self._sec_mastery.setText(tr_ui("stats_spell_mastery"))
        self.btn_train_build.setText(tr_ui("stats_btn_train"))
        self.btn_health_audit.setText(tr_ui("stats_btn_audit"))
        self.btn_back_spells.setText(tr_ui("record_btn_back"))

    def update_live_features(self, features: dict) -> None:
        self._last_features = dict(features) if features else {}
        if not features:
            self.lbl_accel_stats.setText(tr_ui("stats_placeholder_accel"))
            self.lbl_gyro_stats.setText(tr_ui("stats_placeholder_gyro"))
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

    def update_spell_stats(self, spell_counts: dict[str, int]) -> None:
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
            card.clicked.connect(partial(self._emit_spell_selected, spell_name))
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
        for card in [self.feature_card, self.model_card, self.console_card, self.mastery_box]:
            card.setStyleSheet(f"""
                #VanguardCardOuter {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: {CARD_RADIUS}; }}
                #VanguardCardInner {{ background-color: {p.SURFACE_PRIMARY}; border: none; border-radius: calc({CARD_RADIUS} - 4px); }}
            """)
        
        # 2. Update Console
        self.train_console.setStyleSheet(STYLE_TERMINAL)
            
        # 3. Update Lists
        self.sample_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; color: {p.TEXT_PRIMARY}; font-family: {APP_FONT_STACK}; }}
            QListWidget::item {{ background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; border-radius: 12px; margin-bottom: 8px; padding: 12px; }}
            QListWidget::item:selected {{ background-color: {p.PRIMARY}; color: white; border: none; }}
        """)
        
        # 4. Update Mastery Spells
        self.update_spell_stats(self.data_store.spell_counts)

    def _init_ui(self) -> None:
        """Xây dựng layout chính gồm 2 cột: spell cards và features/console."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)
        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=4)
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
        self.feature_card, feature_layout = create_modern_card(margin=MARGIN_COMFORTABLE, spacing=SPACING_MD)
        add_card_shadow(self.feature_card, blur_radius=12, offset_y=3)
        self._sec_preview = make_section_label(tr_ui("stats_live_features"), accent=True)
        feature_layout.addWidget(self._sec_preview)
        self.lbl_accel_stats = QLabel("Accel: mean --  var --  rms --")
        self.lbl_gyro_stats = QLabel("Gyro: mean --  var --  rms --")
        feature_layout.addWidget(self.lbl_accel_stats)
        feature_layout.addWidget(self.lbl_gyro_stats)
        layout.addWidget(self.feature_card)

        # Model Card
        self.model_card, model_layout = create_modern_card(margin=MARGIN_COMFORTABLE, spacing=SPACING_MD)
        add_card_shadow(self.model_card, blur_radius=12, offset_y=3)
        self._sec_model = make_section_label(tr_ui("stats_model_train"), accent=True)
        model_layout.addWidget(self._sec_model)
        self.lbl_train_status = QLabel("Train: idle")
        self.lbl_build_status = QLabel("Build: idle")
        self.model_progress = QProgressBar()
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        self.btn_train_build = make_primary_button(tr_ui("stats_btn_train"))
        self.btn_health_audit = make_outline_button(tr_ui("stats_btn_audit"))
        model_layout.addWidget(self.lbl_train_status)
        model_layout.addWidget(self.lbl_build_status)
        model_layout.addWidget(self.model_progress)
        model_layout.addWidget(self.btn_train_build)
        model_layout.addWidget(self.btn_health_audit)
        layout.addWidget(self.model_card)

        # Console Card (Replaces FFT)
        self.console_card, console_layout = create_modern_card(margin=MARGIN_COMFORTABLE, spacing=SPACING_MD)
        add_card_shadow(self.console_card, blur_radius=12, offset_y=3)
        self._sec_console = make_section_label(tr_ui("sub_console"), accent=True)
        console_layout.addWidget(self._sec_console)
        
        self.train_console = QTextEdit()
        self.train_console.setReadOnly(True)
        self.train_console.setStyleSheet(STYLE_TERMINAL)
        self.train_console.setPlaceholderText("ML pipeline logs will appear here...")
        console_layout.addWidget(self.train_console)
        layout.addWidget(self.console_card, stretch=1)
        
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
        self._sec_mastery = make_section_label(tr_ui("stats_spell_mastery"))
        layout.addWidget(self._sec_mastery)
        
        # Mastery list container
        self.mastery_box, inner_layout = create_modern_card(margin=MARGIN_COMFORTABLE, spacing=SPACING_MD)
        add_card_shadow(self.mastery_box, blur_radius=10, offset_y=2)
        
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
        self.btn_back_spells = make_outline_button(tr_ui("record_btn_back"), BTN_H)
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
        # Use ClickableFrame so callers can connect to `.clicked`
        card = ClickableFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(STYLE_STATISTICS_CARD)
        add_card_shadow(card, blur_radius=8, offset_y=2)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
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
    def _make_card_name_label(name: str) -> QLabel:
        return make_card_name_label(name)

    @staticmethod
    def _make_card_count_label(count: int) -> QLabel:
        return make_card_count_label(count)

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        return make_rarity_badge_statistics(label, color)

    def _emit_spell_selected(self, spell_name: str) -> None:
        self.sig_spell_selected.emit(spell_name)

    def _init_signals(self) -> None:
        self.btn_back_spells.clicked.connect(self._on_btn_back_spells_clicked)
        self.sample_list.itemDoubleClicked.connect(self._on_sample_list_item_double_clicked)
        self.btn_train_build.clicked.connect(self.sig_train_build_requested.emit)
        self.btn_health_audit.clicked.connect(self.sig_health_audit_requested.emit)
        self.sig_spell_selected.connect(self._on_spell_selected)

    def _on_btn_back_spells_clicked(self) -> None:
        self.stacked_spells.setCurrentIndex(0)

    def _on_sample_list_item_double_clicked(self, item) -> None:
        self.sig_sample_opened.emit(item.text())

    def _on_spell_selected(self, spell_name: str) -> None:
        self.load_samples_for_spell(
            spell_name,
            self.data_store.get_samples_for_spell(spell_name),
        )

    def set_training_state(self, running: bool) -> None:
        self.btn_train_build.setEnabled(not running)
        if running:
            self.train_console.clear()
            self.train_console.append(">> ML Pipeline started...")
            self.model_progress.setValue(0)
            self.lbl_train_status.setText("Train: running...")
            self.lbl_build_status.setText("Build: waiting...")

    def update_training_status(self, text: str) -> None:
        msg = text.strip()
        if not msg:
            return
        self.train_console.append(f"[{self._get_time_stamp()}] {msg}")
        # Scroll to bottom
        self.train_console.verticalScrollBar().setValue(
            self.train_console.verticalScrollBar().maximum()
        )
        
        if "[TRAIN]" in msg:
            self.lbl_train_status.setText(f"Train: {msg.replace('[TRAIN]', '').strip()}")
        elif "[BUILD]" in msg:
            self.lbl_build_status.setText(f"Build: {msg.replace('[BUILD]', '').strip()}")
        elif "[DONE]" in msg:
            self.lbl_build_status.setText("Build: completed")

    @staticmethod
    def _get_time_stamp() -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def update_training_progress(self, value: int) -> None:
        self.model_progress.setValue(max(0, min(100, int(value))))

    def set_training_finished(self, success: bool, summary: str) -> None:
        self.btn_train_build.setEnabled(True)
        if success:
            self.train_console.append(">> ML Pipeline completed successfully.")
            self.model_progress.setValue(100)
            self.lbl_train_status.setText("Train: completed")
            self.lbl_build_status.setText(f"Build: {summary}")
        else:
            self.train_console.append(f">> ERROR: {summary}")
            self.lbl_build_status.setText(f"Build: failed - {summary}")

    def _load_data(self) -> None:
        self.update_spell_stats(self.data_store.spell_counts)
        self.update_live_features({})

    def _configure_accessibility(self) -> None:
        self.lbl_total_samples.setAccessibleName("Total samples metric")
        self.lbl_total_spells.setAccessibleName("Active spells metric")
        self.lbl_train_status.setAccessibleName("Model training status")
        self.lbl_build_status.setAccessibleName("Model build status")
        self.train_console.setAccessibleName("Model training console logs")
        self.model_progress.setAccessibleName("Training progress")
        self.btn_back_spells.setAccessibleName("Back to mastery list")
        self.sample_list.setAccessibleName("Samples for selected spell")
        self.btn_train_build.setAccessibleName("Train and build gesture model")

        self.setTabOrder(self.btn_train_build, self.model_progress)
        self.setTabOrder(self.model_progress, self.btn_back_spells)
        self.setTabOrder(self.btn_back_spells, self.sample_list)
        self.setTabOrder(self.sample_list, self.btn_train_build)

"""
PageStatistics — Data distribution and spell mastery view.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from ui.tokens import (
    # Colors
    TEXT_BODY,
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

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._spell_cards_layout: QVBoxLayout | None = None

        self._build_ui()
        self._connect_internal_signals()
        self._configure_accessibility()
        self.update_spell_stats(self.data_store.spell_counts)

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
        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_STATISTICS_MAIN_CONTAINER)
        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(12)
        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=3)
        inner.addLayout(content)
        outer.addWidget(self.main_container)

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        top_row = QHBoxLayout()
        self.lbl_total_samples = self._make_section_label("TOTAL SAMPLES: 0", accent=False)
        self.lbl_total_spells  = self._make_section_label("ACTIVE SPELLS: 0",  accent=False)
        lbl_title = self._make_section_label("DATA DISTRIBUTION")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.lbl_total_samples)
        top_row.addSpacing(16)
        top_row.addWidget(self.lbl_total_spells)
        top_row.addStretch()
        top_row.addWidget(lbl_title)
        layout.addLayout(top_row)
        graph_card = self._make_standard_frame()
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.addWidget(self._make_graph_placeholder())
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
        self.sig_spell_selected.connect(
            lambda spell_name: self.load_samples_for_spell(
                spell_name, 
                self.data_store.get_mock_samples_for_spell(spell_name)
            )
        )

    def _configure_accessibility(self) -> None:
        """Apply basic screen-reader names and tab traversal for keyboard use."""
        self.lbl_total_samples.setAccessibleName("Total samples metric")
        self.lbl_total_spells.setAccessibleName("Active spells metric")
        self.btn_back_spells.setAccessibleName("Back to mastery list")
        self.sample_list.setAccessibleName("Samples for selected spell")

        self.setTabOrder(self.btn_back_spells, self.sample_list)
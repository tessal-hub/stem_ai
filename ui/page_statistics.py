"""
PageStatistics — Data distribution and spell mastery view.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from .common_design_tokens import *


class ClickableFrame(QFrame):
    clicked = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


@dataclass(frozen=True)
class RarityTier:
    min_count: int
    label:     str
    color:     str


RARITY_TIERS: tuple[RarityTier, ...] = (
    RarityTier(0,   "UNLEARNED", RARITY_NONE),
    RarityTier(10,  "COMMON",    RARITY_COM),
    RarityTier(20,  "UNCOMMON",  RARITY_UNC),
    RarityTier(50,  "RARE",      RARITY_RARE),
    RarityTier(100, "EPIC",      RARITY_EPIC),
)


STYLE_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        border-top: none;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
    }}
"""
STYLE_CARD = f"""
    #CardFrame, ClickableFrame {{
        background-color: {BG_LIGHT};
        border: none;
        border-radius: 8px;
    }}
    ClickableFrame:hover {{
        background-color: {HOVER_BG};
    }}
"""
STYLE_SCROLL_AREA = f"""
    QScrollArea {{ border: none; background-color: transparent; }}
    QScrollBar:vertical {{ border: none; background: {BG_LIGHT}; width: 8px; border-radius: 4px; }}
    QScrollBar::handle:vertical {{ background: {BORDER_MID}; border-radius: 4px; }}
"""
STYLE_RARITY_BADGE = """
    QLabel {{
        background-color: transparent;
        color: {color};
        border: 2px solid {color};
        border-radius: 6px;
        padding: 4px 8px;
        font-weight: 900;
        font-size: 10px;
    }}
"""
STYLE_BTN_BACK = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_MID};
        border-radius: 6px;
        font-size: 12px;
        font-weight: bold;
        padding: 6px 12px;
    }}
    QPushButton:hover {{ background-color: {HOVER_BG}; }}
"""
STYLE_LIST = f"""
    QListWidget {{
        background-color: {BG_LIGHT};
        border: none;
        border-radius: 8px;
        outline: 0;
    }}
    QListWidget::item {{ padding: 12px; border-bottom: 1px solid {BORDER}; color: {TEXT_BODY}; font-weight: 500; }}
    QListWidget::item:selected {{ background-color: {TEXT_BODY}; color: {BG_WHITE}; border-radius: 6px; }}
    QListWidget::item:hover:!selected {{ background-color: {HOVER_BG}; border-radius: 6px; }}
"""


def clear_layout(layout: QLayout | None) -> None:
    # FIX: Kiểm tra None trước khi loop
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0)
        # FIX: Kiểm tra item is not None
        if item is None: continue
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                clear_layout(child)
                child.deleteLater()


class PageStatistics(QWidget):
    sig_spell_selected = pyqtSignal(str)
    sig_sample_opened = pyqtSignal(str)

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._spell_cards_layout: QVBoxLayout | None = None

        self._build_ui()
        self._connect_internal_signals()
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
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)
        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)
        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(16)
        content = QHBoxLayout()
        content.setSpacing(16)
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
        graph_layout.setContentsMargins(8, 8, 8, 8)
        graph_layout.addWidget(self._make_graph_placeholder())
        layout.addWidget(graph_card, stretch=1)
        return widget

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.stacked_spells = QStackedWidget()
        self.stacked_spells.addWidget(self._build_mastery_page())
        self.stacked_spells.addWidget(self._build_sample_list_page())
        layout.addWidget(self.stacked_spells, stretch=1)
        return widget

    def _build_mastery_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._make_section_label("SPELL MASTERY"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
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
        layout.setSpacing(12)
        top_row = QHBoxLayout()
        self.btn_back_spells = QPushButton("◀ BACK")
        self.btn_back_spells.setFixedHeight(32)
        self.btn_back_spells.setStyleSheet(STYLE_BTN_BACK)
        self.lbl_current_spell = QLabel("SAMPLES: …")
        self.lbl_current_spell.setStyleSheet(f"color: {WAND_ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(self.btn_back_spells)
        top_row.addWidget(self.lbl_current_spell)
        top_row.addStretch()
        layout.addLayout(top_row)
        self.sample_list = QListWidget()
        self.sample_list.setStyleSheet(STYLE_LIST)
        layout.addWidget(self.sample_list)
        return page

    def _make_spell_card(self, spell_name: str, count: int) -> ClickableFrame:
        card = ClickableFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(STYLE_CARD)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        info = QVBoxLayout()
        info.addWidget(self._make_card_name_label(spell_name))
        info.addWidget(self._make_card_count_label(count))
        rarity = self._resolve_rarity(count)
        badge  = self._make_rarity_badge(rarity.label, rarity.color)
        layout.addLayout(info)
        layout.addStretch()
        layout.addWidget(badge)
        return card

    @staticmethod
    def _make_standard_frame() -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_CARD)
        return frame

    @staticmethod
    def _make_section_label(text: str, accent: bool = True) -> QLabel:
        lbl = QLabel(text)
        color = WAND_ACCENT if accent else TEXT_BODY
        lbl.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;")
        return lbl

    @staticmethod
    def _make_graph_placeholder() -> QLabel:
        lbl = QLabel("DATA GRAPH")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"background-color: {BG_DARK}; color: {TEXT_MUTED}; border-radius: 6px;")
        lbl.setMinimumHeight(GRAPH_MIN_H)
        return lbl

    @staticmethod
    def _make_card_name_label(name: str) -> QLabel:
        lbl = QLabel(name)
        lbl.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 12px;")
        return lbl

    @staticmethod
    def _make_card_count_label(count: int) -> QLabel:
        lbl = QLabel(f"Samples: {count}")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        return lbl

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(STYLE_RARITY_BADGE.format(color=color))
        return lbl

    @staticmethod
    def _resolve_rarity(count: int) -> RarityTier:
        result = RARITY_TIERS[0]
        for tier in RARITY_TIERS:
            if count >= tier.min_count:
                result = tier
        return result

    def _connect_internal_signals(self) -> None:
        self.btn_back_spells.clicked.connect(lambda checked: self.stacked_spells.setCurrentIndex(0))
        self.sample_list.itemDoubleClicked.connect(lambda item: self.sig_sample_opened.emit(item.text()))
        self.sig_spell_selected.connect(
            lambda spell_name: self.load_samples_for_spell(
                spell_name, 
                self.data_store.get_mock_samples_for_spell(spell_name)
            )
        )
"""Panel chọn spell cho firmware — danh sách đã chọn và còn trống."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from logic.rarity_utils import RARITY_TIERS, RarityTier
from ui.modern_layout import MARGIN_STANDARD, SPACING_SM
from ui.tokens import (
    APP_FONT_STACK,
    CARD_RADIUS,
    STYLE_WAND_EMPTY_ROW_TEMPLATE,
    TITLE_FONT_STACK,
    WAND_SPELL_LIST_MIN_H,
)
from ui.component_factory import make_rarity_badge_wand
from ui.wand_panels.shared import make_section_label
from ui.i18n_bridge import tr_ui
from logic.theme_manager import theme_manager


class WandSpellPayloadPanel(QWidget):
    """Panel render danh sách spell chọn được để đưa vào firmware payload."""

    def __init__(self) -> None:
        super().__init__()
        self._spell_order: list[str] = []
        self._selected_spells: set[str] = set()
        self._spell_counts: dict[str, int] = {}
        self._init_ui()
        self._init_signals()
        self.refresh_styles()

    def load_spell_list(self, spell_counts: dict[str, int]) -> None:
        """Nạp danh sách spell vào panel, giữ lại spell đã chọn nếu vẫn hợp lệ.

        Args:
            spell_counts: Dict spell_name → số lượng mẫu.
        """
        self._spell_counts = dict(spell_counts)
        self._spell_order = [name for name in spell_counts.keys() if str(name).strip()]

        # Keep only currently valid selected spells after dataset refresh.
        self._selected_spells.intersection_update(self._spell_order)
        self._refresh_lists()

    def get_checked_spells(self) -> list[str]:
        """Trả về danh sách spell đã được chọn."""
        return [name for name in self._spell_order if name in self._selected_spells]

    def get_available_spell_names(self) -> list[str]:
        """Trả về danh sách spell chưa được chọn."""
        return [name for name in self._spell_order if name not in self._selected_spells]

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        section_style = (
            f"font-family: {TITLE_FONT_STACK}; color: {p.TEXT_PRIMARY}; font-size: 12px; "
            "font-weight: 800; letter-spacing: 0.05em;"
        )
        self._hdr_payload.setStyleSheet(section_style)
        self._left_title.setStyleSheet(section_style)
        self._right_title.setStyleSheet(section_style)
        list_style = f"""
            QListWidget {{
                background-color: {p.SURFACE_PRIMARY};
                border: 1px solid {p.BORDER};
                border-radius: {CARD_RADIUS};
                padding: 6px;
            }}
            QListWidget::item {{
                border: none;
                margin: 0;
                padding: 0;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """
        self.list_selected_spells.setStyleSheet(list_style)
        self.list_available_spells.setStyleSheet(list_style)
        self._refresh_lists()

    def _init_ui(self) -> None:
        """Xây dựng layout gồm 2 danh sách (selected/available) trong QSplitter."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._hdr_payload = make_section_label(tr_ui("wand_section_payload"))
        layout.addWidget(self._hdr_payload)

        split = QSplitter(Qt.Orientation.Horizontal)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING_SM)
        self._left_title = QLabel(tr_ui("wand_selected_title"))
        left_layout.addWidget(self._left_title)

        self.list_selected_spells = QListWidget()
        self.list_selected_spells.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_selected_spells.setMinimumHeight(WAND_SPELL_LIST_MIN_H)
        self.list_selected_spells.setAccessibleName("Selected spells list")
        left_layout.addWidget(self.list_selected_spells, stretch=1)

        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(SPACING_SM)
        self._right_title = QLabel(tr_ui("wand_available_title"))
        right_layout.addWidget(self._right_title)

        self.list_available_spells = QListWidget()
        self.list_available_spells.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_available_spells.setMinimumHeight(WAND_SPELL_LIST_MIN_H)
        self.list_available_spells.setAccessibleName("Available spells list")
        right_layout.addWidget(self.list_available_spells, stretch=1)

        split.addWidget(left_col)
        split.addWidget(right_col)
        split.setChildrenCollapsible(False)
        split.setSizes([1, 1])
        layout.addWidget(split, stretch=1)

        # Backward-compat alias
        self.list_firmware = self.list_selected_spells

    def apply_ui_language(self) -> None:
        self._hdr_payload.setText(tr_ui("wand_section_payload"))
        self._left_title.setText(tr_ui("wand_selected_title"))
        self._right_title.setText(tr_ui("wand_available_title"))
        self._refresh_lists()

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot nội bộ."""
        self.list_selected_spells.itemClicked.connect(self._on_selected_item_clicked)
        self.list_available_spells.itemClicked.connect(self._on_available_item_clicked)

    def _refresh_lists(self) -> None:
        """Xóa và vẽ lại cả hai danh sách spell từ dữ liệu nội bộ."""
        self.list_selected_spells.clear()
        self.list_available_spells.clear()

        if not self._spell_order:
            self._add_empty_row(self.list_selected_spells, tr_ui("wand_wait_sel"))
            self._add_empty_row(self.list_available_spells, tr_ui("wand_wait_avail"))
            return

        for name in self._spell_order:
            count = int(self._spell_counts.get(name, 0))
            if name in self._selected_spells:
                self._add_spell_row(self.list_selected_spells, name, count)
            else:
                self._add_spell_row(self.list_available_spells, name, count)

    def _add_spell_row(self, list_widget: QListWidget, spell_name: str, count: int) -> None:
        """Thêm một hàng spell vào list widget.

        Args:
            list_widget: QListWidget đích.
            spell_name: Tên spell.
            count: Số lượng mẫu.
        """
        item = QListWidgetItem(list_widget)
        item.setData(Qt.ItemDataRole.UserRole, spell_name)
        p = theme_manager.get_palette()

        widget = QWidget()
        widget.setStyleSheet(
            f"background-color: {p.SURFACE_TERTIARY}; border: 1px solid {p.BORDER}; "
            f"border-radius: {CARD_RADIUS}; font-family: {APP_FONT_STACK};"
        )

        row = QHBoxLayout(widget)
        row.setContentsMargins(MARGIN_STANDARD, SPACING_SM, MARGIN_STANDARD, SPACING_SM)
        row.setSpacing(SPACING_SM)

        name_label = QLabel(spell_name)
        name_label.setWordWrap(True)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        name_label.setStyleSheet(
            f"color: {p.TEXT_PRIMARY}; font-size: 13px; font-weight: 700; font-family: {APP_FONT_STACK};"
        )

        rarity = self._resolve_rarity(count)
        badge = self._make_rarity_badge(rarity.label, rarity.color)

        row.addWidget(name_label, stretch=1)
        row.addWidget(badge)

        item.setSizeHint(widget.sizeHint())
        list_widget.setItemWidget(item, widget)

    def _add_empty_row(self, list_widget: QListWidget, text: str) -> None:
        item = QListWidgetItem(list_widget)
        p = theme_manager.get_palette()
        widget = QLabel(text)
        widget.setStyleSheet(STYLE_WAND_EMPTY_ROW_TEMPLATE.format(color=p.TEXT_SECONDARY))
        widget.setWordWrap(True)
        widget.setContentsMargins(MARGIN_STANDARD, SPACING_SM, MARGIN_STANDARD, SPACING_SM)
        item.setSizeHint(widget.sizeHint())
        list_widget.setItemWidget(item, widget)

    def _toggle_spell(self, spell_name: str) -> None:
        """Chuyển trạng thái selected/available của spell và vẽ lại."""
        if spell_name not in self._spell_order:
            return
        if spell_name in self._selected_spells:
            self._selected_spells.remove(spell_name)
        else:
            self._selected_spells.add(spell_name)
        self._refresh_lists()

    def _on_selected_item_clicked(self, item: QListWidgetItem) -> None:
        """Xử lý khi người dùng click vào spell đã chọn — bỏ chọn nó."""
        spell_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if spell_name:
            self._toggle_spell(spell_name)

    def _on_available_item_clicked(self, item: QListWidgetItem) -> None:
        """Xử lý khi người dùng click vào spell chưa chọn — thêm vào danh sách chọn."""
        spell_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if spell_name:
            self._toggle_spell(spell_name)

    @staticmethod
    def _make_rarity_badge(label: str, color: str) -> QLabel:
        return make_rarity_badge_wand(label, color)

    @staticmethod
    def _resolve_rarity(count: int) -> RarityTier:
        return max(
            (tier for tier in RARITY_TIERS if count >= tier.min_count),
            key=lambda tier: tier.min_count,
            default=RARITY_TIERS[0],
        )

"""
ui/wand_panels/spell_payload_panel.py — Panel chọn danh sách spell cho Firmware.

Cho phép người dùng chọn các câu thần chú từ thư viện để đưa vào gói dữ liệu (payload)
của firmware. Hỗ trợ hiển thị độ hiếm (rarity) dựa trên số lượng mẫu đã thu thập.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from logic.rarity_utils import RARITY_TIERS, RarityTier
from logic.theme_manager import theme_manager
from ui.component_factory import make_rarity_badge_wand
from ui.i18n_bridge import tr_ui
from ui.modern_layout import MARGIN_STANDARD, SPACING_SM
from ui.tokens import (
    APP_FONT_STACK,
    CARD_RADIUS,
    TITLE_FONT_STACK,
    WAND_SPELL_LIST_MIN_H,
)
from .shared import make_section_label


class WandSpellPayloadPanel(QWidget):
    """
    Panel hiển thị danh sách các spell khả dụng và các spell đã chọn cho firmware.
    """

    def __init__(self) -> None:
        super().__init__()
        self._spell_order: list[str] = []
        self._selected_spells: set[str] = set()
        self._spell_counts: dict[str, int] = {}
        
        self._init_ui()
        self._init_signals()
        self.refresh_styles()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện (Requirement 7: Removed splitter, added 24px gap)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._hdr_payload = make_section_label(tr_ui("wand_section_payload"))
        layout.addWidget(self._hdr_payload)

        # Requirement 7: Use QHBoxLayout with 24px gap instead of thick splitter
        content_row = QHBoxLayout()
        content_row.setSpacing(24)

        # Cột trái: Đã chọn
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_title = QLabel(tr_ui("wand_selected_title"))
        left_layout.addWidget(self._left_title)

        self.list_selected_spells = QListWidget()
        self.list_selected_spells.setMinimumHeight(WAND_SPELL_LIST_MIN_H)
        left_layout.addWidget(self.list_selected_spells, stretch=1)

        # Requirement 7: Subtle 1px border divider
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.NoFrame)
        self._divider.setFixedWidth(1)
        
        # Cột phải: Khả dụng
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_title = QLabel(tr_ui("wand_available_title"))
        right_layout.addWidget(self._right_title)

        self.list_available_spells = QListWidget()
        self.list_available_spells.setMinimumHeight(WAND_SPELL_LIST_MIN_H)
        right_layout.addWidget(self.list_available_spells, stretch=1)

        content_row.addWidget(left_col, stretch=1)
        content_row.addWidget(self._divider)
        content_row.addWidget(right_col, stretch=1)
        
        layout.addLayout(content_row, stretch=1)

        # Alias cho Handler
        self.list_firmware = self.list_selected_spells

    def _init_signals(self) -> None:
        """Kết nối signal khi người dùng click chọn spell."""
        self.list_selected_spells.itemClicked.connect(self._on_selected_item_clicked)
        self.list_available_spells.itemClicked.connect(self._on_available_item_clicked)

    # ── Public methods ──────────────────────────

    def load_spell_list(self, spell_counts: dict[str, int]) -> None:
        """Nạp danh sách spell và giữ lại trạng thái đã chọn."""
        self._spell_counts = dict(spell_counts)
        self._spell_order = [name for name in spell_counts.keys() if str(name).strip()]
        self._selected_spells.intersection_update(self._spell_order)
        self._refresh_lists()

    def get_checked_spells(self) -> list[str]:
        """Lấy danh sách các spell đã chọn nạp firmware."""
        return [name for name in self._spell_order if name in self._selected_spells]

    def apply_ui_language(self) -> None:
        """Làm mới văn bản khi ngôn ngữ ứng dụng thay đổi."""
        self._hdr_payload.setText(tr_ui("wand_section_payload"))
        self._left_title.setText(tr_ui("wand_selected_title"))
        self._right_title.setText(tr_ui("wand_available_title"))
        self._refresh_lists()

    def refresh_styles(self) -> None:
        """Làm mới style theo theme hiện tại."""
        self._hdr_payload.setProperty("type", "settings_section_label")
        self._left_title.setProperty("type", "settings_section_label")
        self._right_title.setProperty("type", "settings_section_label")
        
        self.list_selected_spells.setProperty("type", "wand_list")
        self.list_available_spells.setProperty("type", "wand_list")
        p = theme_manager.get_palette()
        self._divider.setStyleSheet(f"background-color: {p.BORDER_LIGHT};")
        self._refresh_lists()

    # ── Private methods ─────────────────────────

    def _refresh_lists(self) -> None:
        """Vẽ lại nội dung cho cả hai danh sách."""
        self.list_selected_spells.clear()
        self.list_available_spells.clear()

        if not self._spell_order:
            self._add_empty_row(self.list_selected_spells, tr_ui("wand_wait_sel"))
            self._add_empty_row(self.list_available_spells, tr_ui("wand_wait_avail"))
            return

        for name in self._spell_order:
            count = int(self._spell_counts.get(name, 0))
            target_list = self.list_selected_spells if name in self._selected_spells else self.list_available_spells
            self._add_spell_row(target_list, name, count)

    def _add_spell_row(self, list_widget: QListWidget, name: str, count: int) -> None:
        """Tạo và thêm một hàng spell tùy chỉnh vào danh sách."""
        item = QListWidgetItem(list_widget)
        item.setData(Qt.ItemDataRole.UserRole, name)
        p = theme_manager.get_palette()

        widget = QWidget()
        widget.setProperty("type", "statistics_card")
        widget.setMinimumHeight(42)
        row = QHBoxLayout(widget)
        row.setContentsMargins(12, 8, 12, 8)

        name_lbl = QLabel(name)
        name_lbl.setProperty("type", "wand_spell_name")
        
        rarity = self._resolve_rarity(count)
        badge = make_rarity_badge_wand(rarity.label, rarity.color)

        row.addWidget(name_lbl, stretch=1)
        row.addWidget(badge)
        item.setSizeHint(QSize(0, 44))
        list_widget.setItemWidget(item, widget)

    def _add_empty_row(self, list_widget: QListWidget, text: str) -> None:
        """Thêm một dòng thông báo trạng thái trống."""
        item = QListWidgetItem(list_widget)
        p = theme_manager.get_palette()
        lbl = QLabel(text)
        lbl.setProperty("type", "empty_state_text")
        lbl.setStyleSheet(f"color: {p.TEXT_SECONDARY};")
        lbl.setWordWrap(True)
        item.setSizeHint(lbl.sizeHint())
        list_widget.setItemWidget(item, lbl)

    def _resolve_rarity(self, count: int) -> RarityTier:
        """Xác định độ hiếm của cử chỉ dựa trên số mẫu."""
        return max((t for t in RARITY_TIERS if count >= t.min_count), key=lambda t: t.min_count, default=RARITY_TIERS[0])

    # ── Slots ───────────────────────────────────

    def _on_selected_item_clicked(self, item: QListWidgetItem) -> None:
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if name:
            self._selected_spells.discard(name)
            self._refresh_lists()

    def _on_available_item_clicked(self, item: QListWidgetItem) -> None:
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if name:
            self._selected_spells.add(name)
            self._refresh_lists()

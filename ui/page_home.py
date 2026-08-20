"""
ui/page_home.py — Trang Dashboard chính ("The Threshold").

Hiển thị kết quả nhận diện spell thời gian thực, lịch sử phiên,
danh sách spell đã tải, và tip giáo dục luân phiên.
Tối ưu hóa thị giác với thẻ mượt mà, hiệu ứng drop-shadow, và huy hiệu động.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                             QLabel, QListWidget, QListWidgetItem,
                             QProgressBar, QVBoxLayout, QWidget)

from logic.dataset_layout import _PRIMITIVE_LOGICAL_NAMES, folder_name_match_key
from logic.home_tips_i18n import get_tip_pool
from logic.locale_manager import locale_manager
from logic.rarity_utils import resolve_confidence_level, resolve_rarity
from logic.spell_config_store import SpellConfigStore
from logic.tip_rotator import TipRotator
from logic.theme_manager import theme_manager
from ui.component_factory import (make_card, make_empty_state_card,
                                  make_rarity_badge_wand, make_section_label)
from ui.i18n_bridge import tr_ui
from ui.tokens import (MARGIN_COMFORTABLE, PRIMARY_COLOR, SPACING_LG,
                       SPACING_MD, SPACING_SM, SPACING_XS)

# ── Constants ────────────────────────────────────────────────────────────────
_TIP_ROTATION_MS = 15000
_RELATIVE_TIME_REFRESH_MS = 1000
_PULSE_DURATION_MS = 600
_STAND_BY_NAMES = frozenset({"STAND BY", "STAND_BY"})


def _add_shadow(widget: QWidget, blur: int = 16, alpha: int = 15, y_offset: int = 4) -> None:
    """Thêm hiệu ứng đổ bóng mượt (Soft drop shadow) không gây nghẽn khởi động."""
    def _apply() -> None:
        try:
            shadow = QGraphicsDropShadowEffect(widget)
            shadow.setBlurRadius(blur)
            shadow.setColor(Qt.GlobalColor.black)
            shadow.setOffset(0, y_offset)
            effect_color = shadow.color()
            effect_color.setAlpha(alpha)
            shadow.setColor(effect_color)
            widget.setGraphicsEffect(shadow)
        except Exception:
            pass
    QTimer.singleShot(100, _apply)


class PageHome(QWidget):
    """
    Trang Dashboard hiển thị spell nhận diện, lịch sử, và trạng thái hệ thống.
    Giao diện hiện đại, mượt mà với badge động và thẻ nổi.
    """

    def __init__(self, data_store, spell_config_store: SpellConfigStore | None = None) -> None:
        super().__init__()
        self.data_store = data_store
        if isinstance(spell_config_store, SpellConfigStore):
            self.spell_config_store = spell_config_store
        else:
            cand = getattr(data_store, "spell_config_store", None)
            self.spell_config_store = cand if isinstance(cand, SpellConfigStore) else SpellConfigStore()

        self._connected = False
        self._current_mode = "IDLE"
        self._last_hero_spell = ""
        self._last_confidence_level: str | None = None

        self._tip_rotator = TipRotator(get_tip_pool(
            locale_manager.current_language,
            self._last_confidence_level,
        ))

        self._init_timers()
        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện dashboard."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            MARGIN_COMFORTABLE, MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE, MARGIN_COMFORTABLE,
        )
        layout.setSpacing(SPACING_LG)

        # 1. System status bar (connection + mode)
        self._build_status_bar(layout)

        # 2. Tip banner
        self._build_tip_banner(layout)

        # 3. Hero banner — recognized spell
        self._build_hero_banner(layout)

        # 4. Bottom grid: History (left) + Loaded Spells (right)
        self._build_bottom_grid(layout)

        self.refresh_styles()

    def _init_signals(self) -> None:
        """Kết nối signal/slot."""
        theme_manager.theme_changed.connect(self.refresh_styles)

    def _init_timers(self) -> None:
        """Khởi tạo các timer nội bộ UI-only."""
        self._tip_timer = QTimer(self)
        self._tip_timer.setInterval(_TIP_ROTATION_MS)
        self._tip_timer.timeout.connect(self._on_tip_timer_tick)
        self._tip_timer.start()

        self._relative_time_timer = QTimer(self)
        self._relative_time_timer.setInterval(_RELATIVE_TIME_REFRESH_MS)
        self._relative_time_timer.timeout.connect(
            self._refresh_history_relative_times
        )

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setSingleShot(True)
        self._pulse_timer.timeout.connect(self._on_pulse_timer_done)

        self._orb_dim_timer = QTimer(self)
        self._orb_dim_timer.setSingleShot(True)
        self._orb_dim_timer.timeout.connect(self._set_orb_idle_style)

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ store."""
        self.set_connection_status(self.data_store.is_connected)
        self.update_loaded_spells(getattr(self.data_store, "registered_prototypes", set()))

    # ── Public methods ──────────────────────────

    def set_connection_status(self, connected: bool) -> None:
        """Cập nhật trạng thái kết nối phần cứng."""
        self._connected = connected
        self._refresh_status_bar()

    def set_mode(self, mode: str) -> None:
        """Cập nhật chế độ hoạt động hiện tại."""
        self._current_mode = mode.upper()
        self._refresh_status_bar()

    def show_recognized_spell(self, action: str, confidence: float) -> None:
        """Hiển thị spell vừa nhận diện trên hero banner với thanh tự tin và hiệu ứng pulse."""
        if action in ("None", ""):
            self.lbl_hero_spell.setText(tr_ui("home_hero_idle"))
            self.lbl_hero_confidence.setText("")
            self.lbl_hero_confidence.setProperty("level", "")
            self.hero_confidence_bar.setValue(0)
            self.hero_confidence_bar.setVisible(False)
            self._set_orb_idle_style()
            self._repolish(self.lbl_hero_confidence)
            return

        self.lbl_hero_spell.setText(action)
        pct = int(confidence * 100)
        level = resolve_confidence_level(confidence)
        self._last_confidence_level = level

        level_str = level.upper()
        self.lbl_hero_confidence.setText(f"⚡ {pct}% Match  •  {level_str}")
        self.lbl_hero_confidence.setProperty("level", level)
        self._repolish(self.lbl_hero_confidence)

        self.hero_confidence_bar.setVisible(True)
        self.hero_confidence_bar.setValue(pct)

        # Pulse glow on new spell with spell's configured color
        if action != self._last_hero_spell:
            self._last_hero_spell = action
            self.lbl_hero_spell.setProperty("pulsing", True)
            try:
                cfg = self.spell_config_store.get_spell_config(action)
                color = cfg.get("color") if isinstance(cfg, dict) else [255, 255, 255]
                if not (isinstance(color, (list, tuple)) and len(color) >= 3):
                    color = [255, 255, 255]
                r, g, b = int(color[0]), int(color[1]), int(color[2])
                self.lbl_hero_spell.setStyleSheet(f"color: rgb({r}, {g}, {b}); font-weight: 700;")
                if hasattr(self, "orb_led"):
                    self.orb_led.setStyleSheet(
                        f"QLabel {{ background: qradialgradient(cx:0.5, cy:0.5, radius:0.65, fx:0.35, fy:0.35, "
                        f"stop:0 #FFFFFF, stop:0.45 rgb({r}, {g}, {b}), stop:1 rgba({r}, {g}, {b}, 0.25)); "
                        f"border-radius: 14px; border: 2px solid rgb({r}, {g}, {b}); }}"
                    )
                    self._orb_dim_timer.start(5000)
            except Exception:
                self.lbl_hero_spell.setStyleSheet("")
                self._set_orb_idle_style()
            self._repolish(self.lbl_hero_spell)
            self._pulse_timer.start(_PULSE_DURATION_MS)

    def update_spell_history(self, history: list[dict]) -> None:
        """Cập nhật danh sách lịch sử spell nhận diện gần đây với các hàng widget tùy chỉnh."""
        if not history:
            self._show_history_empty(True)
            return

        self._show_history_empty(False)
        self.history_list.clear()
        now = time.time()
        for entry in history:
            widget = self._make_history_item_widget(entry, now)
            item = QListWidgetItem(self.history_list)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)

        # Start relative time refresh if not running
        if not self._relative_time_timer.isActive():
            self._relative_time_timer.start()

    def update_loaded_spells(self, spells: set[str]) -> None:
        """Cập nhật danh sách spell có prototype trong phiên."""
        self._last_loaded_spells = set(spells)
        prim_keys = {folder_name_match_key(p) for p in _PRIMITIVE_LOGICAL_NAMES}
        prim_keys.add("STAND BY")
        prim_keys.add("STAND_BY")

        filtered = {
            s for s in spells
            if folder_name_match_key(s) not in prim_keys
            and "::" not in s
        }

        if not filtered:
            self._show_loaded_empty(True)
            return

        self._show_loaded_empty(False)
        # Rebuild loaded spells layout
        self._clear_layout(self._loaded_spells_content_layout)
        for spell_name in sorted(filtered):
            count = self.data_store.spell_counts.get(spell_name, 0)
            row = self._make_loaded_spell_row(spell_name, count)
            self._loaded_spells_content_layout.addWidget(row)
        self._loaded_spells_content_layout.addStretch()

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ cho các nhãn tĩnh."""
        lang = locale_manager.current_language
        if hasattr(self, "_lbl_tip_eyebrow"):
            self._lbl_tip_eyebrow.setText(tr_ui("home_tip_title"))
        pool = get_tip_pool(lang, self._last_confidence_level)
        self._tip_rotator.reload_pool(pool)
        self.lbl_tip.setText(self._tip_rotator.next_tip())

        self._refresh_status_bar()
        self.set_connection_status(self._connected)
        self.set_mode(self._current_mode)

        self._lbl_hero_subtitle.setText(tr_ui("home_hero_subtitle"))
        self._lbl_history_title.setText(tr_ui("home_history_title"))
        self._lbl_loaded_title.setText(tr_ui("home_loaded_title"))

        if not self.data_store.spell_history:
            if hasattr(self, "_history_empty_card"):
                lbl = self._history_empty_card.findChild(QLabel, "")
                if lbl:
                    lbl.setText(tr_ui("home_history_empty"))

        if hasattr(self, "_last_loaded_spells"):
            self.update_loaded_spells(self._last_loaded_spells)

        self._refresh_history_relative_times()

    def refresh_styles(self) -> None:
        """Làm mới giao diện theo theme hiện tại."""

    # ── Private methods — UI builders ───────────

    def _build_status_bar(self, parent_layout: QVBoxLayout) -> None:
        """Xây dựng thanh trạng thái kết nối + mode + spell count trong khung nổi mượt."""
        status_frame = QFrame()
        status_frame.setObjectName("HomeStatusBar")
        _add_shadow(status_frame, blur=12, alpha=10, y_offset=2)

        bar = QHBoxLayout(status_frame)
        bar.setContentsMargins(12, 6, 12, 6)
        bar.setSpacing(SPACING_MD)

        self.status_bar = QLabel(tr_ui("home_status_disconnected"))
        self.status_bar.setFixedHeight(32)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setProperty("type", "status_label")
        self.status_bar.setProperty("status", "error")

        self._mode_chip = QLabel(f"{tr_ui('home_mode_prefix')} IDLE")
        self._mode_chip.setFixedHeight(32)
        self._mode_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_chip.setProperty("type", "status_label")
        self._mode_chip.setProperty("status", "accent")

        self._spell_count_chip = QLabel("")
        self._spell_count_chip.setFixedHeight(32)
        self._spell_count_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spell_count_chip.setProperty("type", "status_label")

        bar.addWidget(self.status_bar, stretch=2)
        bar.addWidget(self._mode_chip, stretch=1)
        bar.addWidget(self._spell_count_chip, stretch=1)
        parent_layout.addWidget(status_frame)

    def _build_tip_banner(self, parent_layout: QVBoxLayout) -> None:
        """Xây dựng banner tip giáo dục luân phiên với icon lớn và layout nổi bật."""
        self.tip_card = QFrame()
        self.tip_card.setObjectName("HomeTipCard")
        _add_shadow(self.tip_card, blur=14, alpha=12, y_offset=3)

        tip_layout = QHBoxLayout(self.tip_card)
        tip_layout.setContentsMargins(18, 14, 18, 14)
        tip_layout.setSpacing(14)

        # Tip icon
        lbl_icon = QLabel("💡")
        lbl_icon.setStyleSheet("font-size: 26px;")
        tip_layout.addWidget(lbl_icon, alignment=Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)

        self._lbl_tip_eyebrow = QLabel(tr_ui("home_tip_title"))
        self._lbl_tip_eyebrow.setProperty("type", "tip_eyebrow")

        self.lbl_tip = QLabel(self._tip_rotator.next_tip())
        self.lbl_tip.setProperty("type", "tip_text")
        self.lbl_tip.setWordWrap(True)

        text_box.addWidget(self._lbl_tip_eyebrow)
        text_box.addWidget(self.lbl_tip)
        tip_layout.addLayout(text_box, stretch=1)

        parent_layout.addWidget(self.tip_card)

    def _set_orb_idle_style(self) -> None:
        """Đặt style cho quả cầu LED ma thuật ở trạng thái chờ."""
        if hasattr(self, "orb_led"):
            self.orb_led.setStyleSheet(
                "QLabel { background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.35, fy:0.35, "
                "stop:0 #E5E5EA, stop:1 #8E8E93); "
                "border-radius: 14px; border: 2px solid rgba(0, 0, 0, 0.12); }"
            )

    def _build_hero_banner(self, parent_layout: QVBoxLayout) -> None:
        """Xây dựng hero banner hiển thị spell nhận diện với thanh confidence bar và đèn LED ma thuật."""
        hero_card, hero_layout = make_card(
            margins=(24, 16, 24, 16), spacing=SPACING_XS,
        )
        hero_card.setObjectName("HomeHeroCard")
        hero_card.setFixedHeight(190)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _add_shadow(hero_card, blur=20, alpha=15, y_offset=4)

        # Header hàng: Quả cầu LED ảo + Tiêu đề phụ
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.orb_led = QLabel()
        self.orb_led.setFixedSize(28, 28)
        self.orb_led.setToolTip("Magic Wand LED Indicator")
        self._set_orb_idle_style()
        top_row.addWidget(self.orb_led)

        self._lbl_hero_subtitle = QLabel(tr_ui("home_hero_subtitle"))
        self._lbl_hero_subtitle.setProperty("type", "hero_subtitle")
        self._lbl_hero_subtitle.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self._lbl_hero_subtitle)

        hero_layout.addLayout(top_row)

        self.lbl_hero_spell = QLabel(tr_ui("home_hero_idle"))
        self.lbl_hero_spell.setProperty("type", "hero_spell_name")
        self.lbl_hero_spell.setProperty("pulsing", False)
        self.lbl_hero_spell.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_hero_confidence = QLabel("")
        self.lbl_hero_confidence.setProperty("type", "hero_confidence")
        self.lbl_hero_confidence.setProperty("level", "")
        self.lbl_hero_confidence.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hero_confidence_bar = QProgressBar()
        self.hero_confidence_bar.setProperty("type", "hero_confidence_bar")
        self.hero_confidence_bar.setFixedWidth(220)
        self.hero_confidence_bar.setRange(0, 100)
        self.hero_confidence_bar.setValue(0)
        self.hero_confidence_bar.setTextVisible(False)
        self.hero_confidence_bar.setVisible(False)

        hero_layout.addWidget(self.lbl_hero_spell)
        hero_layout.addWidget(self.lbl_hero_confidence, alignment=Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.hero_confidence_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(hero_card)

    def _build_bottom_grid(self, parent_layout: QVBoxLayout) -> None:
        """Xây dựng lưới dưới: lịch sử (trái) + spell đã tải (phải)."""
        grid = QHBoxLayout()
        grid.setSpacing(SPACING_LG)

        # Left: Spell history
        left_card, left_layout = make_card(
            margins=(20, 16, 20, 16), spacing=SPACING_SM,
        )
        left_card.setObjectName("HomeHistoryCard")
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        _add_shadow(left_card, blur=16, alpha=10, y_offset=3)

        self._lbl_history_title = make_section_label(
            tr_ui("home_history_title"), accent=True,
        )
        left_layout.addWidget(self._lbl_history_title)

        self.history_list = QListWidget()
        self.history_list.setObjectName("HomeHistoryList")

        self._history_empty_card, _ = make_empty_state_card(
            tr_ui("home_history_empty"),
            body=tr_ui("home_history_empty_body"),
        )
        self._history_empty_card.setMinimumHeight(140)

        left_layout.addWidget(self.history_list, stretch=1)
        left_layout.addWidget(self._history_empty_card, stretch=1)
        self._show_history_empty(True)

        grid.addWidget(left_card, stretch=1)

        # Right: Loaded spells
        right_card, right_layout = make_card(
            margins=(20, 16, 20, 16), spacing=SPACING_SM,
        )
        right_card.setObjectName("HomeLoadedCard")
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        _add_shadow(right_card, blur=16, alpha=10, y_offset=3)

        self._lbl_loaded_title = make_section_label(
            tr_ui("home_loaded_title"), accent=True,
        )
        right_layout.addWidget(self._lbl_loaded_title)

        self._loaded_empty_card, _ = make_empty_state_card(
            tr_ui("home_loaded_empty"),
            body=tr_ui("home_loaded_empty_body"),
        )
        self._loaded_empty_card.setMinimumHeight(140)

        self._loaded_spells_container = QWidget()
        self._loaded_spells_content_layout = QVBoxLayout(
            self._loaded_spells_container,
        )
        self._loaded_spells_content_layout.setContentsMargins(0, 0, 0, 0)
        self._loaded_spells_content_layout.setSpacing(SPACING_XS)

        right_layout.addWidget(self._loaded_empty_card, stretch=1)
        right_layout.addWidget(self._loaded_spells_container, stretch=1)
        self._show_loaded_empty(True)

        grid.addWidget(right_card, stretch=1)
        parent_layout.addLayout(grid, stretch=1)

    # ── Private methods — helpers ───────────────

    def _refresh_status_bar(self) -> None:
        """Đồng bộ nội dung 3 chip trạng thái."""
        status_key = (
            "home_status_connected" if self._connected
            else "home_status_disconnected"
        )
        prefix = "● " if self._connected else "○ "
        self.status_bar.setText(f"{prefix}{tr_ui(status_key)}")
        self.status_bar.setProperty(
            "status", "success" if self._connected else "error",
        )
        self._repolish(self.status_bar)

        self._mode_chip.setText(f"⚡ {tr_ui('home_mode_prefix')} {self._current_mode}")

        total = sum(
            1 for k in self.data_store.spell_counts
            if k not in _PRIMITIVE_LOGICAL_NAMES
            and "::" not in k
            and k not in _STAND_BY_NAMES
        )
        self._spell_count_chip.setText(
            f"🔮 {tr_ui('home_spell_count', count=total)}",
        )

    def _make_history_item_widget(self, entry: dict, now: float) -> QFrame:
        """Tạo một widget hàng lịch sử hiển thị spell, timestamp, và confidence badge."""
        row = QFrame()
        row.setProperty("type", "history_item_row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Icon badge
        icon_lbl = QLabel("🔮")
        icon_lbl.setStyleSheet("font-size: 16px;")

        # Spell name & timestamp
        vbox = QVBoxLayout()
        vbox.setSpacing(2)

        lbl_spell = QLabel(entry.get("spell", ""))
        lbl_spell.setStyleSheet("font-weight: 700; font-size: 13px;")

        elapsed = now - entry.get("timestamp", now)
        rel_text = self._format_relative_time(elapsed)
        lbl_rel = QLabel(rel_text)
        lbl_rel.setObjectName("lbl_rel_time")
        lbl_rel.setProperty("type", "settings_hint")

        vbox.addWidget(lbl_spell)
        vbox.addWidget(lbl_rel)

        # Confidence pill badge
        conf = entry.get("confidence", 0.0)
        pct = int(conf * 100)
        level = resolve_confidence_level(conf)

        conf_badge = QLabel(f"{pct}%")
        conf_badge.setProperty("type", "hero_confidence")
        conf_badge.setProperty("level", level)
        conf_badge.setFixedHeight(26)
        conf_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_lbl)
        layout.addLayout(vbox, stretch=1)
        layout.addWidget(conf_badge)
        return row

    def _format_relative_time(self, elapsed: float) -> str:
        """Chuyển đổi khoảng thời gian thành chuỗi tương đối."""
        if elapsed < 5:
            return tr_ui("time_just_now")
        if elapsed < 60:
            return tr_ui("time_seconds_ago", n=int(elapsed))
        minutes = int(elapsed / 60)
        if minutes < 60:
            return tr_ui("time_minutes_ago", n=minutes)
        hours = int(minutes / 60)
        return tr_ui("time_hours_ago", n=hours)

    def _make_loaded_spell_row(
        self, spell_name: str, count: int,
    ) -> QFrame:
        """Tạo một hàng hiển thị spell đã tải với rarity badge."""
        row = QFrame()
        row.setProperty("type", "loaded_spell_row")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(SPACING_MD)

        icon_lbl = QLabel("✨")
        icon_lbl.setStyleSheet("font-size: 14px;")

        lbl_name = QLabel(spell_name)
        lbl_name.setStyleSheet("font-weight: 600; font-size: 13px;")

        tier = resolve_rarity(count)
        badge = make_rarity_badge_wand(tier.label, tier.color)

        lbl_count = QLabel(tr_ui("home_samples_count", count=count))
        lbl_count.setProperty("type", "settings_hint")

        row_layout.addWidget(icon_lbl)
        row_layout.addWidget(lbl_name, stretch=1)
        row_layout.addWidget(badge)
        row_layout.addWidget(lbl_count)
        return row

    def _show_history_empty(self, empty: bool) -> None:
        """Hiển thị/ẩn trạng thái trống cho lịch sử."""
        self.history_list.setVisible(not empty)
        self._history_empty_card.setVisible(empty)
        if empty and hasattr(self, "_relative_time_timer") and self._relative_time_timer.isActive():
            self._relative_time_timer.stop()

    def _show_loaded_empty(self, empty: bool) -> None:
        """Hiển thị/ẩn trạng thái trống cho spell đã tải."""
        self._loaded_empty_card.setVisible(empty)
        self._loaded_spells_container.setVisible(not empty)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """Xóa toàn bộ widget trong layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _repolish(self, widget: QWidget) -> None:
        """Cập nhật style sau khi thay đổi dynamic property."""
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _configure_accessibility(self) -> None:
        """Thiết lập thông tin hỗ trợ người khiếm thị."""
    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if hasattr(self, "_tip_timer") and not self._tip_timer.isActive():
            self._tip_timer.start()

    def hideEvent(self, event: Any) -> None:
        super().hideEvent(event)
        if hasattr(self, "_tip_timer") and self._tip_timer.isActive():
            self._tip_timer.stop()

    # ── Slots ───────────────────────────────────

    def _on_tip_timer_tick(self) -> None:
        """Luân phiên hiển thị tip mới dựa trên mức độ tự tin nhận diện gần nhất."""
        pool = get_tip_pool(
            locale_manager.current_language,
            self._last_confidence_level,
        )
        self.lbl_tip.setText(self._tip_rotator.next_tip(pool))

    def _on_pulse_timer_done(self) -> None:
        """Tắt hiệu ứng pulse sau thời gian quy định."""
        self.lbl_hero_spell.setProperty("pulsing", False)
        self.lbl_hero_spell.setStyleSheet("")
        self._repolish(self.lbl_hero_spell)

    def _refresh_history_relative_times(self) -> None:
        """Cập nhật thời gian tương đối trong danh sách lịch sử."""
        now = time.time()
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            entry = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(entry, dict):
                widget = self.history_list.itemWidget(item)
                if widget:
                    lbl_rel = widget.findChild(QLabel, "lbl_rel_time")
                    if lbl_rel:
                        elapsed = now - entry.get("timestamp", now)
                        lbl_rel.setText(self._format_relative_time(elapsed))

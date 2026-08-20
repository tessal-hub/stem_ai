"""
ui/beginner_guide_dialog.py — Hộp thoại hướng dẫn người dùng mới (Beginner Guide).

Cung cấp popup hướng dẫn trực quan, phân bước rõ ràng cho từng màn hình
(Trang chủ, Ghi mẫu, Đũa phép, Cài đặt), giải thích chi tiết 2 loại firmware và lộ trình 3 bước chuẩn xác.
Kích thước rộng rãi (960x700), bố cục 2 cột trực quan, không bị tràn màn hình hay cắt chữ.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from ui.component_factory import make_card, make_primary_button
from ui.i18n_bridge import tr_ui
from ui.tokens import (
    ACCENT,
    APP_FONT_STACK,
    BTN_H,
    SUCCESS,
    TEXT_MUTED,
    WARNING,
)


class BeginnerGuideDialog(QDialog):
    """Hộp thoại hướng dẫn người mới với kích thước rộng và bố cục trực quan đa cột."""

    sig_navigate_to = pyqtSignal(int)

    def __init__(self, initial_page_index: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page_idx = initial_page_index
        self.setWindowTitle(tr_ui("guide_modal_title"))

        # Kích thước rộng rãi để hiển thị đầy đủ mọi nội dung mà không bị chật chội
        self.setMinimumSize(880, 640)
        if parent is not None and hasattr(parent, "width") and parent.width() > 900:
            target_w = min(1080, max(960, int(parent.width() * 0.92)))
            target_h = min(780, max(680, int(parent.height() * 0.88)))
            self.resize(target_w, target_h)
        else:
            self.resize(960, 700)

        self.setModal(True)

        self._p = theme_manager.get_palette()
        self._is_dark = theme_manager.current_theme == "dark"

        self._init_ui()
        self._apply_theme()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        p = self._p

        # Header banner
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel("🪄")
        icon_lbl.setStyleSheet("font-size: 30px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self._lbl_title = QLabel(tr_ui("guide_modal_title"))
        self._lbl_title.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {p.TEXT_PRIMARY};")
        self._lbl_subtitle = QLabel(tr_ui("guide_modal_subtitle"))
        self._lbl_subtitle.setStyleSheet(f"font-size: 13px; color: {p.TEXT_SECONDARY};")
        title_box.addWidget(self._lbl_title)
        title_box.addWidget(self._lbl_subtitle)
        header.addLayout(title_box, stretch=1)

        layout.addLayout(header)

        # Tabs: Roadmap | Page Walkthrough | 2 Firmware Modes | Shortcuts
        self._tabs = QTabWidget()
        self._tabs.setObjectName("GuideTabs")

        self._tab_roadmap = self._build_roadmap_tab()
        self._tab_page_guide = self._build_page_guide_tab()
        self._tab_firmware = self._build_firmware_tab()
        self._tab_shortcuts = self._build_shortcuts_tab()

        self._tabs.addTab(self._tab_roadmap, tr_ui("guide_tab_roadmap"))
        self._tabs.addTab(self._tab_page_guide, tr_ui("guide_tab_current"))
        self._tabs.addTab(self._tab_firmware, tr_ui("guide_tab_firmware"))
        self._tabs.addTab(self._tab_shortcuts, tr_ui("guide_tab_shortcuts"))

        # If opening from non-home page, default to current page tab
        if self._current_page_idx in (2, 3):  # Record or Wand
            self._tabs.setCurrentIndex(1)

        layout.addWidget(self._tabs, stretch=1)

        # Bottom Bar: Close Button
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self._btn_close = make_primary_button(tr_ui("guide_btn_close"), height=38)
        self._btn_close.setMinimumWidth(140)
        self._btn_close.setStyleSheet("font-size: 13px; font-weight: 700;")
        self._btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(self._btn_close)

        layout.addLayout(bottom_bar)

    def _make_scroll_area(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        scroll.setWidget(container)
        return scroll, layout

    def _on_cta_clicked(self, tab_index: int) -> None:
        """Kích hoạt chuyển tab và đóng dialog hướng dẫn."""
        self.sig_navigate_to.emit(tab_index)
        self.accept()

    def _build_roadmap_tab(self) -> QWidget:
        scroll, layout = self._make_scroll_area()

        # Step 1: Connect & Flash Data Firmware (Tab 3: Wand)
        layout.addWidget(
            self._make_step_card(
                step_num="1",
                icon="🔌",
                title=tr_ui("guide_step1_title"),
                badge=tr_ui("nav_wand"),
                badge_color=ACCENT,
                desc=tr_ui("guide_step1_desc"),
                tips=[
                    tr_ui("guide_step1_tip1"),
                    tr_ui("guide_step1_tip2"),
                ],
                target_tab_idx=3,
                cta_text=tr_ui("guide_btn_go_wand"),
            )
        )

        # Step 2: Record & Crop Spells (Tab 2: Record)
        layout.addWidget(
            self._make_step_card(
                step_num="2",
                icon="✍️",
                title=tr_ui("guide_step2_title"),
                badge=tr_ui("nav_record"),
                badge_color=WARNING,
                desc=tr_ui("guide_step2_desc"),
                tips=[
                    tr_ui("guide_step2_tip1"),
                    tr_ui("guide_step2_tip2"),
                ],
                target_tab_idx=2,
                cta_text=tr_ui("guide_btn_go_record"),
            )
        )

        # Step 3: Build Model & Flash to Wand (Tab 3: Wand) -> Cast (Home)
        layout.addWidget(
            self._make_step_card(
                step_num="3",
                icon="⚡",
                title=tr_ui("guide_step3_title"),
                badge=tr_ui("nav_wand"),
                badge_color=SUCCESS,
                desc=tr_ui("guide_step3_desc"),
                tips=[
                    tr_ui("guide_step3_tip1"),
                ],
                target_tab_idx=3,
                cta_text=tr_ui("guide_btn_go_wand"),
            )
        )

        layout.addStretch()
        return scroll

    def _build_page_guide_tab(self) -> QWidget:
        scroll, layout = self._make_scroll_area()
        p = self._p

        pages_info = [
            (
                "nav_home",
                "🏠",
                tr_ui("guide_page_home_title"),
                tr_ui("guide_page_home_desc"),
                [
                    tr_ui("guide_page_home_tip1"),
                    tr_ui("guide_page_home_tip2"),
                ],
                0,
                tr_ui("guide_btn_go_home"),
            ),
            (
                "nav_record",
                "📊",
                tr_ui("guide_page_record_title"),
                tr_ui("guide_page_record_desc"),
                [
                    tr_ui("guide_page_record_tip1"),
                    tr_ui("guide_page_record_tip2"),
                    tr_ui("guide_page_record_tip3"),
                ],
                2,
                tr_ui("guide_btn_go_record"),
            ),
            (
                "nav_wand",
                "🪄",
                tr_ui("guide_page_wand_title"),
                tr_ui("guide_page_wand_desc"),
                [
                    tr_ui("guide_page_wand_tip1"),
                    tr_ui("guide_page_wand_tip2"),
                ],
                3,
                tr_ui("guide_btn_go_wand"),
            ),
        ]

        for nav_key, icon, title, desc, tips, tab_idx, cta_txt in pages_info:
            card, c_layout = make_card(margins=(18, 14, 18, 14), spacing=8)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            header = QHBoxLayout()
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet("font-size: 20px;")
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {p.TEXT_PRIMARY};")
            header.addWidget(lbl_icon)
            header.addWidget(lbl_t)
            header.addStretch()

            btn_go = QPushButton(cta_txt)
            btn_go.setFixedHeight(30)
            btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_go.setStyleSheet(
                f"background: rgba(0, 122, 255, 0.1); color: #007AFF; "
                f"border: 1px solid rgba(0, 122, 255, 0.35); border-radius: 6px; "
                f"padding: 2px 12px; font-weight: 700; font-size: 12px;"
            )
            btn_go.clicked.connect(lambda _, idx=tab_idx: self._on_cta_clicked(idx))
            header.addWidget(btn_go)

            c_layout.addLayout(header)

            lbl_d = QLabel(desc)
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet(f"font-size: 13px; color: {p.TEXT_PRIMARY}; line-height: 1.45;")
            c_layout.addWidget(lbl_d)

            if tips:
                for tip in tips:
                    lbl_tip = QLabel(f"• {tip}")
                    lbl_tip.setWordWrap(True)
                    lbl_tip.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 8px; line-height: 1.35;")
                    c_layout.addWidget(lbl_tip)

            layout.addWidget(card)

        layout.addStretch()
        return scroll

    def _build_firmware_tab(self) -> QWidget:
        scroll, layout = self._make_scroll_area()
        p = self._p

        # Header Intro
        intro_card, i_layout = make_card(margins=(18, 14, 18, 14), spacing=6)
        lbl_head = QLabel(tr_ui("guide_fw_header"))
        lbl_head.setStyleSheet("font-weight: 800; font-size: 16px; color: #007AFF;")
        lbl_sub = QLabel(tr_ui("guide_fw_subtitle"))
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet(f"font-size: 13px; color: {p.TEXT_SECONDARY}; line-height: 1.4;")
        i_layout.addWidget(lbl_head)
        i_layout.addWidget(lbl_sub)
        layout.addWidget(intro_card)

        # 2-Column Side-by-Side Grid for 2 Firmwares
        cols_container = QWidget()
        cols_layout = QHBoxLayout(cols_container)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(14)

        # Firmware 1: Data Collection (Left Column)
        fw1_card, f1_layout = make_card(margins=(18, 16, 18, 16), spacing=10)
        f1_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        h1 = QHBoxLayout()
        icon1 = QLabel("📡")
        icon1.setStyleSheet("font-size: 22px;")
        t1 = QLabel(tr_ui("guide_fw_data_title"))
        t1.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {p.TEXT_PRIMARY};")
        b1 = QLabel(tr_ui("btn_flash_data"))
        b1.setStyleSheet("background: rgba(0, 122, 255, 0.12); color: #007AFF; border: 1px solid rgba(0, 122, 255, 0.35); border-radius: 4px; padding: 3px 8px; font-weight: 700; font-size: 10px;")
        h1.addWidget(icon1)
        h1.addWidget(t1, stretch=1)
        h1.addWidget(b1)
        f1_layout.addLayout(h1)

        d1 = QLabel(tr_ui("guide_fw_data_desc"))
        d1.setWordWrap(True)
        d1.setStyleSheet(f"font-size: 12px; color: {p.TEXT_PRIMARY}; line-height: 1.45;")
        w1 = QLabel(f"• <b>{tr_ui('guide_fw_data_when')}</b>")
        w1.setWordWrap(True)
        w1.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 4px; line-height: 1.35;")
        feat1 = QLabel(f"• {tr_ui('guide_fw_data_feature')}")
        feat1.setWordWrap(True)
        feat1.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 4px; line-height: 1.35;")

        f1_layout.addWidget(d1)
        f1_layout.addWidget(w1)
        f1_layout.addWidget(feat1)
        f1_layout.addStretch()

        btn_fw1_go = QPushButton(tr_ui("guide_btn_go_settings"))
        btn_fw1_go.setFixedHeight(30)
        btn_fw1_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fw1_go.setStyleSheet(
            "background: rgba(0, 122, 255, 0.1); color: #007AFF; "
            "border: 1px solid rgba(0, 122, 255, 0.35); border-radius: 5px; "
            "padding: 2px 10px; font-weight: 700; font-size: 11px;"
        )
        btn_fw1_go.clicked.connect(lambda _: self._on_cta_clicked(4))
        f1_layout.addWidget(btn_fw1_go)

        cols_layout.addWidget(fw1_card, stretch=1)

        # Firmware 2: AI Engine (Right Column)
        fw2_card, f2_layout = make_card(margins=(18, 16, 18, 16), spacing=10)
        f2_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        h2 = QHBoxLayout()
        icon2 = QLabel("🧠")
        icon2.setStyleSheet("font-size: 22px;")
        t2 = QLabel(tr_ui("guide_fw_ai_title"))
        t2.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {p.TEXT_PRIMARY};")
        b2 = QLabel(tr_ui("wand_upload_model"))
        b2.setStyleSheet("background: rgba(52, 199, 89, 0.15); color: #28A745; border: 1px solid rgba(52, 199, 89, 0.35); border-radius: 4px; padding: 3px 8px; font-weight: 700; font-size: 10px;")
        h2.addWidget(icon2)
        h2.addWidget(t2, stretch=1)
        h2.addWidget(b2)
        f2_layout.addLayout(h2)

        d2 = QLabel(tr_ui("guide_fw_ai_desc"))
        d2.setWordWrap(True)
        d2.setStyleSheet(f"font-size: 12px; color: {p.TEXT_PRIMARY}; line-height: 1.45;")
        w2 = QLabel(f"• <b>{tr_ui('guide_fw_ai_when')}</b>")
        w2.setWordWrap(True)
        w2.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 4px; line-height: 1.35;")
        feat2 = QLabel(f"• {tr_ui('guide_fw_ai_feature')}")
        feat2.setWordWrap(True)
        feat2.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 4px; line-height: 1.35;")

        f2_layout.addWidget(d2)
        f2_layout.addWidget(w2)
        f2_layout.addWidget(feat2)
        f2_layout.addStretch()

        btn_fw2_go = QPushButton(tr_ui("guide_btn_go_wand"))
        btn_fw2_go.setFixedHeight(30)
        btn_fw2_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fw2_go.setStyleSheet(
            "background: rgba(52, 199, 89, 0.15); color: #28A745; "
            "border: 1px solid rgba(52, 199, 89, 0.35); border-radius: 5px; "
            "padding: 2px 10px; font-weight: 700; font-size: 11px;"
        )
        btn_fw2_go.clicked.connect(lambda _: self._on_cta_clicked(3))
        f2_layout.addWidget(btn_fw2_go)

        cols_layout.addWidget(fw2_card, stretch=1)

        layout.addWidget(cols_container)

        # Flow summary card with Wand CTA
        flow_card, fl_layout = make_card(margins=(18, 14, 18, 14), spacing=8)
        fl_header = QHBoxLayout()
        lbl_flow_t = QLabel(f"🔄 {tr_ui('guide_fw_flow_title')}")
        lbl_flow_t.setStyleSheet("font-weight: 700; font-size: 14px; color: #FF9500;")
        fl_header.addWidget(lbl_flow_t)
        fl_header.addStretch()

        btn_go_home = QPushButton(tr_ui("guide_btn_go_home"))
        btn_go_home.setFixedHeight(30)
        btn_go_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go_home.setStyleSheet(
            "background: rgba(255, 149, 0, 0.12); color: #FF9500; "
            "border: 1px solid rgba(255, 149, 0, 0.35); border-radius: 6px; "
            "padding: 2px 12px; font-weight: 700; font-size: 12px;"
        )
        btn_go_home.clicked.connect(lambda _: self._on_cta_clicked(0))
        fl_header.addWidget(btn_go_home)

        fl_layout.addLayout(fl_header)
        lbl_flow_d = QLabel(tr_ui("guide_fw_flow_desc"))
        lbl_flow_d.setWordWrap(True)
        lbl_flow_d.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {p.TEXT_PRIMARY}; line-height: 1.4;")
        fl_layout.addWidget(lbl_flow_d)
        layout.addWidget(flow_card)

        layout.addStretch()
        return scroll

    def _build_shortcuts_tab(self) -> QWidget:
        scroll, layout = self._make_scroll_area()
        p = self._p
        is_dark = self._is_dark

        # 2-Column Side-by-Side Grid for Shortcuts (Left) and Pro Tips (Right)
        cols_container = QWidget()
        cols_layout = QHBoxLayout(cols_container)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(14)

        # Left Column: Global Shortcuts
        card, c_layout = make_card(margins=(18, 16, 18, 16), spacing=12)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        lbl_sec = QLabel(tr_ui("guide_shortcuts_header"))
        lbl_sec.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {p.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_sec)

        shortcuts = [
            ("Ctrl + S", tr_ui("guide_shortcut_start")),
            ("Ctrl + T", tr_ui("guide_shortcut_stop")),
            ("Ctrl + X", tr_ui("guide_shortcut_snip")),
            ("Space", tr_ui("guide_shortcut_space")),
        ]

        badge_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.06)"
        badge_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)"

        for key_combo, desc in shortcuts:
            row = QHBoxLayout()
            badge = QLabel(key_combo)
            badge.setStyleSheet(
                f"background: {badge_bg}; color: {p.TEXT_PRIMARY}; "
                f"border: 1px solid {badge_border}; border-radius: 5px; "
                f"padding: 5px 12px; font-weight: 700; font-family: monospace; font-size: 12px;"
            )
            badge.setFixedWidth(110)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_desc = QLabel(desc)
            lbl_desc.setStyleSheet(f"font-size: 13px; color: {p.TEXT_PRIMARY};")
            row.addWidget(badge)
            row.addWidget(lbl_desc, stretch=1)
            c_layout.addLayout(row)

        c_layout.addStretch()
        cols_layout.addWidget(card, stretch=1)

        # Right Column: Pro Tips
        tips_card, t_layout = make_card(margins=(18, 16, 18, 16), spacing=12)
        t_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        lbl_t_head = QLabel(tr_ui("guide_protips_header"))
        lbl_t_head.setStyleSheet("font-weight: 700; font-size: 15px; color: #10B981;")
        t_layout.addWidget(lbl_t_head)

        protips = [
            tr_ui("guide_protip1"),
            tr_ui("guide_protip2"),
            tr_ui("guide_protip3"),
        ]
        for pt in protips:
            lbl = QLabel(f"💡 {pt}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"font-size: 13px; color: {p.TEXT_PRIMARY}; line-height: 1.45;")
            t_layout.addWidget(lbl)

        t_layout.addStretch()
        cols_layout.addWidget(tips_card, stretch=1)

        layout.addWidget(cols_container)
        layout.addStretch()
        return scroll

    def _make_step_card(
        self,
        step_num: str,
        icon: str,
        title: str,
        badge: str,
        badge_color: str,
        desc: str,
        tips: list[str],
        target_tab_idx: int | None = None,
        cta_text: str | None = None,
    ) -> QFrame:
        card, layout = make_card(margins=(18, 14, 18, 14), spacing=8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        p = self._p

        # Header: Step badge + Icon + Title + Page Tag + CTA Button
        header = QHBoxLayout()
        header.setSpacing(10)

        num_badge = QLabel(step_num)
        num_badge.setFixedSize(26, 26)
        num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_badge.setStyleSheet(
            f"background: {ACCENT}; color: #FFFFFF; font-weight: 800; "
            f"font-size: 13px; border-radius: 13px;"
        )

        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px;")

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {p.TEXT_PRIMARY};")

        page_badge = QLabel(badge)
        page_badge.setStyleSheet(
            f"background: {badge_color}1A; color: {badge_color}; border: 1px solid {badge_color}44; "
            f"border-radius: 4px; padding: 3px 10px; font-weight: 700; font-size: 11px;"
        )

        header.addWidget(num_badge)
        header.addWidget(lbl_icon)
        header.addWidget(lbl_t, stretch=1)
        header.addWidget(page_badge)

        if target_tab_idx is not None and cta_text:
            btn_cta = QPushButton(cta_text)
            btn_cta.setFixedHeight(30)
            btn_cta.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cta.setStyleSheet(
                f"background: {badge_color}1A; color: {badge_color}; "
                f"border: 1px solid {badge_color}44; border-radius: 6px; "
                f"padding: 2px 12px; font-weight: 700; font-size: 12px;"
            )
            btn_cta.clicked.connect(lambda _, idx=target_tab_idx: self._on_cta_clicked(idx))
            header.addWidget(btn_cta)

        layout.addLayout(header)

        # Description
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 13px; color: {p.TEXT_PRIMARY}; line-height: 1.45;")
        layout.addWidget(lbl_desc)

        # Bullets
        if tips:
            for tip in tips:
                lbl_tip = QLabel(f"• {tip}")
                lbl_tip.setWordWrap(True)
                lbl_tip.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY}; margin-left: 8px; line-height: 1.35;")
                layout.addWidget(lbl_tip)

        return card

    def _apply_theme(self) -> None:
        p = self._p
        is_dark = self._is_dark
        border_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
        bg_dialog = p.SURFACE_SECONDARY
        card_bg = p.SURFACE_PRIMARY

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_dialog};
                font-family: {APP_FONT_STACK};
            }}
            QTabWidget::pane {{
                border: 1px solid {border_color};
                border-radius: 10px;
                background: {bg_dialog};
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                margin-right: 6px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                color: {p.TEXT_SECONDARY};
                background: transparent;
            }}
            QTabBar::tab:selected {{
                color: {ACCENT};
                border-bottom: 2px solid {ACCENT};
                font-weight: 700;
            }}
            QFrame#Card {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {'rgba(255,255,255,0.2)' if is_dark else 'rgba(0,0,0,0.15)'};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

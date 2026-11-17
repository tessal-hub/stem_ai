"""
ui/mac_shell.py — Shell điều hướng Material You (M3 Navigation Rail / Drawer) với hỗ trợ cử chỉ.

Cung cấp giao diện khung cho ứng dụng gồm thanh công cụ (toolbar), thanh điều hướng (navigation rail)
và hỗ trợ chuyển trang bằng vuốt (swipe gesture).
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QFrame, QGestureEvent, QHBoxLayout, QLabel,
                             QSizePolicy, QSwipeGesture, QToolButton,
                             QVBoxLayout, QWidget)
try:
    from PyQt6.QtWidgets import QSwipeDirection
except ImportError:
    # PyQt6 ≮ 6.4: direction available directly on QSwipeGesture
    QSwipeDirection = None

from logic.theme_manager import theme_manager
from ui.asset_utils import resolve_asset_path
from ui.i18n_bridge import tr_ui
from ui.tokens import (SHELL_BRAND_H, SHELL_BRAND_ICON, SHELL_NAV_H,
                       SHELL_SIDEBAR_W)


@dataclass(frozen=True)
class NavItem:
    """Định nghĩa một mục trong menu điều hướng."""

    label_key: str
    icon: str
    subtitle_key: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("nav_home", "assets/icon/home.svg", "shell_subtitle_home"),
    NavItem("nav_primitives", "assets/icon/statistic.svg", "shell_subtitle_primitives"),
    NavItem("nav_record", "assets/icon/record.svg", "shell_subtitle_record"),
    NavItem("nav_wand", "assets/icon/wand.svg", "shell_subtitle_wand"),
    NavItem("nav_settings", "assets/icon/setting.svg", "shell_subtitle_settings"),
)


class MacShell(QWidget):
    """
    Khung giao diện chính (Shell) điều phối navigation.
    """

    nav_requested = pyqtSignal(int)
    open_ml_lab_requested = pyqtSignal()

    def __init__(self, title: str = "Reboot") -> None:
        super().__init__()
        self._buttons: list[QToolButton] = []
        self._active_index = 0
        self._fallback_title = title

        self._init_ui(title)
        self._init_signals()
        self.set_active_index(0)

    def _init_ui(self, title: str) -> None:
        """Khởi tạo giao diện và bố cục."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._chrome = QWidget()
        self._chrome.setObjectName("StemChrome")
        chrome_layout = QVBoxLayout(self._chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.content_host = QWidget()
        self.content_host.setObjectName("StemContentHost")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        right_layout.addWidget(self._build_toolbar(title))
        right_layout.addWidget(self.content_host, stretch=1)

        body_layout.addWidget(self._build_sidebar())
        body_layout.addWidget(right_panel, stretch=1)

        chrome_layout.addWidget(body, stretch=1)
        outer.addWidget(self._chrome)

        # Cấu hình cảm ứng
        self.grabGesture(Qt.GestureType.SwipeGesture)
        self.content_host.grabGesture(Qt.GestureType.SwipeGesture)

        self.refresh_styles()

    def _init_signals(self) -> None:
        """Kết nối signal/slot."""
        theme_manager.theme_changed.connect(self.refresh_styles)

    def _load_data(self) -> None:
        """Không có dữ liệu ban đầu cần nạp."""

    # ── Public methods ──────────────────────────

    def set_active_index(self, index: int) -> None:
        """Chuyển trang hiển thị và cập nhật trạng thái menu."""
        if not (0 <= index < len(NAV_ITEMS)):
            return

        # Nếu nút mục tiêu đang bị ẩn (Simple Mode), chuyển về trang hiển thị hợp lệ (mặc định Home)
        if index < len(self._buttons) and not self._buttons[index].isVisible():
            visible_indices = [i for i, btn in enumerate(self._buttons) if btn.isVisible()]
            if visible_indices and index not in visible_indices:
                index = 0

        if index == self._active_index and self._buttons[index].property("active"):
            return

        self._active_index = index
        for i, btn in enumerate(self._buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._update_nav_icons()

        item = NAV_ITEMS[index]
        self.lbl_title.setText(tr_ui(item.label_key))
        self.lbl_subtitle.setText(tr_ui(item.subtitle_key))

        self.nav_requested.emit(index)

    def set_compact_mode(self, compact: bool) -> None:
        """Thu gọn sidebar 220→64px cho màn hẹp — icon-only, ẩn nhãn."""
        if compact == getattr(self, "_is_compact", False):
            return
        self._is_compact = compact
        target_w = 64 if compact else SHELL_SIDEBAR_W
        if hasattr(self, "_sidebar"):
            self._sidebar.setFixedWidth(target_w)
        # Brand text ẩn hiện
        for attr in ("_brand_title", "_brand_subtitle", "_nav_label"):
            w = getattr(self, attr, None)
            if w:
                w.setVisible(not compact)
        if hasattr(self, "_brand_text_box"):
            # tighten margins khi compact
            parent = self._brand_frame.layout() if hasattr(self, "_brand_frame") else None
            if parent:
                parent.setContentsMargins(12 if compact else 20, 0, 12 if compact else 20, 0)
        for i, btn in enumerate(self._buttons):
            if compact:
                btn.setText("")
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                btn.setFixedHeight(44)
            else:
                from ui.i18n_bridge import tr_ui as _tr
                # restore label
                if i < len(NAV_ITEMS):
                    btn.setText(f"  {_tr(NAV_ITEMS[i].label_key)}")
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                btn.setFixedHeight(44)
            # keep tooltip as label in compact
            if compact and i < len(NAV_ITEMS):
                from ui.i18n_bridge import tr_ui as _tr2
                btn.setToolTip(_tr2(NAV_ITEMS[i].label_key))
            else:
                btn.setToolTip("")

    def set_nav_item_visible(self, index: int, visible: bool) -> None:
        """Hiển thị hoặc ẩn nút menu điều hướng theo chỉ số."""
        if 0 <= index < len(self._buttons):
            self._buttons[index].setVisible(visible)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ hiển thị."""
        self._brand_title.setText(tr_ui("shell_brand_stem"))
        self._brand_subtitle.setText(tr_ui("shell_brand_book"))
        self._nav_label.setText(tr_ui("shell_nav_title"))

        for i, item in enumerate(NAV_ITEMS):
            if i < len(self._buttons):
                self._buttons[i].setText(f"  {tr_ui(item.label_key)}")
                self._buttons[i].setAccessibleName(tr_ui(item.label_key))

        # Cập nhật toolbar hiện tại
        item = NAV_ITEMS[self._active_index]
        self.lbl_title.setText(tr_ui(item.label_key))
        self.lbl_subtitle.setText(tr_ui(item.subtitle_key))
        if hasattr(self, "btn_ml_lab"):
            self.btn_ml_lab.setText(tr_ui("shell_ml_lab_button"))
            self.btn_ml_lab.setToolTip(tr_ui("shell_ml_lab_tooltip"))
        if hasattr(self, "btn_guide"):
            self.btn_guide.setText(tr_ui("guide_btn_title"))

    def _update_nav_icons(self) -> None:
        """Cập nhật màu icon (tint) theo trạng thái active và theme."""
        from ui.asset_utils import make_tinted_icon
        is_dark = theme_manager.current_theme == "dark"
        for i, btn in enumerate(self._buttons):
            if i >= len(NAV_ITEMS):
                continue
            item = NAV_ITEMS[i]
            is_active = (i == self._active_index)
            if is_active:
                color = "#DFE0FF" if is_dark else "#0A1365"  # M3 On-Primary Container
            elif is_dark:
                color = "#C6C5D0"  # M3 Dark On-Surface Variant
            else:
                color = "#46464F"  # M3 On-Surface Variant
            btn.setIcon(make_tinted_icon(item.icon, color))

        btn_color = "#C6C5D0" if is_dark else "#46464F"
        if hasattr(self, "_brand_icon_lbl"):
            brand_color = "#DFE0FF" if is_dark else theme_manager.get_palette().PRIMARY
            self._brand_icon_lbl.setPixmap(make_tinted_icon("assets/icon/wand.svg", brand_color).pixmap(SHELL_BRAND_ICON))
        if hasattr(self, "btn_ml_lab"):
            self.btn_ml_lab.setIcon(make_tinted_icon("assets/icon/statistic.svg", btn_color))
        if hasattr(self, "btn_guide"):
            self.btn_guide.setIcon(make_tinted_icon("assets/icon/cooliocns SVG/Warning/Help.svg", btn_color))

    def refresh_styles(self) -> None:
        """Repaint shell chrome using current theme stylesheet."""
        from theme import get_modern_stylesheet
        self._chrome.setStyleSheet(get_modern_stylesheet(theme_manager.current_theme))
        self._update_nav_icons()
    def event(self, event: QEvent) -> bool:
        """Xử lý sự kiện chung, bao gồm cử chỉ."""
        if event.type() == QEvent.Type.Gesture:
            return self._handle_gesture(event)
        return super().event(event)

    # ── Private methods ─────────────────────────

    def _build_sidebar(self) -> QWidget:
        """Thanh điều hướng — 220px desktop, 64px compact khi cửa sổ hẹp."""
        self._sidebar = QWidget()
        self._sidebar.setObjectName("StemSidebar")
        self._sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        self._sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._is_compact = False
        sidebar = self._sidebar

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 6, 0, 18)
        layout.setSpacing(6)

        # 1. Khu vực Brand
        layout.addWidget(self._build_brand_section())

        # 2. Danh sách Navigation
        self._nav_label = QLabel(tr_ui("shell_nav_title"))
        self._nav_label.setObjectName("StemNavSectionLabel")
        self._nav_label.setContentsMargins(20, 6, 20, 0)
        layout.addWidget(self._nav_label)

        for i, item in enumerate(NAV_ITEMS):
            btn = self._make_nav_button(i, item)
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        return sidebar

    def _build_brand_section(self) -> QFrame:
        """Tạo cụm logo và tiêu đề ứng dụng."""
        brand = QFrame()
        brand.setFixedHeight(SHELL_BRAND_H)
        self._brand_frame = brand
        layout = QHBoxLayout(brand)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Icon SVG
        icon_lbl = QLabel()
        self._brand_icon_lbl = icon_lbl
        pixmap = self._render_svg_icon("assets/icon/wand.svg", SHELL_BRAND_ICON)
        icon_lbl.setPixmap(pixmap)

        self._brand_text_box = QVBoxLayout()
        self._brand_text_box.setSpacing(0)
        self._brand_title = QLabel(tr_ui("shell_brand_stem"))
        self._brand_title.setObjectName("StemBrandTitle")
        self._brand_subtitle = QLabel(tr_ui("shell_brand_book"))
        self._brand_subtitle.setObjectName("StemBrandSubtitle")
        self._brand_text_box.addWidget(self._brand_title)
        self._brand_text_box.addWidget(self._brand_subtitle)

        layout.addWidget(icon_lbl)
        layout.addLayout(self._brand_text_box)
        layout.addStretch()
        return brand

    def _make_nav_button(self, index: int, item: NavItem) -> QToolButton:
        """Tạo một nút bấm điều hướng."""
        from ui.asset_utils import make_tinted_icon
        is_dark = theme_manager.current_theme == "dark"
        if index == self._active_index:
            icon_color = "#DFE0FF" if is_dark else "#0A1365"
        else:
            icon_color = "#C6C5D0" if is_dark else "#46464F"

        btn = QToolButton()
        btn.setObjectName("StemNavBtn")
        label = tr_ui(item.label_key)
        btn.setText(f"  {label}")
        # Compact mode xóa text — accessibleName giữ tên cho screen reader
        btn.setAccessibleName(label)
        btn.setIcon(make_tinted_icon(item.icon, icon_color))
        btn.setIconSize(QSize(20, 20))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._on_nav_btn_clicked)
        btn.setProperty("nav_index", index)
        return btn

    def _render_svg_icon(self, path: str, size: QSize) -> QPixmap:
        """Render file SVG thành QPixmap."""
        renderer = QSvgRenderer(resolve_asset_path(path))
        pixmap = QPixmap(size * 2)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _build_toolbar(self, title: str) -> QWidget:
        """Xây dựng thanh công cụ phía trên."""
        toolbar = QFrame()
        toolbar.setObjectName("StemToolbar")
        toolbar.setFixedHeight(SHELL_NAV_H + 28)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(16)

        text_stack = QVBoxLayout()
        text_stack.setSpacing(2)
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("StemToolbarTitle")
        self.lbl_subtitle = QLabel("")
        self.lbl_subtitle.setObjectName("StemToolbarSubtitle")
        text_stack.addStretch()
        text_stack.addWidget(self.lbl_title)
        text_stack.addWidget(self.lbl_subtitle)
        text_stack.addStretch()

        layout.addLayout(text_stack)
        layout.addStretch()

        from ui.component_factory import make_outline_button
        from ui.asset_utils import make_tinted_icon
        p = theme_manager.get_palette()
        btn_color = p.TEXT_SECONDARY

        self.btn_ml_lab = make_outline_button(tr_ui('shell_ml_lab_button'), height=36)
        self.btn_ml_lab.setObjectName("StemMlLabBtn")
        self.btn_ml_lab.setIcon(make_tinted_icon("assets/icon/statistic.svg", btn_color))
        self.btn_ml_lab.setIconSize(QSize(16, 16))
        self.btn_ml_lab.setToolTip(tr_ui("shell_ml_lab_tooltip"))
        self.btn_ml_lab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ml_lab.clicked.connect(self.open_ml_lab_requested.emit)
        layout.addWidget(self.btn_ml_lab, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_guide = make_outline_button(tr_ui('guide_btn_title'), height=36)
        self.btn_guide.setObjectName("StemGuideBtn")
        self.btn_guide.setIcon(make_tinted_icon("assets/icon/cooliocns SVG/Warning/Help.svg", btn_color))
        self.btn_guide.setIconSize(QSize(16, 16))
        self.btn_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guide.clicked.connect(self._open_beginner_guide)
        layout.addWidget(self.btn_guide, alignment=Qt.AlignmentFlag.AlignVCenter)

        return toolbar

    def _open_beginner_guide(self) -> None:
        """Mở popup hướng dẫn người mới cho trang đang hiển thị."""
        from ui.beginner_guide_dialog import BeginnerGuideDialog
        dlg = BeginnerGuideDialog(initial_page_index=self._active_index, parent=self)
        dlg.sig_navigate_to.connect(self.set_active_index)
        dlg.exec()

    def _handle_gesture(self, event: QGestureEvent) -> bool:
        """Điều phối cử chỉ vuốt ngang giữa các trang đang hiển thị."""
        swipe = event.gesture(Qt.GestureType.SwipeGesture)
        if isinstance(swipe, QSwipeGesture):
            direction = swipe.horizontalDirection()
            left = QSwipeGesture.SwipeDirection.Left
            right = QSwipeGesture.SwipeDirection.Right
            visible_indices = [i for i, btn in enumerate(self._buttons) if btn.isVisible()]
            if not visible_indices:
                return True
            try:
                curr_pos = visible_indices.index(self._active_index)
            except ValueError:
                curr_pos = 0

            if direction == left and curr_pos < len(visible_indices) - 1:
                self.set_active_index(visible_indices[curr_pos + 1])
            elif direction == right and curr_pos > 0:
                self.set_active_index(visible_indices[curr_pos - 1])
            return True
        return False

    # ── Slots ───────────────────────────────────

    def _on_nav_btn_clicked(self) -> None:
        """Xử lý khi bấm nút menu."""
        btn = self.sender()
        if isinstance(btn, QToolButton):
            idx = btn.property("nav_index")
            if isinstance(idx, int):
                self.set_active_index(idx)

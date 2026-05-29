"""
ui/mac_shell.py — Shell điều hướng kiểu iOS với sidebar và hỗ trợ cử chỉ.

Cung cấp giao diện khung cho ứng dụng gồm thanh công cụ (toolbar), thanh điều hướng (sidebar)
và hỗ trợ chuyển trang bằng vuốt (swipe gesture).
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QGestureEvent,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSwipeGesture,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logic.theme_manager import theme_manager
from ui.asset_utils import resolve_asset_path
from ui.i18n_bridge import tr_ui
from ui.tokens import (
    SHELL_BRAND_H,
    SHELL_BRAND_ICON,
    SHELL_NAV_H,
    SHELL_SIDEBAR_W,
)


@dataclass(frozen=True)
class NavItem:
    """Định nghĩa một mục trong menu điều hướng."""

    label_key: str
    icon: str
    subtitle_key: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("nav_home_editorial", "assets/icon/home.svg", "shell_subtitle_home"),
    NavItem("nav_primitives_editorial", "assets/icon/record.svg", "shell_subtitle_primitives"),
    NavItem("nav_record_editorial", "assets/icon/record.svg", "shell_subtitle_record"),
    NavItem("nav_wand_editorial", "assets/icon/wand.svg", "shell_subtitle_wand"),
    NavItem("nav_settings_editorial", "assets/icon/setting.svg", "shell_subtitle_settings"),
)


class MacShell(QWidget):
    """
    Khung giao diện chính (Shell) điều phối navigation.
    """

    nav_requested = pyqtSignal(int)

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
        pass

    # ── Public methods ──────────────────────────

    def set_active_index(self, index: int) -> None:
        """Chuyển trang hiển thị và cập nhật trạng thái menu."""
        if not (0 <= index < len(NAV_ITEMS)):
            return
            
        if index == self._active_index and self._buttons[index].property("active"):
            return

        self._active_index = index
        for i, btn in enumerate(self._buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        item = NAV_ITEMS[index]
        self.lbl_title.setText(tr_ui(item.label_key))
        self.lbl_subtitle.setText(tr_ui(item.subtitle_key))

        self.nav_requested.emit(index)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ hiển thị."""
        self._brand_title.setText(tr_ui("shell_brand_stem"))
        self._brand_subtitle.setText(tr_ui("shell_brand_book"))
        self._nav_label.setText(tr_ui("shell_nav_title"))
        self._swipe_hint.setText(tr_ui("shell_nav_hint"))

        for i, item in enumerate(NAV_ITEMS):
            if i < len(self._buttons):
                self._buttons[i].setText(f"  {tr_ui(item.label_key)}")

        # Cập nhật toolbar hiện tại
        item = NAV_ITEMS[self._active_index]
        self.lbl_title.setText(tr_ui(item.label_key))
        self.lbl_subtitle.setText(tr_ui(item.subtitle_key))

    def refresh_styles(self) -> None:
        """Làm mới toàn bộ stylesheet theo theme."""
        pass

    def event(self, event: QEvent) -> bool:
        """Xử lý sự kiện chung, bao gồm cử chỉ."""
        if event.type() == QEvent.Type.Gesture:
            return self._handle_gesture(event)
        return super().event(event)

    # ── Private methods ─────────────────────────



    def _build_sidebar(self) -> QWidget:
        """Xây dựng thanh điều hướng (Requirement 2: Fixed 320px)."""
        sidebar = QWidget()
        sidebar.setObjectName("StemSidebar")
        sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

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

        # 3. Hint vuốt
        self._swipe_hint = QLabel(tr_ui("shell_nav_hint"))
        self._swipe_hint.setProperty("type", "shell_nav_hint")
        self._swipe_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._swipe_hint)

        return sidebar

    def _build_brand_section(self) -> QFrame:
        """Tạo cụm logo và tiêu đề ứng dụng."""
        brand = QFrame()
        brand.setFixedHeight(SHELL_BRAND_H)
        layout = QHBoxLayout(brand)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Icon SVG
        icon_lbl = QLabel()
        pixmap = self._render_svg_icon("assets/icon/wand.svg", SHELL_BRAND_ICON)
        icon_lbl.setPixmap(pixmap)

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self._brand_title = QLabel(tr_ui("shell_brand_stem"))
        self._brand_title.setObjectName("StemBrandTitle")
        self._brand_subtitle = QLabel(tr_ui("shell_brand_book"))
        self._brand_subtitle.setObjectName("StemBrandSubtitle")
        text_box.addWidget(self._brand_title)
        text_box.addWidget(self._brand_subtitle)

        layout.addWidget(icon_lbl)
        layout.addLayout(text_box)
        layout.addStretch()
        return brand

    def _make_nav_button(self, index: int, item: NavItem) -> QToolButton:
        """Tạo một nút bấm điều hướng."""
        btn = QToolButton()
        btn.setObjectName("StemNavBtn")
        btn.setText(f"  {tr_ui(item.label_key)}")
        btn.setIcon(QIcon(resolve_asset_path(item.icon)))
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
        return toolbar

    def _handle_gesture(self, event: QGestureEvent) -> bool:
        """Điều phối cử chỉ vuốt ngang."""
        swipe = event.gesture(Qt.GestureType.SwipeGesture)
        if isinstance(swipe, QSwipeGesture):
            if swipe.horizontalDirection() == QSwipeDirection.Left:
                self.set_active_index(min(len(NAV_ITEMS) - 1, self._active_index + 1))
            elif swipe.horizontalDirection() == QSwipeDirection.Right:
                self.set_active_index(max(0, self._active_index - 1))
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

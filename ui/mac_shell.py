"""
Shell điều hướng kiểu iOS với sidebar và hỗ trợ vuốt (swipe gesture).

Cung cấp giao diện navigation sidebar với brand section, toolbar tiêu đề,
và hỗ trợ swipe trái/phải để chuyển trang.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QGestureEvent,
    QHBoxLayout,
    QLabel,
    QSwipeGesture,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.asset_utils import resolve_asset_path
from ui.i18n_bridge import tr_ui
from ui.mac_material import apply_soft_shadow
from logic.theme_manager import theme_manager
from ui.tokens import (
    APP_FONT_STACK,
    TITLE_FONT_STACK,
    BORDER_COLOR,
    HOVER_BG,
    PRIMARY_COLOR,
    PRIMARY_LIGHT,
    SHELL_BRAND_H,
    SHELL_BRAND_ICON,
    SHELL_NAV_H,
    SHELL_SIDEBAR_W,
    SURFACE_0,
    SURFACE_1,
    SURFACE_2,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    BTN_RADIUS,
    CARD_RADIUS,
)
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_MD, SPACING_SM


@dataclass(frozen=True)
class NavItem:
    """Sidebar navigation entry (i18n keys + icon)."""

    label_key: str
    icon: str
    subtitle_key: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("nav_home_editorial", "assets/icon/home.svg", "shell_subtitle_home"),
    NavItem("nav_primitives_editorial", "assets/icon/record.svg", "shell_subtitle_primitives"),
    NavItem("nav_statistics_editorial", "assets/icon/statistic.svg", "shell_subtitle_statistics"),
    NavItem("nav_record_editorial", "assets/icon/record.svg", "shell_subtitle_record"),
    NavItem("nav_wand_editorial", "assets/icon/wand.svg", "shell_subtitle_wand"),
    NavItem("nav_settings_editorial", "assets/icon/setting.svg", "shell_subtitle_settings"),
)


class MacShell(QWidget):
    """
    Shell ứng dụng kiểu macOS/iOS với sidebar navigation.
    Phát signal nav_requested(int) khi người dùng chọn trang mới.
    """

    nav_requested = pyqtSignal(int)

    def __init__(self, title: str = "Reboot") -> None:
        super().__init__()
        self._buttons: list[QToolButton] = []
        self._active_index = 0
        self._fallback_title = title

        self._init_ui(title)

    # ------------------------------------------------------------------
    # Khởi tạo giao diện
    # ------------------------------------------------------------------

    def _init_ui(self, title: str) -> None:
        """Xây dựng layout chính gồm toolbar, sidebar và vùng nội dung."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        chrome = QWidget()
        chrome.setObjectName("StemChrome")
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.content_host = QWidget()
        self.content_host.setObjectName("StemContentHost")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        body_layout.addWidget(self._build_sidebar())
        body_layout.addWidget(self.content_host, stretch=1)

        chrome_layout.addWidget(self._build_toolbar(title))
        chrome_layout.addWidget(body, stretch=1)
        outer.addWidget(chrome)

        theme_manager.theme_changed.connect(self.refresh_styles)
        self.refresh_styles()

        # Đăng ký gesture vuốt cho cả shell và vùng nội dung
        self.grabGesture(Qt.GestureType.SwipeGesture)
        self.content_host.grabGesture(Qt.GestureType.SwipeGesture)

        self.set_active_index(0)

    def refresh_styles(self) -> None:
        """Re-apply global shell stylesheet based on active theme."""
        p = theme_manager.get_palette()
        self.setStyleSheet(f"""
            * {{
                font-family: {APP_FONT_STACK};
                color: {p.TEXT_PRIMARY};
            }}
            #StemChrome {{
                background-color: {p.SURFACE_SECONDARY};
            }}
            #StemToolbar {{
                background-color: {p.SURFACE_PRIMARY};
                border-bottom: 1px solid {p.BORDER};
                border-radius: 0px;
            }}
            #StemToolbarTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 18px;
                font-weight: 600;
                color: {p.TEXT_PRIMARY};
                letter-spacing: -0.01em;
            }}
            #StemToolbarSubtitle {{
                font-size: 12px;
                font-weight: 500;
                color: {p.TEXT_SECONDARY};
            }}
            #StemSidebar {{
                background-color: {p.SURFACE_TERTIARY};
                border-right: 1px solid {p.BORDER};
            }}
            #StemBrandTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 16px;
                font-weight: 700;
                color: {p.TEXT_PRIMARY};
            }}
            #StemBrandSubtitle {{
                font-size: 10px;
                font-weight: 600;
                color: {p.TEXT_SECONDARY};
                letter-spacing: 0.05em;
            }}
            #StemNavSectionLabel {{
                font-size: 10px;
                font-weight: 700;
                color: {p.TEXT_TERTIARY};
                letter-spacing: 0.08em;
                margin-top: 16px;
                margin-bottom: 8px;
            }}
            QToolButton#StemNavBtn {{
                background-color: transparent;
                border: none;
                border-radius: {BTN_RADIUS};
                color: {p.TEXT_PRIMARY};
                font-family: {APP_FONT_STACK};
                font-size: 14px;
                font-weight: 500;
                padding-left: 12px;
                padding-right: 12px;
                text-align: left;
                margin: 2px 8px;
            }}
            QToolButton#StemNavBtn:hover {{
                background-color: {p.HOVER_BG};
            }}
            QToolButton#StemNavBtn[active="true"] {{
                background-color: {p.PRIMARY};
                color: {p.SURFACE_PRIMARY};
                font-weight: 700;
            }}
        """)

    def apply_ui_language(self) -> None:
        """Làm mới toàn bộ text trong shell khi ngôn ngữ thay đổi."""
        self._brand_title.setText(tr_ui("shell_brand_stem"))
        self._brand_subtitle.setText(tr_ui("shell_brand_book"))
        self._nav_label.setText(tr_ui("shell_nav_title"))
        self._swipe_hint.setText(tr_ui("shell_nav_hint"))

        for i, item in enumerate(NAV_ITEMS):
            if i < len(self._buttons):
                self._buttons[i].setText(f"  {tr_ui(item.label_key)}")

        # Refresh current title/subtitle
        item = NAV_ITEMS[self._active_index]
        self.lbl_title.setText(tr_ui(item.label_key))
        self.lbl_subtitle.setText(tr_ui(item.subtitle_key))

    def _build_sidebar(self) -> QWidget:
        """Tạo cột điều hướng bên trái."""
        sidebar = QWidget()
        sidebar.setObjectName("StemSidebar")
        sidebar.setFixedWidth(SHELL_SIDEBAR_W)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)

        # Brand Section
        brand = QFrame()
        brand.setFixedHeight(SHELL_BRAND_H)
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(20, 0, 20, 0)
        brand_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_path = resolve_asset_path("assets/icon/wand.svg")
        renderer = QSvgRenderer(icon_path)
        pixmap = QPixmap(SHELL_BRAND_ICON * 2)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon_lbl.setPixmap(pixmap.scaled(SHELL_BRAND_ICON, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self._brand_title = QLabel(tr_ui("shell_brand_stem"))
        self._brand_title.setObjectName("StemBrandTitle")
        self._brand_subtitle = QLabel(tr_ui("shell_brand_book"))
        self._brand_subtitle.setObjectName("StemBrandSubtitle")
        text_box.addWidget(self._brand_title)
        text_box.addWidget(self._brand_subtitle)

        brand_layout.addWidget(icon_lbl)
        brand_layout.addLayout(text_box)
        brand_layout.addStretch()

        layout.addWidget(brand)

        # Navigation
        self._nav_label = QLabel(tr_ui("shell_nav_title"))
        self._nav_label.setObjectName("StemNavSectionLabel")
        self._nav_label.setContentsMargins(20, 0, 20, 0)
        layout.addWidget(self._nav_label)

        for i, item in enumerate(NAV_ITEMS):
            btn = QToolButton()
            btn.setObjectName("StemNavBtn")
            btn.setText(f"  {tr_ui(item.label_key)}")
            btn.setIcon(QIcon(resolve_asset_path(item.icon)))
            btn.setIconSize(QSize(20, 20))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setFixedHeight(44)
            btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().verticalPolicy())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Sử dụng closure để bắt index chính xác
            btn.clicked.connect(lambda checked, idx=i: self.set_active_index(idx))
            
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        # Swipe hint
        self._swipe_hint = QLabel(tr_ui("shell_nav_hint"))
        self._swipe_hint.setStyleSheet(f"color: {theme_manager.get_palette().TEXT_TERTIARY}; font-size: 10px; font-style: italic;")
        self._swipe_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._swipe_hint)

        return sidebar

    def _build_toolbar(self, title: str) -> QWidget:
        """Tạo thanh công cụ phía trên."""
        toolbar = QFrame()
        toolbar.setObjectName("StemToolbar")
        toolbar.setFixedHeight(SHELL_NAV_H + 20)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(24, 0, 24, 0)
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active_index(self, index: int) -> None:
        """Chuyển đổi trang hiển thị và cập nhật trạng thái sidebar."""
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

    def event(self, event: QEvent) -> bool:
        """Xử lý gesture vuốt để chuyển trang."""
        if event.type() == QEvent.Type.Gesture:
            return self._handle_gesture(event)
        return super().event(event)

    def _handle_gesture(self, event: QGestureEvent) -> bool:
        """Điều phối gesture vuốt."""
        swipe = event.gesture(Qt.GestureType.SwipeGesture)
        if isinstance(swipe, QSwipeGesture):
            if swipe.horizontalDirection() == QSwipeGesture.SwipeDirection.Left:
                self.set_active_index(min(len(NAV_ITEMS) - 1, self._active_index + 1))
            elif swipe.horizontalDirection() == QSwipeGesture.SwipeDirection.Right:
                self.set_active_index(max(0, self._active_index - 1))
            return True
        return False

"""
Shell điều hướng kiểu iOS với sidebar và hỗ trợ vuốt (swipe gesture).

Cung cấp giao diện navigation sidebar với brand section, toolbar tiêu đề,
và hỗ trợ swipe trái/phải để chuyển trang.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
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
from ui.tokens import (
    APP_FONT_STACK,
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

        self._apply_shell_styles()

        # Đăng ký gesture vuốt cho cả shell và vùng nội dung
        self.grabGesture(Qt.GestureType.SwipeGesture)
        self.content_host.grabGesture(Qt.GestureType.SwipeGesture)

        self.set_active_index(0)

    def _apply_shell_styles(self) -> None:
        """Apply the global shell stylesheet based on minimalist tokens."""
        self.setStyleSheet(f"""
            * {{
                font-family: {APP_FONT_STACK};
                color: {TEXT_PRIMARY};
            }}
            #StemChrome {{
                background-color: {SURFACE_0};
            }}
            #StemToolbar {{
                background-color: {SURFACE_1};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
            #StemToolbarTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 22px;
                font-weight: 500;
                color: {TEXT_PRIMARY};
                letter-spacing: -0.01em;
            }}
            #StemToolbarSubtitle {{
                font-size: 12px;
                font-weight: 500;
                color: {TEXT_SECONDARY};
                letter-spacing: 0.02em;
            }}
            #StemNavHint {{
                font-size: 11px;
                font-weight: 600;
                color: {TEXT_TERTIARY};
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            #StemSidebar {{
                background-color: {SURFACE_2};
                border-right: 1px solid {BORDER_COLOR};
            }}
            #StemBrandTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 18px;
                font-weight: 600;
                letter-spacing: 0.02em;
                color: {TEXT_PRIMARY};
                font-style: italic;
            }}
            #StemBrandSubtitle {{
                font-size: 10px;
                font-weight: 800;
                color: {TEXT_SECONDARY};
                letter-spacing: 0.15em;
                text-transform: uppercase;
            }}
            #StemNavSectionLabel {{
                font-size: 10px;
                font-weight: 800;
                color: {TEXT_TERTIARY};
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-top: 20px;
                margin-bottom: 8px;
            }}
            QToolButton#StemNavBtn {{
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: {TEXT_SECONDARY};
                font-size: 13px;
                font-weight: 600;
                padding-left: 12px;
                text-align: left;
            }}
            QToolButton#StemNavBtn:hover {{
                background-color: {HOVER_BG};
                color: {TEXT_PRIMARY};
            }}
            QToolButton#StemNavBtn[active="true"] {{
                background-color: {PRIMARY_COLOR};
                color: #FFFFFF;
            }}
            #StemContentHost {{
                background-color: transparent;
            }}
        """)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def set_active_index(self, index: int) -> None:
        """Đặt trang active trong sidebar và cập nhật tiêu đề toolbar.

        Args:
            index: Chỉ số trang cần active.
        """
        if not NAV_ITEMS:
            return
        self._active_index = max(0, min(len(NAV_ITEMS) - 1, index))
        item = NAV_ITEMS[self._active_index]

        self.title_label.setText(tr_ui(item.label_key))
        self.subtitle_label.setText(tr_ui(item.subtitle_key))

        for button_index, button in enumerate(self._buttons):
            is_active = button_index == self._active_index
            button.setProperty("active", is_active)
            lk = button.property("nav_label_key")
            if isinstance(lk, str) and lk:
                button.setText(tr_ui(lk))
            icon_path = button.property("nav_icon_path")
            if isinstance(icon_path, str) and icon_path:
                icon = self._tint_svg(
                    icon_path,
                    QColor("white") if is_active else QColor(TEXT_SECONDARY),
                    SHELL_BRAND_ICON,
                )
                if icon.isNull():
                    icon = QIcon(icon_path)
                button.setIcon(icon)
            button_style = button.style()
            if button_style is not None:
                button_style.unpolish(button)
                button_style.polish(button)

    def event(self, event: QEvent) -> bool:
        """Xử lý gesture event cho swipe navigation."""
        if event.type() == QEvent.Type.Gesture:
            if isinstance(event, QGestureEvent):
                return self._handle_gesture_event(event)
        return super().event(event)

    # ------------------------------------------------------------------
    # Private methods — UI builders
    # ------------------------------------------------------------------

    def _build_toolbar(self, title: str) -> QWidget:
        """Top toolbar with title and navigation hint."""
        toolbar = QWidget()
        toolbar.setObjectName("StemToolbar")
        toolbar.setFixedHeight(80)  # More whitespace
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            MARGIN_COMFORTABLE, 0, MARGIN_COMFORTABLE, 0
        )
        toolbar_layout.setSpacing(SPACING_SM)

        self.title_label = QLabel(tr_ui("nav_home"))
        self.title_label.setObjectName("StemToolbarTitle")
        self.subtitle_label = QLabel(tr_ui("shell_subtitle_home"))
        self.subtitle_label.setObjectName("StemToolbarSubtitle")

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.nav_hint_label = QLabel(tr_ui("shell_nav_hint"))
        self.nav_hint_label.setObjectName("StemNavHint")

        toolbar_layout.addWidget(title_block)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.nav_hint_label)
        _ = title  # legacy param; shell uses i18n keys
        return toolbar

    def apply_ui_language(self) -> None:
        """Refresh shell chrome strings after locale change."""
        self.nav_hint_label.setText(tr_ui("shell_nav_hint"))
        self._brand_title_label.setText(tr_ui("shell_brand_stem"))
        self._brand_subtitle_label.setText(tr_ui("shell_brand_book"))
        self._nav_section_label.setText(tr_ui("shell_nav_title"))
        for button in self._buttons:
            lk = button.property("nav_label_key")
            if isinstance(lk, str) and lk:
                button.setText(tr_ui(lk))
                button.setAccessibleName(tr_ui(lk))
        self.set_active_index(self._active_index)

    def _build_brand_widget(self) -> QWidget:
        """Tạo widget brand (logo + tên app) cho phần đầu sidebar."""
        brand = QWidget()
        brand.setFixedHeight(SHELL_BRAND_H)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(6)

        brand_icon_row = QWidget()
        icon_layout = QHBoxLayout(brand_icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        icon_layout.addStretch()

        brand_icon = QLabel("◉")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(30, 30)
        brand_icon.setStyleSheet(
            f"background-color: {PRIMARY_COLOR}; color: white; border-radius: 15px; font-size: 14px; font-weight: 900;"
        )
        icon_layout.addWidget(brand_icon)
        icon_layout.addStretch()

        brand_title = QLabel(tr_ui("shell_brand_stem"))
        brand_title.setObjectName("StemBrandTitle")
        self._brand_title_label = brand_title
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_subtitle = QLabel(tr_ui("shell_brand_book"))
        brand_subtitle.setObjectName("StemBrandSubtitle")
        self._brand_subtitle_label = brand_subtitle
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_layout.addWidget(brand_icon_row)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        return brand

    def _build_sidebar(self) -> QWidget:
        """Tạo sidebar với brand, danh sách nút điều hướng."""
        self.sidebar = QWidget()
        self.sidebar.setObjectName("StemSidebar")
        self.sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(
            SPACING_MD, MARGIN_COMFORTABLE, SPACING_MD, MARGIN_COMFORTABLE
        )
        sidebar_layout.setSpacing(SPACING_SM)

        sidebar_layout.addWidget(self._build_brand_widget())

        nav_title = QLabel(tr_ui("shell_nav_title"))
        nav_title.setObjectName("StemNavSectionLabel")
        self._nav_section_label = nav_title
        sidebar_layout.addWidget(nav_title)

        for index, item in enumerate(NAV_ITEMS):
            button = self._make_nav_button(item.label_key, item.icon, index)
            self._buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        return self.sidebar

    def _make_nav_button(self, label_key: str, icon_path: str, index: int) -> QToolButton:
        """Create a sidebar navigation button."""
        button = QToolButton()
        button.setObjectName("StemNavBtn")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(SHELL_NAV_H)
        button.setCheckable(True)
        button.setAutoRaise(False)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIconSize(SHELL_BRAND_ICON)
        button.setProperty("nav_label_key", label_key)
        button.setText(tr_ui(label_key))
        button.setAccessibleName(tr_ui(label_key))
        button.setStyleSheet("")
        if icon_path:
            resolved_icon = resolve_asset_path(icon_path)
            button.setProperty("nav_icon_path", resolved_icon)
            icon = self._tint_svg(
                resolved_icon,
                QColor(TEXT_SECONDARY),
                SHELL_BRAND_ICON,
            )
            if icon.isNull():
                icon = QIcon(resolved_icon)
            button.setIcon(icon)
            button.setIconSize(SHELL_BRAND_ICON)
        # Lambda đơn giản — chỉ forward index, không chứa logic phức tạp
        button.clicked.connect(lambda _, idx=index: self._on_nav_button_clicked(idx))
        return button

    def _navigate_by_delta(self, delta: int) -> None:
        """Điều hướng tương đối theo delta (+1 hoặc -1).

        Args:
            delta: Số trang cần dịch chuyển (dương = tiến, âm = lùi).
        """
        if not NAV_ITEMS:
            return
        next_index = max(0, min(len(NAV_ITEMS) - 1, self._active_index + delta))
        if next_index == self._active_index:
            return
        self._on_nav_button_clicked(next_index)

    def _handle_gesture_event(self, event: QGestureEvent) -> bool:
        """Xử lý swipe gesture để chuyển trang.

        Args:
            event: Sự kiện gesture từ Qt.

        Returns:
            True nếu gesture đã được xử lý.
        """
        gesture = event.gesture(Qt.GestureType.SwipeGesture)
        if not isinstance(gesture, QSwipeGesture):
            return False

        if gesture.state() != Qt.GestureState.GestureFinished:
            return True

        if gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Left:
            self._navigate_by_delta(1)
            return True
        if gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Right:
            self._navigate_by_delta(-1)
            return True
        return True

    @staticmethod
    def _tint_svg(path: str, color: QColor, size: QSize | None = None) -> QIcon:
        """Tô màu icon SVG bằng composition mode.

        Args:
            path: Đường dẫn file SVG.
            color: Màu cần tô.
            size: Kích thước render (mặc định 16x16).

        Returns:
            QIcon đã được tô màu.
        """
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return QIcon(path)
        render_size = size if size is not None else QSize(16, 16)
        pixmap = QPixmap(render_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return QIcon(pixmap)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_nav_button_clicked(self, index: int) -> None:
        """Xử lý khi người dùng click nút điều hướng trong sidebar.

        Args:
            index: Chỉ số trang được chọn.
        """
        self.set_active_index(index)
        self.nav_requested.emit(index)

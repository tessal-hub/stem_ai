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
                border: 1px solid {p.BORDER};
                border-radius: 0px;
            }}
            #StemToolbarTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 18px;
                font-weight: 500;
                color: {p.TEXT_PRIMARY};
                letter-spacing: -0.01em;
            }}
            #StemToolbarSubtitle {{
                font-size: 11px;
                font-weight: 500;
                color: {p.TEXT_SECONDARY};
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }}
            #StemSidebar {{
                background-color: {p.SURFACE_TERTIARY};
                border-right: 1px solid {p.BORDER};
            }}
            #StemBrandTitle {{
                font-family: {TITLE_FONT_STACK};
                font-size: 16px;
                font-weight: 600;
                color: {p.TEXT_PRIMARY};
                font-style: italic;
            }}
            #StemBrandSubtitle {{
                font-size: 9px;
                font-weight: 800;
                color: {p.TEXT_SECONDARY};
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }}
            #StemNavSectionLabel {{
                font-size: 9px;
                font-weight: 800;
                color: {p.TEXT_TERTIARY};
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-top: 16px;
                margin-bottom: 4px;
            }}
            QToolButton#StemNavBtn {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: {p.TEXT_PRIMARY};
                font-family: {APP_FONT_STACK};
                font-size: 13px;
                font-weight: 600;
                padding-left: 10px;
                padding-right: 10px;
                text-align: left;
            }}
            QToolButton#StemNavBtn:hover {{
                background-color: {p.HOVER_BG};
                color: {p.TEXT_PRIMARY};
            }}
            QToolButton#StemNavBtn[active="true"] {{
                background-color: {p.PRIMARY};
                color: {p.SURFACE_PRIMARY};
            }}
            #StemContentHost {{
                background-color: transparent;
            }}
        """)
        # Refresh brand icon
        icon = self._tint_svg(
            resolve_asset_path("assets/icon/cooliocns SVG/Interface/Book_Open.svg"),
            QColor(p.PRIMARY),
            QSize(24, 24)
        )
        self._brand_icon.setPixmap(icon.pixmap(QSize(24, 24)))
        # Refresh buttons
        self.set_active_index(self._active_index)
        self._update_sidebar_width()

    def _build_toolbar(self, title: str) -> QWidget:
        """Top toolbar with title and navigation hint — Floating Island architecture."""
        container = QWidget()
        container.setObjectName("StemToolbarContainer")
        container.setFixedHeight(54) # Shrunk from 96
        
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(16, 12, 16, 4)
        c_layout.addStretch(1)
        
        self.toolbar = QFrame()
        self.toolbar.setObjectName("StemToolbar")
        self.toolbar.setFixedWidth(500)  # Narrower island
        self.toolbar.setFixedHeight(36)  # Shrunk from 64
        apply_soft_shadow(self.toolbar, blur_radius=12, y_offset=3, color="rgba(0,0,0,0.06)")
        
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        toolbar_layout.setSpacing(SPACING_MD)

        self.title_label = QLabel(tr_ui("nav_home"))
        self.title_label.setObjectName("StemToolbarTitle")
        self.subtitle_label = QLabel(tr_ui("shell_subtitle_home"))
        self.subtitle_label.setObjectName("StemToolbarSubtitle")

        title_block = QWidget()
        title_block.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(SPACING_MD)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        toolbar_layout.addStretch()
        toolbar_layout.addWidget(title_block)
        toolbar_layout.addStretch()
        
        c_layout.addWidget(self.toolbar)
        c_layout.addStretch(1)
        
        _ = title  # legacy param
        return container

    def _build_brand_widget(self) -> QWidget:
        """Tạo widget brand (logo + tên app) cho phần đầu sidebar."""
        brand = QWidget()
        brand.setFixedHeight(SHELL_BRAND_H)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(4)

        self._brand_icon = QLabel()
        self._brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        brand_title = QLabel(tr_ui("shell_brand_stem"))
        brand_title.setObjectName("StemBrandTitle")
        self._brand_title_label = brand_title
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_subtitle = QLabel(tr_ui("shell_brand_book"))
        brand_subtitle.setObjectName("StemBrandSubtitle")
        self._brand_subtitle_label = brand_subtitle
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_layout.addWidget(self._brand_icon)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        return brand

    def _build_sidebar(self) -> QWidget:
        """Tạo sidebar với brand, danh sách nút điều hướng cực kỳ gọn gàng."""
        self.sidebar = QWidget()
        self.sidebar.setObjectName("StemSidebar")
        self.sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16) # Reduced margins
        sidebar_layout.setSpacing(0)

        sidebar_layout.addWidget(self._build_brand_widget())
        sidebar_layout.addSpacing(12)

        nav_title = QLabel(tr_ui("shell_nav_title"))
        nav_title.setObjectName("StemNavSectionLabel")
        self._nav_section_label = nav_title
        sidebar_layout.addWidget(nav_title)
        sidebar_layout.addSpacing(6)

        self._buttons = []
        for index, item in enumerate(NAV_ITEMS):
            button = self._make_nav_button(item.label_key, item.icon, index)
            self._buttons.append(button)
            sidebar_layout.addWidget(button)
            sidebar_layout.addSpacing(4) # Tighter spacing

        sidebar_layout.addStretch()
        self._update_sidebar_width()
        return self.sidebar

    def _update_sidebar_width(self) -> None:
        """Grow sidebar width so all nav labels stay fully visible."""
        if not hasattr(self, "sidebar") or not self._buttons:
            return
        max_btn_width = 0
        for button in self._buttons:
            metrics = QFontMetrics(button.font())
            text_width = metrics.horizontalAdvance(button.text())
            icon_width = button.iconSize().width()
            button_width = text_width + icon_width + 56  # icon/text gap + button paddings + safety
            max_btn_width = max(max_btn_width, button_width, button.sizeHint().width())
        nav_title_width = self._nav_section_label.sizeHint().width()
        content_width = max(max_btn_width, nav_title_width)
        sidebar_margins = 24  # left + right margins in sidebar_layout
        target_width = max(SHELL_SIDEBAR_W, content_width + sidebar_margins + 20)
        self.sidebar.setFixedWidth(target_width)

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
    # Public API
    # ------------------------------------------------------------------

    def set_active_index(self, index: int) -> None:
        """Cập nhật trạng thái 'active' của các nút trong sidebar."""
        self._active_index = index
        p = theme_manager.get_palette()
        for i, button in enumerate(self._buttons):
            is_active = (i == index)
            button.setChecked(is_active)
            button.setProperty("active", is_active)
            
            # Update icon color based on active state
            icon_path = button.property("nav_icon_path")
            color = QColor(p.SURFACE_PRIMARY) if is_active else QColor(p.TEXT_SECONDARY)
            button.setIcon(self._tint_svg(icon_path, color, SHELL_BRAND_ICON))
            
            # Refresh stylesheet to apply active color
            button.style().unpolish(button)
            button.style().polish(button)

        # Update toolbar title/subtitle
        if 0 <= index < len(NAV_ITEMS):
            item = NAV_ITEMS[index]
            self.title_label.setText(tr_ui(item.label_key))
            self.subtitle_label.setText(tr_ui(item.subtitle_key))

    def apply_ui_language(self) -> None:
        """Refresh shell labels after locale change."""
        self._brand_title_label.setText(tr_ui("shell_brand_stem"))
        self._brand_subtitle_label.setText(tr_ui("shell_brand_book"))
        self._nav_section_label.setText(tr_ui("shell_nav_title"))
        for button in self._buttons:
            label_key = button.property("nav_label_key")
            if isinstance(label_key, str):
                translated = tr_ui(label_key)
                button.setText(translated)
                button.setAccessibleName(translated)
        self._update_sidebar_width()
        self.set_active_index(self._active_index)

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

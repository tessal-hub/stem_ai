"""iOS-inspired app shell with sidebar navigation and swipe gestures."""

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
from ui.tokens import (
    APP_FONT_STACK,
    BORDER_COLOR,
    BORDER_LIGHT,
    HOVER_BG,
    MAC_TEXT_PRIMARY,
    PRIMARY_COLOR,
    SHELL_BRAND_H,
    SHELL_BRAND_ICON,
    SHELL_NAV_H,
    SHELL_SIDEBAR_W,
    SURFACE_2,
    SURFACE_PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_MD, SPACING_SM


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str
    subtitle: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("Home", "assets/icon/home.svg", "Overview and quick actions"),
    NavItem("Record", "assets/icon/record.svg", "Capture and trim motion samples"),
    NavItem("Statistics", "assets/icon/statistic.svg", "Live metrics and model progress"),
    NavItem("Primitives", "assets/icon/record.svg", "Collect primitive gesture datasets"),
    NavItem("Wand", "assets/icon/wand.svg", "Hardware tools and telemetry"),
    NavItem("Setting", "assets/icon/setting.svg", "Configuration and firmware"),
)


class MacShell(QWidget):
    nav_requested = pyqtSignal(int)

    def __init__(self, title: str = "Reboot") -> None:
        super().__init__()
        self._buttons: list[QToolButton] = []
        self._active_index = 0
        self._fallback_title = title
        self._build_ui(title)
        self.grabGesture(Qt.GestureType.SwipeGesture)
        self.content_host.grabGesture(Qt.GestureType.SwipeGesture)

    def set_active_index(self, index: int) -> None:
        if not NAV_ITEMS:
            return
        self._active_index = max(0, min(len(NAV_ITEMS) - 1, index))
        item = NAV_ITEMS[self._active_index]

        self.title_label.setText(item.label or self._fallback_title)
        self.subtitle_label.setText(item.subtitle)

        for button_index, button in enumerate(self._buttons):
            is_active = button_index == self._active_index
            button.setProperty("active", is_active)
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
        if event.type() == QEvent.Type.Gesture:
            if isinstance(event, QGestureEvent):
                return self._handle_gesture_event(event)
        return super().event(event)

    def _build_ui(self, title: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        chrome = QWidget()
        chrome.setStyleSheet(
            f"background-color: {SURFACE_PRIMARY}; border: none; border-radius: 14px;"
        )
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.content_host = QWidget()
        self.content_host.setStyleSheet(f"background-color: {SURFACE_PRIMARY};")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        body_layout.addWidget(self._build_sidebar())
        body_layout.addWidget(self.content_host, stretch=1)

        chrome_layout.addWidget(self._build_toolbar(title))
        chrome_layout.addWidget(body, stretch=1)
        outer.addWidget(chrome)

        self.setStyleSheet(
            f"* {{ font-family: {APP_FONT_STACK}; }} QPushButton {{ text-align: left; }}"
        )
        self.set_active_index(0)

    def _build_toolbar(self, title: str) -> QWidget:
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setStyleSheet(
            f"background-color: {SURFACE_PRIMARY}; border-bottom: 1px solid rgba(0, 0, 0, 0.06);"
        )
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            MARGIN_COMFORTABLE, SPACING_SM, MARGIN_COMFORTABLE, SPACING_SM
        )
        toolbar_layout.setSpacing(SPACING_SM)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {MAC_TEXT_PRIMARY}; font-size: 20px; font-weight: 700;"
        )
        self.subtitle_label = QLabel("App dashboard")
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500;"
        )

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.nav_hint_label = QLabel("Swipe left or right to navigate")
        self.nav_hint_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 500;"
        )

        toolbar_layout.addWidget(title_block)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.nav_hint_label)
        return toolbar

    def _build_brand_widget(self) -> QWidget:
        brand = QWidget()
        brand.setFixedHeight(SHELL_BRAND_H)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(SPACING_SM)

        brand_icon_row = QWidget()
        icon_layout = QHBoxLayout(brand_icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        icon_layout.addStretch()

        brand_icon = QLabel("◉")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(SHELL_BRAND_ICON)
        brand_icon.setStyleSheet(
            "background-color: "
            f"{PRIMARY_COLOR}; color: white; border-radius: 15px; font-size: 16px; font-weight: 900;"
        )
        icon_layout.addWidget(brand_icon)
        icon_layout.addStretch()

        brand_title = QLabel("STEM")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_title.setStyleSheet(
            f"color: {MAC_TEXT_PRIMARY}; font-size: 12px; font-weight: 800;"
        )
        brand_subtitle = QLabel("Spell Book")
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_subtitle.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 600;"
        )

        brand_layout.addWidget(brand_icon_row)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        return brand

    def _build_sidebar(self) -> QWidget:
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        self.sidebar.setStyleSheet(
            f"background-color: {SURFACE_2}; border-right: 1px solid rgba(0, 0, 0, 0.06);"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(
            SPACING_MD, MARGIN_COMFORTABLE, SPACING_MD, MARGIN_COMFORTABLE
        )
        sidebar_layout.setSpacing(SPACING_SM)

        sidebar_layout.addWidget(self._build_brand_widget())

        nav_title = QLabel("Navigation")
        nav_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700;"
        )
        sidebar_layout.addWidget(nav_title)

        for index, item in enumerate(NAV_ITEMS):
            button = self._make_nav_button(item.label, item.icon, index)
            self._buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        return self.sidebar

    def _make_nav_button(self, label: str, icon_path: str, index: int) -> QToolButton:
        button = QToolButton()
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(SHELL_NAV_H)
        button.setCheckable(True)
        button.setAutoRaise(False)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIconSize(SHELL_BRAND_ICON)
        button.setText(label)
        button.setAccessibleName(f"Navigate to {label}")
        button.setStyleSheet(
            f"""
            QToolButton {{
                color: {TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 14px;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 600;
                qproperty-iconSize: 30px 30px;
                text-align: left;
            }}
            QToolButton[active="true"] {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: 1px solid {PRIMARY_COLOR};
                border-radius: 14px;
            }}
            QToolButton:hover {{
                background-color: {HOVER_BG};
                color: {PRIMARY_COLOR};
                border: 1px solid rgba(10, 132, 255, 0.24);
                border-radius: 14px;
            }}
            """
        )
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
        button.clicked.connect(lambda _, idx=index: self._on_nav(idx))
        return button

    def _on_nav(self, index: int) -> None:
        self.set_active_index(index)
        self.nav_requested.emit(index)

    def _navigate_by_delta(self, delta: int) -> None:
        if not NAV_ITEMS:
            return
        next_index = max(0, min(len(NAV_ITEMS) - 1, self._active_index + delta))
        if next_index == self._active_index:
            return
        self._on_nav(next_index)

    def _handle_gesture_event(self, event: QGestureEvent) -> bool:
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

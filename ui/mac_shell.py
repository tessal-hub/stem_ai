"""macOS-style app shell with sidebar navigation and unified toolbar."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from ui.tokens import (
    APP_FONT_STACK,
    MAC_TEXT_PRIMARY,
    PRIMARY_COLOR,
    SURFACE_PRIMARY,
    SURFACE_SECONDARY,
    TEXT_SECONDARY,
    BORDER_COLOR,
    BORDER_LIGHT,
    SHELL_BRAND_ICON,
    SHELL_BRAND_H,
    SHELL_NAV_H,
    SHELL_SIDEBAR_W,
    TEXT_MUTED,
)


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("Home", "assets/icon/home.svg"),
    NavItem("Record", "assets/icon/record.svg"),
    NavItem("Statistics", "assets/icon/statistic.svg"),
    NavItem("Wand", "assets/icon/wand.svg"),
    NavItem("Setting", "assets/icon/setting.svg"),
)


class MacShell(QWidget):
    nav_requested = pyqtSignal(int)

    def __init__(self, title: str = "Reboot") -> None:
        super().__init__()
        self._buttons: list[QToolButton] = []
        self._build_ui(title)

    def set_active_index(self, index: int) -> None:
        for button_index, button in enumerate(self._buttons):
            button.setProperty("active", button_index == index)
            button_style = button.style()
            if button_style is not None:
                button_style.unpolish(button)
                button_style.polish(button)

    def _build_ui(self, title: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        chrome = QWidget()
        chrome.setStyleSheet(
            f"background-color: {SURFACE_PRIMARY}; border: 1px solid {BORDER_COLOR};"
        )
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.content_host = QWidget()
        self.content_host.setStyleSheet(f"background-color: {SURFACE_SECONDARY};")
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
        """Build the top toolbar with title and subtitle labels."""
        toolbar = QWidget()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet(
            f"background-color: {SURFACE_PRIMARY}; border-bottom: 1px solid {BORDER_LIGHT};"
        )
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 6, 16, 6)
        toolbar_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 700;"
        )
        self.subtitle_label = QLabel("Desktop control surface")
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 500;"
        )

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        toolbar_layout.addWidget(title_block)
        toolbar_layout.addStretch()
        return toolbar

    def _build_brand_widget(self) -> QWidget:
        """Build the brand icon + title block shown at the top of the sidebar."""
        brand = QWidget()
        brand.setFixedHeight(SHELL_BRAND_H)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        brand_icon_row = QWidget()
        icon_layout = QHBoxLayout(brand_icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        icon_layout.addStretch()

        brand_icon = QLabel("◉")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(SHELL_BRAND_ICON)
        brand_icon.setStyleSheet(
            f"background-color: {PRIMARY_COLOR}; color: white; border-radius: 17px; font-size: 18px; font-weight: 900;"
        )
        icon_layout.addWidget(brand_icon)
        icon_layout.addStretch()

        brand_title = QLabel("STEM")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_title.setStyleSheet(
            f"color: {MAC_TEXT_PRIMARY}; font-size: 11px; font-weight: 900; letter-spacing: 1px;"
        )
        brand_subtitle = QLabel("Spell Book")
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_subtitle.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; font-weight: 700; letter-spacing: 0.6px;"
        )

        brand_layout.addWidget(brand_icon_row)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        return brand

    def _build_sidebar(self) -> QWidget:
        """Build the fixed-width sidebar with brand and navigation buttons."""
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(SHELL_SIDEBAR_W)
        self.sidebar.setStyleSheet(
            f"background-color: {SURFACE_SECONDARY}; border-right: 1px solid {BORDER_LIGHT};"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(8)

        sidebar_layout.addWidget(self._build_brand_widget())

        nav_title = QLabel("NAV")
        nav_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 1.6px;"
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
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIconSize(SHELL_BRAND_ICON)
        button.setText(label)
        button.setAccessibleName(f"Navigate to {label}")
        button.setStyleSheet(
            f"""
            QToolButton {{
                color: {TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 6px 4px;
                font-size: 10px;
                font-weight: 700;
                qproperty-iconSize: 34px 34px;
            }}
            QToolButton[active="true"] {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
            }}
            QToolButton:hover {{
                background-color: rgba(59, 130, 246, 0.08);
                color: {PRIMARY_COLOR};
                border-radius: 8px;
            }}
            """
        )
        if icon_path:
            icon = self._tint_svg(
                icon_path,
                QColor(PRIMARY_COLOR if index == 0 else TEXT_SECONDARY),
                SHELL_BRAND_ICON,
            )
            button.setIcon(icon)
            button.setIconSize(SHELL_BRAND_ICON)
        button.clicked.connect(lambda _, idx=index: self._on_nav(idx))
        return button

    def _on_nav(self, index: int) -> None:
        self.set_active_index(index)
        self.nav_requested.emit(index)

    @staticmethod
    def _tint_svg(path: str, color: QColor, size: QSize | None = None) -> QIcon:
        renderer = QSvgRenderer(path)
        render_size = size if size is not None else QSize(16, 16)
        pixmap = QPixmap(render_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return QIcon(pixmap)

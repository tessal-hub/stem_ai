"""macOS-style app shell with sidebar navigation and unified toolbar."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout, QWidget

from ui.tokens import (
    APP_FONT_STACK,
    ACCENT,
    BG_LIGHT,
    BG_WHITE,
    BORDER,
    MAC_BG,
    MAC_BORDER,
    MAC_SIDEBAR_BG,
    MAC_TOOLBAR_BG,
    MAC_TEXT_PRIMARY,
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
        self._buttons: list[QPushButton] = []
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
            f"background-color: {MAC_BG}; border: 1px solid {MAC_BORDER};"
        )
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet(
            f"background-color: {MAC_TOOLBAR_BG}; border-bottom: 1px solid {MAC_BORDER};"
        )
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 6, 16, 6)
        toolbar_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {MAC_TEXT_PRIMARY}; font-size: 13px; font-weight: 700;"
        )
        self.subtitle_label = QLabel("Desktop control surface")
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 500;"
        )

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        toolbar_layout.addWidget(title_block)
        toolbar_layout.addStretch()

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(188)
        self.sidebar.setStyleSheet(
            f"background-color: {MAC_SIDEBAR_BG}; border-right: 1px solid {MAC_BORDER};"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 10, 12, 10)
        sidebar_layout.setSpacing(6)

        sidebar_title = QLabel("Navigation")
        sidebar_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;"
        )
        sidebar_layout.addWidget(sidebar_title)

        for index, item in enumerate(NAV_ITEMS):
            button = self._make_nav_button(item.label, item.icon, index)
            self._buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        self.content_host = QWidget()
        self.content_host.setStyleSheet(f"background-color: {BG_LIGHT};")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.content_host, stretch=1)

        chrome_layout.addWidget(toolbar)
        chrome_layout.addWidget(body, stretch=1)
        outer.addWidget(chrome)

        self.setStyleSheet(
            f"* {{ font-family: {APP_FONT_STACK}; }} QPushButton {{ text-align: left; }}"
        )
        self.set_active_index(0)

    def _make_nav_button(self, label: str, icon_path: str, index: int) -> QPushButton:
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(34)
        button.setCheckable(True)
        button.setStyleSheet(
            f"""
            QPushButton {{
                color: {MAC_TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton[active="true"] {{
                background-color: rgba(255, 255, 255, 0.82);
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.55);
            }}
            """
        )
        if icon_path:
            icon = self._tint_svg(icon_path, QColor(ACCENT if index == 0 else TEXT_MUTED))
            button.setIcon(icon)
        button.clicked.connect(lambda _, idx=index: self._on_nav(idx))
        return button

    def _on_nav(self, index: int) -> None:
        self.set_active_index(index)
        self.nav_requested.emit(index)

    @staticmethod
    def _tint_svg(path: str, color: QColor) -> QIcon:
        renderer = QSvgRenderer(path)
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return QIcon(pixmap)

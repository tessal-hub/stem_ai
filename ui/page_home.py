"""PageHome — main dashboard view."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ui.wand_3d_widget import Wand3DWidget
from ui.component_factory import make_empty_state_card, make_card
from ui.mac_material import apply_soft_shadow
from ui.i18n_bridge import tr_ui
from logic.theme_manager import theme_manager
from ui.tokens import (
    HOME_STATUS_H,
    HOME_VIEWER_MIN_H,
    STYLE_HOME_SECTION_TITLE,
    STYLE_HOME_SECTION_SUBTITLE,
    MARGIN_COMFORTABLE,
    SPACING_LG,
    SPACING_XS,
    TITLE_FONT_STACK,
)


class PageHome(QWidget):
    """
    Trang Dashboard chính của ứng dụng.
    Hiển thị trạng thái kết nối wand và mô phỏng hướng 3D.
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._connected = False
        self._current_mode = "IDLE"
        
        self._init_ui()
        self._configure_accessibility()
        self._load_data()

    def set_connection_status(self, connected: bool) -> None:
        """Cập nhật giao diện trạng thái kết nối wand."""
        self._connected = connected
        p = theme_manager.get_palette()
        if connected:
            self.status_bar.setText(tr_ui("home_status_connected"))
            self.status_bar.setStyleSheet(self._status_style(p.PRIMARY, "#FFFFFF"))
        else:
            self.status_bar.setText(tr_ui("home_status_disconnected"))
            self.status_bar.setStyleSheet(self._status_style(p.STATUS_ERROR_TEXT, "#FFFFFF"))

    def set_mode(self, mode: str) -> None:
        """Cập nhật nhãn chế độ hoạt động hiện tại."""
        self._current_mode = mode.upper()

    def apply_ui_language(self) -> None:
        """Refresh static labels after locale change."""
        self._viewer_title.setText(tr_ui("home_viewer_title"))
        self._viewer_subtitle.setText(tr_ui("home_viewer_subtitle"))
        self.set_mode(self._current_mode)
        self.set_connection_status(self._connected)

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        
        # Update Hero Section Titles
        self._viewer_title.setStyleSheet(f"font-family: {TITLE_FONT_STACK}; color: {p.TEXT_PRIMARY}; font-size: 24px; font-weight: 500;")
        self._viewer_subtitle.setStyleSheet(f"color: {p.TEXT_SECONDARY}; font-weight: 600; font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;")
        
        # Update Viewer Card
        self.viewer_card.setStyleSheet(f"""
            #HomeViewerCard {{
                background-color: {p.SURFACE_TERTIARY};
                border: 1px solid {p.BORDER};
                border-radius: 24px;
            }}
        """)
        self.sim_view.setStyleSheet(f"background-color: {p.SURFACE_PRIMARY}; border-radius: 16px;")
        
        # Update Status Bar
        self.set_connection_status(self._connected)

    def _init_ui(self) -> None:
        """Trang chính (Dashboard) — hiển thị trạng thái kết nối, mô phỏng 3D."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)

        outer.addWidget(self._build_status_bar())

        content = QVBoxLayout()
        content.setSpacing(SPACING_LG)
        content.setContentsMargins(0, 0, 0, 0)
        
        # Expanding content area
        viewer_container = QHBoxLayout()
        viewer_container.addStretch(1)
        self.viewer_card = self._build_viewer_box()
        self.viewer_card.setMaximumWidth(1400) # Allow full-bleed on standard screens
        viewer_container.addWidget(self.viewer_card, stretch=10)
        viewer_container.addStretch(1)
        
        content.addLayout(viewer_container, stretch=1)
        outer.addLayout(content, stretch=1)
        
        self.refresh_styles()

    def _build_status_bar(self) -> QWidget:
        """Xây dựng status bar kiểu 'Floating Island'."""
        container = QWidget()
        container.setFixedHeight(HOME_STATUS_H + 16)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addStretch(1)
        
        self.status_bar = QLabel(tr_ui("home_status_disconnected"))
        self.status_bar.setObjectName("HomeStatusBar")
        self.status_bar.setFixedWidth(340)
        self.status_bar.setFixedHeight(HOME_STATUS_H)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        apply_soft_shadow(self.status_bar, blur_radius=12, y_offset=4, color="rgba(0,0,0,0.08)")
        
        layout.addWidget(self.status_bar)
        layout.addStretch(1)
        return container

    @staticmethod
    def _status_style(bg_color: str, fg_color: str) -> str:
        return (
            "QLabel {{ "
            f"background-color: {bg_color}; "
            f"color: {fg_color}; padding: 6px 18px; font-size: 11px; "
            "font-weight: 800; letter-spacing: 0.05em; border-radius: 15px; }}"
        )

    def _build_viewer_box(self) -> QFrame:
        """Xây dựng box chứa vùng hiển thị 3D wand."""
        box = QFrame()
        box.setObjectName("HomeViewerCard")
        
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        inner_content = QFrame()
        inner_content.setObjectName("HomeInnerCore")
        inner_layout = QVBoxLayout(inner_content)
        inner_layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        
        header = QVBoxLayout()
        header.setContentsMargins(0, 0, 0, SPACING_LG)
        header.setSpacing(SPACING_XS)
        
        self._viewer_title = QLabel(tr_ui("home_viewer_title"))
        self._viewer_subtitle = QLabel(tr_ui("home_viewer_subtitle"))
        
        header.addWidget(self._viewer_title)
        header.addWidget(self._viewer_subtitle)
        inner_layout.addLayout(header)

        self.sim_view = QFrame()
        self.sim_view.setObjectName("HomeViewerSurface")
        self.sim_view.setMinimumHeight(HOME_VIEWER_MIN_H)
        
        sim_inner = QVBoxLayout(self.sim_view)
        sim_inner.setContentsMargins(0, 0, 0, 0)
        
        self.wand_3d = Wand3DWidget()
        sim_inner.addWidget(self.wand_3d, stretch=1)

        inner_layout.addWidget(self.sim_view, stretch=1)
        layout.addWidget(inner_content)
        
        return box

    def _load_data(self) -> None:
        """Nạp trạng thái ban đầu."""
        self.set_connection_status(False)

    def _configure_accessibility(self) -> None:
        """Đặt accessible names."""
        self.status_bar.setAccessibleName("Home status banner")
        self.wand_3d.setAccessibleName("3D wand orientation viewer")

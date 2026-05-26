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
from ui.color_utils import readable_text_on
from ui.tokens import (
    APP_FONT_STACK,
    HOME_STATUS_H,
    HOME_VIEWER_MIN_H,
    STYLE_HOME_SECTION_TITLE,
    STYLE_HOME_SECTION_SUBTITLE,
    MARGIN_COMFORTABLE,
    SPACING_LG,
    SPACING_XS,
    TITLE_FONT_STACK,
    CARD_RADIUS,
    BTN_RADIUS,
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
            self.status_bar.setStyleSheet(
                self._status_style(
                    p.STATUS_SUCCESS,
                    readable_text_on(p.STATUS_SUCCESS, dark_text=p.STATUS_SUCCESS_TEXT, light_text="#FFFFFF"),
                )
            )
        else:
            self.status_bar.setText(tr_ui("home_status_disconnected"))
            self.status_bar.setStyleSheet(
                self._status_style(
                    p.STATUS_ERROR,
                    readable_text_on(p.STATUS_ERROR, dark_text=p.STATUS_ERROR_TEXT, light_text="#FFFFFF"),
                )
            )

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
        self._viewer_title.setStyleSheet(f"font-family: {TITLE_FONT_STACK}; color: {p.TEXT_PRIMARY}; font-size: 24px; font-weight: 600;")
        self._viewer_subtitle.setStyleSheet(f"color: {p.TEXT_SECONDARY}; font-weight: 500; font-size: 12px; font-family: {APP_FONT_STACK};")
        
        # Update Viewer Card
        self.viewer_card.setStyleSheet(f"""
            #HomeViewerCard {{
                background-color: {p.SURFACE_TERTIARY};
                border: 1px solid {p.BORDER};
                border-radius: {CARD_RADIUS};
            }}
        """)
        self.sim_view.setStyleSheet(f"background-color: {p.SURFACE_PRIMARY}; border-radius: {BTN_RADIUS};")

    def _init_ui(self) -> None:
        """Khởi tạo các thành phần giao diện."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_LG)

        # ── Status Bar ──
        self.status_bar = QLabel(tr_ui("home_status_disconnected"))
        self.status_bar.setMinimumHeight(HOME_STATUS_H + 12)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_bar)

        # ── Content Layout (2 columns) ──
        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)

        # Left Column (3D Viewer)
        left_col = QVBoxLayout()
        left_col.setSpacing(SPACING_XS)
        
        self._viewer_title = QLabel(tr_ui("home_viewer_title"))
        self._viewer_title.setStyleSheet(STYLE_HOME_SECTION_TITLE)
        self._viewer_subtitle = QLabel(tr_ui("home_viewer_subtitle"))
        self._viewer_subtitle.setStyleSheet(STYLE_HOME_SECTION_SUBTITLE)
        
        left_col.addWidget(self._viewer_title)
        left_col.addWidget(self._viewer_subtitle)

        self.viewer_card = QFrame()
        self.viewer_card.setObjectName("HomeViewerCard")
        self.viewer_card.setMinimumHeight(HOME_VIEWER_MIN_H)
        viewer_layout = QVBoxLayout(self.viewer_card)
        viewer_layout.setContentsMargins(12, 12, 12, 12)

        self.sim_view = Wand3DWidget()
        viewer_layout.addWidget(self.sim_view)
        
        left_col.addWidget(self.viewer_card, stretch=1)
        content.addLayout(left_col, stretch=2)

        # Right Column (Legacy placeholder)
        right_col = QVBoxLayout()
        # Adding empty state as a temporary aesthetic placeholder
        empty_card, _ = make_empty_state_card(tr_ui("home_no_spells_title"), tr_ui("home_no_spells_body"))
        right_col.addWidget(empty_card)
        right_col.addStretch()
        content.addLayout(right_col, stretch=1)

        layout.addLayout(content)
        self.refresh_styles()

    def _status_style(self, bg_color: str, fg_color: str) -> str:
        """Helper generating status bar stylesheet."""
        return f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: {BTN_RADIUS};
            font-family: {APP_FONT_STACK};
            font-size: 13px;
            font-weight: 700;
        """

    def _load_data(self) -> None:
        """Nạp trạng thái ban đầu."""
        self.set_connection_status(self.data_store.is_connected)

    def _configure_accessibility(self) -> None:
        """Cấu hình accessible names."""
        self.status_bar.setAccessibleName("Wand connection status")
        self.sim_view.setAccessibleName("3D Wand orientation preview")

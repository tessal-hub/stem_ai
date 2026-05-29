"""
ui/page_home.py — Trang Dashboard chính (Tổng quan).

Hiển thị trạng thái kết nối của thiết bị và mô phỏng hướng 3D của đũa phép (wand)
trong thời gian thực. Cung cấp cái nhìn tổng quan về hệ thống.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from logic.theme_manager import theme_manager
from ui.color_utils import readable_text_on
from ui.component_factory import make_card, make_empty_state_card, make_section_label
from ui.i18n_bridge import tr_ui
from ui.tokens import (
    MARGIN_COMFORTABLE,
    SPACING_LG,
    SPACING_MD,
    SPACING_XS,
)
from ui.wand_3d_widget import Wand3DWidget


class PageHome(QWidget):
    """
    Trang Dashboard hiển thị mô phỏng 3D và trạng thái hệ thống.
    """

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._connected = False
        self._current_mode = "IDLE"
        
        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện dashboard với bố cục editorial 2 cột."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, 80)
        layout.setSpacing(SPACING_LG)

        header = QFrame()
        header.setObjectName("HomeHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(SPACING_XS)

        self._eyebrow = make_section_label("REAL-TIME COMMAND CENTER", accent=True)
        self._eyebrow.setProperty("type", "settings_section_label")

        self._viewer_title = QLabel(tr_ui("home_viewer_title"))
        self._viewer_title.setProperty("type", "section_title")

        self._viewer_subtitle = QLabel(tr_ui("home_viewer_subtitle"))
        self._viewer_subtitle.setProperty("type", "section_subtitle")

        header_layout.addWidget(self._eyebrow)
        header_layout.addWidget(self._viewer_title)
        header_layout.addWidget(self._viewer_subtitle)
        layout.addWidget(header)

        # 1. Thanh trạng thái kết nối
        self.status_bar = QLabel(tr_ui("home_status_disconnected"))
        self.status_bar.setFixedHeight(42)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setProperty("type", "status_label")
        self.status_bar.setProperty("status", "error")
        layout.addWidget(self.status_bar)

        # 2. Nội dung chính (2 cột)
        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)

        # Cột trái: Mô phỏng 3D
        left_col = self._build_viewer_column()
        content.addLayout(left_col, stretch=2)

        # Cột phải: Thông tin bổ sung
        right_col = QVBoxLayout()
        empty_card, _ = make_empty_state_card("No data to evaluate yet", tr_ui("home_no_spells_body"))
        empty_card.setObjectName("HomeRightSection")
        right_col.addWidget(empty_card)
        right_col.addStretch()
        content.addLayout(right_col, stretch=1)

        layout.addLayout(content)
        self.refresh_styles()

    def _init_signals(self) -> None:
        """Kết nối signal/slot."""
        pass

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ store."""
        self.set_connection_status(self.data_store.is_connected)

    # ── Public methods ──────────────────────────

    def set_connection_status(self, connected: bool) -> None:
        """Cập nhật nhãn trạng thái kết nối."""
        self._connected = connected
        status_key = "home_status_connected" if connected else "home_status_disconnected"
        self.status_bar.setText(tr_ui(status_key))
        if hasattr(self, "_status_chip"):
            self._status_chip.setText(tr_ui(status_key))
        
        self.status_bar.setProperty("status", "success" if connected else "error")
        if hasattr(self, "_status_chip"):
            self._status_chip.setProperty("status", "success" if connected else "error")
            self._status_chip.style().unpolish(self._status_chip)
            self._status_chip.style().polish(self._status_chip)
        self.status_bar.style().unpolish(self.status_bar)
        self.status_bar.style().polish(self.status_bar)

    def set_mode(self, mode: str) -> None:
        """Cập nhật chế độ hoạt động hiện tại."""
        self._current_mode = mode.upper()
        if hasattr(self, "_mode_chip"):
            self._mode_chip.setText(f"MODE: {self._current_mode}")

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ cho các nhãn tĩnh."""
        self._viewer_title.setText(tr_ui("home_viewer_title"))
        self._viewer_subtitle.setText(tr_ui("home_viewer_subtitle"))
        self.set_connection_status(self._connected)
        self.set_mode(self._current_mode)

    def refresh_styles(self) -> None:
        """Làm mới giao diện theo theme hiện tại."""
        pass  # Không cần thiết lập lại stylesheet thủ công vì theme.py đã quản lý

    # ── Private methods ─────────────────────────

    def _build_viewer_column(self) -> QVBoxLayout:
        """Xây dựng cột hiển thị mô phỏng 3D."""
        col = QVBoxLayout()
        col.setSpacing(SPACING_XS)

        self.viewer_card, viewer_layout = make_card(margins=(16, 16, 16, 16), spacing=0)
        self.viewer_card.setMinimumHeight(520)
        self.viewer_card.setObjectName("HomeViewerCard")

        self.sim_view = Wand3DWidget()
        self.sim_view.setObjectName("HomeViewerSurface")
        self.wand_3d = self.sim_view 
        viewer_layout.addWidget(self.sim_view)
        
        col.addWidget(self.viewer_card, stretch=1)
        return col

    def _configure_accessibility(self) -> None:
        """Thiết lập thông tin hỗ trợ người khiếm thị."""
        self.status_bar.setAccessibleName("Trạng thái kết nối đũa phép")
        self.sim_view.setAccessibleName("Vùng xem trước 3D")

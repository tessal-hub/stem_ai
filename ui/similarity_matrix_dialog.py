"""
ui/similarity_matrix_dialog.py — Hộp thoại ma trận tương đồng và phân biệt thần chú (Spell Similarity Matrix).

Hiển thị bảng ma trận nhiệt (heatmap table) đo độ tương đồng cử chỉ giữa tất cả các thần chú
trong dataset, tự động phát hiện và cảnh báo các cặp thần chú có nguy cơ nhầm lẫn cao (>80%).
Tương thích hoàn hảo cả Light Mode và Dark Mode.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from logic.theme_manager import theme_manager
from ui.component_factory import make_card, make_primary_button
from ui.i18n_bridge import tr_ui
from ui.tokens import (
    ACCENT,
    APP_FONT_STACK,
    RADIUS_MD,
    SUCCESS,
    WARNING,
)


class SimilarityMatrixDialog(QDialog):
    """Hộp thoại trực quan hóa ma trận tương đồng giữa các thần chú và cảnh báo xung đột."""

    def __init__(
        self,
        spell_names: list[str],
        matrix: np.ndarray,
        conflicts: list[tuple[str, str, float]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._spell_names = spell_names
        self._matrix = matrix
        self._conflicts = conflicts

        self.setWindowTitle("🔍 STEM AI — Ma Trận Tương Đồng Thần Chú (Confusion Matrix)")
        self.setMinimumSize(780, 560)
        self.resize(860, 620)
        self.setModal(True)

        self._p = theme_manager.get_palette()
        self._is_dark = theme_manager.current_theme == "dark"

        self._init_ui()
        self._apply_theme()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        p = self._p

        # 1. Header
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 28px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Ma Trận Phân Biệt & Tương Đồng Thần Chú")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {p.TEXT_PRIMARY};")
        lbl_sub = QLabel("Phân tích không gian vector 16-D để phát hiện sớm các thần chú có động tác vung dễ gây nhầm lẫn.")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {p.TEXT_SECONDARY};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box, stretch=1)

        layout.addLayout(header)

        # 2. Conflict Banner / Status Alert Card
        alert_card, a_layout = make_card(margins=(16, 12, 16, 12), spacing=6)
        if self._conflicts:
            alert_header = QLabel(f"⚠️ Phát hiện {len(self._conflicts)} cặp thần chú có độ tương đồng cao (>75%):")
            alert_header.setStyleSheet("font-weight: 700; font-size: 13px; color: #FF3B30;")
            a_layout.addWidget(alert_header)

            for sp_a, sp_b, score in self._conflicts[:3]:
                pct = int(round(score * 100))
                lbl_c = QLabel(f"• <b>{sp_a}</b> ⟷ <b>{sp_b}</b>: giống nhau <b>{pct}%</b>. <i>(Khuyến nghị: Thử đổi hướng xuất phát hoặc góc vung tay để AI phân biệt sắc nét hơn)</i>")
                lbl_c.setWordWrap(True)
                lbl_c.setStyleSheet(f"font-size: 12px; color: {p.TEXT_PRIMARY}; margin-left: 6px;")
                a_layout.addWidget(lbl_c)
        else:
            if len(self._spell_names) >= 2:
                alert_header = QLabel("✅ Bộ thần chú có độ phân biệt xuất sắc!")
                alert_header.setStyleSheet("font-weight: 700; font-size: 13px; color: #28A745;")
                lbl_ok = QLabel("Tất cả các thần chú đã đăng ký đều có quỹ đạo cử chỉ khác biệt rõ ràng, AI sẽ nhận diện cực kỳ chính xác.")
                lbl_ok.setStyleSheet(f"font-size: 12px; color: {p.TEXT_PRIMARY};")
                a_layout.addWidget(alert_header)
                a_layout.addWidget(lbl_ok)
            else:
                alert_header = QLabel("ℹ️ Cần tối thiểu 2 thần chú có dữ liệu để lập ma trận so sánh.")
                alert_header.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {p.TEXT_SECONDARY};")
                a_layout.addWidget(alert_header)

        layout.addWidget(alert_card)

        # 3. Heatmap Table
        n = len(self._spell_names)
        self._table = QTableWidget(n, n)
        self._table.setHorizontalHeaderLabels(self._spell_names)
        self._table.setVerticalHeaderLabels(self._spell_names)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for i in range(n):
            for j in range(n):
                val = float(self._matrix[i, j]) if self._matrix.size > 0 else 0.0
                pct = int(round(val * 100))
                item = QTableWidgetItem(f"{pct}%")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if i == j:
                    item.setText("100%")
                    item.setToolTip(f"{self._spell_names[i]} (Tự so sánh)")
                else:
                    item.setToolTip(f"Độ tương đồng giữa {self._spell_names[i]} và {self._spell_names[j]}: {pct}%")

                self._table.setItem(i, j, item)

        self._style_table_cells()
        layout.addWidget(self._table, stretch=1)

        # 4. Legend & Bottom bar
        bottom_bar = QHBoxLayout()
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(14)

        leg1 = QLabel("🟢 < 50%: Tách biệt rất tốt")
        leg1.setStyleSheet("font-size: 11px; font-weight: 600; color: #28A745;")
        leg2 = QLabel("🟡 50% - 75%: Tương đồng vừa phải")
        leg2.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF9500;")
        leg3 = QLabel("🔴 > 75%: Nguy cơ nhầm lẫn")
        leg3.setStyleSheet("font-size: 11px; font-weight: 700; color: #FF3B30;")

        legend_layout.addWidget(leg1)
        legend_layout.addWidget(leg2)
        legend_layout.addWidget(leg3)
        bottom_bar.addLayout(legend_layout)
        bottom_bar.addStretch()

        btn_close = make_primary_button("Đã Hiểu", height=36)
        btn_close.setMinimumWidth(110)
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def _style_table_cells(self) -> None:
        n = len(self._spell_names)
        is_dark = self._is_dark
        p = self._p

        for i in range(n):
            for j in range(n):
                item = self._table.item(i, j)
                if not item:
                    continue
                val = float(self._matrix[i, j]) if self._matrix.size > 0 else 0.0
                if i == j:
                    # Diagonal
                    bg = "rgba(0, 122, 255, 0.15)"
                    color = "#007AFF"
                else:
                    if val >= 0.75:
                        bg = "rgba(255, 59, 48, 0.22)"
                        color = "#FF3B30"
                    elif val >= 0.50:
                        bg = "rgba(255, 149, 0, 0.18)"
                        color = "#FF9500"
                    else:
                        bg = "rgba(52, 199, 89, 0.15)"
                        color = "#28A745"

                # Cell font and background
                font = item.font()
                font.setBold(i == j or val >= 0.75)
                item.setFont(font)
                if i == j:
                    item.setForeground(Qt.GlobalColor.darkBlue if not is_dark else Qt.GlobalColor.cyan)
                elif val >= 0.75:
                    item.setForeground(Qt.GlobalColor.darkRed if not is_dark else Qt.GlobalColor.red)
                elif val >= 0.50:
                    item.setForeground(Qt.GlobalColor.darkYellow if not is_dark else Qt.GlobalColor.yellow)
                else:
                    item.setForeground(Qt.GlobalColor.darkGreen if not is_dark else Qt.GlobalColor.green)

    def _apply_theme(self) -> None:
        p = self._p
        is_dark = self._is_dark
        border_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
        bg_dialog = p.SURFACE_SECONDARY
        card_bg = p.SURFACE_PRIMARY

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_dialog};
                font-family: {APP_FONT_STACK};
            }}
            QTableWidget {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
                gridline-color: {border_color};
                font-size: 13px;
                color: {p.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {p.SURFACE_TERTIARY};
                color: {p.TEXT_PRIMARY};
                font-weight: 700;
                font-size: 12px;
                padding: 6px;
                border: 1px solid {border_color};
            }}
            QFrame#Card {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
        """)

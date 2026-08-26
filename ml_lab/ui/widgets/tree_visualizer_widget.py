"""
ml_lab/ui/widgets/tree_visualizer_widget.py — Trực quan hóa cấu trúc Cây Quyết Định (Tree Graph).

Vẽ sơ đồ phân nhánh nhị phân của Decision Tree với các câu hỏi kiểm tra ngưỡng,
chỉ số Gini Impurity, số lượng mẫu và lớp dự đoán tại từng node.
"""

from __future__ import annotations

from typing import Any, Sequence
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QScrollArea, QWidget


class TreeVisualizerWidget(QWidget):
    """
    Widget vẽ sơ đồ cấu trúc cây quyết định.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 380)
        self._tree_model: Any = None
        self._feature_names: list[str] = []
        self._class_names: list[str] = []

    def set_tree_model(
        self, tree_model: Any, feature_names: Sequence[str], class_names: Sequence[str]
    ) -> None:
        self._tree_model = tree_model
        self._feature_names = list(feature_names)
        self._class_names = list(class_names)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))

            if self._tree_model is None or not hasattr(self._tree_model, "tree_"):
                self._draw_empty_state(painter, w, h)
                return

            tree = self._tree_model.tree_
            max_depth = self._tree_model.max_depth or 4

            node_positions: dict[int, QPointF] = {}

            # Tính tọa độ cho các node
            def compute_positions(node_id: int, depth: int, left_bound: float, right_bound: float) -> None:
                x = (left_bound + right_bound) / 2.0
                y = 40 + depth * 75.0
                node_positions[node_id] = QPointF(x, y)

                left = tree.children_left[node_id]
                right = tree.children_right[node_id]

                if left != -1:
                    compute_positions(left, depth + 1, left_bound, x)
                if right != -1:
                    compute_positions(right, depth + 1, x, right_bound)

            compute_positions(0, 0, 20.0, float(w - 20))

            # 1. Vẽ các đường nối cạnh (Branches)
            painter.setPen(QPen(QColor(180, 185, 195), 1.5))
            for node_id, pos in node_positions.items():
                left = tree.children_left[node_id]
                right = tree.children_right[node_id]

                if left != -1 and left in node_positions:
                    child_pos = node_positions[left]
                    painter.drawLine(pos, child_pos)
                    # Label "True"
                    mid_x, mid_y = (pos.x() + child_pos.x()) / 2.0, (pos.y() + child_pos.y()) / 2.0
                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.setPen(QColor(52, 199, 89))
                    painter.drawText(int(mid_x - 14), int(mid_y), "True")
                    painter.setPen(QPen(QColor(180, 185, 195), 1.5))

                if right != -1 and right in node_positions:
                    child_pos = node_positions[right]
                    painter.drawLine(pos, child_pos)
                    # Label "False"
                    mid_x, mid_y = (pos.x() + child_pos.x()) / 2.0, (pos.y() + child_pos.y()) / 2.0
                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.setPen(QColor(255, 59, 48))
                    painter.drawText(int(mid_x + 4), int(mid_y), "False")
                    painter.setPen(QPen(QColor(180, 185, 195), 1.5))

            # 2. Vẽ các hộp Node
            node_w = 110.0
            node_h = 46.0

            for node_id, pos in node_positions.items():
                left = tree.children_left[node_id]
                right = tree.children_right[node_id]
                is_leaf = (left == -1 and right == -1)

                rect = QRectF(pos.x() - node_w / 2.0, pos.y() - node_h / 2.0, node_w, node_h)

                if is_leaf:
                    cls_idx = int(np.argmax(tree.value[node_id][0]))
                    cls_name = self._class_names[cls_idx] if cls_idx < len(self._class_names) else f"C{cls_idx}"
                    col = self._get_class_color(cls_idx)

                    painter.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 35)))
                    painter.setPen(QPen(col, 2))
                    painter.drawRoundedRect(rect, 6, 6)

                    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    painter.setPen(col)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"🏷️ {cls_name}\n({int(tree.n_node_samples[node_id])} mẫu)")
                else:
                    feat_idx = tree.feature[node_id]
                    feat_name = self._feature_names[feat_idx] if feat_idx < len(self._feature_names) else f"f_{feat_idx}"
                    thresh = tree.threshold[node_id]

                    painter.setBrush(QBrush(QColor(248, 249, 250)))
                    painter.setPen(QPen(QColor(0, 122, 255), 1.5))
                    painter.drawRoundedRect(rect, 6, 6)

                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.setPen(QColor(30, 30, 40))
                    text = f"{feat_name}\n≤ {thresh:.2f} (n={tree.n_node_samples[node_id]})"
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        finally:
            painter.end()

    def _get_class_color(self, idx: int) -> QColor:
        palette = [
            QColor(0, 122, 255),
            QColor(255, 59, 48),
            QColor(52, 199, 89),
            QColor(255, 149, 0),
            QColor(88, 86, 214),
        ]
        return palette[idx % len(palette)]

    def _draw_empty_state(self, painter: QPainter, w: int, h: int) -> None:
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(100, 110, 122))
        painter.drawText(
            QRectF(0, 0, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "Chưa có mô hình Cây Quyết Định.\nHãy chọn Decision Tree ở Tab Huấn Luyện để xem sơ đồ cây.",
        )

"""
ui/page_primitive_collect.py — Trang thu thập cử chỉ nguyên thủy (Primitives).

Tạo dữ liệu huấn luyện cho mô hình Encoder, đánh giá chất lượng mẫu thu thập
và quản lý các nhóm cử chỉ cơ bản theo danh mục.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                             QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from logic.locale_manager import locale_manager
from logic.primitive_i18n import get_primitive_catalog
from logic.theme_manager import theme_manager
from ui.component_factory import make_button, make_hint, make_section_label
from ui.i18n_bridge import tr_ui
from ui.layout_utils import clear_layout
from ui.modern_layout import (MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD,
                              SPACING_SM)
from ui.tokens import (PLOT_AX_COLOR, PLOT_AY_COLOR, PLOT_AZ_COLOR,
                       RIGHT_MAX_W, RIGHT_MIN_W)


class PagePrimitiveCollect(QWidget):
    """
    Trang thu thập và quản lý mẫu cử chỉ gốc.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_start_collection = pyqtSignal(str, str)
    sig_stop_collection = pyqtSignal()
    sig_capture_collection = pyqtSignal(str, str)
    sig_train_encoder_requested = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.store = data_store
        self._selected_gesture = None
        self._selected_group = None
        self._collecting = False
        self._capture_ready = False
        self._catalog = get_primitive_catalog(locale_manager.current_language)
        self._stats = {name: 0 for name in self._catalog}
        self._card_widgets = {}

        self._init_ui()
        self._setup_plot()
        self._init_signals()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện trang thu thập mẫu gốc."""
        layout = QVBoxLayout(self)
        # Bỏ padding-bottom cứng để nội dung được bung hết cỡ
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_LG)

        content = QHBoxLayout()
        content.setSpacing(SPACING_LG)
        content.addWidget(self._build_monitor_column(), stretch=3)
        content.addWidget(self._build_catalog_column(), stretch=2)

        layout.addLayout(content)
        self.refresh_styles()

    def _init_signals(self) -> None:
        """Kết nối các signal UI."""
        self.btn_start_collect.clicked.connect(self._on_start_clicked)
        self.btn_stop_collect.clicked.connect(self._on_stop_clicked)
        self.btn_capture_collect.clicked.connect(self._on_capture_clicked)

    def _load_data(self) -> None:
        """Nạp trạng thái dữ liệu ban đầu."""
        if hasattr(self.store, "get_primitive_collection_stats"):
            stats = self.store.get_primitive_collection_stats()
        else:
            stats = {}
        self.update_collection_stats(stats)

    def showEvent(self, event) -> None:
        """Refresh primitive stats every time this page becomes visible.

        This ensures samples recorded via the regular Record page
        (and any other path) are reflected without requiring a
        save/delete event to trigger the signal.
        """
        super().showEvent(event)
        if hasattr(self.store, "sig_primitive_stats_updated"):
            if hasattr(self.store, "refresh_primitive_stats"):
                self.store.refresh_primitive_stats()

    # ── Public methods ──────────────────────────

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ và làm mới catalog cử chỉ."""
        self._catalog = get_primitive_catalog(locale_manager.current_language)
        self._rebuild_cards()
        self._sec_preview.setText(tr_ui("primitive_signal_preview"))
        if hasattr(self, '_sec_training'):
            self._sec_training.setText("ENCODER TRAINING")

    def refresh_styles(self) -> None:
        """Làm mới style theo theme hiện tại."""
        p = theme_manager.get_palette()
        self.preview_plot.setBackground("transparent")
        self.preview_plot.getAxis("left").setPen(p.TEXT_TERTIARY)
        self._rebuild_cards()

    def update_signal_preview(self, snapshot: list) -> None:
        """Vẽ lại đồ thị sensor thời gian thực."""
        if not snapshot:
            self.preview_stack.setCurrentIndex(0)
            return
        self.preview_stack.setCurrentIndex(1)
        arr = np.asarray(snapshot, dtype=np.float32)
        if arr.ndim == 2 and arr.shape[1] >= 6:
            self.curve_ax.setData(arr[:, 0])
            self.curve_ay.setData(arr[:, 1])
            self.curve_az.setData(arr[:, 2])

    def update_collection_stats(self, stats: dict) -> None:
        """Cập nhật tiến độ thu thập cho từng cử chỉ."""
        self._stats = stats  # Lưu lại để dùng khi rebuild UI
        gestures_ready = 0
        for name, widgets in self._card_widgets.items():
            count = int(stats.get(name, 0))
            int(self._catalog[name]["target_samples"])
            widgets["progress"].setValue(count)
            if count >= 100:
                gestures_ready += 1
            self._update_group_buttons(name, count, widgets["groups"])
            
        if hasattr(self, 'btn_train_encoder'):
            self.btn_train_encoder.setEnabled(gestures_ready >= 6)

    def _update_group_buttons(self, gesture_name: str, total_count: int, buttons: dict) -> None:
        """Cập nhật nhãn và style cho các nút bấm nhóm cử chỉ."""
        group_counts = self._compute_group_counts(gesture_name, total_count)
        
        # Check if the new prefix system is used for this gesture
        has_specific_groups = False
        if hasattr(self, '_stats'):
            has_specific_groups = any(k.startswith(f"{gesture_name}::") for k in self._stats)
            
        for g_name, btn in buttons.items():
            target = int(self._catalog[gesture_name]["groups"][g_name]["count"])
            
            if has_specific_groups:
                current = int(self._stats.get(f"{gesture_name}::{g_name}", 0))
            else:
                current = int(group_counts.get(g_name, 0))
                
            display_name = self._get_group_display_name(g_name)
            btn.setText(f"{display_name}: {current}/{target}")

            if current >= target:
                btn.setProperty("status", "success")
                btn.setProperty("type", "base")
            elif gesture_name == self._selected_gesture and g_name == self._selected_group:
                btn.setProperty("type", "primary")
                btn.setProperty("status", "")
            else:
                btn.setProperty("type", "base")
                btn.setProperty("status", "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _compute_group_counts(self, gesture_name: str, total_count: int) -> dict[str, int]:
        """Tính toán số lượng mẫu cho từng nhóm dựa trên tổng số."""
        result = {}
        remaining = int(total_count)
        for g_name, info in self._catalog[gesture_name]["groups"].items():
            target = int(info["count"])
            current = max(0, min(target, remaining))
            result[g_name] = current
            remaining -= current
        return result

    def _get_group_display_name(self, g_name: str) -> str:
        lang = locale_manager.current_language
        mapping = {
            "A_standard": "A (Chuẩn)" if lang == "vi" else "A (Standard)",
            "B_speed": "B (Tốc độ)" if lang == "vi" else "B (Speed)",
            "C_variant": "C (Biến thể)" if lang == "vi" else "C (Variant)",
            "A_still": "A (Đứng yên)" if lang == "vi" else "A (Still)",
            "B_small_move": "B (Cử động nhẹ)" if lang == "vi" else "B (Small Move)",
            "C_transition": "C (Chuyển tiếp)" if lang == "vi" else "C (Transition)"
        }
        if g_name in mapping:
            return mapping[g_name]
        parts = g_name.split("_", 1)
        return f"{parts[0]} ({parts[1].title()})" if len(parts) > 1 else g_name

    def on_encoder_training_status(self, message: str) -> None:
        if hasattr(self, 'lbl_train_status'):
            self.lbl_train_status.setText(message)
            
    def on_encoder_training_progress(self, value: int) -> None:
        if hasattr(self, 'train_progress'):
            self.train_progress.setValue(value)
            
    def on_encoder_training_finished(self, success: bool, message: str) -> None:
        if success:
            self.lbl_train_status.setText("Training completed.")
            # Parse the summary string for metrics
            # Expected format: "... distance_ratio=1.23, fewshot5=0.85, fewshot10=0.90, fewshot20=0.92 ..."
            parts = message.split(',')
            for part in parts:
                if 'distance_ratio=' in part:
                    self.lbl_distance_ratio.setText(f"Distance Ratio: {part.split('=')[1].strip()}")
                elif 'fewshot5=' in part:
                    self.lbl_fewshot_5.setText(f"Few-shot 5-sample: {part.split('=')[1].strip()}")
                elif 'fewshot10=' in part:
                    self.lbl_fewshot_10.setText(f"Few-shot 10-sample: {part.split('=')[1].strip()}")
        else:
            self.lbl_train_status.setText(f"Error: {message}")

    # ── Private methods ─────────────────────────

    def _build_monitor_column(self) -> QWidget:
        """Cột bên trái hiển thị đồ thị và chất lượng."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setSpacing(SPACING_LG)

        from ui.component_factory import make_card

        # 1. Preview
        card_p, lay_p = make_card(margins=(20, 20, 20, 20), spacing=SPACING_MD)
        self._sec_preview = make_section_label(tr_ui("primitive_signal_preview"))
        self.preview_plot = pg.PlotWidget()
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self._make_empty_state_widget())
        self.preview_stack.addWidget(self.preview_plot)
        lay_p.addWidget(self._sec_preview)
        lay_p.addWidget(self.preview_stack)
        lay.addWidget(card_p, stretch=3)

        # 2. Encoder Training
        card_t, lay_t = make_card(margins=(20, 20, 20, 20), spacing=SPACING_MD)
        self._sec_training = make_section_label("ENCODER TRAINING")
        
        self.btn_train_encoder = make_button("TRAIN ENCODER", "primary")
        self.btn_train_encoder.setEnabled(False)
        self.btn_train_encoder.clicked.connect(self.sig_train_encoder_requested.emit)
        
        self.train_progress = QProgressBar()
        self.train_progress.setRange(0, 100)
        self.train_progress.setValue(0)
        self.lbl_train_status = QLabel("Ready to train")
        
        self.lbl_distance_ratio = QLabel("Distance Ratio: --")
        self.lbl_fewshot_5 = QLabel("Few-shot 5-sample: --")
        self.lbl_fewshot_10 = QLabel("Few-shot 10-sample: --")
        
        lay_t.addWidget(self._sec_training)
        lay_t.addWidget(self.btn_train_encoder)
        lay_t.addWidget(self.train_progress)
        lay_t.addWidget(self.lbl_train_status)
        lay_t.addWidget(self.lbl_distance_ratio)
        lay_t.addWidget(self.lbl_fewshot_5)
        lay_t.addWidget(self.lbl_fewshot_10)
        lay.addWidget(card_t, stretch=2)

        return col

    def _build_catalog_column(self) -> QWidget:
        """Cột bên phải chứa danh mục cử chỉ và điều khiển."""
        col = QWidget()
        col.setMinimumWidth(RIGHT_MIN_W)
        col.setMaximumWidth(RIGHT_MAX_W)
        lay = QVBoxLayout(col)
        lay.setSpacing(SPACING_MD)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_content.setObjectName("StemContentHost")
        self.cards_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        lay.addWidget(scroll, stretch=1)

        # Sắp xếp nút điều khiển theo chiều dọc để tránh mất chữ
        actions = QVBoxLayout()
        actions.setSpacing(SPACING_MD)

        row1 = QHBoxLayout()
        self.btn_start_collect = make_button(tr_ui("record_btn_start"), "start")
        self.btn_stop_collect = make_button(tr_ui("record_btn_stop"), "stop")
        row1.addWidget(self.btn_start_collect)
        row1.addWidget(self.btn_stop_collect)

        self.btn_capture_collect = make_button(tr_ui("primitive_btn_capture"), "snip")

        actions.addLayout(row1)
        actions.addWidget(self.btn_capture_collect)
        lay.addLayout(actions)

        self.lbl_instruction = make_hint(tr_ui("primitive_flow_hint"))
        lay.addWidget(self.lbl_instruction)
        return col

    def _setup_plot(self) -> None:
        """Cấu hình chi tiết đồ thị pyqtgraph."""
        self.preview_plot.showGrid(x=True, y=True, alpha=0.1)
        self.curve_ax = self.preview_plot.plot(pen=pg.mkPen(PLOT_AX_COLOR, width=2))
        self.curve_ay = self.preview_plot.plot(pen=pg.mkPen(PLOT_AY_COLOR, width=2))
        self.curve_az = self.preview_plot.plot(pen=pg.mkPen(PLOT_AZ_COLOR, width=2))

    def _rebuild_cards(self) -> None:
        """Xây dựng lại các thẻ card cử chỉ."""
        clear_layout(self.cards_layout)
        self._card_widgets.clear()
        for name, info in self._catalog.items():
            card = self._create_gesture_card(name, info)
            self.cards_layout.addWidget(card)
        self.cards_layout.addStretch()
        # Áp dụng lại số liệu đếm
        if hasattr(self, '_stats'):
            self.update_collection_stats(self._stats)

    def _make_empty_state_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setMinimumHeight(220)
        icon = QLabel("📊")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setProperty("type", "empty_state_icon")
        text = QLabel("No data to evaluate yet")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setProperty("type", "empty_state_text")
        layout.addWidget(icon)
        layout.addWidget(text)
        return widget

    def _create_gesture_card(self, name: str, info: dict) -> QFrame:
        """Tạo một thẻ cử chỉ đơn lẻ."""
        card = QFrame()
        card.setProperty("type", "statistics_card")
        lay = QVBoxLayout(card)

        title = QLabel(name)
        title.setProperty("type", "gesture_card_title")
        prog = QProgressBar()
        prog.setRange(0, int(info["target_samples"]))

        lay.addWidget(title)
        lay.addWidget(QLabel(info["description"]))
        lay.addWidget(prog)

        group_btns = {}
        row = QHBoxLayout()
        for g_name in info["groups"]:
            display_name = self._get_group_display_name(g_name)
            btn = make_button(display_name, "base", height=32)
            btn.setToolTip(info["groups"][g_name].get("instruction", ""))
            btn.clicked.connect(lambda _b, g=name, gn=g_name: self._on_group_selected(g, gn))
            row.addWidget(btn)
            group_btns[g_name] = btn
        lay.addLayout(row)

        self._card_widgets[name] = {"progress": prog, "groups": group_btns}
        return card

    # ── Slots ───────────────────────────────────

    def _on_start_clicked(self) -> None:
        if self._selected_gesture:
            self.sig_start_collection.emit(self._selected_gesture, self._selected_group)

    def _on_stop_clicked(self) -> None:
        self.sig_stop_collection.emit()

    def _on_capture_clicked(self) -> None:
        if self._selected_gesture:
            self.sig_capture_collection.emit(self._selected_gesture, self._selected_group)

    def _on_group_selected(self, gesture: str, group: str) -> None:
        """Xử lý khi người dùng chọn một nhóm cử chỉ."""
        if self._collecting:
            return
        self._selected_gesture = gesture
        self._selected_group = group
        
        # Lấy instruction từ catalog
        instruction_text = self._catalog[gesture]["groups"][group].get("instruction", "")
        display_name = self._get_group_display_name(group)
        
        self.lbl_instruction.setText(f"Đang chọn: {gesture} ➜ {display_name}\n\nHướng dẫn: {instruction_text}")
        self.btn_start_collect.setEnabled(True)
        self.refresh_styles()

    def set_collection_state(self, collecting: bool) -> None:
        self._collecting = collecting
        self.btn_start_collect.setEnabled(not collecting and self._selected_gesture is not None)
        self.btn_stop_collect.setEnabled(collecting)
        
    def update_collection_progress(self, gesture_name: str, count: int) -> None:
        # Check if we hit 30-sample marks or 50-sample group completions.
        # This will be handled by Handler, so we just update UI.
        pass


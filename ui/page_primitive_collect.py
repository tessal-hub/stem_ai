"""
ui/page_primitive_collect.py — Trang thu thập cử chỉ nguyên thủy (Primitives).

Tạo dữ liệu huấn luyện cho mô hình Encoder, đánh giá chất lượng mẫu thu thập
và quản lý các nhóm cử chỉ cơ bản theo danh mục.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                             QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QComboBox)
from PyQt6.QtGui import QShortcut, QKeySequence

from logic.locale_manager import locale_manager
from logic.primitive_i18n import get_primitive_catalog
from logic.theme_manager import theme_manager
from ui.component_factory import make_button, make_hint, make_section_label
from ui.i18n_bridge import tr_ui
from ui.layout_utils import clear_layout
from ui.modern_layout import (MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD,
                              SPACING_SM)
from ui.tokens import (PLOT_AX_COLOR, PLOT_AY_COLOR, PLOT_AZ_COLOR,
                       PLOT_GX_COLOR, PLOT_GY_COLOR, PLOT_GZ_COLOR,
                       RIGHT_MAX_W, RIGHT_MIN_W)


class PagePrimitiveCollect(QWidget):
    """
    Trang thu thập và quản lý mẫu cử chỉ gốc.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_start_collection = pyqtSignal(str, str)
    sig_stop_collection = pyqtSignal()
    sig_capture_collection = pyqtSignal(str, str)
    sig_train_encoder_requested = pyqtSignal(str)

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

        # High-performance timer-based polling for plots (avoids UI choking at 100Hz)
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._render_plots)
        if self.isVisible():
            self._plot_timer.start(40)  # 25 Hz

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

        self.shortcut_start = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_start.activated.connect(self._trigger_start)

        self.shortcut_stop = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_stop.activated.connect(self._trigger_stop)

        self.shortcut_capture = QShortcut(QKeySequence("Ctrl+X"), self)
        self.shortcut_capture.activated.connect(self._trigger_capture)

    def _trigger_start(self) -> None:
        if self.btn_start_collect.isEnabled():
            self.btn_start_collect.click()
            
    def _trigger_stop(self) -> None:
        if self.btn_stop_collect.isEnabled():
            self.btn_stop_collect.click()

    def _trigger_capture(self) -> None:
        if self.btn_capture_collect.isEnabled():
            self.btn_capture_collect.click()

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
        self.preview_plot_accel.setBackground("transparent")
        self.preview_plot_gyro.setBackground("transparent")
        self.preview_plot_accel.getAxis("left").setPen(p.TEXT_TERTIARY)
        self.preview_plot_gyro.getAxis("left").setPen(p.TEXT_TERTIARY)
        if not self._card_widgets:
            self._rebuild_cards()
        elif hasattr(self, '_stats'):
            self.update_collection_stats(self._stats)

    def update_signal_preview(self, snapshot: list) -> None:
        """Giờ là hàm dummy để tương thích ngược. Vẽ chính được thực hiện qua QTimer."""
        pass

    def _render_plots(self) -> None:
        """Vẽ lại đồ thị sensor thời gian thực định kỳ từ live buffer."""
        if not self.isVisible():
            return
        arr = self.store.get_live_buffer_numpy()
        if arr.size == 0:
            if self.preview_stack.currentIndex() != 0:
                self.preview_stack.setCurrentIndex(0)
            return
        if self.preview_stack.currentIndex() != 1:
            self.preview_stack.setCurrentIndex(1)
        try:
            if arr.ndim == 2 and arr.shape[1] >= 6:
                self.curve_ax.setData(arr[:, 0])
                self.curve_ay.setData(arr[:, 1])
                self.curve_az.setData(arr[:, 2])
                self.curve_gx.setData(arr[:, 3])
                self.curve_gy.setData(arr[:, 4])
                self.curve_gz.setData(arr[:, 5])
        except Exception:
            pass

    def update_collection_stats(self, stats: dict) -> None:
        """Cập nhật tiến độ thu thập cho từng cử chỉ."""
        self._stats = stats
        gestures_ready = 0
        for name, widgets in self._card_widgets.items():
            count = int(stats.get(name, 0))
            target = int(self._catalog[name]["target_samples"])
            prog = widgets["progress"]
            prog.setMaximum(target)           # fixed at 150 — bar never overflows
            if prog.value() != min(count, target):
                prog.setValue(min(count, target)) # cap visual fill at 100%
            fmt = f"{count}/{target}"
            if prog.format() != fmt:
                prog.setFormat(fmt)  # text shows real count e.g. "187/150"
            prog.setTextVisible(True)
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
            new_text = f"{display_name}: {current}/{target}"
            if btn.text() != new_text:
                btn.setText(new_text)

            if gesture_name == self._selected_gesture and g_name == self._selected_group:
                new_type, new_status = "primary", ""
            elif current >= target:
                new_type, new_status = "base", "success"
            else:
                new_type, new_status = "base", ""

            if btn.property("type") != new_type or btn.property("status") != new_status:
                btn.setProperty("type", new_type)
                btn.setProperty("status", new_status)
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
        if hasattr(self, 'console'):
            self.console.append_line(message)
            
    def on_encoder_training_progress(self, value: int) -> None:
        if hasattr(self, 'console'):
            self.console.append_line(f"[Progress] {value}%")
            
    def on_encoder_training_finished(self, success: bool, message: str) -> None:
        if hasattr(self, 'console'):
            if success:
                self.console.append_line(">> Training completed successfully.")
                self.console.append_line(f">> Summary: {message}")
            else:
                self.console.append_line(f">> Error: {message}")

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
        
        # Double plots (Accel & Gyro separate) to avoid scale issues
        self.preview_plot_accel = pg.PlotWidget()
        self.preview_plot_gyro = pg.PlotWidget()
        self.plots_container = QWidget()
        plots_lay = QVBoxLayout(self.plots_container)
        plots_lay.setContentsMargins(0, 0, 0, 0)
        plots_lay.setSpacing(6)
        plots_lay.addWidget(self.preview_plot_accel)
        plots_lay.addWidget(self.preview_plot_gyro)
        
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self._make_empty_state_widget())
        self.preview_stack.addWidget(self.plots_container)
        lay_p.addWidget(self._sec_preview)
        lay_p.addWidget(self.preview_stack)
        lay.addWidget(card_p, stretch=3)

        # 2. Encoder Training
        card_t, lay_t = make_card(margins=(20, 20, 20, 20), spacing=SPACING_MD)
        self._sec_training = make_section_label("ENCODER TRAINING")
        
        self.cbo_preset = QComboBox()
        self.cbo_preset.addItems(["original", "medium", "aggressive"])
        self.cbo_preset.setToolTip("Select model architecture preset")
        
        self.btn_train_encoder = make_button("TRAIN ENCODER", "primary")
        self.btn_train_encoder.setEnabled(False)
        self.btn_train_encoder.clicked.connect(lambda _: self.sig_train_encoder_requested.emit(self.cbo_preset.currentText()))
        
        from ui.terminal_widget import TerminalWidget
        self.console = TerminalWidget(max_lines=1000, read_only=True)
        self.console.setMinimumHeight(150)
        self.console.setPlainText(">> ENCODER TRAINING TERMINAL INITIALIZED...\n>> WAITING FOR TRAINING START...")
        
        row_t = QHBoxLayout()
        row_t.addWidget(self.cbo_preset)
        row_t.addWidget(self.btn_train_encoder)
        
        lay_t.addWidget(self._sec_training)
        lay_t.addLayout(row_t)
        lay_t.addWidget(self.console)
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
        """Cấu hình chi tiết đồ thị pyqtgraph — 6 kênh IMU tách biệt."""
        # Accelerometer Plot (ax, ay, az)
        self.preview_plot_accel.showGrid(x=True, y=True, alpha=0.1)
        self.curve_ax = self.preview_plot_accel.plot(pen=pg.mkPen(PLOT_AX_COLOR, width=2))
        self.curve_ay = self.preview_plot_accel.plot(pen=pg.mkPen(PLOT_AY_COLOR, width=2))
        self.curve_az = self.preview_plot_accel.plot(pen=pg.mkPen(PLOT_AZ_COLOR, width=2))
        
        # Gyroscope Plot (gx, gy, gz)
        self.preview_plot_gyro.showGrid(x=True, y=True, alpha=0.1)
        self.curve_gx = self.preview_plot_gyro.plot(pen=pg.mkPen(PLOT_GX_COLOR, width=2))
        self.curve_gy = self.preview_plot_gyro.plot(pen=pg.mkPen(PLOT_GY_COLOR, width=2))
        self.curve_gz = self.preview_plot_gyro.plot(pen=pg.mkPen(PLOT_GZ_COLOR, width=2))

        for c in [self.curve_ax, self.curve_ay, self.curve_az, self.curve_gx, self.curve_gy, self.curve_gz]:
            c.setSkipFiniteCheck(True)

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
        prog.setValue(0)
        prog.setFormat(f"0/{int(info['target_samples'])}")
        prog.setTextVisible(True)

        lay.addWidget(title)
        lay.addWidget(QLabel(info["description"]))
        lay.addWidget(prog)

        group_btns = {}
        row = QVBoxLayout()
        row.setSpacing(4)
        for g_name in info["groups"]:
            display_name = self._get_group_display_name(g_name)
            btn = make_button(display_name, "base", height=30)
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

        self.lbl_instruction.setText(
            f"Đang chọn: {gesture} ➜ {display_name}\n\nHướng dẫn: {instruction_text}"
        )
        self.btn_start_collect.setEnabled(True)

        # Refresh all button styles in-place to highlight the new selection and
        # clear any previous ones, without rebuilding widgets (which resets scroll).
        for g_name, widgets in self._card_widgets.items():
            g_count = int(self._stats.get(g_name, 0))
            self._update_group_buttons(g_name, g_count, widgets["groups"])

    def set_collection_state(self, collecting: bool) -> None:
        self._collecting = collecting
        self.btn_start_collect.setEnabled(not collecting and self._selected_gesture is not None)
        self.btn_stop_collect.setEnabled(collecting)

    def set_capture_ready(self, ready: bool) -> None:
        self._capture_ready = ready
        self.btn_capture_collect.setEnabled(ready)

    def on_capture_saved(self, success: bool, message: str) -> None:
        if success:
            self.set_capture_ready(False)
            self.lbl_instruction.setText(f"Đã lưu thành công: {message}")
        else:
            self.lbl_instruction.setText(f"Lỗi khi lưu: {message}")

    def update_collection_progress(self, gesture_name: str, count: int) -> None:
        # Check if we hit 30-sample marks or 50-sample group completions.
        # This will be handled by Handler, so we just update UI.
        pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "_plot_timer") and not self._plot_timer.isActive():
            self._plot_timer.start(40)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if hasattr(self, "_plot_timer") and self._plot_timer.isActive():
            self._plot_timer.stop()


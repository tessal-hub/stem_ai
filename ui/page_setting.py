"""
ui/page_setting.py — Trang cài đặt và cấu hình hệ thống.

Cho phép điều chỉnh các tham số phần cứng (IMU), thuật toán nhận dạng (ML),
giao diện (Theme/Ngôn ngữ) và nạp firmware cho đũa phép.
Tối ưu hóa giao diện Dashboard 2 cột mượt mà:
  - Cột trái: Cấu hình chung, IMU, Metrics phần cứng/mô hình, Chất lượng Dataset.
  - Cột phải: Quản lý Firmware & Console log terminal.
Hỗ trợ cuộn linh hoạt với QScrollArea.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                             QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QProgressBar, QPushButton, QScrollArea,
                             QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from logic.locale_manager import locale_manager
from logic.ui_i18n import normalize_ui_language, tr
from ui.asset_utils import resolve_asset_path
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from ui.terminal_widget import TerminalWidget
from ui.tokens import SETTINGS_ACCENT, SPACE_32


class PageSetting(QWidget):
    """
    Trang cài đặt tập trung các thông số vận hành của ứng dụng theo bố cục 2 cột.
    """

    # ── Signal xuất bản ───────────────────────────
    sig_settings_saved = pyqtSignal(dict)
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()
    sig_scan_primitive_quality = pyqtSignal()
    sig_stop_primitive_scan = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._i18n_text: list[tuple[QWidget, str, str]] = []
        self._lang = "en"
        self._last_saved: dict[str, Any] = {}

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._hide_status_message)

        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục Dashboard 2 Cột với QScrollArea bảo vệ hiển thị."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Scroll Area bảo đảm giao diện không bị cắt ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("MainBox")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # ── Dashboard 2 Cột ──
        columns = QHBoxLayout()
        columns.setSpacing(18)

        self._left_col = QVBoxLayout()
        self._left_col.setSpacing(16)

        self._right_col = QVBoxLayout()
        self._right_col.setSpacing(16)

        # Khởi tạo các khối chức năng
        self._sec_general = self._build_general_settings()
        self._sec_hardware = self._build_hardware_column()
        self._sec_metrics = self._build_hardware_info_card()
        self.quality_card_widget = self._build_quality_card()
        self._sec_firmware = self._build_firmware_section()

        self._rebalance_layout(True)

        columns.addLayout(self._left_col, stretch=11)
        columns.addLayout(self._right_col, stretch=11)

        content_layout.addLayout(columns, stretch=1)
        scroll.setWidget(scroll_content)

        outer.addWidget(scroll, stretch=1)
        outer.addWidget(self._build_control_bar())

    # ── Section Builders ────────────────────────

    def _build_general_settings(self) -> QWidget:
        """Khối Cấu hình Hệ thống & Giao diện."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self._make_section_label_i18n("section_appearance"))

        card, c_lay = self._make_card(margins=(20, 18, 20, 18), spacing=14)

        self.combo_ui_language = self._make_combo([])
        self.combo_ui_theme = self._make_combo(["Light Mode", "Dark Mode"])
        self.chk_show_primitives = QCheckBox()
        self.chk_show_primitives.setToolTip("Bật giao diện đầy đủ (Console, UART Terminal, Primitives)" if self._lang == "vi" else "Enable full interface (Console, UART Terminal, Primitives)")

        form = self._make_form_layout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)

        # Language
        self._add_i18n_form_row(form, "label_ui_language", self.combo_ui_language)

        # Theme
        lbl_theme = QLabel("Theme:")
        lbl_theme.setProperty("type", "settings_form_label")
        form.addRow(lbl_theme, self.combo_ui_theme)

        folder_icon = QIcon(resolve_asset_path("assets/icon/cooliocns SVG/File/Folder_Open.svg"))

        # Dataset Directory Input Group
        self.txt_dataset_dir = QLineEdit()
        self.txt_dataset_dir.setPlaceholderText("Select dataset directory...")
        self.txt_dataset_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_browse_dataset = QPushButton(" 🔍 Browse")
        self.btn_browse_dataset.setIcon(folder_icon)
        self.btn_browse_dataset.setIconSize(QSize(14, 14))
        self.btn_browse_dataset.setProperty("type", "outline")
        self.btn_browse_dataset.setFixedHeight(34)

        dataset_container = QWidget()
        dataset_row = QHBoxLayout(dataset_container)
        dataset_row.setContentsMargins(0, 0, 0, 0)
        dataset_row.setSpacing(8)
        dataset_row.addWidget(self.txt_dataset_dir, stretch=1)
        dataset_row.addWidget(self.btn_browse_dataset)
        self._add_i18n_form_row(form, "label_dataset_dir", dataset_container)

        # Model File Input Group
        self.txt_model_path = QLineEdit()
        self.txt_model_path.setPlaceholderText("Select TFLite model file (.tflite)...")
        self.txt_model_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_browse_model = QPushButton(" 🔍 Browse")
        self.btn_browse_model.setIcon(folder_icon)
        self.btn_browse_model.setIconSize(QSize(14, 14))
        self.btn_browse_model.setProperty("type", "outline")
        self.btn_browse_model.setFixedHeight(34)

        model_container = QWidget()
        model_row = QHBoxLayout(model_container)
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(8)
        model_row.addWidget(self.txt_model_path, stretch=1)
        model_row.addWidget(self.btn_browse_model)
        self._add_i18n_form_row(form, "label_model_path", model_container)

        # Advanced Mode Checkbox
        self.lbl_show_primitives = QLabel("Chế độ nâng cao" if self._lang == "vi" else "Advanced Mode")
        self.lbl_show_primitives.setProperty("type", "settings_form_label")
        form.addRow(self.lbl_show_primitives, self.chk_show_primitives)

        c_lay.addLayout(form)
        lay.addWidget(card)
        return col

    def _build_hardware_column(self) -> QWidget:
        """Khối Cấu hình Phần cứng IMU (Sample rate, Accel/Gyro Scale)."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self._make_section_label_i18n("section_imu"))

        card, c_lay = self._make_card(margins=(20, 18, 20, 18), spacing=14)
        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g"])
        self.combo_gyro_scale = self._make_combo(["±250 dps", "±500 dps"])

        imu_row = QHBoxLayout()
        imu_row.setSpacing(16)

        # Rate
        rate_box = QVBoxLayout()
        rate_box.setSpacing(4)
        lbl_rate = QLabel(tr(self._lang, "label_sample_rate"))
        lbl_rate.setProperty("type", "settings_form_label")
        rate_box.addWidget(lbl_rate)
        rate_box.addWidget(self.combo_sample_rate)
        imu_row.addLayout(rate_box, stretch=1)

        # Accel Scale
        accel_box = QVBoxLayout()
        accel_box.setSpacing(4)
        lbl_accel = QLabel(tr(self._lang, "label_accel"))
        lbl_accel.setProperty("type", "settings_form_label")
        accel_box.addWidget(lbl_accel)
        accel_box.addWidget(self.combo_accel_scale)
        imu_row.addLayout(accel_box, stretch=1)

        # Gyro Scale
        gyro_box = QVBoxLayout()
        gyro_box.setSpacing(4)
        lbl_gyro = QLabel(tr(self._lang, "label_gyro"))
        lbl_gyro.setProperty("type", "settings_form_label")
        gyro_box.addWidget(lbl_gyro)
        gyro_box.addWidget(self.combo_gyro_scale)
        imu_row.addLayout(gyro_box, stretch=1)

        c_lay.addLayout(imu_row)
        lay.addWidget(card)
        return col

    def _build_hardware_info_card(self) -> QWidget:
        """Thông số cấu hình phần cứng MCU và chỉ số TinyML Model."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.lbl_hw_metrics_title = QLabel("CẤU HÌNH PHẦN CỨNG & MÔ HÌNH" if self._lang == "vi" else "HARDWARE & MODEL METRICS")
        self.lbl_hw_metrics_title.setProperty("type", "settings_section_label")
        self.lbl_hw_metrics_title.setProperty("status", "accent")
        lay.addWidget(self.lbl_hw_metrics_title)

        card, c_lay = self._make_card(margins=(20, 18, 20, 18), spacing=12)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        lang = self._lang
        mcu_lbl = "MCU Target:" if lang == "en" else "Vi xử lý mục tiêu:"
        mcu_val = "ESP32 / Dual-Core @ 240MHz"
        mem_lbl = "SRAM / Flash:"
        mem_val = "520 KB / 4 MB"
        fw_lbl = "TinyML Engine:" if lang == "en" else "Động cơ TinyML:"
        fw_val = "TF Lite Micro (INT8)"
        size_lbl = "Model Size:" if lang == "en" else "Kích thước mô hình:"
        gestures_lbl = "Active Gestures:" if lang == "en" else "Số cử chỉ kích hoạt:"

        def add_row(row_idx: int, label: str, value: str) -> None:
            lbl_name = QLabel(label)
            lbl_name.setProperty("type", "record_field_label")
            lbl_val = QLabel(value)
            lbl_val.setStyleSheet("font-weight: 600;")
            grid.addWidget(lbl_name, row_idx, 0)
            grid.addWidget(lbl_val, row_idx, 1)

        add_row(0, mcu_lbl, mcu_val)
        add_row(1, mem_lbl, mem_val)
        add_row(2, fw_lbl, fw_val)

        from config import APP_DATA_DIR
        tflite_path = APP_DATA_DIR / "gesture_encoder.tflite"
        size_str = "N/A"
        if tflite_path.exists():
            try:
                sz = tflite_path.stat().st_size
                size_str = f"{sz / 1024:.1f} KB"
            except OSError:
                pass
        add_row(3, size_lbl, size_str)

        classes_count = str(len(getattr(self.data_store, "spell_counts", {})))
        add_row(4, gestures_lbl, classes_count)

        c_lay.addLayout(grid)
        lay.addWidget(card)
        return col

    def _build_quality_card(self) -> QWidget:
        """Quét và Đánh giá chất lượng Tập dữ liệu Primitive."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl_quality = QLabel("PRIMITIVE DATASET QUALITY")
        lbl_quality.setProperty("type", "settings_section_label")
        lbl_quality.setProperty("status", "accent")
        lay.addWidget(lbl_quality)

        quality_card, quality_layout = self._make_card(margins=(20, 18, 20, 18), spacing=14)

        quality_btn_row = QHBoxLayout()
        quality_btn_row.setSpacing(12)

        self.btn_scan_quality = QPushButton("🔍 SCAN QUALITY")
        self.btn_scan_quality.setProperty("type", "primary")
        self.btn_scan_quality.setFixedHeight(34)
        self.btn_scan_quality.setToolTip(
            "Scan all primitive gesture folders and generate a quality report"
        )

        self.btn_stop_scan = QPushButton("■ STOP SCAN")
        self.btn_stop_scan.setEnabled(False)
        self.btn_stop_scan.setProperty("type", "stop")
        self.btn_stop_scan.setFixedHeight(34)
        self.btn_stop_scan.setToolTip("Stop the running quality scan")

        quality_btn_row.addWidget(self.btn_scan_quality, stretch=1)
        quality_btn_row.addWidget(self.btn_stop_scan, stretch=1)
        quality_layout.addLayout(quality_btn_row)

        self.quality_progress = QProgressBar()
        self.quality_progress.setRange(0, 100)
        self.quality_progress.setValue(0)
        self.quality_progress.setMinimumHeight(8)
        self.quality_progress.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        quality_layout.addWidget(self.quality_progress)
        lay.addWidget(quality_card)
        return col

    def _build_firmware_section(self) -> QWidget:
        """Trình nạp Firmware & Console theo dõi Log."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self._make_section_label_i18n("section_firmware"))

        card, c_lay = self._make_card(margins=(20, 20, 20, 20), spacing=14)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Buttons Row
        btns = QHBoxLayout()
        btns.setSpacing(12)
        self.btn_flash_collect = QPushButton("")
        self.btn_flash_collect.setProperty("type", "primary")
        self.btn_flash_collect.setFixedHeight(36)
        self._tx(self.btn_flash_collect, "btn_flash_data", "⬆ ")

        self.btn_flash_ai = QPushButton("")
        self.btn_flash_ai.setProperty("type", "primary")
        self.btn_flash_ai.setFixedHeight(36)
        self._tx(self.btn_flash_ai, "btn_flash_ai", "⬆ ")

        btns.addWidget(self.btn_flash_collect, stretch=1)
        btns.addWidget(self.btn_flash_ai, stretch=1)
        c_lay.addLayout(btns)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        c_lay.addWidget(self.progress_bar)

        # Terminal Console
        self.console_log = TerminalWidget(read_only=True)
        self.console_log.setMinimumHeight(320)
        self.console_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        c_lay.addWidget(self.console_log, stretch=1)

        lay.addWidget(card, stretch=1)
        return col

    def _build_control_bar(self) -> QWidget:
        """Thanh tác vụ lưu/hủy cấu hình đính bên dưới."""
        container = QFrame()
        container.setObjectName("CardFrame")
        container.setStyleSheet("QFrame#CardFrame { border-top: 1px solid rgba(0,0,0,0.08); border-radius: 0px; }")

        row = QHBoxLayout(container)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(14)

        self.lbl_status_msg = QLabel("")
        self.lbl_status_msg.setStyleSheet("font-weight: 500; color: #10B981;")
        self.lbl_status_msg.hide()

        self.btn_revert = QPushButton("")
        self.btn_revert.setProperty("type", "outline")
        self.btn_revert.setFixedHeight(36)
        self._tx(self.btn_revert, "btn_revert")

        self.btn_save = QPushButton("")
        self.btn_save.setProperty("type", "primary")
        self.btn_save.setFixedHeight(36)
        self._tx(self.btn_save, "btn_save")

        row.addWidget(self.lbl_status_msg)
        row.addStretch()
        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_save)
        return container

    # ── Signal Connections ───────────────────────

    def _init_signals(self) -> None:
        """Kết nối signal và slot."""
        self.btn_save.clicked.connect(self._on_btn_save_clicked)
        self.btn_revert.clicked.connect(self._on_btn_revert_clicked)
        self.btn_flash_collect.clicked.connect(self._on_btn_flash_collect_clicked)
        self.btn_flash_ai.clicked.connect(self._on_btn_flash_ai_clicked)
        self.btn_browse_dataset.clicked.connect(self._on_btn_browse_dataset_clicked)
        self.btn_browse_model.clicked.connect(self._on_btn_browse_model_clicked)
        self.combo_ui_language.currentIndexChanged.connect(self._on_ui_language_changed)
        self.combo_ui_theme.currentIndexChanged.connect(self._on_ui_theme_changed)
        self.btn_scan_quality.clicked.connect(self._on_btn_scan_quality_clicked)
        self.btn_stop_scan.clicked.connect(self._on_btn_stop_scan_clicked)
        self.chk_show_primitives.toggled.connect(self.set_advanced_mode)

    def _load_data(self) -> None:
        """Nạp dữ liệu cài đặt từ store."""
        self._last_saved = self.data_store.get_settings_snapshot()
        lang = normalize_ui_language(self._last_saved.get("ui_language"))
        self._refresh_ui_texts(lang)
        self.load_settings(self._last_saved)

    # ── Public methods ──────────────────────────

    def load_settings(self, config: dict[str, Any]) -> None:
        """Đẩy giá trị cấu hình vào các widget UI."""
        from logic.theme_manager import theme_manager
        widgets = {
            "sample_rate": self.combo_sample_rate,
            "accel_scale": self.combo_accel_scale,
            "gyro_scale": self.combo_gyro_scale,
            "dataset_dir": self.txt_dataset_dir,
            "model_path": self.txt_model_path,
            "show_primitives_menu": self.chk_show_primitives,
            "advanced_mode": self.chk_show_primitives,
        }
        for key, w in widgets.items():
            if key in config:
                w.blockSignals(True)
                if isinstance(w, QComboBox):
                    w.setCurrentText(str(config[key]))
                elif isinstance(w, QSpinBox):
                    w.setValue(int(config[key]))
                elif isinstance(w, QLineEdit):
                    w.setText(str(config[key]))
                elif isinstance(w, QCheckBox):
                    w.setChecked(bool(config[key]))
                w.blockSignals(False)

        adv = config.get("advanced_mode", config.get("show_primitives_menu", True))
        self.chk_show_primitives.setChecked(bool(adv))
        self.set_advanced_mode(bool(adv))

        self._set_combo_data(self.combo_ui_language, normalize_ui_language(config.get("ui_language")))

        current_theme = config.get("theme", theme_manager.current_theme)
        theme_idx = 1 if str(current_theme).lower() == "dark" else 0
        self.combo_ui_theme.blockSignals(True)
        self.combo_ui_theme.setCurrentIndex(theme_idx)
        self.combo_ui_theme.blockSignals(False)
        theme_manager.current_theme = current_theme

    def _rebalance_layout(self, advanced: bool) -> None:
        """Cân bằng lại vị trí các khối giữa 2 cột theo chế độ."""
        if not hasattr(self, "_left_col") or not hasattr(self, "_right_col"):
            return

        while self._left_col.count():
            self._left_col.takeAt(0)
        while self._right_col.count():
            self._right_col.takeAt(0)

        if advanced:
            # Chế độ nâng cao
            self._left_col.addWidget(self._sec_general)
            self._left_col.addWidget(self._sec_hardware)
            self._left_col.addWidget(self.quality_card_widget)
            self._left_col.addStretch()

            self._right_col.addWidget(self._sec_firmware, stretch=1)
            self._right_col.addWidget(self._sec_metrics)
        else:
            # Chế độ tiêu chuẩn (Không nâng cao) - Cân đối 2 bên (2 cards mỗi cột)
            self._left_col.addWidget(self._sec_general)
            self._left_col.addWidget(self._sec_hardware)
            self._left_col.addStretch()

            self._right_col.addWidget(self._sec_firmware)
            self._right_col.addWidget(self._sec_metrics)
            self._right_col.addStretch()

    def set_advanced_mode(self, enabled: bool) -> None:
        """Bật/tắt chế độ nâng cao (ẩn/hiện Console & Primitive Quality Scan) và tái cân bằng layout."""
        if hasattr(self, "console_log") and self.console_log:
            self.console_log.setVisible(enabled)
        if hasattr(self, "quality_card_widget") and self.quality_card_widget:
            self.quality_card_widget.setVisible(enabled)
        self._rebalance_layout(enabled)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ hiển thị toàn trang."""
        self._refresh_ui_texts(locale_manager.current_language)

    def append_console_text(self, msg: str) -> None:
        """Thêm log vào console flash."""
        if self.console_log:
            self.console_log.append_line(msg, strip_right=True)

    def update_flash_progress(self, val: int) -> None:
        """Cập nhật thanh tiến độ nạp firmware."""
        self.progress_bar.setValue(max(0, min(100, val)))

    def set_flash_buttons_enabled(self, enabled: bool) -> None:
        """Bật/tắt các nút thao tác nạp firmware."""
        self.btn_flash_collect.setEnabled(enabled)
        self.btn_flash_ai.setEnabled(enabled)

    def set_scan_running(self, running: bool) -> None:
        """Bật/tắt các nút tiến trình quét quality dataset."""
        self.btn_scan_quality.setEnabled(not running)
        self.btn_stop_scan.setEnabled(running)
        if running:
            self.quality_progress.setValue(0)

    def update_scan_progress(self, value: int) -> None:
        """Cập nhật tiến độ quét quality dataset."""
        self.quality_progress.setValue(max(0, min(100, value)))

    def show_status_message(self, text: str, is_error: bool = False, timeout_ms: int = 3000) -> None:
        """Hiển thị thông báo trạng thái tạm thời trên thanh điều khiển."""
        color = "#EF4444" if is_error else "#10B981"
        self.lbl_status_msg.setStyleSheet(f"font-weight: 600; color: {color};")
        self.lbl_status_msg.setText(text)
        self.lbl_status_msg.show()
        self._status_timer.start(timeout_ms)

    def _hide_status_message(self) -> None:
        self.lbl_status_msg.hide()

    # ── Utility Helpers ─────────────────────────

    def _tx(self, w: QWidget, key: str, prefix: str = "") -> None:
        self._i18n_text.append((w, key, prefix))

    def _make_card(self, margins: tuple[int, int, int, int] = (12, 12, 12, 12), spacing: int = 8) -> tuple[QFrame, QVBoxLayout]:
        from ui.component_factory import make_card
        return make_card(margins=margins, spacing=spacing)

    def _make_combo(self, items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(36)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return combo

    def _make_form_layout(self) -> QFormLayout:
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        return form

    def _add_i18n_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel("")
        label.setProperty("type", "settings_form_label")
        label.setMinimumWidth(120)
        label.setWordWrap(False)
        form.addRow(label, field)
        self._tx(label, key)

    def _make_section_label_i18n(self, key: str, color: str = SETTINGS_ACCENT) -> QLabel:
        lbl = QLabel("")
        lbl.setProperty("type", "settings_section_label")
        lbl.setProperty("status", "accent" if color == SETTINGS_ACCENT else "error")
        self._tx(lbl, key)
        return lbl

    def _set_combo_data(self, combo: QComboBox, data: str) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _refresh_ui_texts(self, lang: str) -> None:
        self._lang = lang
        for w, key, prefix in self._i18n_text:
            w.setText(prefix + tr(lang, key))

        if hasattr(self, "lbl_show_primitives"):
            self.lbl_show_primitives.setText("Chế độ nâng cao" if lang == "vi" else "Advanced Mode")

        if hasattr(self, "lbl_hw_metrics_title"):
            self.lbl_hw_metrics_title.setText("CẤU HÌNH PHẦN CỨNG & MÔ HÌNH" if lang == "vi" else "HARDWARE & MODEL METRICS")

        current_data = self.combo_ui_language.currentData()
        if not current_data:
            current_data = lang

        self.combo_ui_language.blockSignals(True)
        self.combo_ui_language.clear()
        self.combo_ui_language.addItem("English", "en")
        self.combo_ui_language.addItem("Tiếng Việt", "vi")

        self._set_combo_data(self.combo_ui_language, current_data)
        self.combo_ui_language.blockSignals(False)

    def _configure_accessibility(self) -> None:
        self.btn_scan_quality.setAccessibleName("Scan primitive dataset quality")
        self.btn_stop_scan.setAccessibleName("Stop quality scan")

    # ── Slots ───────────────────────────────────

    def _on_btn_save_clicked(self) -> None:
        from logic.theme_manager import theme_manager
        config = {
            "sample_rate": self.combo_sample_rate.currentText(),
            "accel_scale": self.combo_accel_scale.currentText(),
            "gyro_scale": self.combo_gyro_scale.currentText(),
            "ui_language": self.combo_ui_language.currentData(),
            "theme": theme_manager.current_theme,
            "auto_save": True,
            "dataset_dir": self.txt_dataset_dir.text().strip(),
            "model_path": self.txt_model_path.text().strip(),
            "show_primitives_menu": self.chk_show_primitives.isChecked(),
            "advanced_mode": self.chk_show_primitives.isChecked(),
        }
        self._last_saved = config
        self.sig_settings_saved.emit(config)
        self.show_status_message("✓ Settings saved successfully", is_error=False)

    def _on_btn_revert_clicked(self) -> None:
        self.load_settings(self._last_saved)
        self.show_status_message("Changes reverted", is_error=False)

    def _on_btn_flash_collect_clicked(self) -> None:
        self.sig_flash_data_firmware.emit()

    def _on_btn_flash_ai_clicked(self) -> None:
        self.sig_flash_inference_firmware.emit()

    def _on_ui_language_changed(self) -> None:
        lang = self.combo_ui_language.currentData()
        self._refresh_ui_texts(lang)
        locale_manager.current_language = lang

    def _on_ui_theme_changed(self) -> None:
        from logic.theme_manager import theme_manager
        idx = self.combo_ui_theme.currentIndex()
        theme_str = "dark" if idx == 1 else "light"
        theme_manager.current_theme = theme_str

    def _on_btn_browse_dataset_clicked(self) -> None:
        """Mở hộp thoại chọn thư mục dataset."""
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục Dataset")
        if path:
            self.txt_dataset_dir.setText(path)

    def _on_btn_browse_model_clicked(self) -> None:
        """Open file dialog to select model file (.tflite)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Model File", "", "TFLite Models (*.tflite);;All Files (*)"
        )
        if path:
            self.txt_model_path.setText(path)

    def _on_btn_scan_quality_clicked(self) -> None:
        """Bắt đầu quét chất lượng dataset primitive."""
        self.set_scan_running(True)
        self.console_log.clear()
        self.append_console_text("[INFO] Starting primitive dataset quality scan...")
        self.sig_scan_primitive_quality.emit()

    def _on_btn_stop_scan_clicked(self) -> None:
        """Dừng quét chất lượng đang chạy."""
        self.sig_stop_primitive_scan.emit()

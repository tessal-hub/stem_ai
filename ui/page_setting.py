"""
ui/page_setting.py — Trang cài đặt và cấu hình hệ thống.

Cho phép điều chỉnh các tham số phần cứng (IMU), thuật toán nhận dạng (ML),
giao diện (Theme/Ngôn ngữ) và nạp firmware cho đũa phép.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                             QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QProgressBar, QPushButton, QScrollArea,
                             QSizePolicy, QSpinBox, QVBoxLayout, QWidget)
from ui.asset_utils import resolve_asset_path

from logic.locale_manager import locale_manager
from logic.ui_i18n import normalize_ui_language, tr
from ui.confirm_dialog import confirm_destructive
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from ui.terminal_widget import TerminalWidget
from ui.tokens import DANGER, SETTINGS_ACCENT, SPACE_32, STYLE_SETTING_BTN_DANGER, STYLE_SETTING_PROGRESS


class PageSetting(QWidget):
    """
    Trang cài đặt tập trung các thông số vận hành của ứng dụng.
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

        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục trang cài đặt chuyên nghiệp dạng Dashboard."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)

        # Cấu trúc 2 cột chính
        columns = QHBoxLayout()
        columns.setSpacing(SPACE_32)

        # ── Cột TRÁI: bọc trong ScrollArea để tránh bị ép khi cửa sổ nhỏ ──
        left_inner = QWidget()
        left_col = QVBoxLayout(left_inner)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(SPACING_LG)
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_col.addWidget(self._build_hardware_column())
        left_col.addWidget(self._build_general_settings())
        left_col.addWidget(self._build_quality_card())
        left_col.addWidget(self._build_hardware_info_card())
        left_col.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_inner)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_scroll.setMinimumWidth(280)
        left_scroll.setStyleSheet("QScrollArea#SettingScroll { background: transparent; border: none; }")
        left_scroll.setObjectName("SettingScroll")
        left_inner.setObjectName("SettingLeftInner")
        left_inner.setStyleSheet("QWidget#SettingLeftInner { background: transparent; }")
        left_scroll.viewport().setAutoFillBackground(False)

        # ── Cột PHẢI: Firmware + console ──
        right_col = QVBoxLayout()
        right_col.setSpacing(SPACING_LG)
        right_col.addWidget(self._build_firmware_section(), stretch=1)

        # Tỷ lệ cân bằng: trái ~45%, phải ~55%
        columns.addWidget(left_scroll, stretch=9)
        columns.addLayout(right_col, stretch=11)

        outer.addLayout(columns, stretch=1)

        # Thanh điều khiển (Lưu / Hủy) nằm dưới cùng
        outer.addLayout(self._build_control_bar())


    def _build_hardware_column(self) -> QWidget:
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_imu"))

        card, c_lay = self._make_card()
        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g"])
        self.combo_gyro_scale = self._make_combo(["±250 dps", "±500 dps"])

        form = self._make_form_layout()
        self._add_i18n_form_row(form, "label_sample_rate", self.combo_sample_rate)
        self._add_i18n_form_row(form, "label_accel", self.combo_accel_scale)
        self._add_i18n_form_row(form, "label_gyro", self.combo_gyro_scale)
        c_lay.addLayout(form)
        lay.addWidget(card)
        return col

    def _build_quality_card(self) -> QWidget:
        """Primitive Dataset Quality scan — moved to left column after ML section removed."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)

        lbl_quality = QLabel("PRIMITIVE DATASET QUALITY")
        lbl_quality.setProperty("type", "settings_section_label")
        lbl_quality.setProperty("status", "accent")
        lay.addWidget(lbl_quality)

        quality_card, quality_layout = self._make_card()

        quality_btn_row = QHBoxLayout()
        quality_btn_row.setSpacing(SPACING_MD)

        self.btn_scan_quality = QPushButton("🔍 SCAN QUALITY")
        self.btn_scan_quality.setProperty("type", "primary")
        self.btn_scan_quality.setToolTip(
            "Scan all primitive gesture folders and generate a quality report"
        )

        self.btn_stop_scan = QPushButton("■ STOP SCAN")
        self.btn_stop_scan.setEnabled(False)
        self.btn_stop_scan.setProperty("type", "stop")
        self.btn_stop_scan.setStyleSheet(STYLE_SETTING_BTN_DANGER)
        self.btn_stop_scan.setToolTip("Stop the running quality scan")

        quality_btn_row.addWidget(self.btn_scan_quality)
        quality_btn_row.addWidget(self.btn_stop_scan)
        quality_layout.addLayout(quality_btn_row)

        self.quality_progress = QProgressBar()
        self.quality_progress.setRange(0, 100)
        self.quality_progress.setValue(0)
        self.quality_progress.setStyleSheet(STYLE_SETTING_PROGRESS)
        self.quality_progress.setMinimumHeight(6)
        self.quality_progress.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        quality_layout.addWidget(self.quality_progress)
        lay.addWidget(quality_card)
        return col

    def _build_general_settings(self) -> QWidget:
        """Khối cấu hình chung: Giao diện, dự án, đường dẫn và các tùy chọn khác."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_appearance"))
        
        card, c_lay = self._make_card(margins=(16, 16, 16, 16), spacing=SPACING_SM)
        self.combo_ui_language = self._make_combo([])
        self.chk_auto_save = QCheckBox()
        self.chk_show_primitives = QCheckBox()

        form = self._make_form_layout()
        self._add_i18n_form_row(form, "label_ui_language", self.combo_ui_language)
        
        # Đường dẫn Dataset
        folder_icon = QIcon(resolve_asset_path("assets/icon/cooliocns SVG/File/Folder_Open.svg"))
        self.txt_dataset_dir = QLineEdit()
        self.txt_dataset_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_browse_dataset = QPushButton()
        self.btn_browse_dataset.setIcon(folder_icon)
        self.btn_browse_dataset.setIconSize(QSize(16, 16))
        self.btn_browse_dataset.setFixedWidth(28)

        dataset_container = QWidget()
        dataset_row = QHBoxLayout(dataset_container)
        dataset_row.setContentsMargins(0, 0, 0, 0)
        dataset_row.setSpacing(8)
        dataset_row.addWidget(self.txt_dataset_dir)
        dataset_row.addWidget(self.btn_browse_dataset)
        self._add_i18n_form_row(form, "label_dataset_dir", dataset_container)

        # Đường dẫn Model
        self.txt_model_path = QLineEdit()
        self.txt_model_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_browse_model = QPushButton()
        self.btn_browse_model.setIcon(folder_icon)
        self.btn_browse_model.setIconSize(QSize(16, 16))
        self.btn_browse_model.setFixedWidth(28)

        model_container = QWidget()
        model_row = QHBoxLayout(model_container)
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(8)
        model_row.addWidget(self.txt_model_path)
        model_row.addWidget(self.btn_browse_model)
        self._add_i18n_form_row(form, "label_model_path", model_container)

        form.addRow(QLabel("Auto Save"), self.chk_auto_save)
        
        self.lbl_show_primitives = QLabel("Hiển thị menu Primitives" if self._lang == "vi" else "Show Primitives Menu")
        form.addRow(self.lbl_show_primitives, self.chk_show_primitives)
        
        c_lay.addLayout(form)
        lay.addWidget(card)
        return col

    def _build_hardware_info_card(self) -> QWidget:
        """Thẻ hiển thị thông số phần cứng ESP32 và kích thước mô hình TinyML."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        
        lbl_title = QLabel("CẤU HÌNH PHẦN CỨNG & MÔ HÌNH" if self._lang == "vi" else "HARDWARE & MODEL METRICS")
        lbl_title.setProperty("type", "settings_section_label")
        lbl_title.setProperty("status", "accent")
        lay.addWidget(lbl_title)
        
        card, c_lay = self._make_card(margins=(16, 16, 16, 16), spacing=SPACING_SM)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # Labels and Specs translation
        lang = self._lang
        mcu_lbl = "MCU Target:" if lang == "en" else "Vi xử lý mục tiêu:"
        mcu_val = "ESP32 / Dual-Core LX6 @ 240MHz"
        mem_lbl = "SRAM / Flash:"
        mem_val = "520 KB / 4 MB"
        fw_lbl = "TinyML Engine:" if lang == "en" else "Động cơ TinyML:"
        fw_val = "TF Lite Micro (INT8)"
        size_lbl = "Model Size (.tflite):" if lang == "en" else "Kích thước mô hình (.tflite):"
        gestures_lbl = "Active Gestures:" if lang == "en" else "Số cử chỉ kích hoạt:"
        
        def add_row(row_idx, label, value):
            lbl_name = QLabel(label)
            lbl_name.setStyleSheet("color: rgba(128, 128, 128, 200); font-weight: bold;")
            lbl_val = QLabel(value)
            lbl_val.setStyleSheet("font-weight: 500;")
            grid.addWidget(lbl_name, row_idx, 0)
            grid.addWidget(lbl_val, row_idx, 1)

        add_row(0, mcu_lbl, mcu_val)
        add_row(1, mem_lbl, mem_val)
        add_row(2, fw_lbl, fw_val)
        
        # Load dynamic TFLite size
        from config import APP_DATA_DIR
        tflite_path = APP_DATA_DIR / "gesture_encoder.tflite"
        size_str = "N/A"
        if tflite_path.exists():
            try:
                sz = tflite_path.stat().st_size
                size_str = f"{sz / 1024:.1f} KB"
            except OSError as exc:
                import logging as _log
                _log.getLogger(__name__).warning("Could not stat tflite file: %s", exc)
        add_row(3, size_lbl, size_str)
        
        # Load active gestures count
        classes_count = str(len(self.data_store.spell_counts))
        add_row(4, gestures_lbl, classes_count)
        
        c_lay.addLayout(grid)
        lay.addWidget(card)
        return col


    def _build_firmware_section(self) -> QWidget:
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_firmware"))

        card, c_lay = self._make_card(margins=(16, 16, 16, 16), spacing=SPACING_SM)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        btns = QHBoxLayout()
        btns.setSpacing(SPACING_SM)
        self.btn_flash_collect = QPushButton("")
        self.btn_flash_collect.setProperty("type", "primary")
        self.btn_flash_collect.setFixedHeight(32)
        self._tx(self.btn_flash_collect, "btn_flash_data", "⬆ ")

        self.btn_flash_ai = QPushButton("")
        self.btn_flash_ai.setProperty("type", "primary")
        self.btn_flash_ai.setFixedHeight(32)
        self._tx(self.btn_flash_ai, "btn_flash_ai", "⬆ ")

        btns.addWidget(self.btn_flash_collect)
        btns.addWidget(self.btn_flash_ai)
        c_lay.addLayout(btns)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        c_lay.addWidget(self.progress_bar)

        # Console: min height bảo vệ, max height giới hạn để không chiếm hết
        self.console_log = TerminalWidget(read_only=True)
        self.console_log.setMinimumHeight(200)
        self.console_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        c_lay.addWidget(self.console_log, stretch=1)
        lay.addWidget(card, stretch=1)
        return col

    def _build_control_bar(self) -> QHBoxLayout:
        """Thanh điều khiển lưu/hủy gọn gàng."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.btn_revert = QPushButton("")
        self.btn_revert.setProperty("type", "outline")
        self.btn_revert.setFixedHeight(34)
        self._tx(self.btn_revert, "btn_revert")

        self.btn_save = QPushButton("")
        self.btn_save.setProperty("type", "primary")
        self.btn_save.setFixedHeight(34)
        self._tx(self.btn_save, "btn_save")

        row.addStretch()
        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_save)
        return row



    def _init_signals(self) -> None:
        """Kết nối signal và slot."""
        self.btn_save.clicked.connect(self._on_btn_save_clicked)
        self.btn_revert.clicked.connect(self._on_btn_revert_clicked)
        self.btn_flash_collect.clicked.connect(self._on_btn_flash_collect_clicked)
        self.btn_flash_ai.clicked.connect(self._on_btn_flash_ai_clicked)
        self.btn_browse_dataset.clicked.connect(self._on_btn_browse_dataset_clicked)
        self.btn_browse_model.clicked.connect(self._on_btn_browse_model_clicked)
        self.combo_ui_language.currentIndexChanged.connect(self._on_ui_language_changed)
        self.btn_scan_quality.clicked.connect(self._on_btn_scan_quality_clicked)
        self.btn_stop_scan.clicked.connect(self._on_btn_stop_scan_clicked)

    def _load_data(self) -> None:
        """Nạp dữ liệu cài đặt từ store."""
        self._last_saved = self.data_store.get_settings_snapshot()
        lang = normalize_ui_language(self._last_saved.get("ui_language"))
        self._refresh_ui_texts(lang)
        self.load_settings(self._last_saved)

    # ── Public methods ──────────────────────────

    def load_settings(self, config: dict[str, Any]) -> None:
        """Đẩy giá trị cấu hình vào các widget UI."""
        widgets = {
            "sample_rate": self.combo_sample_rate,
            "accel_scale": self.combo_accel_scale,
            "gyro_scale": self.combo_gyro_scale,
            "auto_save": self.chk_auto_save,
            "dataset_dir": self.txt_dataset_dir,
            "model_path": self.txt_model_path,
            "show_primitives_menu": self.chk_show_primitives,
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

        self._set_combo_data(self.combo_ui_language, normalize_ui_language(config.get("ui_language")))

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
        """Toggle quality scan button states.

        Args:
            running: True while scan is in progress.
        """
        self.btn_scan_quality.setEnabled(not running)
        self.btn_stop_scan.setEnabled(running)
        if running:
            self.quality_progress.setValue(0)

    def update_scan_progress(self, value: int) -> None:
        """Update quality scan progress bar.

        Args:
            value: Progress percent 0-100.
        """
        self.quality_progress.setValue(max(0, min(100, value)))

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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        return form

    def _add_i18n_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel("")
        label.setProperty("type", "settings_form_label")
        label.setMinimumWidth(110)   # prevent label from collapsing/truncating
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
            self.lbl_show_primitives.setText("Hiển thị menu Primitives" if lang == "vi" else "Show Primitives Menu")

        # Preserve the currently selected language
        current_data = self.combo_ui_language.currentData()
        if not current_data:
            current_data = lang

        self.combo_ui_language.blockSignals(True)

        self.combo_ui_language.clear()
        self.combo_ui_language.addItem("English", "en")
        self.combo_ui_language.addItem("Tiếng Việt", "vi")
        
        # Restore selection
        self._set_combo_data(self.combo_ui_language, current_data)

        self.combo_ui_language.blockSignals(False)

    def _configure_accessibility(self) -> None:
        self.btn_scan_quality.setAccessibleName("Scan primitive dataset quality")
        self.btn_stop_scan.setAccessibleName("Stop quality scan")

    # ── Slots ───────────────────────────────────

    def _on_btn_save_clicked(self) -> None:
        config = {
            "sample_rate": self.combo_sample_rate.currentText(),
            "accel_scale": self.combo_accel_scale.currentText(),
            "gyro_scale": self.combo_gyro_scale.currentText(),
            "ui_language": self.combo_ui_language.currentData(),
            "auto_save": self.chk_auto_save.isChecked(),
            "dataset_dir": self.txt_dataset_dir.text().strip(),
            "model_path": self.txt_model_path.text().strip(),
            "show_primitives_menu": self.chk_show_primitives.isChecked(),
        }
        self.sig_settings_saved.emit(config)

    def _on_btn_revert_clicked(self) -> None:
        self.load_settings(self._last_saved)



    def _on_btn_flash_collect_clicked(self) -> None:
        self.sig_flash_data_firmware.emit()

    def _on_btn_flash_ai_clicked(self) -> None:
        self.sig_flash_inference_firmware.emit()

    def _on_ui_language_changed(self) -> None:
        lang = self.combo_ui_language.currentData()
        self._refresh_ui_texts(lang)
        locale_manager.current_language = lang

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

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
                             QLineEdit, QProgressBar, QPushButton, QSizePolicy,
                             QSpinBox, QVBoxLayout, QWidget)
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
    sig_clear_database = pyqtSignal()
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
        """Khởi tạo bố cục trang cài đặt siêu gọn (Zero-scroll)."""
        outer = QVBoxLayout(self)
        # Bỏ padding-bottom cứng để nội dung được bung hết cỡ
        outer.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        outer.setSpacing(SPACING_LG)

        # Requirement 2: 2-column layout
        columns = QHBoxLayout()
        columns.setSpacing(SPACE_32)
        
        left_col = QVBoxLayout()
        left_col.setSpacing(SPACING_LG)
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        right_col = QVBoxLayout()
        right_col.setSpacing(SPACING_LG)
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        left_col.addWidget(self._build_hardware_column())
        left_col.addWidget(self._build_software_column())
        
        right_col.addWidget(self._build_appearance_column())
        right_col.addWidget(self._build_paths_card())
        right_col.addWidget(self._build_danger_card())
        
        columns.addLayout(left_col, stretch=1)
        columns.addLayout(right_col, stretch=1)
        
        outer.addLayout(columns)

        # 2. Section Firmware (Full width)
        outer.addWidget(self._build_firmware_section(), stretch=1)

        # 3. Thanh điều khiển
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

    def _build_software_column(self) -> QWidget:
        """Requirement 1: Removed duplicate Appearance section from here."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_ml"))

        card, c_lay = self._make_card()
        self.combo_ml_pipeline = self._make_combo(["Random Forest (Edge)", "SVM"])
        self.spin_window_size = QSpinBox()
        self.spin_window_size.setRange(1, 1000)
        self.spin_window_overlap = QSpinBox()
        self.spin_window_overlap.setRange(0, 99)

        form = self._make_form_layout()
        self._add_i18n_form_row(form, "label_algorithm", self.combo_ml_pipeline)
        self._add_i18n_form_row(form, "label_window_size", self.spin_window_size)
        self._add_i18n_form_row(form, "label_window_overlap", self.spin_window_overlap)
        c_lay.addLayout(form)
        lay.addWidget(card)

        lbl_quality = QLabel("PRIMITIVE DATASET QUALITY")
        lbl_quality.setProperty("type", "settings_section_label")
        lbl_quality.setProperty("status", "accent")
        lay.addWidget(lbl_quality)
        
        quality_card, quality_layout = self._make_card()

        quality_btn_row = QHBoxLayout()
        quality_btn_row.setSpacing(SPACING_MD)

        self.btn_scan_quality = QPushButton("🔍  SCAN QUALITY")
        self.btn_scan_quality.setProperty("type", "primary")
        self.btn_scan_quality.setToolTip(
            "Scan all primitive gesture folders and generate a quality report"
        )

        self.btn_stop_scan = QPushButton("■  STOP SCAN")
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

    def _build_appearance_column(self) -> QWidget:
        """Khối cài đặt giao diện."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_appearance"))
        card, a_lay = self._make_card()
        self.combo_ui_language = self._make_combo([])
        self.txt_project_name = QLineEdit()
        self.chk_auto_save = QCheckBox()

        form = self._make_form_layout()
        self._add_i18n_form_row(form, "label_ui_language", self.combo_ui_language)
        self._add_i18n_form_row(form, "label_project_name", self.txt_project_name)
        form.addRow(QLabel("Auto Save"), self.chk_auto_save)
        a_lay.addLayout(form)
        lay.addWidget(card)
        return col

    def _build_danger_card(self) -> QWidget:
        """Khối thao tác nguy hiểm (Requirement 8)."""
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_danger", color=DANGER))
        card, c_lay = self._make_card()

        self.btn_clear_db = QPushButton("")
        self.btn_clear_db.setProperty("type", "stop")
        self.btn_clear_db.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tx(self.btn_clear_db, "btn_clear_db")
        c_lay.addWidget(self.btn_clear_db)
        lay.addWidget(card)
        return col

    def _build_firmware_section(self) -> QWidget:
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_firmware"))

        card, c_lay = self._make_card(margins=(16, 16, 16, 16), spacing=SPACING_SM)

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

        # Requirement 4: Terminal style
        self.console_log = TerminalWidget(read_only=True)
        self.console_log.setFixedHeight(120)
        c_lay.addWidget(self.console_log)
        lay.addWidget(card)
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

    def _build_paths_card(self) -> QWidget:
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_SM)
        lay.addWidget(self._make_section_label_i18n("section_paths"))

        card, c_lay = self._make_card(margins=(16, 16, 16, 16), spacing=SPACING_SM)
        
        form = self._make_form_layout()
        
        folder_icon = QIcon(resolve_asset_path("assets/icon/cooliocns SVG/File/Folder_Open.svg"))

        self.txt_idf_main_dir = QLineEdit()
        self.txt_idf_main_dir.setFixedHeight(28)
        self.btn_browse_idf_main = QPushButton()
        self.btn_browse_idf_main.setIcon(folder_icon)
        self.btn_browse_idf_main.setIconSize(QSize(16, 16))
        self.btn_browse_idf_main.setFixedSize(28, 28)
        
        idf_container = QWidget()
        idf_row = QHBoxLayout(idf_container)
        idf_row.setContentsMargins(0, 0, 0, 0)
        idf_row.setSpacing(8)
        idf_row.addWidget(self.txt_idf_main_dir)
        idf_row.addWidget(self.btn_browse_idf_main)
        
        self._add_i18n_form_row(form, "label_idf_main", idf_container)

        self.txt_dataset_dir = QLineEdit()
        self.txt_dataset_dir.setFixedHeight(28)
        self.btn_browse_dataset = QPushButton()
        self.btn_browse_dataset.setIcon(folder_icon)
        self.btn_browse_dataset.setIconSize(QSize(16, 16))
        self.btn_browse_dataset.setFixedSize(28, 28)
        
        dataset_container = QWidget()
        dataset_row = QHBoxLayout(dataset_container)
        dataset_row.setContentsMargins(0, 0, 0, 0)
        dataset_row.setSpacing(8)
        dataset_row.addWidget(self.txt_dataset_dir)
        dataset_row.addWidget(self.btn_browse_dataset)
        
        self._add_i18n_form_row(form, "label_dataset_dir", dataset_container)

        c_lay.addLayout(form)
        lay.addWidget(card)
        return col

    def _init_signals(self) -> None:
        """Kết nối signal và slot."""
        self.btn_save.clicked.connect(self._on_btn_save_clicked)
        self.btn_revert.clicked.connect(self._on_btn_revert_clicked)
        self.btn_clear_db.clicked.connect(self._on_btn_clear_db_clicked)
        self.btn_flash_collect.clicked.connect(self._on_btn_flash_collect_clicked)
        self.btn_flash_ai.clicked.connect(self._on_btn_flash_ai_clicked)
        self.btn_browse_idf_main.clicked.connect(self._on_btn_browse_clicked)
        self.btn_browse_dataset.clicked.connect(self._on_btn_browse_dataset_clicked)
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
            "ml_pipeline": self.combo_ml_pipeline,
            "window_size": self.spin_window_size,
            "window_overlap": self.spin_window_overlap,
            "project_name": self.txt_project_name,
            "auto_save": self.chk_auto_save,
            "idf_main_dir": self.txt_idf_main_dir,
            "dataset_dir": self.txt_dataset_dir,
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
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _add_i18n_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel("")
        label.setProperty("type", "settings_form_label")
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
            "ml_pipeline": self.combo_ml_pipeline.currentText(),
            "theme": "light",
            "ui_language": self.combo_ui_language.currentData(),
            "auto_save": self.chk_auto_save.isChecked(),
            "idf_main_dir": self.txt_idf_main_dir.text().strip(),
            "dataset_dir": self.txt_dataset_dir.text().strip(),
        }
        self.sig_settings_saved.emit(config)

    def _on_btn_revert_clicked(self) -> None:
        self.load_settings(self._last_saved)

    def _on_btn_clear_db_clicked(self) -> None:
        if confirm_destructive(self, title="Xóa dữ liệu", message="Bạn có chắc muốn xóa tất cả dataset?"):
            self.sig_clear_database.emit()

    def _on_btn_flash_collect_clicked(self) -> None:
        self.sig_flash_data_firmware.emit()

    def _on_btn_flash_ai_clicked(self) -> None:
        self.sig_flash_inference_firmware.emit()

    def _on_ui_language_changed(self) -> None:
        lang = self.combo_ui_language.currentData()
        self._refresh_ui_texts(lang)
        locale_manager.current_language = lang

    def _on_btn_browse_clicked(self) -> None:
        """Mở hộp thoại chọn thư mục IDF main."""
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục dự án")
        if path:
            self.txt_idf_main_dir.setText(path)

    def _on_btn_browse_dataset_clicked(self) -> None:
        """Mở hộp thoại chọn thư mục dataset."""
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục Dataset")
        if path:
            self.txt_dataset_dir.setText(path)

    def _on_btn_scan_quality_clicked(self) -> None:
        """Bắt đầu quét chất lượng dataset primitive."""
        self.set_scan_running(True)
        self.console_log.clear()
        self.append_console_text("[INFO] Starting primitive dataset quality scan...")
        self.sig_scan_primitive_quality.emit()

    def _on_btn_stop_scan_clicked(self) -> None:
        """Dừng quét chất lượng đang chạy."""
        self.sig_stop_primitive_scan.emit()

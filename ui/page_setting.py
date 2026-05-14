"""Trang cài đặt ứng dụng — cấu hình cảm biến, ML pipeline, và flash firmware."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QProgressBar,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logic.locale_manager import locale_manager
from logic.ui_i18n import normalize_ui_language, tr

from ui.tokens import (
    # Colors
    DANGER,
    LABEL_W,
    SETTINGS_ACCENT,
    SETTINGS_BTN_H,
    SETTINGS_INPUT_H,
    PROGRESS_H,
    SETTING_CONSOLE_MIN_H,
    TEXT_MUTED,
    # Styles
    STYLE_SETTING_CARD,
    STYLE_SETTING_BTN_OUTLINE,
    STYLE_SETTING_BTN_PRIMARY,
    STYLE_SETTING_BTN_DANGER,
    STYLE_SETTING_INPUT,
    STYLE_SETTING_CHECKBOX,
    STYLE_SETTING_PROGRESS,
    STYLE_SETTINGS_FORM_LABEL,
    STYLE_SETTINGS_HINT_TEMPLATE,
    STYLE_SETTINGS_INPUT_INVALID,
    STYLE_SETTINGS_SECTION_LABEL_TEMPLATE,
    STYLE_CONSOLE,
)
from ui.confirm_dialog import confirm_destructive
from ui.mac_material import apply_soft_shadow
from ui.terminal_widget import TerminalWidget
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_LG, SPACING_MD, SPACING_SM
from config import WORKSPACE_ROOT

# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class PageSetting(QWidget):
    """
    Trang cài đặt ứng dụng.
    Cho phép cấu hình cảm biến IMU, ML pipeline, thông số dự án,
    đường dẫn ESP-IDF, và flash firmware lên thiết bị.
    """

    sig_settings_saved = pyqtSignal(dict)
    sig_clear_database = pyqtSignal()
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._i18n_text: list[tuple[QWidget, str, str]] = []
        self._i18n_tooltips: list[tuple[QWidget, str]] = []
        self._lang = "en"
        self._init_ui()
        self._init_signals()
        self._configure_accessibility()
        self._load_data()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_settings(self, config: dict[str, Any]) -> None:
        """Nạp giá trị từ *config* vào tất cả widget form, tắt signal trong lúc set.

        Args:
            config: Dict chứa các cặp key-value tương ứng với từng widget.
        """
        widgets = {
            "sample_rate":    self.combo_sample_rate,
            "accel_scale":    self.combo_accel_scale,
            "gyro_scale":     self.combo_gyro_scale,
            "ml_pipeline":    self.combo_ml_pipeline,
            "window_size":    self.spin_window_size,
            "window_overlap": self.spin_window_overlap,
            "project_name":   self.txt_project_name,
            "auto_save":      self.chk_auto_save,
            "idf_main_dir":   self.txt_idf_main_dir,
        }

        for key, widget in widgets.items():
            if key not in config:
                continue
            value = config[key]
            widget.blockSignals(True)
            try:
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
            finally:
                widget.blockSignals(False)

        theme_val = str(config.get("theme", "light")).strip().lower()
        if theme_val not in ("light", "dark"):
            theme_val = "light"
        self.combo_theme.blockSignals(True)
        try:
            idx = self.combo_theme.findData(theme_val)
            if idx >= 0:
                self.combo_theme.setCurrentIndex(idx)
        finally:
            self.combo_theme.blockSignals(False)

        lang_val = normalize_ui_language(config.get("ui_language"))
        self.combo_ui_language.blockSignals(True)
        try:
            li = self.combo_ui_language.findData(lang_val)
            if li >= 0:
                self.combo_ui_language.setCurrentIndex(li)
        finally:
            self.combo_ui_language.blockSignals(False)

    def append_console_text(self, message: str) -> None:
        """Thêm *message* vào console log và tự cuộn xuống cuối.

        Args:
            message: Nội dung cần ghi vào console.
        """
        if self.console_log is None:
            return
        self.console_log.append_line(message, strip_right=True)

    def update_flash_progress(self, value: int) -> None:
        """Đặt thanh tiến trình flash về *value* (giới hạn 0–100).

        Args:
            value: Phần trăm hoàn thành.
        """
        self.progress_bar.setValue(max(0, min(100, value)))

    def set_flash_buttons_enabled(self, enabled: bool) -> None:
        """Bật hoặc tắt cả hai nút flash firmware cùng lúc.

        Args:
            enabled: True để bật, False để tắt.
        """
        self.btn_flash_collect.setEnabled(enabled)
        self.btn_flash_ai.setEnabled(enabled)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def refresh_styles(self) -> None:
        """Re-apply styles based on current theme."""
        p = theme_manager.get_palette()
        self.setStyleSheet(f"color: {p.TEXT_PRIMARY};")
        
        # Update any card styles if needed
        # In this page, most components are standard or use factory styles
        # but we can ensure the console and progress bar are updated
        if hasattr(self, 'console_log') and self.console_log:
             self.console_log.setStyleSheet(STYLE_CONSOLE)
        if hasattr(self, 'progress_bar') and self.progress_bar:
             self.progress_bar.setStyleSheet(STYLE_SETTING_PROGRESS)

    def _init_ui(self) -> None:
        """Main layout: scrollable 3-column top row, paths, firmware; fixed control bar."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
            MARGIN_COMFORTABLE,
        )
        outer.setSpacing(SPACING_LG)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        inner = QWidget()
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 0, 0)
        inner_l.setSpacing(SPACING_LG)

        top_row = QHBoxLayout()
        top_row.setSpacing(SPACING_LG)
        top_row.addWidget(self._build_hardware_column(), stretch=1)
        top_row.addWidget(self._build_software_column(), stretch=1)
        top_row.addWidget(self._build_danger_column(), stretch=1)
        inner_l.addLayout(top_row)
        inner_l.addWidget(self._build_paths_card())
        inner_l.addWidget(self._build_firmware_section(), stretch=1)

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)
        outer.addLayout(self._build_control_bar())

    def _build_hardware_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._make_section_label_i18n("section_imu"))
        sensor_card, sensor_layout = self._make_card()

        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz", "400 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g", "±16g"])
        self.combo_gyro_scale  = self._make_combo(["±250 dps", "±500 dps", "±1000 dps", "±2000 dps"])

        sensor_form = self._make_form_layout()
        self._add_i18n_form_row(sensor_form, "label_sample_rate", self.combo_sample_rate)
        self._add_i18n_form_row(sensor_form, "label_accel", self.combo_accel_scale)
        self._add_i18n_form_row(sensor_form, "label_gyro", self.combo_gyro_scale)
        sensor_layout.addLayout(sensor_form)
        layout.addWidget(sensor_card)

        layout.addWidget(self._make_section_label_i18n("section_windowing"))
        window_card, window_layout = self._make_card()

        self.spin_window_size    = self._make_spinbox(10,  2000, step=10, suffix=" ms")
        self.spin_window_overlap = self._make_spinbox(0,   90,   step=10, suffix=" %")

        window_form = self._make_form_layout()
        self._add_i18n_form_row(window_form, "label_window_size", self.spin_window_size)
        self._add_i18n_form_row(window_form, "label_overlap", self.spin_window_overlap)
        window_layout.addLayout(window_form)
        window_layout.addWidget(self._make_hint_i18n("hint_windowing"))
        layout.addWidget(window_card)

        layout.addStretch()
        return widget

    def _build_software_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._make_section_label_i18n("section_ml"))
        ml_card, ml_layout = self._make_card()

        self.combo_ml_pipeline = self._make_combo([
            "Random Forest (Edge)",
            "Support Vector Machine",
            "Tiny Neural Network (TFLite)",
        ])

        ml_form = self._make_form_layout()
        self._add_i18n_form_row(ml_form, "label_algorithm", self.combo_ml_pipeline)
        ml_layout.addLayout(ml_form)
        ml_layout.addWidget(self._make_hint_i18n("hint_ml"))
        layout.addWidget(ml_card)

        layout.addWidget(self._make_section_label_i18n("section_appearance"))
        appearance_card, appearance_layout = self._make_card()

        self.combo_theme = QComboBox()
        self.combo_theme.setStyleSheet(STYLE_SETTING_INPUT)
        self.combo_theme.setMinimumHeight(SETTINGS_INPUT_H)
        self.combo_theme.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.combo_theme.setCursor(Qt.CursorShape.PointingHandCursor)

        self.combo_ui_language = QComboBox()
        self.combo_ui_language.setStyleSheet(STYLE_SETTING_INPUT)
        self.combo_ui_language.setMinimumHeight(SETTINGS_INPUT_H)
        self.combo_ui_language.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.combo_ui_language.setCursor(Qt.CursorShape.PointingHandCursor)

        appearance_form = self._make_form_layout()
        self._add_i18n_form_row(appearance_form, "label_theme", self.combo_theme)
        self._add_i18n_form_row(appearance_form, "label_ui_language", self.combo_ui_language)
        appearance_layout.addLayout(appearance_form)
        layout.addWidget(appearance_card)

        layout.addWidget(self._make_section_label_i18n("section_project"))
        sys_card, sys_layout = self._make_card()

        self.txt_project_name = QLineEdit()
        self.txt_project_name.setStyleSheet(STYLE_SETTING_INPUT)
        self.txt_project_name.setMinimumHeight(SETTINGS_INPUT_H)
        self.txt_project_name.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.chk_auto_save = QCheckBox("")
        self.chk_auto_save.setStyleSheet(STYLE_SETTING_CHECKBOX)
        self._tx(self.chk_auto_save, "chk_auto_save")

        sys_form = self._make_form_layout()
        self._add_i18n_form_row(sys_form, "label_project_name", self.txt_project_name)
        sys_layout.addLayout(sys_form)
        sys_layout.addWidget(self.chk_auto_save)
        layout.addWidget(sys_card)

        layout.addStretch()
        return widget

    def _build_danger_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._make_section_label_i18n("section_danger", color=DANGER))
        danger_card, danger_layout = self._make_card()

        self.btn_clear_db = QPushButton("")
        self.btn_clear_db.setStyleSheet(STYLE_SETTING_BTN_DANGER)
        self.btn_clear_db.setFixedHeight(SETTINGS_BTN_H)
        self.btn_clear_db.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_clear_db, "btn_clear_db")

        danger_layout.addWidget(self.btn_clear_db)
        danger_layout.addWidget(self._make_hint_i18n("hint_danger", color=DANGER))
        layout.addWidget(danger_card)
        layout.addStretch()
        return widget

    def _build_firmware_section(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._make_section_label_i18n("section_firmware"))

        firmware_card, fw_layout = self._make_card()

        # Flash buttons
        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(SPACING_MD)
        button_grid.setVerticalSpacing(SPACING_SM)

        self.btn_flash_collect = QPushButton("")
        self.btn_flash_collect.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        self.btn_flash_collect.setMinimumHeight(SETTINGS_BTN_H)
        self.btn_flash_collect.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_flash_collect, "btn_flash_data", "⬆  ")

        self.btn_flash_ai = QPushButton("")
        self.btn_flash_ai.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        self.btn_flash_ai.setMinimumHeight(SETTINGS_BTN_H)
        self.btn_flash_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_flash_ai, "btn_flash_ai", "⬆  ")

        button_grid.addWidget(self.btn_flash_collect, 0, 0)
        button_grid.addWidget(self.btn_flash_ai, 0, 1)
        fw_layout.addLayout(button_grid)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(STYLE_SETTING_PROGRESS)
        self.progress_bar.setMinimumHeight(PROGRESS_H)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        fw_layout.addWidget(self.progress_bar)

        # Console log
        fw_layout.addWidget(self._make_section_label_i18n("sub_console", color=TEXT_MUTED))
        self.console_log = TerminalWidget(max_lines=1000, read_only=True)
        self.console_log.setMinimumHeight(SETTING_CONSOLE_MIN_H)
        self.console_log.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.console_log.setStyleSheet(STYLE_CONSOLE)
        fw_layout.addWidget(self.console_log)

        layout.addWidget(firmware_card)
        layout.addWidget(self._make_hint_i18n("hint_firmware"))
        return widget

    def _build_control_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACING_SM)
        row.addStretch()

        self.btn_revert = QPushButton("")
        self.btn_revert.setStyleSheet(STYLE_SETTING_BTN_OUTLINE)
        self.btn_revert.setFixedHeight(SETTINGS_BTN_H)
        self.btn_revert.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_revert, "btn_revert")

        self.btn_save = QPushButton("")
        self.btn_save.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        self.btn_save.setFixedHeight(SETTINGS_BTN_H)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_save, "btn_save")

        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_save)
        return row

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot của trang cài đặt."""
        self.btn_save.clicked.connect(self._on_btn_save_clicked)
        self.btn_revert.clicked.connect(self._on_btn_revert_clicked)
        self.btn_clear_db.clicked.connect(self._on_btn_clear_db_clicked)
        self.btn_flash_collect.clicked.connect(self._on_btn_flash_collect_clicked)
        self.btn_flash_ai.clicked.connect(self._on_btn_flash_ai_clicked)
        self.btn_open_idf_main.clicked.connect(self._on_btn_open_idf_main_clicked)
        self.btn_browse_idf_main.clicked.connect(self._on_btn_browse_idf_main_clicked)
        self.btn_reset_idf_main.clicked.connect(self._on_btn_reset_idf_main_clicked)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        self.combo_ui_language.currentIndexChanged.connect(self._on_ui_language_changed)

    def _on_theme_changed(self, _index: int = 0) -> None:
        from logic.theme_manager import theme_manager

        raw = self.combo_theme.currentData()
        name = str(raw) if raw in ("light", "dark") else "light"
        theme_manager.current_theme = name

    def _configure_accessibility(self) -> None:
        """Đặt accessible names và thứ tự tab traversal cho các control."""
        self.combo_sample_rate.setAccessibleName("Sample rate")
        self.combo_accel_scale.setAccessibleName("Accelerometer full scale")
        self.combo_gyro_scale.setAccessibleName("Gyroscope full scale")
        self.spin_window_size.setAccessibleName("Window size")
        self.spin_window_overlap.setAccessibleName("Window overlap")
        self.combo_ml_pipeline.setAccessibleName("Machine learning pipeline")
        self.combo_theme.setAccessibleName("App theme")
        self.combo_ui_language.setAccessibleName("Interface language")
        self.txt_project_name.setAccessibleName("Project name")
        self.chk_auto_save.setAccessibleName("Auto save recording samples")
        self.txt_idf_main_dir.setAccessibleName("ESP-IDF main directory path")
        self.btn_browse_idf_main.setAccessibleName("Browse for ESP-IDF main directory")
        self.btn_reset_idf_main.setAccessibleName("Reset IDF main directory path")
        self.btn_open_idf_main.setAccessibleName("Open ESP-IDF project")
        # Firmware and action buttons
        self.btn_revert.setAccessibleName("Revert settings")
        self.btn_save.setAccessibleName("Save settings")
        self.btn_flash_collect.setAccessibleName("Install data firmware")
        self.btn_flash_ai.setAccessibleName("Install AI firmware")
        self.btn_clear_db.setAccessibleName("Erase all collected data")

        self.setTabOrder(self.combo_sample_rate, self.combo_accel_scale)
        self.setTabOrder(self.combo_accel_scale, self.combo_gyro_scale)
        self.setTabOrder(self.combo_gyro_scale, self.spin_window_size)
        self.setTabOrder(self.spin_window_size, self.spin_window_overlap)
        self.setTabOrder(self.spin_window_overlap, self.combo_ml_pipeline)
        self.setTabOrder(self.combo_ml_pipeline, self.combo_theme)
        self.setTabOrder(self.combo_theme, self.combo_ui_language)
        self.setTabOrder(self.combo_ui_language, self.txt_project_name)
        self.setTabOrder(self.txt_project_name, self.chk_auto_save)
        self.setTabOrder(self.chk_auto_save, self.txt_idf_main_dir)
        self.setTabOrder(self.txt_idf_main_dir, self.btn_browse_idf_main)
        self.setTabOrder(self.btn_browse_idf_main, self.btn_reset_idf_main)
        self.setTabOrder(self.btn_reset_idf_main, self.btn_open_idf_main)
        self.setTabOrder(self.btn_open_idf_main, self.btn_revert)
        self.setTabOrder(self.btn_revert, self.btn_save)
        self.setTabOrder(self.btn_save, self.btn_flash_collect)
        self.setTabOrder(self.btn_flash_collect, self.btn_flash_ai)
        self.setTabOrder(self.btn_flash_ai, self.btn_clear_db)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        """Nạp settings ban đầu từ DataStore snapshot vào form."""
        from logic.theme_manager import theme_manager

        self._last_saved: dict[str, Any] = self.data_store.get_settings_snapshot()
        lang = normalize_ui_language(self._last_saved.get("ui_language"))
        self._refresh_ui_texts(lang)
        self.load_settings(self._last_saved)
        theme_manager.current_theme = str(self.combo_theme.currentData() or "light")
        locale_manager.current_language = lang

    def _collect_config(self) -> dict[str, Any]:
        """Thu thập giá trị hiện tại từ tất cả widget form.

        Returns:
            Dict chứa toàn bộ cấu hình đã nhập.
        """
        return {
            "sample_rate":       self.combo_sample_rate.currentText(),
            "accel_scale":       self.combo_accel_scale.currentText(),
            "gyro_scale":        self.combo_gyro_scale.currentText(),
            "window_size":       self.spin_window_size.value(),
            "window_overlap":    self.spin_window_overlap.value(),
            "ml_pipeline":       self.combo_ml_pipeline.currentText(),
            "theme":             str(self.combo_theme.currentData() or "light"),
            "ui_language":       str(self.combo_ui_language.currentData() or "en"),
            "project_name":      self.txt_project_name.text().strip(),
            "auto_save":         self.chk_auto_save.isChecked(),
            "idf_main_dir":      self.txt_idf_main_dir.text().strip(),
        }

    def _on_btn_save_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Save Settings."""
        config = self._collect_config()
        if not config.get("project_name"):
            QMessageBox.warning(
                self,
                tr(self._lang, "msg_missing_project_title"),
                tr(self._lang, "msg_missing_project"),
            )
            self.txt_project_name.setFocus()
            return
        if not self._validate_paths(config):
            return
        self._last_saved = config
        self.sig_settings_saved.emit(config)

    def _on_btn_revert_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Revert Changes."""
        from logic.theme_manager import theme_manager

        lang = normalize_ui_language(self._last_saved.get("ui_language"))
        self._refresh_ui_texts(lang)
        self.load_settings(self._last_saved)
        theme_manager.current_theme = str(self.combo_theme.currentData() or "light")
        locale_manager.current_language = lang

    def _on_btn_clear_db_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Erase All Data — yêu cầu xác nhận."""
        if confirm_destructive(
            self,
            title=tr(self._lang, "erase_title"),
            message=tr(self._lang, "erase_message"),
            confirm_text=tr(self._lang, "erase_confirm"),
            cancel_text=tr(self._lang, "erase_cancel"),
        ):
            self.sig_clear_database.emit()

    def _on_btn_flash_collect_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Install Data Firmware."""
        self._begin_flash("[INFO] Starting DATA FIRMWARE flash…")
        self.sig_flash_data_firmware.emit()

    def _on_btn_flash_ai_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút Install AI Engine."""
        self._begin_flash("[INFO] Starting AI ENGINE flash…")
        self.sig_flash_inference_firmware.emit()

    def _begin_flash(self, initial_message: str) -> None:
        """Thiết lập chung trước mỗi thao tác flash firmware.

        Args:
            initial_message: Thông báo khởi đầu hiển thị trong console.
        """
        self.set_flash_buttons_enabled(False)
        self.console_log.clear()
        self.progress_bar.setValue(0)
        self.append_console_text(initial_message)

    def _on_btn_open_idf_main_clicked(self) -> None:
        """Mở thư mục gốc ESP-IDF project đang chọn trong VS Code."""
        raw_main = self.txt_idf_main_dir.text().strip()
        if not raw_main:
            QMessageBox.warning(
                self,
                tr(self._lang, "msg_missing_path_title"),
                tr(self._lang, "msg_missing_path"),
            )
            return

        main_dir = Path(raw_main).expanduser()
        target = main_dir.parent if main_dir.name.lower() == "main" else main_dir
        target_str = str(target)

        if shutil.which("code"):
            try:
                subprocess.Popen(["code", target_str])
                self.append_console_text(f"[INFO] VSCode opened: {target_str}")
                return
            except OSError as exc:
                self.append_console_text(f"[WARN] Could not run 'code': {exc}")

        if hasattr(os, "startfile"):
            try:
                os.startfile(target_str)  # type: ignore[attr-defined]
                self.append_console_text(f"[INFO] Opened with system shell: {target_str}")
                return
            except OSError as exc:
                self.append_console_text(f"[ERROR] Failed to open workspace target: {exc}")

        QMessageBox.warning(
            self,
            tr(self._lang, "msg_open_failed_title"),
            tr(self._lang, "msg_open_failed"),
        )

    def _on_btn_browse_idf_main_clicked(self) -> None:
        """Mở dialog chọn thư mục ESP-IDF main."""
        path = QFileDialog.getExistingDirectory(
            self,
            tr(self._lang, "browse_idf_title"),
            self.txt_idf_main_dir.text() or str(WORKSPACE_ROOT),
        )
        if path:
            self.txt_idf_main_dir.setText(path)
            self.txt_idf_main_dir.setStyleSheet(STYLE_SETTING_INPUT)

    def _on_btn_reset_idf_main_clicked(self) -> None:
        """Xóa đường dẫn ESP-IDF main và reset style."""
        self.txt_idf_main_dir.setText("")
        self.txt_idf_main_dir.setStyleSheet(STYLE_SETTING_INPUT)

    # Path validation

    def _validate_paths(self, config: dict[str, Any]) -> bool:
        """Kiểm tra tính hợp lệ của các trường đường dẫn, đánh dấu đỏ nếu sai.

        Args:
            config: Dict chứa cấu hình cần validate.

        Returns:
            True nếu tất cả đường dẫn hợp lệ.
        """
        idf_main_str = str(config.get("idf_main_dir", "")).strip()
        if not idf_main_str:
            self.txt_idf_main_dir.setStyleSheet(STYLE_SETTING_INPUT)
            return True

        idf_main_dir = Path(idf_main_str).expanduser().resolve()
        invalid_reasons: list[str] = []
        if not idf_main_dir.exists() or not idf_main_dir.is_dir():
            invalid_reasons.append(tr(self._lang, "invalid_idf_missing"))
        if idf_main_dir.name.lower() != "main":
            invalid_reasons.append(tr(self._lang, "invalid_idf_not_main"))

        idf_root = idf_main_dir.parent
        if not (idf_root / "CMakeLists.txt").exists():
            invalid_reasons.append(tr(self._lang, "invalid_idf_no_cmake"))

        if invalid_reasons:
            self.txt_idf_main_dir.setStyleSheet(
                STYLE_SETTING_INPUT + STYLE_SETTINGS_INPUT_INVALID
            )
            QMessageBox.warning(
                self,
                tr(self._lang, "msg_invalid_path_title"),
                tr(self._lang, "msg_invalid_path_prefix") + "\n• " + "\n• ".join(invalid_reasons),
            )
            return False

        self.txt_idf_main_dir.setStyleSheet(STYLE_SETTING_INPUT)
        return True

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def _tx(self, widget: QWidget, key: str, prefix: str = "") -> None:
        self._i18n_text.append((widget, key, prefix))

    def _tip(self, widget: QWidget, key: str) -> None:
        self._i18n_tooltips.append((widget, key))

    def _make_section_label_i18n(self, key: str, color: str = SETTINGS_ACCENT) -> QLabel:
        lbl = QLabel("")
        lbl.setStyleSheet(STYLE_SETTINGS_SECTION_LABEL_TEMPLATE.format(color=color))
        lbl.setWordWrap(True)
        self._tx(lbl, key)
        return lbl

    def _make_hint_i18n(self, key: str, color: str = TEXT_MUTED) -> QLabel:
        lbl = QLabel("")
        lbl.setStyleSheet(STYLE_SETTINGS_HINT_TEMPLATE.format(color=color))
        lbl.setWordWrap(True)
        self._tx(lbl, key)
        return lbl

    def _add_i18n_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel("")
        label.setStyleSheet(STYLE_SETTINGS_FORM_LABEL)
        label.setWordWrap(True)
        field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.addRow(label, field)
        self._tx(label, key)

    def _rebuild_theme_combo(self, selected: str) -> None:
        sel = selected if selected in ("light", "dark") else "light"
        self.combo_theme.blockSignals(True)
        self.combo_theme.clear()
        self.combo_theme.addItem(tr(self._lang, "theme_light"), "light")
        self.combo_theme.addItem(tr(self._lang, "theme_dark"), "dark")
        idx = self.combo_theme.findData(sel)
        self.combo_theme.setCurrentIndex(max(0, idx))
        self.combo_theme.blockSignals(False)

    def _rebuild_lang_combo(self, selected: str) -> None:
        sel = normalize_ui_language(selected)
        self.combo_ui_language.blockSignals(True)
        self.combo_ui_language.clear()
        self.combo_ui_language.addItem(tr(self._lang, "lang_option_en"), "en")
        self.combo_ui_language.addItem(tr(self._lang, "lang_option_vi"), "vi")
        idx = self.combo_ui_language.findData(sel)
        self.combo_ui_language.setCurrentIndex(max(0, idx))
        self.combo_ui_language.blockSignals(False)

    def _refresh_ui_texts(self, lang: str | None) -> None:
        lang_norm = normalize_ui_language(lang)
        theme_sel = self.combo_theme.currentData()
        if theme_sel not in ("light", "dark"):
            theme_sel = "light"
        self._lang = lang_norm
        for w, key, prefix in self._i18n_text:
            w.setText(prefix + tr(self._lang, key))
        for w, key in self._i18n_tooltips:
            w.setToolTip(tr(self._lang, key))
        self._rebuild_theme_combo(str(theme_sel))
        self._rebuild_lang_combo(lang_norm)
        self.txt_project_name.setPlaceholderText(tr(self._lang, "placeholder_project"))
        self.txt_idf_main_dir.setPlaceholderText(tr(self._lang, "placeholder_idf"))

    def apply_ui_language(self) -> None:
        """Re-apply labels when language is changed from MainWindow (e.g. startup sync)."""
        self._refresh_ui_texts(locale_manager.current_language)

    def _on_ui_language_changed(self) -> None:
        raw = self.combo_ui_language.currentData()
        lang = normalize_ui_language(str(raw) if raw is not None else "en")
        self._refresh_ui_texts(lang)
        locale_manager.current_language = lang

    def _build_paths_card(self) -> QWidget:
        """Tạo card PATH CONFIGURATION với trường chọn thư mục IDF main."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._make_section_label_i18n("section_paths"))

        card, card_layout = self._make_card()

        def _make_path_field() -> QLineEdit:
            field = QLineEdit()
            field.setStyleSheet(STYLE_SETTING_INPUT)
            field.setMinimumHeight(SETTINGS_INPUT_H)
            field.setPlaceholderText("")
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return field

        def _make_browse_btn() -> QPushButton:
            btn = QPushButton("")
            btn.setStyleSheet(STYLE_SETTING_BTN_OUTLINE)
            btn.setFixedHeight(SETTINGS_INPUT_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._tx(btn, "btn_browse")
            return btn

        def _make_reset_btn() -> QToolButton:
            btn = QToolButton()
            btn.setText("↺")
            btn.setFixedSize(SETTINGS_INPUT_H, SETTINGS_INPUT_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._tip(btn, "tooltip_reset_path")
            return btn

        self.txt_idf_main_dir = _make_path_field()
        self.btn_browse_idf_main = _make_browse_btn()
        self.btn_reset_idf_main = _make_reset_btn()
        self.btn_open_idf_main = QPushButton("")
        self.btn_open_idf_main.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        self.btn_open_idf_main.setFixedHeight(SETTINGS_INPUT_H)
        self.btn_open_idf_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tx(self.btn_open_idf_main, "btn_open_idf")

        idf_row = QHBoxLayout()
        idf_row.setContentsMargins(0, 0, 0, 0)
        idf_row.setSpacing(SPACING_SM)
        idf_row.addWidget(self.txt_idf_main_dir, stretch=1)
        idf_row.addWidget(self.btn_browse_idf_main)
        idf_row.addWidget(self.btn_reset_idf_main)
        idf_row.addWidget(self.btn_open_idf_main)

        path_form = self._make_form_layout()
        idf_widget = QWidget()
        idf_widget.setLayout(idf_row)
        self._add_i18n_form_row(path_form, "label_idf_main", idf_widget)

        card_layout.addLayout(path_form)
        card_layout.addWidget(self._make_hint_i18n("hint_paths"))
        layout.addWidget(card)
        return widget

    @staticmethod
    def _make_card() -> tuple[QFrame, QVBoxLayout]:
        """Tạo card frame có style và layout sẵn sàng sử dụng.

        Returns:
            Tuple gồm (frame, layout).        
        """
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_SETTING_CARD)
        apply_soft_shadow(frame, blur_radius=20, y_offset=4, color="rgba(15, 23, 42, 0.16)")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_MD)
        return frame, layout

    @staticmethod
    def _make_form_layout() -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setHorizontalSpacing(SPACING_MD)
        form.setVerticalSpacing(SPACING_SM)
        return form

    @staticmethod
    def _add_form_row(form: QFormLayout, label_text: str, widget: QWidget) -> None:
        label = QLabel(label_text)
        label.setStyleSheet(STYLE_SETTINGS_FORM_LABEL)
        label.setWordWrap(True)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.addRow(label, widget)

    @staticmethod
    def _make_section_label(text: str, color: str = SETTINGS_ACCENT) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(STYLE_SETTINGS_SECTION_LABEL_TEMPLATE.format(color=color))
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _make_combo(items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setStyleSheet(STYLE_SETTING_INPUT)
        combo.setMinimumHeight(SETTINGS_INPUT_H)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        return combo

    @staticmethod
    def _make_spinbox(
        min_val: int, max_val: int, *, step: int, suffix: str = ""
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setStyleSheet(STYLE_SETTING_INPUT)
        spin.setMinimumHeight(SETTINGS_INPUT_H)
        spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return spin

    @staticmethod
    def _make_primary_button(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        btn.setMinimumHeight(SETTINGS_BTN_H)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    @staticmethod
    def _make_form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(STYLE_SETTINGS_FORM_LABEL)
        lbl.setMinimumWidth(LABEL_W)
        lbl.setWordWrap(True)
        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        return row

    @staticmethod
    def _make_hint(text: str, color: str = TEXT_MUTED) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(STYLE_SETTINGS_HINT_TEMPLATE.format(color=color))
        lbl.setWordWrap(True)
        return lbl

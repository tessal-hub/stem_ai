"""PageSettings — Application, sensor, and machine-learning configuration view."""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ui.tokens import (
    # Colors
    ACCENT_TEXT,
    BG_LIGHT,
    BG_WHITE,
    BORDER,
    BORDER_MID,
    DANGER,
    LABEL_W,
    SETTINGS_ACCENT,
    SETTINGS_ACCENT_DARK,
    SETTINGS_BTN_H,
    SETTINGS_HOVER_BG,
    SETTINGS_INPUT_H,
    SUCCESS,
    TEXT_BODY,
    TEXT_MUTED,
    # Styles
    STYLE_SETTING_MAIN_CONTAINER,
    STYLE_SETTING_CARD,
    STYLE_SETTING_BTN_OUTLINE,
    STYLE_SETTING_BTN_PRIMARY,
    STYLE_SETTING_BTN_DANGER,
    STYLE_SETTING_INPUT,
    STYLE_SETTING_CHECKBOX,
    STYLE_SETTING_PROGRESS,
    STYLE_CONSOLE,
    STYLE_SCROLL_AREA,
)
from ui.confirm_dialog import confirm_destructive
from ui.mac_material import apply_soft_shadow
from ui.terminal_widget import TerminalWidget
from config import VSCODE_WORKSPACE_FILE

# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class PageSetting(QWidget):
    """Settings page: sensor, ML pipeline, project options, firmware flashing."""

    sig_settings_saved = pyqtSignal(dict)
    sig_clear_database = pyqtSignal()
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._build_ui()
        self._connect_internal_signals()
        self._configure_accessibility()

        # Snapshot the store's current settings and populate the form.
        self._last_saved: dict[str, Any] = self.data_store.get_settings_snapshot()
        self.load_settings(self._last_saved)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_settings(self, config: dict[str, Any]) -> None:
        """Populate all form widgets from *config*, suppressing change signals."""
        widgets = {
            "sample_rate":    self.combo_sample_rate,
            "accel_scale":    self.combo_accel_scale,
            "gyro_scale":     self.combo_gyro_scale,
            "ml_pipeline":    self.combo_ml_pipeline,
            "window_size":    self.spin_window_size,
            "window_overlap": self.spin_window_overlap,
            "project_name":   self.txt_project_name,
            "auto_save":      self.chk_auto_save,
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

    def append_console_text(self, message: str) -> None:
        """Append *message* to the console log and auto-scroll to the bottom."""
        if self.console_log is None:
            return
        self.console_log.append_line(message, strip_right=True)

    def update_flash_progress(self, value: int) -> None:
        """Set the progress bar to *value* (clamped to 0–100)."""
        self.progress_bar.setValue(max(0, min(100, value)))

    def set_flash_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable both firmware flash buttons together."""
        self.btn_flash_collect.setEnabled(enabled)
        self.btn_flash_ai.setEnabled(enabled)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setFrameShape(QFrame.Shape.NoFrame)
        self.main_container.setFrameShadow(QFrame.Shadow.Plain)
        self.main_container.setStyleSheet(STYLE_SETTING_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(12)

        cols = QHBoxLayout()
        cols.setSpacing(12)
        cols.addWidget(self._build_hardware_column(), stretch=1)
        cols.addWidget(self._build_software_column(), stretch=1)
        inner.addLayout(cols, stretch=1)
        inner.addWidget(self._build_firmware_section())
        inner.addLayout(self._build_control_bar())

        scroll.setWidget(self.main_container)
        outer.addWidget(scroll)

    def _build_hardware_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Sensor card ─────────────────────────────────────────────────
        layout.addWidget(self._make_section_label("IMU SENSOR CONFIGURATION"))
        sensor_card, sensor_layout = self._make_card()

        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz", "400 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g", "±16g"])
        self.combo_gyro_scale  = self._make_combo(["±250 dps", "±500 dps", "±1000 dps", "±2000 dps"])

        sensor_form = self._make_form_layout()
        self._add_form_row(sensor_form, "Sampling Rate:", self.combo_sample_rate)
        self._add_form_row(sensor_form, "Accelerometer FSR:", self.combo_accel_scale)
        self._add_form_row(sensor_form, "Gyroscope FSR:", self.combo_gyro_scale)
        sensor_layout.addLayout(sensor_form)
        layout.addWidget(sensor_card)

        # ── Windowing card ──────────────────────────────────────────────
        layout.addWidget(self._make_section_label("DATA WINDOWING (TIME-SERIES)"))
        window_card, window_layout = self._make_card()

        self.spin_window_size    = self._make_spinbox(10,  2000, step=10, suffix=" ms")
        self.spin_window_overlap = self._make_spinbox(0,   90,   step=10, suffix=" %")

        window_form = self._make_form_layout()
        self._add_form_row(window_form, "Window Size:", self.spin_window_size)
        self._add_form_row(window_form, "Overlap:", self.spin_window_overlap)
        window_layout.addLayout(window_form)
        window_layout.addWidget(
            self._make_hint("Adjust window size based on typical spell cast duration.")
        )
        layout.addWidget(window_card)

        layout.addStretch()
        return widget

    def _build_software_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── ML pipeline card ────────────────────────────────────────────
        layout.addWidget(self._make_section_label("MACHINE LEARNING PIPELINE"))
        ml_card, ml_layout = self._make_card()

        self.combo_ml_pipeline = self._make_combo([
            "Random Forest (Edge)",
            "Support Vector Machine",
            "Tiny Neural Network (TFLite)",
        ])
        ml_form = self._make_form_layout()
        self._add_form_row(ml_form, "Algorithm:", self.combo_ml_pipeline)
        ml_layout.addLayout(ml_form)
        ml_layout.addWidget(
            self._make_hint("Select the target inference engine for the ESP32.")
        )
        layout.addWidget(ml_card)

        # ── Project settings card ───────────────────────────────────────
        layout.addWidget(self._make_section_label("PROJECT SETTINGS"))
        sys_card, sys_layout = self._make_card()

        self.txt_project_name = QLineEdit()
        self.txt_project_name.setStyleSheet(STYLE_SETTING_INPUT)
        self.txt_project_name.setMinimumHeight(SETTINGS_INPUT_H)
        self.txt_project_name.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.txt_project_name.setPlaceholderText("Enter project name…")

        self.chk_auto_save = QCheckBox("Auto-save recording samples")
        self.chk_auto_save.setStyleSheet(STYLE_SETTING_CHECKBOX)

        sys_form = self._make_form_layout()
        self._add_form_row(sys_form, "Project Name:", self.txt_project_name)
        sys_layout.addLayout(sys_form)
        sys_layout.addWidget(self.chk_auto_save)
        layout.addWidget(sys_card)

        # ── Danger zone card ────────────────────────────────────────────
        layout.addWidget(self._make_section_label("DANGER ZONE", color=DANGER))
        danger_card, danger_layout = self._make_card()

        self.btn_clear_db = QPushButton("ERASE ALL COLLECTED DATA")
        self.btn_clear_db.setStyleSheet(STYLE_SETTING_BTN_DANGER)
        self.btn_clear_db.setFixedHeight(SETTINGS_BTN_H)
        self.btn_clear_db.setCursor(Qt.CursorShape.PointingHandCursor)

        danger_layout.addWidget(self.btn_clear_db)
        danger_layout.addWidget(
            self._make_hint(
                "This will permanently delete every recorded sample. Cannot be undone.",
                color=DANGER,
            )
        )
        layout.addWidget(danger_card)

        layout.addStretch()
        return widget

    def _build_firmware_section(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._make_section_label("FIRMWARE MANAGEMENT"))

        firmware_card, fw_layout = self._make_card()

        # Flash buttons
        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(12)
        button_grid.setVerticalSpacing(8)

        self.btn_flash_collect = self._make_primary_button("⬆  INSTALL DATA FIRMWARE")
        self.btn_flash_ai      = self._make_primary_button("⬆  INSTALL AI ENGINE")

        button_grid.addWidget(self.btn_flash_collect, 0, 0)
        button_grid.addWidget(self.btn_flash_ai, 0, 1)
        fw_layout.addLayout(button_grid)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(STYLE_SETTING_PROGRESS)
        self.progress_bar.setMinimumHeight(22)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        fw_layout.addWidget(self.progress_bar)

        # Console log
        fw_layout.addWidget(
            self._make_section_label("Console Output", color=TEXT_MUTED)
        )
        self.console_log = TerminalWidget(max_lines=1000, read_only=True)
        self.console_log.setMinimumHeight(180)
        self.console_log.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.console_log.setStyleSheet(STYLE_CONSOLE)
        fw_layout.addWidget(self.console_log)

        layout.addWidget(firmware_card)
        layout.addWidget(
            self._make_hint("Flash operation requires serial port selection and an active connection.")
        )
        return widget

    def _build_control_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.btn_open_workspace = QPushButton("OPEN VSCODE WORKSPACE")
        self.btn_open_workspace.setStyleSheet(STYLE_SETTING_BTN_OUTLINE)
        self.btn_open_workspace.setFixedHeight(SETTINGS_BTN_H)
        self.btn_open_workspace.setCursor(Qt.CursorShape.PointingHandCursor)

        row.addWidget(self.btn_open_workspace)
        row.addStretch()

        self.btn_revert = QPushButton("REVERT CHANGES")
        self.btn_revert.setStyleSheet(STYLE_SETTING_BTN_OUTLINE)
        self.btn_revert.setFixedHeight(SETTINGS_BTN_H)
        self.btn_revert.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_save = QPushButton("SAVE SETTINGS")
        self.btn_save.setStyleSheet(STYLE_SETTING_BTN_PRIMARY)
        self.btn_save.setFixedHeight(SETTINGS_BTN_H)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)

        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_save)
        return row

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_internal_signals(self) -> None:
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_revert.clicked.connect(self._on_revert_clicked)
        self.btn_clear_db.clicked.connect(self._on_clear_db_clicked)
        self.btn_flash_collect.clicked.connect(self._on_flash_collect_clicked)
        self.btn_flash_ai.clicked.connect(self._on_flash_ai_clicked)
        self.btn_open_workspace.clicked.connect(self._on_open_workspace_clicked)

    def _configure_accessibility(self) -> None:
        """Configure accessible names and deterministic keyboard traversal."""
        self.combo_sample_rate.setAccessibleName("Sample rate")
        self.combo_accel_scale.setAccessibleName("Accelerometer full scale")
        self.combo_gyro_scale.setAccessibleName("Gyroscope full scale")
        self.spin_window_size.setAccessibleName("Window size")
        self.spin_window_overlap.setAccessibleName("Window overlap")
        self.combo_ml_pipeline.setAccessibleName("Machine learning pipeline")
        self.txt_project_name.setAccessibleName("Project name")
        self.chk_auto_save.setAccessibleName("Auto save recording samples")
        self.btn_revert.setAccessibleName("Revert settings")
        self.btn_save.setAccessibleName("Save settings")
        self.btn_flash_collect.setAccessibleName("Install data firmware")
        self.btn_flash_ai.setAccessibleName("Install AI firmware")
        self.btn_clear_db.setAccessibleName("Erase all collected data")
        self.btn_open_workspace.setAccessibleName("Open VS Code workspace")

        self.setTabOrder(self.combo_sample_rate, self.combo_accel_scale)
        self.setTabOrder(self.combo_accel_scale, self.combo_gyro_scale)
        self.setTabOrder(self.combo_gyro_scale, self.spin_window_size)
        self.setTabOrder(self.spin_window_size, self.spin_window_overlap)
        self.setTabOrder(self.spin_window_overlap, self.combo_ml_pipeline)
        self.setTabOrder(self.combo_ml_pipeline, self.txt_project_name)
        self.setTabOrder(self.txt_project_name, self.chk_auto_save)
        self.setTabOrder(self.chk_auto_save, self.btn_open_workspace)
        self.setTabOrder(self.btn_open_workspace, self.btn_revert)
        self.setTabOrder(self.btn_revert, self.btn_save)
        self.setTabOrder(self.btn_save, self.btn_flash_collect)
        self.setTabOrder(self.btn_flash_collect, self.btn_flash_ai)
        self.setTabOrder(self.btn_flash_ai, self.btn_clear_db)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def _collect_config(self) -> dict[str, Any]:
        return {
            "sample_rate":    self.combo_sample_rate.currentText(),
            "accel_scale":    self.combo_accel_scale.currentText(),
            "gyro_scale":     self.combo_gyro_scale.currentText(),
            "window_size":    self.spin_window_size.value(),
            "window_overlap": self.spin_window_overlap.value(),
            "ml_pipeline":    self.combo_ml_pipeline.currentText(),
            "project_name":   self.txt_project_name.text().strip(),
            "auto_save":      self.chk_auto_save.isChecked(),
        }

    def _on_save_clicked(self) -> None:
        config = self._collect_config()
        if not config.get("project_name"):
            QMessageBox.warning(self, "Missing Field", "Project name cannot be empty.")
            self.txt_project_name.setFocus()
            return
        self._last_saved = config
        self.sig_settings_saved.emit(config)

    def _on_revert_clicked(self) -> None:
        self.load_settings(self._last_saved)

    def _on_clear_db_clicked(self) -> None:
        if confirm_destructive(
            self,
            title="Erase All Data",
            message=(
                "This will permanently delete every collected spell sample.\n\n"
                "Use this only when you are certain the dataset can be rebuilt."
            ),
            confirm_text="Erase Data",
        ):
            self.sig_clear_database.emit()

    def _on_flash_collect_clicked(self) -> None:
        self._begin_flash("[INFO] Starting DATA FIRMWARE flash…")
        self.sig_flash_data_firmware.emit()

    def _on_flash_ai_clicked(self) -> None:
        self._begin_flash("[INFO] Starting AI ENGINE flash…")
        self.sig_flash_inference_firmware.emit()

    def _begin_flash(self, initial_message: str) -> None:
        """Shared setup before any flash operation."""
        self.set_flash_buttons_enabled(False)
        self.console_log.clear()
        self.progress_bar.setValue(0)
        self.append_console_text(initial_message)

    def _on_open_workspace_clicked(self) -> None:
        """Open the current workspace in VS Code from inside the app."""
        target_str = str(VSCODE_WORKSPACE_FILE)

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
            "Open Workspace Failed",
            "Could not open VSCode workspace. Ensure the 'code' command is available in PATH.",
        )

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_card() -> tuple[QFrame, QVBoxLayout]:
        """Return a styled card frame together with its ready-to-use layout."""
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_SETTING_CARD)
        apply_soft_shadow(frame, blur_radius=20, y_offset=4, color="rgba(0, 0, 0, 0.10)")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        return frame, layout

    @staticmethod
    def _make_form_layout() -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        return form

    @staticmethod
    def _add_form_row(form: QFormLayout, label_text: str, widget: QWidget) -> None:
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;")
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.addRow(label, widget)

    @staticmethod
    def _make_section_label(text: str, color: str = SETTINGS_ACCENT) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
        )
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
        lbl.setStyleSheet(f"color: {TEXT_BODY}; font-weight: 600; font-size: 11px;")
        lbl.setMinimumWidth(LABEL_W)
        lbl.setMaximumWidth(LABEL_W)
        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        return row

    @staticmethod
    def _make_hint(text: str, color: str = TEXT_MUTED) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        lbl.setWordWrap(True)
        return lbl
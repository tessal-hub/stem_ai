"""PageSettings — Application, sensor, and machine-learning configuration view."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .common_design_tokens import (
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
)

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

_STYLE_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        border-top: none;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
"""

_STYLE_CARD = f"""
    #CardFrame {{
        background-color: {BG_LIGHT};
        border: none;
        border-radius: 8px;
    }}
"""

_STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {TEXT_BODY};
        border: 1px solid {BORDER_MID};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{
        background-color: {SETTINGS_HOVER_BG};
        border-color: {SETTINGS_ACCENT};
        color: {SETTINGS_ACCENT};
    }}
    QPushButton:disabled {{
        opacity: 0.5;
    }}
"""

_STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {SETTINGS_ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background-color: {SETTINGS_ACCENT_DARK}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

_STYLE_BTN_DANGER = f"""
    QPushButton {{
        background-color: {BG_WHITE};
        color: {DANGER};
        border: 1px solid {DANGER};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background-color: {DANGER}; color: {BG_WHITE}; }}
    QPushButton:disabled {{ opacity: 0.5; }}
"""

_STYLE_INPUT = f"""
    QComboBox, QLineEdit, QSpinBox {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER_MID};
        border-radius: 6px;
        padding: 4px 8px;
        color: {TEXT_BODY};
        font-weight: bold;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        selection-background-color: {SETTINGS_HOVER_BG};
        color: {TEXT_BODY};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{ border: none; width: 16px; }}
"""

_STYLE_CHECKBOX = f"""
    QCheckBox {{ color: {TEXT_BODY}; font-weight: bold; font-size: 11px; }}
    QCheckBox::indicator:checked {{
        background-color: {SETTINGS_ACCENT};
        border: 1px solid {SETTINGS_ACCENT};
        border-radius: 3px;
    }}
    QCheckBox::indicator:unchecked {{
        border: 1px solid {BORDER_MID};
        border-radius: 3px;
        background-color: {BG_WHITE};
    }}
"""

_STYLE_PROGRESS = f"""
    QProgressBar {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        text-align: center;
        background-color: {BG_WHITE};
    }}
    QProgressBar::chunk {{
        background-color: {SUCCESS};
        border-radius: 3px;
    }}
"""

_STYLE_CONSOLE = """
    QTextEdit {
        background-color: #0d0d0d;
        color: #00ff88;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 10px;
        padding: 8px;
    }
"""

# Fields that map directly to widget setters; order matches the UI top-to-bottom.
_SETTING_KEYS: tuple[str, ...] = (
    "sample_rate",
    "accel_scale",
    "gyro_scale",
    "window_size",
    "window_overlap",
    "ml_pipeline",
    "project_name",
    "auto_save",
)


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

        # Snapshot the store's current settings and populate the form.
        self._last_saved: dict[str, Any] = dict(self.data_store.settings)
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
        self.console_log.append(message.rstrip())
        sb = self.console_log.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

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
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(_STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(24, 24, 24, 24)
        inner.setSpacing(24)

        cols = QHBoxLayout()
        cols.setSpacing(24)
        cols.addWidget(self._build_hardware_column(), stretch=1)
        cols.addWidget(self._build_software_column(), stretch=1)
        inner.addLayout(cols, stretch=1)
        inner.addWidget(self._build_firmware_section())
        inner.addLayout(self._build_control_bar())

        outer.addWidget(self.main_container)

    def _build_hardware_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Sensor card ─────────────────────────────────────────────────
        layout.addWidget(self._make_section_label("IMU SENSOR CONFIGURATION"))
        sensor_card, sensor_layout = self._make_card()

        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz", "400 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g", "±16g"])
        self.combo_gyro_scale  = self._make_combo(["±250 dps", "±500 dps", "±1000 dps", "±2000 dps"])

        sensor_layout.addLayout(self._make_form_row("Sampling Rate:",     self.combo_sample_rate))
        sensor_layout.addLayout(self._make_form_row("Accelerometer FSR:", self.combo_accel_scale))
        sensor_layout.addLayout(self._make_form_row("Gyroscope FSR:",     self.combo_gyro_scale))
        layout.addWidget(sensor_card)

        # ── Windowing card ──────────────────────────────────────────────
        layout.addWidget(self._make_section_label("DATA WINDOWING (TIME-SERIES)"))
        window_card, window_layout = self._make_card()

        self.spin_window_size    = self._make_spinbox(10,  2000, step=10, suffix=" ms")
        self.spin_window_overlap = self._make_spinbox(0,   90,   step=10, suffix=" %")

        window_layout.addLayout(self._make_form_row("Window Size:", self.spin_window_size))
        window_layout.addLayout(self._make_form_row("Overlap:",     self.spin_window_overlap))
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
        layout.setSpacing(16)

        # ── ML pipeline card ────────────────────────────────────────────
        layout.addWidget(self._make_section_label("MACHINE LEARNING PIPELINE"))
        ml_card, ml_layout = self._make_card()

        self.combo_ml_pipeline = self._make_combo([
            "Random Forest (Edge)",
            "Support Vector Machine",
            "Tiny Neural Network (TFLite)",
        ])
        ml_layout.addLayout(self._make_form_row("Algorithm:", self.combo_ml_pipeline))
        ml_layout.addWidget(
            self._make_hint("Select the target inference engine for the ESP32.")
        )
        layout.addWidget(ml_card)

        # ── Project settings card ───────────────────────────────────────
        layout.addWidget(self._make_section_label("PROJECT SETTINGS"))
        sys_card, sys_layout = self._make_card()

        self.txt_project_name = QLineEdit()
        self.txt_project_name.setStyleSheet(_STYLE_INPUT)
        self.txt_project_name.setFixedHeight(SETTINGS_INPUT_H)
        self.txt_project_name.setPlaceholderText("Enter project name…")

        self.chk_auto_save = QCheckBox("Auto-save recording samples")
        self.chk_auto_save.setStyleSheet(_STYLE_CHECKBOX)

        sys_layout.addLayout(self._make_form_row("Project Name:", self.txt_project_name))
        sys_layout.addWidget(self.chk_auto_save)
        layout.addWidget(sys_card)

        # ── Danger zone card ────────────────────────────────────────────
        layout.addWidget(self._make_section_label("DANGER ZONE", color=DANGER))
        danger_card, danger_layout = self._make_card()

        self.btn_clear_db = QPushButton("ERASE ALL COLLECTED DATA")
        self.btn_clear_db.setStyleSheet(_STYLE_BTN_DANGER)
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
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_flash_collect = self._make_primary_button("⬆  INSTALL DATA FIRMWARE")
        self.btn_flash_ai      = self._make_primary_button("⬆  INSTALL AI ENGINE")

        btn_row.addWidget(self.btn_flash_collect, stretch=1)
        btn_row.addWidget(self.btn_flash_ai,      stretch=1)
        fw_layout.addLayout(btn_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(_STYLE_PROGRESS)
        self.progress_bar.setFixedHeight(24)
        fw_layout.addWidget(self.progress_bar)

        # Console log
        fw_layout.addWidget(
            self._make_section_label("Console Output", color=TEXT_MUTED)
        )
        self.console_log = QTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setFixedHeight(180)
        self.console_log.setStyleSheet(_STYLE_CONSOLE)
        fw_layout.addWidget(self.console_log)

        layout.addWidget(firmware_card)
        layout.addWidget(
            self._make_hint("Flash operation requires serial port selection and an active connection.")
        )
        return widget

    def _build_control_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()

        self.btn_revert = QPushButton("REVERT CHANGES")
        self.btn_revert.setStyleSheet(_STYLE_BTN_OUTLINE)
        self.btn_revert.setFixedHeight(SETTINGS_BTN_H)
        self.btn_revert.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_save = QPushButton("SAVE SETTINGS")
        self.btn_save.setStyleSheet(_STYLE_BTN_PRIMARY)
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
        reply = QMessageBox.warning(
            self,
            "Erase All Data",
            (
                "Are you sure you want to permanently delete ALL collected spell samples?\n\n"
                "This action cannot be undone."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
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

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_card() -> tuple[QFrame, QVBoxLayout]:
        """Return a styled card frame together with its ready-to-use layout."""
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(_STYLE_CARD)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        return frame, layout

    @staticmethod
    def _make_section_label(text: str, color: str = SETTINGS_ACCENT) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-weight: 900; font-size: 12px; letter-spacing: 1px;"
        )
        return lbl

    @staticmethod
    def _make_combo(items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setStyleSheet(_STYLE_INPUT)
        combo.setFixedHeight(SETTINGS_INPUT_H)
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
        spin.setStyleSheet(_STYLE_INPUT)
        spin.setFixedHeight(SETTINGS_INPUT_H)
        return spin

    @staticmethod
    def _make_primary_button(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setStyleSheet(_STYLE_BTN_PRIMARY)
        btn.setFixedHeight(SETTINGS_BTN_H)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    @staticmethod
    def _make_form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {TEXT_BODY}; font-weight: bold; font-size: 11px;")
        lbl.setMinimumWidth(LABEL_W)
        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        return row

    @staticmethod
    def _make_hint(text: str, color: str = TEXT_MUTED) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        lbl.setWordWrap(True)
        return lbl
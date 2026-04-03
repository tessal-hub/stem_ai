"""PageSettings — Application, sensor, and machine-learning configuration view."""
from __future__ import annotations
from typing import Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)

class Colors:
    ACCENT       = "#6366f1"
    ACCENT_DARK  = "#4f46e5"
    ACCENT_TEXT  = "#ffffff"
    BG_LIGHT     = "#f3f4f6"
    BG_WHITE     = "#ffffff"
    BORDER       = "#e5e7eb"
    BORDER_MID   = "#d1d5db"
    TEXT_BODY    = "#1f2937"
    TEXT_MUTED   = "#6b7280"
    HOVER_BG     = "#e0e7ff"
    SUCCESS      = "#10b981"
    DANGER       = "#ef4444"
    DANGER_DARK  = "#dc2626"

class Sizes:
    BTN_H    = 36
    INPUT_H  = 32
    LABEL_W  = 130 

STYLE_MAIN_CONTAINER = f"""
    #MainBox {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER};
        border-top: none;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
    }}
"""
STYLE_CARD = f"""
    #CardFrame {{
        background-color: {Colors.BG_LIGHT};
        border: none;
        border-radius: 8px;
    }}
"""
STYLE_BTN_OUTLINE = f"""
    QPushButton {{
        background-color: {Colors.BG_WHITE};
        color: {Colors.TEXT_BODY};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{
        background-color: {Colors.HOVER_BG};
        border-color: {Colors.ACCENT};
        color: {Colors.ACCENT};
    }}
"""
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {Colors.ACCENT};
        color: {Colors.ACCENT_TEXT};
        border: none;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background-color: {Colors.ACCENT_DARK}; }}
"""
STYLE_BTN_DANGER = f"""
    QPushButton {{
        background-color: {Colors.BG_WHITE};
        color: {Colors.DANGER};
        border: 1px solid {Colors.DANGER};
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background-color: {Colors.DANGER}; color: {Colors.BG_WHITE}; }}
"""
STYLE_INPUT = f"""
    QComboBox, QLineEdit, QSpinBox {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER_MID};
        border-radius: 6px;
        padding: 4px 8px;
        color: {Colors.TEXT_BODY};
        font-weight: bold;
        font-size: 11px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_WHITE};
        border: 1px solid {Colors.BORDER};
        selection-background-color: {Colors.HOVER_BG};
        color: {Colors.TEXT_BODY};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{ border: none; width: 16px; }}
"""
STYLE_CHECKBOX = f"""
    QCheckBox {{ color: {Colors.TEXT_BODY}; font-weight: bold; font-size: 11px; }}
    QCheckBox::indicator:checked {{ background-color: {Colors.ACCENT}; border: 1px solid {Colors.ACCENT}; border-radius: 3px; }}
    QCheckBox::indicator:unchecked {{ border: 1px solid {Colors.BORDER_MID}; border-radius: 3px; background-color: {Colors.BG_WHITE}; }}
"""

class PageSetting(QWidget):
    sig_settings_saved = pyqtSignal(dict)
    sig_clear_database = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        
        self._build_ui()
        self._connect_internal_signals()
        
        # Pull initial state from DataStore instead of hardcoded _DEFAULT_CONFIG
        self._last_saved: dict[str, Any] = dict(self.data_store.settings)
        self.load_settings(self._last_saved)

    def load_settings(self, config: dict[str, Any]) -> None:
        if "sample_rate"    in config: self.combo_sample_rate.setCurrentText(config["sample_rate"])
        if "accel_scale"    in config: self.combo_accel_scale.setCurrentText(config["accel_scale"])
        if "gyro_scale"     in config: self.combo_gyro_scale.setCurrentText(config["gyro_scale"])
        if "window_size"    in config: self.spin_window_size.setValue(config["window_size"])
        if "window_overlap" in config: self.spin_window_overlap.setValue(config["window_overlap"])
        if "ml_pipeline"    in config: self.combo_ml_pipeline.setCurrentText(config["ml_pipeline"])
        if "project_name"   in config: self.txt_project_name.setText(config["project_name"])
        if "auto_save"      in config: self.chk_auto_save.setChecked(config["auto_save"])

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 0, 12, 12)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(24, 24, 24, 24)
        inner.setSpacing(24)

        content = QHBoxLayout()
        content.setSpacing(24)
        content.addWidget(self._build_hardware_column(), stretch=1)
        content.addWidget(self._build_software_column(), stretch=1)
        inner.addLayout(content, stretch=1)

        inner.addLayout(self._build_control_bar())
        outer.addWidget(self.main_container)

    def _build_hardware_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._make_section_label("IMU SENSOR CONFIGURATION"))
        sensor_card = self._make_card_frame()
        sensor_layout = QVBoxLayout(sensor_card)
        sensor_layout.setContentsMargins(16, 16, 16, 16)
        sensor_layout.setSpacing(12)

        self.combo_sample_rate = self._make_combo(["50 Hz", "100 Hz", "200 Hz", "400 Hz"])
        self.combo_accel_scale = self._make_combo(["±2g", "±4g", "±8g", "±16g"])
        self.combo_gyro_scale  = self._make_combo(["±250 dps", "±500 dps", "±1000 dps", "±2000 dps"])

        sensor_layout.addLayout(self._make_form_row("Sampling Rate:",     self.combo_sample_rate))
        sensor_layout.addLayout(self._make_form_row("Accelerometer FSR:", self.combo_accel_scale))
        sensor_layout.addLayout(self._make_form_row("Gyroscope FSR:",     self.combo_gyro_scale))
        layout.addWidget(sensor_card)

        layout.addWidget(self._make_section_label("DATA WINDOWING (TIME-SERIES)"))
        window_card = self._make_card_frame()
        window_layout = QVBoxLayout(window_card)
        window_layout.setContentsMargins(16, 16, 16, 16)
        window_layout.setSpacing(12)

        self.spin_window_size    = self._make_spinbox(10,   2000, step=10, suffix=" ms")
        self.spin_window_overlap = self._make_spinbox(0,    90,   step=10, suffix=" %")

        window_layout.addLayout(self._make_form_row("Window Size:", self.spin_window_size))
        window_layout.addLayout(self._make_form_row("Overlap:",     self.spin_window_overlap))
        window_layout.addWidget(self._make_hint("Adjust window size based on typical spell cast duration."))
        layout.addWidget(window_card)

        layout.addStretch()
        return widget

    def _build_software_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._make_section_label("MACHINE LEARNING PIPELINE"))
        ml_card = self._make_card_frame()
        ml_layout = QVBoxLayout(ml_card)
        ml_layout.setContentsMargins(16, 16, 16, 16)
        ml_layout.setSpacing(12)

        self.combo_ml_pipeline = self._make_combo([
            "Random Forest (Edge)",
            "Support Vector Machine",
            "Tiny Neural Network (TFLite)",
        ])
        ml_layout.addLayout(self._make_form_row("Algorithm:", self.combo_ml_pipeline))
        ml_layout.addWidget(self._make_hint("Select the target inference engine for the ESP32."))
        layout.addWidget(ml_card)

        layout.addWidget(self._make_section_label("PROJECT SETTINGS"))
        sys_card = self._make_card_frame()
        sys_layout = QVBoxLayout(sys_card)
        sys_layout.setContentsMargins(16, 16, 16, 16)
        sys_layout.setSpacing(12)

        self.txt_project_name = QLineEdit()
        self.txt_project_name.setStyleSheet(STYLE_INPUT)
        self.txt_project_name.setFixedHeight(Sizes.INPUT_H)
        self.txt_project_name.setPlaceholderText("Enter project name…")

        self.chk_auto_save = QCheckBox("Auto-save recording samples")
        self.chk_auto_save.setStyleSheet(STYLE_CHECKBOX)

        sys_layout.addLayout(self._make_form_row("Project Name:", self.txt_project_name))
        sys_layout.addWidget(self.chk_auto_save)
        layout.addWidget(sys_card)

        layout.addWidget(self._make_section_label("DANGER ZONE", color=Colors.DANGER))
        danger_card = self._make_card_frame()
        danger_layout = QVBoxLayout(danger_card)
        danger_layout.setContentsMargins(16, 16, 16, 16)
        danger_layout.setSpacing(8)

        self.btn_clear_db = QPushButton("ERASE ALL COLLECTED DATA")
        self.btn_clear_db.setStyleSheet(STYLE_BTN_DANGER)
        self.btn_clear_db.setFixedHeight(Sizes.BTN_H)

        lbl_danger_hint = self._make_hint("This will permanently delete every recorded sample. Cannot be undone.", color=Colors.DANGER)
        danger_layout.addWidget(self.btn_clear_db)
        danger_layout.addWidget(lbl_danger_hint)
        layout.addWidget(danger_card)

        layout.addStretch()
        return widget

    def _build_control_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        self.btn_revert = QPushButton("REVERT CHANGES")
        self.btn_revert.setStyleSheet(STYLE_BTN_OUTLINE)
        self.btn_revert.setFixedHeight(Sizes.BTN_H)
        self.btn_save = QPushButton("SAVE SETTINGS")
        self.btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_save.setFixedHeight(Sizes.BTN_H)
        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_save)
        return row

    @staticmethod
    def _make_card_frame() -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setStyleSheet(STYLE_CARD)
        return frame

    @staticmethod
    def _make_section_label(text: str, color: str | None = None) -> QLabel:
        resolved = color if color is not None else Colors.ACCENT
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {resolved}; font-weight: 900; font-size: 12px; letter-spacing: 1px;")
        return lbl

    @staticmethod
    def _make_combo(items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setStyleSheet(STYLE_INPUT)
        combo.setFixedHeight(Sizes.INPUT_H)
        return combo

    @staticmethod
    def _make_spinbox(min_val: int, max_val: int, step: int, suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setStyleSheet(STYLE_INPUT)
        spin.setFixedHeight(Sizes.INPUT_H)
        return spin

    @staticmethod
    def _make_form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_BODY}; font-weight: bold; font-size: 11px;")
        lbl.setMinimumWidth(Sizes.LABEL_W)
        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        return row

    @staticmethod
    def _make_hint(text: str, color: str = Colors.TEXT_MUTED) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        lbl.setWordWrap(True)
        return lbl

    def _connect_internal_signals(self) -> None:
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_revert.clicked.connect(self._on_revert_clicked)
        self.btn_clear_db.clicked.connect(self._on_clear_db_clicked)

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
        self._last_saved = config          
        self.sig_settings_saved.emit(config)

    def _on_revert_clicked(self) -> None:
        self.load_settings(self._last_saved)

    def _on_clear_db_clicked(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Erase All Data",
            "Are you sure you want to permanently delete ALL collected spell samples?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sig_clear_database.emit()
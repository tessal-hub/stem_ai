"""
ui/wand_panels/settings_panel.py — Panel Cài đặt Hệ thống & Giao diện cho trang Wand.

Cung cấp các tùy chọn giao diện, đường dẫn dataset/model và chuyển đổi Chế độ Nâng cao
khi hoạt động ở chế độ cơ bản (không nâng cao).
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                             QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from logic.locale_manager import locale_manager
from logic.ui_i18n import normalize_ui_language, tr
from logic.theme_manager import theme_manager
from ui.asset_utils import resolve_asset_path
from ui.component_factory import make_card, make_section_label
from ui.i18n_bridge import tr_ui
from ui.modern_layout import MARGIN_COMFORTABLE, SPACING_SM, SPACING_XS
from ui.tokens import BTN_H, SETTINGS_ACCENT, SETTINGS_INPUT_H


class WandSettingsPanel(QWidget):
    """
    Panel Cài đặt tích hợp cho trang Wand trong chế độ cơ bản.
    """

    sig_settings_saved = pyqtSignal(dict)

    def __init__(self, data_store=None) -> None:
        super().__init__()
        self.data_store = data_store
        self._lang = locale_manager.current_language
        self._last_saved: dict[str, Any] = {}

        self._init_ui()
        self._init_signals()
        if data_store:
            self.load_settings(data_store.get_settings_snapshot())

    def _init_ui(self) -> None:
        """Khởi tạo giao diện panel cài đặt."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._title_lbl = make_section_label(tr_ui("section_appearance"))
        layout.addWidget(self._title_lbl)

        card, c_lay = make_card(
            margins=(16, 14, 16, 14),
            spacing=SPACING_SM,
        )

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        # 1. Ngôn ngữ
        self.lbl_language = QLabel(tr(self._lang, "label_ui_language"))
        self.lbl_language.setProperty("type", "settings_form_label")
        self.combo_ui_language = QComboBox()
        self.combo_ui_language.setFixedHeight(SETTINGS_INPUT_H)
        self.combo_ui_language.addItem("Tiếng Việt", "vi")
        self.combo_ui_language.addItem("English", "en")
        form.addRow(self.lbl_language, self.combo_ui_language)

        # 2. Giao diện (Theme)
        self.lbl_theme = QLabel(tr(self._lang, "label_theme"))
        self.lbl_theme.setProperty("type", "settings_form_label")
        self.combo_ui_theme = QComboBox()
        self.combo_ui_theme.setFixedHeight(SETTINGS_INPUT_H)
        self.combo_ui_theme.addItems(["Light Mode", "Dark Mode"])
        form.addRow(self.lbl_theme, self.combo_ui_theme)

        folder_icon = QIcon(resolve_asset_path("assets/icon/cooliocns SVG/File/Folder_Open.svg"))

        # 3. Thư mục Dataset
        self.lbl_dataset_dir = QLabel(tr(self._lang, "label_dataset_dir"))
        self.lbl_dataset_dir.setProperty("type", "settings_form_label")
        self.txt_dataset_dir = QLineEdit()
        self.txt_dataset_dir.setFixedHeight(SETTINGS_INPUT_H)
        self.txt_dataset_dir.setPlaceholderText("Select dataset directory...")

        self.btn_browse_dataset = QPushButton(" Browse")
        self.btn_browse_dataset.setIcon(folder_icon)
        self.btn_browse_dataset.setIconSize(QSize(14, 14))
        self.btn_browse_dataset.setProperty("type", "outline")
        self.btn_browse_dataset.setFixedHeight(SETTINGS_INPUT_H)

        ds_row = QHBoxLayout()
        ds_row.setContentsMargins(0, 0, 0, 0)
        ds_row.setSpacing(6)
        ds_row.addWidget(self.txt_dataset_dir, stretch=1)
        ds_row.addWidget(self.btn_browse_dataset)
        form.addRow(self.lbl_dataset_dir, ds_row)

        # 4. File Model (.tflite)
        self.lbl_model_path = QLabel(tr(self._lang, "label_model_path"))
        self.lbl_model_path.setProperty("type", "settings_form_label")
        self.txt_model_path = QLineEdit()
        self.txt_model_path.setFixedHeight(SETTINGS_INPUT_H)
        self.txt_model_path.setPlaceholderText("Select TFLite model (.tflite)...")

        self.btn_browse_model = QPushButton(" Browse")
        self.btn_browse_model.setIcon(folder_icon)
        self.btn_browse_model.setIconSize(QSize(14, 14))
        self.btn_browse_model.setProperty("type", "outline")
        self.btn_browse_model.setFixedHeight(SETTINGS_INPUT_H)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(6)
        model_row.addWidget(self.txt_model_path, stretch=1)
        model_row.addWidget(self.btn_browse_model)
        form.addRow(self.lbl_model_path, model_row)

        # 5. Chế độ nâng cao checkbox
        self.lbl_advanced_mode = QLabel("Chế độ nâng cao" if self._lang == "vi" else "Advanced Mode")
        self.lbl_advanced_mode.setProperty("type", "settings_form_label")
        self.chk_advanced_mode = QCheckBox()
        self.chk_advanced_mode.setToolTip("Bật giao diện đầy đủ (Console, UART Terminal, Primitives)")
        form.addRow(self.lbl_advanced_mode, self.chk_advanced_mode)

        c_lay.addLayout(form)

        # Nút Lưu cấu hình
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 500;")
        self.btn_save = QPushButton("LƯU CÀI ĐẶT" if self._lang == "vi" else "SAVE SETTINGS")
        self.btn_save.setProperty("type", "primary")
        self.btn_save.setFixedHeight(32)

        btn_box.addWidget(self.lbl_status, stretch=1)
        btn_box.addWidget(self.btn_save)
        c_lay.addLayout(btn_box)

        layout.addWidget(card)

    def _init_signals(self) -> None:
        """Kết nối các signal."""
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_browse_dataset.clicked.connect(self._on_browse_dataset)
        self.btn_browse_model.clicked.connect(self._on_browse_model)
        self.chk_advanced_mode.toggled.connect(self._on_advanced_mode_toggled)
        self.combo_ui_language.currentIndexChanged.connect(self._on_language_changed)
        self.combo_ui_theme.currentIndexChanged.connect(self._on_theme_changed)

    def load_settings(self, config: dict[str, Any]) -> None:
        """Đẩy dữ liệu cấu hình vào UI."""
        if not config:
            return
        self._last_saved = dict(config)

        # Language
        lang = normalize_ui_language(config.get("ui_language"))
        idx = self.combo_ui_language.findData(lang)
        if idx >= 0:
            self.combo_ui_language.blockSignals(True)
            self.combo_ui_language.setCurrentIndex(idx)
            self.combo_ui_language.blockSignals(False)

        # Theme
        theme_str = str(config.get("theme", theme_manager.current_theme)).lower()
        self.combo_ui_theme.blockSignals(True)
        self.combo_ui_theme.setCurrentIndex(1 if theme_str == "dark" else 0)
        self.combo_ui_theme.blockSignals(False)

        # Paths
        if "dataset_dir" in config:
            self.txt_dataset_dir.setText(str(config["dataset_dir"]))
        if "model_path" in config:
            self.txt_model_path.setText(str(config["model_path"]))

        # Advanced Mode
        adv = bool(config.get("advanced_mode", config.get("show_primitives_menu", False)))
        self.chk_advanced_mode.blockSignals(True)
        self.chk_advanced_mode.setChecked(adv)
        self.chk_advanced_mode.blockSignals(False)

    def apply_ui_language(self) -> None:
        """Cập nhật ngôn ngữ."""
        self._lang = locale_manager.current_language
        self._title_lbl.setText(tr_ui("section_appearance"))
        self.lbl_language.setText(tr(self._lang, "label_ui_language"))
        self.lbl_theme.setText(tr(self._lang, "label_theme"))
        self.lbl_dataset_dir.setText(tr(self._lang, "label_dataset_dir"))
        self.lbl_model_path.setText(tr(self._lang, "label_model_path"))
        self.lbl_advanced_mode.setText("Chế độ nâng cao" if self._lang == "vi" else "Advanced Mode")
        self.btn_save.setText("LƯU CÀI ĐẶT" if self._lang == "vi" else "SAVE SETTINGS")

    def _collect_config(self) -> dict[str, Any]:
        """Thu thập cấu hình hiện tại."""
        lang = self.combo_ui_language.currentData() or self._lang
        theme_str = "dark" if self.combo_ui_theme.currentIndex() == 1 else "light"
        adv = self.chk_advanced_mode.isChecked()
        return {
            "ui_language": lang,
            "theme": theme_str,
            "dataset_dir": self.txt_dataset_dir.text().strip(),
            "model_path": self.txt_model_path.text().strip(),
            "advanced_mode": adv,
            "show_primitives_menu": adv,
            "auto_save": True,
        }

    def _on_save_clicked(self) -> None:
        """Xử lý khi bấm nút Lưu cài đặt."""
        config = self._collect_config()
        self._last_saved = config
        self.sig_settings_saved.emit(config)
        self.lbl_status.setText("✓ Đã lưu" if self._lang == "vi" else "✓ Saved")

    def _on_advanced_mode_toggled(self, checked: bool) -> None:
        """Tự động phát tín hiệu lưu khi chuyển đổi chế độ nâng cao."""
        config = self._collect_config()
        config["advanced_mode"] = checked
        config["show_primitives_menu"] = checked
        self._last_saved = config
        self.sig_settings_saved.emit(config)

    def _on_language_changed(self) -> None:
        lang = self.combo_ui_language.currentData()
        if lang:
            locale_manager.current_language = lang
            self.apply_ui_language()

    def _on_theme_changed(self) -> None:
        theme_str = "dark" if self.combo_ui_theme.currentIndex() == 1 else "light"
        theme_manager.current_theme = theme_str

    def _on_browse_dataset(self) -> None:
        current = self.txt_dataset_dir.text().strip() or "."
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục Dataset", current)
        if folder:
            self.txt_dataset_dir.setText(folder)

    def _on_browse_model(self) -> None:
        current = self.txt_model_path.text().strip() or "."
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Model TFLite", current, "TFLite Models (*.tflite);;All Files (*)")
        if file_path:
            self.txt_model_path.setText(file_path)

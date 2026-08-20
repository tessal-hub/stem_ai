"""Hộp thoại cấu hình tổng hợp hiệu ứng cho spell: Màu đèn RGB LED và Âm thanh nhận diện."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Optional, Sequence, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import SOUNDS_PRESET_DIR, SOUNDS_USER_DIR
from logic.sound_player import SoundPlayer
from ui.i18n_bridge import tr_ui

PRESET_IDS = [
    "whoosh",
    "zap",
    "explosion",
    "chime",
    "thunder",
    "shield",
    "heal",
    "ice",
    "dark",
    "wind",
    "beam",
    "summon",
]

# Danh sách màu RGB mẫu thông dụng
PALETTE_COLORS: list[tuple[str, tuple[int, int, int]]] = [
    ("Red", (255, 0, 0)),
    ("Orange", (255, 128, 0)),
    ("Yellow", (255, 230, 0)),
    ("Green", (0, 255, 0)),
    ("Cyan", (0, 220, 255)),
    ("Blue", (0, 100, 255)),
    ("Purple", (170, 0, 255)),
    ("Pink", (255, 80, 180)),
    ("White", (255, 255, 255)),
]


class _SoundRowWidget(QWidget):
    """Widget dòng hiển thị tên âm thanh và nút nghe thử."""

    def __init__(
        self,
        display_name: str,
        sound_id: str,
        sound_player: Optional[SoundPlayer] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.sound_id = sound_id
        self._sound_player = sound_player

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        self.lbl_name = QLabel(display_name)
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: 500;")

        self.btn_preview = QPushButton("▶ " + tr_ui("btn_preview"))
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.setFixedHeight(28)
        self.btn_preview.setFixedWidth(90)
        self.btn_preview.setStyleSheet(
            "QPushButton { font-size: 12px; padding: 2px 8px; border-radius: 4px; "
            "background-color: #F0F0F2; color: #1C1C1E; border: 1px solid #D1D1D6; }"
            "QPushButton:hover { background-color: #E5E5EA; }"
        )
        self.btn_preview.clicked.connect(self._on_preview)

        layout.addWidget(self.lbl_name, 1)
        layout.addWidget(self.btn_preview, 0)

    def _on_preview(self) -> None:
        """Phát thử âm thanh."""
        if self._sound_player:
            self._sound_player.preview(self.sound_id)


class SoundSelectorDialog(QDialog):
    """Hộp thoại cấu hình hiệu ứng âm thanh và màu đèn RGB LED cho spell."""

    def __init__(
        self,
        current_sound_id: Optional[str] = None,
        sound_player: Optional[SoundPlayer] = None,
        preset_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None,
        spell_name: str = "",
        current_color: Union[Sequence[int], tuple[int, int, int]] = (255, 255, 255),
        current_volume: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self.spell_name = spell_name
        title = tr_ui("spell_effects_title")
        if spell_name:
            title = f"{title} — {spell_name}"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setMinimumHeight(520)
        self.setObjectName("SoundSelectorDialog")

        self._selected_sound_id = current_sound_id
        self._selected_color = list(current_color) if current_color else [255, 255, 255]
        self._selected_volume = max(0.0, min(1.0, float(current_volume)))
        self._sound_player = sound_player
        self._preset_dir = Path(preset_dir) if preset_dir else SOUNDS_PRESET_DIR
        self._user_dir = Path(user_dir) if user_dir else SOUNDS_USER_DIR
        self._user_dir.mkdir(parents=True, exist_ok=True)

        self._init_ui()
        self._populate_presets()
        self._populate_customs()
        self._select_initial_item()
        self._update_color_display()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        # ── 1. Phần cấu hình màu RGB LED Phần cứng ──
        lbl_color_section = QLabel("💡 " + tr_ui("section_led_color"))
        lbl_color_section.setStyleSheet("font-size: 13px; font-weight: 700; color: #3A3A3C;")
        layout.addWidget(lbl_color_section)

        color_card = QFrame()
        color_card.setStyleSheet(
            "QFrame { background-color: #F9F9FB; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px; }"
        )
        color_card_layout = QHBoxLayout(color_card)
        color_card_layout.setContentsMargins(10, 8, 10, 8)
        color_card_layout.setSpacing(12)

        # Chấm tròn hiển thị màu đang chọn
        self.btn_color_preview = QPushButton()
        self.btn_color_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color_preview.setFixedSize(34, 34)
        self.btn_color_preview.setToolTip(tr_ui("select_color_title"))
        self.btn_color_preview.clicked.connect(self._on_choose_custom_color)
        color_card_layout.addWidget(self.btn_color_preview, 0)

        # Palette màu nhanh
        palette_layout = QHBoxLayout()
        palette_layout.setSpacing(6)
        for name, rgb in PALETTE_COLORS:
            btn_pal = QPushButton()
            btn_pal.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pal.setFixedSize(22, 22)
            btn_pal.setToolTip(name)
            btn_pal.setStyleSheet(
                f"QPushButton {{ background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]}); "
                f"border-radius: 11px; border: 1.5px solid rgba(0, 0, 0, 0.2); }}"
                f"QPushButton:hover {{ border: 2.5px solid #007AFF; }}"
            )
            btn_pal.clicked.connect(lambda _, c=rgb: self._set_color(c))
            palette_layout.addWidget(btn_pal)

        color_card_layout.addLayout(palette_layout)
        color_card_layout.addStretch(1)

        # Nút chọn màu tùy biến (Color Dialog)
        self.btn_custom_color = QPushButton("🎨 " + tr_ui("btn_custom_color"))
        self.btn_custom_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_color.setFixedHeight(28)
        self.btn_custom_color.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 6px; "
            "background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #1C1C1E; }"
            "QPushButton:hover { background-color: #F0F0F2; }"
        )
        self.btn_custom_color.clicked.connect(self._on_choose_custom_color)
        color_card_layout.addWidget(self.btn_custom_color, 0)

        layout.addWidget(color_card)

        # ── 2. Phần cấu hình Âm thanh nhận diện ──
        lbl_sound_section = QLabel("🔊 " + tr_ui("section_sound_effect"))
        lbl_sound_section.setStyleSheet("font-size: 13px; font-weight: 700; color: #3A3A3C; margin-top: 4px;")
        layout.addWidget(lbl_sound_section)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #D1D1D6; border-radius: 6px; background: #FFFFFF; }"
            "QTabBar::tab { padding: 6px 16px; font-size: 13px; font-weight: 500; }"
        )

        # Tab 1: Presets
        preset_tab = QWidget()
        preset_layout = QVBoxLayout(preset_tab)
        preset_layout.setContentsMargins(8, 8, 8, 8)
        self.preset_list = QListWidget()
        self.preset_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item:selected { background-color: #E5E5EA; border-radius: 6px; }"
        )
        self.preset_list.itemClicked.connect(self._on_preset_clicked)
        self.preset_list.itemDoubleClicked.connect(self._on_preset_double_clicked)
        preset_layout.addWidget(self.preset_list)
        self.tab_widget.addTab(preset_tab, tr_ui("tab_presets"))

        # Tab 2: Custom
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        custom_layout.setContentsMargins(8, 8, 8, 8)
        self.custom_list = QListWidget()
        self.custom_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item:selected { background-color: #E5E5EA; border-radius: 6px; }"
        )
        self.custom_list.itemClicked.connect(self._on_custom_clicked)
        self.custom_list.itemDoubleClicked.connect(self._on_custom_double_clicked)
        custom_layout.addWidget(self.custom_list)

        btn_import = QPushButton("➕ " + tr_ui("btn_import_sound"))
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setFixedHeight(32)
        btn_import.setStyleSheet(
            "QPushButton { font-size: 13px; font-weight: 500; border-radius: 6px; "
            "background-color: #F2F2F7; border: 1px dashed #8E8E93; color: #007AFF; }"
            "QPushButton:hover { background-color: #E5E5EA; }"
        )
        btn_import.clicked.connect(self._on_import_sound)
        custom_layout.addWidget(btn_import)

        self.tab_widget.addTab(custom_tab, tr_ui("tab_custom"))
        layout.addWidget(self.tab_widget, 1)

        # ── 3. Thanh điều chỉnh âm lượng (Volume Slider) ──
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(10)
        self.lbl_volume = QLabel(tr_ui("sound_volume_label").format(pct=int(self._selected_volume * 100)))
        self.lbl_volume.setStyleSheet("font-size: 12px; font-weight: 500; color: #636366;")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(int(self._selected_volume * 100))
        self.slider_volume.valueChanged.connect(self._on_volume_changed)

        volume_layout.addWidget(self.lbl_volume, 0)
        volume_layout.addWidget(self.slider_volume, 1)
        layout.addLayout(volume_layout)

        # ── 4. Nút tác vụ chân trang (Bottom actions) ──
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.btn_clear = QPushButton("🔇 " + tr_ui("btn_remove_sound"))
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFixedHeight(34)
        self.btn_clear.setStyleSheet(
            "QPushButton { font-size: 13px; padding: 4px 12px; border-radius: 6px; "
            "background-color: #FFF0F0; color: #D32F2F; border: 1px solid #FFCDD2; }"
            "QPushButton:hover { background-color: #FFEBEE; }"
        )
        self.btn_clear.clicked.connect(self.on_clear_sound)
        action_layout.addWidget(self.btn_clear)

        action_layout.addStretch(1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_cancel = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.btn_ok = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(34)
        self.btn_ok.setFixedHeight(34)

        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        action_layout.addWidget(button_box)

        layout.addLayout(action_layout)

    def _set_color(self, rgb: Sequence[int]) -> None:
        """Cập nhật màu RGB được chọn."""
        self._selected_color = [int(rgb[0]), int(rgb[1]), int(rgb[2])]
        self._update_color_display()

    def _on_choose_custom_color(self) -> None:
        """Mở QColorDialog để chọn màu tùy biến."""
        initial = QColor(self._selected_color[0], self._selected_color[1], self._selected_color[2])
        chosen = QColorDialog.getColor(initial, self, tr_ui("select_color_title"))
        if chosen.isValid():
            self._set_color((chosen.red(), chosen.green(), chosen.blue()))

    def _update_color_display(self) -> None:
        """Cập nhật chấm tròn màu xem trước."""
        r, g, b = self._selected_color[0], self._selected_color[1], self._selected_color[2]
        self.btn_color_preview.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r}, {g}, {b}); border-radius: 17px; "
            f"border: 2.5px solid rgba(0, 0, 0, 0.25); }}"
            f"QPushButton:hover {{ border: 2.5px solid #007AFF; }}"
        )

    def _on_volume_changed(self, value: int) -> None:
        """Cập nhật âm lượng khi kéo slider."""
        self._selected_volume = value / 100.0
        self.lbl_volume.setText(tr_ui("sound_volume_label").format(pct=value))

    def _populate_presets(self) -> None:
        """Nạp danh sách 12 âm thanh preset."""
        self.preset_list.clear()
        for pid in PRESET_IDS:
            sound_id = f"preset:{pid}"
            disp = tr_ui(f"preset_{pid}")
            if not disp or disp == f"preset_{pid}":
                disp = pid.capitalize()

            item = QListWidgetItem(self.preset_list)
            item.setData(Qt.ItemDataRole.UserRole, sound_id)
            row_widget = _SoundRowWidget(disp, sound_id, self._sound_player)
            item.setSizeHint(row_widget.sizeHint())
            self.preset_list.setItemWidget(item, row_widget)

    def _populate_customs(self) -> None:
        """Nạp danh sách âm thanh custom do người dùng nhập."""
        self.custom_list.clear()
        if not self._user_dir.exists():
            return

        supported_exts = {".mp3", ".wav"}
        for f in sorted(self._user_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in supported_exts:
                sound_id = f"custom:{f.name}"
                item = QListWidgetItem(self.custom_list)
                item.setData(Qt.ItemDataRole.UserRole, sound_id)
                row_widget = _SoundRowWidget(f.name, sound_id, self._sound_player)
                item.setSizeHint(row_widget.sizeHint())
                self.custom_list.setItemWidget(item, row_widget)

    def _select_initial_item(self) -> None:
        """Đánh dấu mục đang chọn ban đầu nếu có."""
        if not self._selected_sound_id:
            return

        if self._selected_sound_id.startswith("preset:"):
            self.tab_widget.setCurrentIndex(0)
            for i in range(self.preset_list.count()):
                item = self.preset_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self._selected_sound_id:
                    self.preset_list.setCurrentItem(item)
                    break
        elif self._selected_sound_id.startswith("custom:"):
            self.tab_widget.setCurrentIndex(1)
            for i in range(self.custom_list.count()):
                item = self.custom_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self._selected_sound_id:
                    self.custom_list.setCurrentItem(item)
                    break

    def _on_preset_clicked(self, item: QListWidgetItem) -> None:
        """Cập nhật sound_id khi bấm chọn preset."""
        self._selected_sound_id = item.data(Qt.ItemDataRole.UserRole)

    def _on_preset_double_clicked(self, item: QListWidgetItem) -> None:
        """Xác nhận chọn khi double click preset."""
        self._selected_sound_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_custom_clicked(self, item: QListWidgetItem) -> None:
        """Cập nhật sound_id khi bấm chọn custom sound."""
        self._selected_sound_id = item.data(Qt.ItemDataRole.UserRole)

    def _on_custom_double_clicked(self, item: QListWidgetItem) -> None:
        """Xác nhận chọn khi double click custom sound."""
        self._selected_sound_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_import_sound(self) -> None:
        """Mở file dialog để nhập file âm thanh mới."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr_ui("btn_import_sound"),
            "",
            "Audio Files (*.mp3 *.wav);;All Files (*)",
        )
        if not file_path:
            return

        src = Path(file_path)
        dest = self._user_dir / src.name

        # Nếu trùng tên, đổi tên tự động
        counter = 1
        stem = src.stem
        ext = src.suffix
        while dest.exists():
            dest = self._user_dir / f"{stem}_{counter}{ext}"
            counter += 1

        try:
            shutil.copy2(str(src), str(dest))
            self._populate_customs()
            sound_id = f"custom:{dest.name}"
            self._selected_sound_id = sound_id
            self.tab_widget.setCurrentIndex(1)
            # Chọn item mới thêm
            for i in range(self.custom_list.count()):
                item = self.custom_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == sound_id:
                    self.custom_list.setCurrentItem(item)
                    break
        except Exception as e:
            print(f"[ERROR] Failed to import audio file: {e}")

    def on_clear_sound(self) -> None:
        """Xóa lựa chọn âm thanh (Mute)."""
        self._selected_sound_id = None
        self.preset_list.clearSelection()
        self.custom_list.clearSelection()
        self.accept()

    def get_selected_sound(self) -> Optional[str]:
        """Lấy sound_id đã chọn hoặc None nếu tắt âm."""
        return self._selected_sound_id

    def get_selected_color(self) -> list[int]:
        """Lấy mã màu RGB đã chọn [r, g, b]."""
        return list(self._selected_color)

    def get_selected_volume(self) -> float:
        """Lấy âm lượng đã chọn (0.0 - 1.0)."""
        return float(self._selected_volume)

    @classmethod
    def select_effects(
        cls,
        spell_name: str,
        current_color: Sequence[int] = (255, 255, 255),
        current_sound_id: Optional[str] = None,
        current_volume: float = 1.0,
        sound_player: Optional[SoundPlayer] = None,
        preset_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> tuple[bool, list[int], Optional[str], float]:
        """Hàm tiện ích modal mở dialog cấu hình toàn diện (Màu + Âm thanh + Âm lượng)."""
        dialog = cls(
            current_sound_id=current_sound_id,
            sound_player=sound_player,
            preset_dir=preset_dir,
            user_dir=user_dir,
            parent=parent,
            spell_name=spell_name,
            current_color=current_color,
            current_volume=current_volume,
        )
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            return (
                True,
                dialog.get_selected_color(),
                dialog.get_selected_sound(),
                dialog.get_selected_volume(),
            )
        return False, list(current_color), current_sound_id, current_volume

    @classmethod
    def select_sound(
        cls,
        current_sound_id: Optional[str] = None,
        sound_player: Optional[SoundPlayer] = None,
        preset_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> tuple[bool, Optional[str]]:
        """Hàm tiện ích tương thích ngược để chọn riêng sound_id."""
        dialog = cls(
            current_sound_id=current_sound_id,
            sound_player=sound_player,
            preset_dir=preset_dir,
            user_dir=user_dir,
            parent=parent,
        )
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            return True, dialog.get_selected_sound()
        return False, current_sound_id

"""Widget phần tử danh sách phép (Spell Card) hiển thị màu LED và âm thanh đi kèm."""

from __future__ import annotations

from typing import Optional, Sequence, Union

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from logic.theme_manager import theme_manager
from ui.i18n_bridge import tr_ui


class SpellCardWidget(QWidget):
    """Widget dòng hiển thị thông tin spell trong danh sách quản lý spell."""

    sig_color_clicked = pyqtSignal(str)
    sig_sound_clicked = pyqtSignal(str)

    def __init__(
        self,
        spell_name: str,
        sample_count: int = 0,
        color: Union[Sequence[int], tuple[int, int, int]] = (255, 255, 255),
        sound_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Khởi tạo widget thẻ phép.

        Args:
            spell_name: Tên spell.
            sample_count: Số lượng mẫu đã thu thập.
            color: Màu RGB (3 phần tử 0-255).
            sound_id: Mã định danh âm thanh hoặc None.
            parent: Widget cha.
        """
        super().__init__(parent)
        self.spell_name = spell_name
        self._count = sample_count
        self._color = list(color) if color else [255, 255, 255]
        self._sound_id = sound_id

        self.setFixedHeight(56)
        self.setMinimumHeight(56)
        self._init_ui()
        self._refresh_display()

    def sizeHint(self) -> QSize:
        return QSize(220, 56)

    def _init_ui(self) -> None:
        """Khởi tạo các thành phần giao diện của widget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(10)

        # Dot màu — hit area 32px, visual 22px centered (touch-friendly)
        self.btn_color = QPushButton()
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.setFixedSize(32, 32)
        self.btn_color.setToolTip(tr_ui("tooltip_color_dot"))
        self.btn_color.setAccessibleName(tr_ui("tooltip_color_dot"))
        self.btn_color.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_color.clicked.connect(self._on_color_click)
        layout.addWidget(self.btn_color, 0)

        # Cột ở giữa: Tên spell + Dòng phụ hiển thị màu RGB & Âm thanh
        mid_col = QVBoxLayout()
        mid_col.setContentsMargins(0, 0, 0, 0)
        mid_col.setSpacing(2)

        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: 600;")
        mid_col.addWidget(self.lbl_name)

        self.lbl_subtitle = QLabel()
        self.lbl_subtitle.setProperty("type", "settings_hint")
        self.lbl_subtitle.setWordWrap(True)
        mid_col.addWidget(self.lbl_subtitle)

        layout.addLayout(mid_col, 1)

        # Nút âm thanh — 36px touch, tonal fill, palette-driven (theme-safe)
        self.btn_sound = QPushButton()
        self.btn_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sound.setFixedSize(36, 36)
        self.btn_sound.setToolTip(tr_ui("tooltip_sound_icon"))
        self.btn_sound.setAccessibleName(tr_ui("tooltip_sound_icon"))
        self.btn_sound.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_sound.clicked.connect(self._on_sound_click)
        layout.addWidget(self.btn_sound, 0)
        self._apply_theme_styles()

    def _apply_theme_styles(self) -> None:
        """Gán màu theo palette hiện tại — gọi lại khi theme đổi để không còn hex hard-code."""
        p = theme_manager.get_palette()
        is_dark = theme_manager.current_theme == "dark"
        self.lbl_subtitle.setStyleSheet(f"font-size: 11px; color: {p.TEXT_TERTIARY};")
        chip_hover = "rgba(255, 255, 255, 0.14)" if is_dark else p.SURFACE_SECONDARY
        focus_border = "#f2f2f7" if is_dark else "#0f172a"
        self.btn_sound.setStyleSheet(
            f"QPushButton {{ font-size: 14px; border: 1px solid {p.BORDER}; "
            f"background: {p.SURFACE_TERTIARY}; border-radius: 8px; padding: 0px; color: {p.TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ background-color: {chip_hover}; border-color: {p.BORDER}; }}"
            f"QPushButton:focus {{ border-color: {p.PRIMARY}; }}"
        )
        self._focus_border = focus_border

    def _on_color_click(self) -> None:
        """Phát tín hiệu khi người dùng bấm vào nút đổi màu."""
        self.sig_color_clicked.emit(self.spell_name)

    def _on_sound_click(self) -> None:
        """Phát tín hiệu khi người dùng bấm vào nút đổi âm thanh."""
        self.sig_sound_clicked.emit(self.spell_name)

    def _refresh_display(self) -> None:
        """Cập nhật giao diện nút màu, nhãn tên, dòng phụ và nút âm thanh."""
        # Cập nhật tên và số lượng mẫu
        self.lbl_name.setText(f"{self.spell_name} ({self._count})")

        # Dot màu — visual centered in 32px hit area
        r, g, b = (self._color[0], self._color[1], self._color[2]) if len(self._color) >= 3 else (255, 255, 255)
        self.btn_color.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r}, {g}, {b}); border-radius: 16px; "
            f"border: 2px solid rgba(15, 23, 42, 0.12); min-width: 22px; min-height: 22px; margin: 5px; }}"
            f"QPushButton:hover {{ border: 2px solid {theme_manager.get_palette().PRIMARY}; }}"
            f"QPushButton:focus {{ border: 2px solid {self._focus_border}; }}"
        )

        # Cập nhật nút âm thanh và dòng phụ
        sound_label = tr_ui("no_sound")
        if self._sound_id:
            self.btn_sound.setText("🔊")
            disp = self._sound_id.split(":")[-1]
            if self._sound_id.startswith("preset:"):
                trans = tr_ui(f"preset_{disp}")
                if trans and trans != f"preset_{disp}":
                    disp = trans.split("(")[0].strip()
            sound_label = disp
        else:
            self.btn_sound.setText("🔇")

        self.lbl_subtitle.setText(f"RGB({r},{g},{b}) • {sound_label}")

    def update_config(
        self,
        color: Optional[Union[Sequence[int], tuple[int, int, int]]] = None,
        sound_id: Optional[str] = None,
        count: Optional[int] = None,
    ) -> None:
        """Cập nhật thuộc tính của spell card.

        Args:
            color: Màu RGB mới.
            sound_id: Mã âm thanh mới.
            count: Số lượng mẫu mới.
        """
        if color is not None:
            self._color = list(color)
        if sound_id is not None or sound_id is None:
            self._sound_id = sound_id
        if count is not None:
            self._count = int(count)
        self._refresh_display()

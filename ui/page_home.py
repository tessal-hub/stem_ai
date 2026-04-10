"""PageHome — main dashboard view."""

from __future__ import annotations

import os
from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ui.wand_3d_widget import Wand3DWidget
from ui.tokens import (
    ACCENT,
    ACCENT_TEXT,
    BG_LIGHT,
    BG_WHITE,
    BORDER,
    BORDER_MID,
    DANGER,
    HOVER_BG,
    HOME_ATTACH_H,
    HOME_RIGHT_W,
    HOME_STATUS_H,
    HOME_VIEWER_MIN_H,
    ICON,
    STYLE_HOME_ACTION_BTN,
    STYLE_HOME_ACTION_BTN_SECONDARY,
    STYLE_HOME_ATTACHMENT_BAR,
    STYLE_HOME_ATTACHMENT_PILL,
    STYLE_HOME_MAIN_CONTAINER as STYLE_MAIN_CONTAINER,
    STYLE_HOME_MANAGER_BAR,
    STYLE_HOME_MANAGER_ROW,
    STYLE_HOME_MODE_LABEL,
    STYLE_HOME_MODULE_BTN,
    STYLE_HOME_RIGHT_PANEL,
    STYLE_HOME_RIGHT_SECTION,
    STYLE_HOME_SECTION_SUBTITLE,
    STYLE_HOME_SECTION_TITLE,
    STYLE_HOME_SPELL_BTN,
    STYLE_HOME_STAT_NAME,
    STYLE_HOME_STAT_VALUE,
    STYLE_HOME_STATUS_BAR,
    STYLE_HOME_VIEWER_CARD,
    STYLE_SCROLL_AREA,
    STYLE_TRANSPARENT_WIDGET,
    TEXT_BODY,
    TEXT_MUTED,
)
from ui.modern_layout import (
    create_modern_card,
    add_card_shadow,
    create_elevated_panel,
    MARGIN_COMFORTABLE,
    MARGIN_STANDARD,
    SPACING_MD,
    SPACING_LG,
    SPACING_SM,
    SPACING_XS,
)


_HOME_SYSTEM_STAT_KEYS = (
    "CPU",
    "RAM",
    "Port",
    "Baudrate",
    "UDP Rate",
    "UDP Jitter",
    "UDP Loss",
)


@dataclass(frozen=True)
class ModuleEntry:
    icon: str
    label: str


MODULES: list[ModuleEntry] = [
    ModuleEntry("assets/icon/fan.svg", "FAN"),
    ModuleEntry("assets/icon/led.svg", "LED"),
    ModuleEntry("assets/icon/speaker.svg", "SPEAKER"),
    ModuleEntry("assets/icon/mouse.svg", "MOUSE"),
    ModuleEntry("assets/icon/keyboard.svg", "KEY"),
]


class PageHome(QWidget):
    sig_simulation_replay_requested = pyqtSignal()
    sig_simulation_stop_requested = pyqtSignal()
    sig_calibrate_requested = pyqtSignal()
    sig_quick_test_requested = pyqtSignal()

    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._stat_rows: dict[str, tuple[QLabel, QLabel, QProgressBar]] = {}
        self._manager_keys: tuple[str, ...] = ()
        self._build_ui()
        self._configure_accessibility()
        self.set_connection_status(False)

    def set_connection_status(self, connected: bool) -> None:
        if connected:
            self.status_bar.setText("▶ WAND CONNECTED - READY")
            self.status_bar.setStyleSheet(self._status_style(ACCENT, ACCENT_TEXT))
        else:
            self.status_bar.setText("● WAND DISCONNECTED - WAITING FOR DEVICE")
            self.status_bar.setStyleSheet(self._status_style(DANGER, ACCENT_TEXT))

    def set_mode(self, mode: str) -> None:
        self.mode_label.setText(f"MODE:  {mode.upper()}")

    def set_sensor_readout(self, values: list[float] | tuple[float, ...]) -> None:
        return

    def set_simulation_running(self, active: bool) -> None:
        return

    def set_inference_active(self, active: bool) -> None:
        """Set inference mode visual state for quick test."""
        self.btn_quick_test.setEnabled(not active)
        if active:
            self.btn_quick_test.setText("▶ TESTING...")
        else:
            self.btn_quick_test.setText("▶ QUICK TEST")

    def update_manager_stats(self, stats: dict[str, str]) -> None:
        if stats is None:
            return

        normalized = {str(key): str(value) for key, value in stats.items()}
        normalized_keys = tuple(normalized.keys())
        if not any(key in _HOME_SYSTEM_STAT_KEYS for key in normalized):
            return
        if normalized_keys != self._manager_keys:
            self._rebuild_manager_rows(normalized)
            return

        for key, value in normalized.items():
            row = self._stat_rows.get(key)
            if row is None:
                continue
            name_label, value_label, progress_bar = row
            value_label.setText(value)
            progress_bar.setValue(self._stat_value_to_percent(value))

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setStyleSheet(STYLE_SCROLL_AREA)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setFrameShape(QFrame.Shape.NoFrame)
        self.main_container.setFrameShadow(QFrame.Shadow.Plain)
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        # Use modern breathing room: 24px margins and 16px spacing
        inner.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        inner.setSpacing(SPACING_LG)

        inner.addWidget(self._build_status_bar())

        content = QHBoxLayout()
        # Increased spacing between major columns
        content.setSpacing(SPACING_LG)
        content.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self._build_center_column(), stretch=1)
        content.addWidget(self._build_right_column(), stretch=0)
        inner.addLayout(content, stretch=1)

        page_scroll.setWidget(self.main_container)
        outer.addWidget(page_scroll)

    def _build_status_bar(self) -> QLabel:
        self.status_bar = QLabel("● WAND DISCONNECTED - WAITING FOR DEVICE")
        self.status_bar.setObjectName("HomeStatusBar")
        self.status_bar.setStyleSheet(self._status_style(DANGER, ACCENT_TEXT))
        self.status_bar.setFixedHeight(HOME_STATUS_H)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return self.status_bar

    @staticmethod
    def _status_style(bg_color: str, fg_color: str) -> str:
        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {fg_color};
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 900;
                border-radius: 8px;
                letter-spacing: 1px;
            }}
        """

    def _build_center_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)  # Modern 16px spacing between major sections
        layout.addWidget(self._build_viewer_box(), stretch=1)
        layout.addWidget(self._build_attachment_bar())
        return widget

    def _build_viewer_box(self) -> QFrame:
        box = QFrame()
        box.setObjectName("HomeViewerCard")
        box.setStyleSheet(STYLE_HOME_VIEWER_CARD)
        # Add shadow for elevation
        add_card_shadow(box, blur_radius=14, offset_y=4, color="rgba(0, 0, 0, 0.10)")
        
        layout = QVBoxLayout(box)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_MD)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(SPACING_MD)
        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(2)
        title = QLabel("3D WAND ORIENTATION")
        title.setStyleSheet(STYLE_HOME_SECTION_TITLE)
        subtitle = QLabel("Complementary filter using normalized MPU6050 samples")
        subtitle.setStyleSheet(STYLE_HOME_SECTION_SUBTITLE)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()
        layout.addLayout(header)

        self.sim_view = QFrame()
        self.sim_view.setObjectName("HomeViewerSurface")
        self.sim_view.setFrameShape(QFrame.Shape.NoFrame)
        self.sim_view.setFrameShadow(QFrame.Shadow.Plain)
        self.sim_view.setStyleSheet(STYLE_HOME_VIEWER_CARD)
        self.sim_view.setMinimumHeight(HOME_VIEWER_MIN_H)

        sim_inner = QVBoxLayout(self.sim_view)
        sim_inner.setContentsMargins(1, 1, 1, 1)
        self.wand_3d = Wand3DWidget()
        sim_inner.addWidget(self.wand_3d, stretch=1)

        layout.addWidget(self.sim_view, stretch=1)
        return box

    def _build_attachment_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("HomeAttachmentBar")
        bar.setFixedHeight(HOME_ATTACH_H)
        bar.setStyleSheet(STYLE_HOME_ATTACHMENT_BAR)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        label = QLabel("ATTACHMENTS")
        label.setStyleSheet(STYLE_HOME_SECTION_SUBTITLE)
        layout.addWidget(label)

        for mod in MODULES:
            layout.addWidget(self._make_module_button(mod))

        layout.addStretch()

        self.btn_simulate = QPushButton("REPLAY LAST INPUT")
        self.btn_simulate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simulate.setStyleSheet(STYLE_HOME_ACTION_BTN)
        self.btn_simulate.clicked.connect(self.sig_simulation_replay_requested.emit)

        self.btn_sim_stop = QPushButton("STOP SIM")
        self.btn_sim_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sim_stop.setStyleSheet(STYLE_HOME_ACTION_BTN_SECONDARY)
        self.btn_sim_stop.clicked.connect(self.sig_simulation_stop_requested.emit)
        self.btn_sim_stop.setEnabled(False)

        self.btn_calibrate = QPushButton("⚙ CALIBRATE WAND")
        self.btn_calibrate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calibrate.setStyleSheet(STYLE_HOME_ACTION_BTN)
        self.btn_calibrate.setToolTip("Calibrate wand sensor offsets and scales")
        self.btn_calibrate.clicked.connect(self.sig_calibrate_requested.emit)

        self.btn_quick_test = QPushButton("▶ QUICK TEST")
        self.btn_quick_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_test.setStyleSheet(STYLE_HOME_ACTION_BTN)
        self.btn_quick_test.setToolTip("Perform quick gesture recognition test")
        self.btn_quick_test.clicked.connect(self.sig_quick_test_requested.emit)

        layout.addWidget(self.btn_simulate)
        layout.addWidget(self.btn_sim_stop)
        layout.addWidget(self.btn_calibrate)
        layout.addWidget(self.btn_quick_test)
        return bar

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("HomeRightPanel")
        widget.setFixedWidth(HOME_RIGHT_W)
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        widget.setStyleSheet(STYLE_HOME_RIGHT_PANEL)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_LG)  # Modern 16px spacing between right column sections
        layout.addWidget(self._build_mode_box())
        layout.addWidget(self._build_spellbook())
        layout.addWidget(self._build_manager_box(), stretch=1)
        return widget

    def _build_mode_box(self) -> QFrame:
        box = QFrame()
        box.setObjectName("HomeRightSection")
        box.setStyleSheet(STYLE_HOME_RIGHT_SECTION)
        box.setFixedHeight(48)
        # Add shadow for proper card elevation
        add_card_shadow(box, blur_radius=10, offset_y=2, color="rgba(0, 0, 0, 0.08)")

        layout = QHBoxLayout(box)
        layout.setContentsMargins(MARGIN_COMFORTABLE, 0, MARGIN_COMFORTABLE, 0)
        layout.setSpacing(SPACING_MD)
        self.mode_label = QLabel("MODE:  IDLE")
        self.mode_label.setObjectName("HomeModePill")
        self.mode_label.setStyleSheet(STYLE_HOME_MODE_LABEL)
        layout.addWidget(self.mode_label)
        layout.addStretch()
        return box

    def _build_spellbook(self) -> QFrame:
        box = QFrame()
        box.setObjectName("HomeRightSection")
        box.setStyleSheet(STYLE_HOME_RIGHT_SECTION)
        # Add shadow for proper card elevation
        add_card_shadow(box, blur_radius=10, offset_y=2, color="rgba(0, 0, 0, 0.08)")

        layout = QVBoxLayout(box)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_MD)

        title = QLabel("SPELLBOOK")
        title.setStyleSheet(STYLE_HOME_SECTION_TITLE)
        layout.addWidget(title)

        content = QWidget()
        content.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        spell_layout = QVBoxLayout(content)
        spell_layout.setContentsMargins(0, 0, 0, 0)
        spell_layout.setSpacing(SPACING_SM)

        spells = self.data_store.get_spell_list()
        max_display = 3
        if not spells:
            no_spell = QLabel("No spells recorded yet.")
            no_spell.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-style: italic;")
            spell_layout.addWidget(no_spell)
        else:
            for spell in spells[:max_display]:
                spell_layout.addWidget(self._make_spell_button(f"✨ {spell}"))
            if len(spells) > max_display:
                overflow_lbl = QLabel(f"+ {len(spells) - max_display} more")
                overflow_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-style: italic; padding: 2px 0;")
                spell_layout.addWidget(overflow_lbl)

        spell_layout.addStretch()
        layout.addWidget(content)
        return box

    def _build_manager_box(self) -> QFrame:
        box = QFrame()
        box.setObjectName("HomeRightSection")
        box.setStyleSheet(STYLE_HOME_RIGHT_SECTION)
        box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        # Add shadow for proper card elevation
        add_card_shadow(box, blur_radius=10, offset_y=2, color="rgba(0, 0, 0, 0.08)")

        layout = QVBoxLayout(box)
        layout.setContentsMargins(MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE, MARGIN_COMFORTABLE)
        layout.setSpacing(SPACING_SM)

        title = QLabel("SYSTEM MANAGER")
        title.setStyleSheet(STYLE_HOME_SECTION_SUBTITLE)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._manager_container = QWidget()
        self._manager_container.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        self._manager_layout = QVBoxLayout(self._manager_container)
        self._manager_layout.setContentsMargins(0, 0, 0, 0)
        self._manager_layout.setSpacing(SPACING_SM)
        scroll.setWidget(self._manager_container)
        layout.addWidget(scroll, stretch=1)

        self._rebuild_manager_rows(self.data_store.system_stats)
        return box

    def _rebuild_manager_rows(self, stats: dict[str, str]) -> None:
        self._manager_keys = tuple(stats.keys())
        self._stat_rows = {}

        while self._manager_layout.count():
            item = self._manager_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for key, value in stats.items():
            row = QWidget()
            row.setObjectName("HomeManagerRow")
            row.setStyleSheet(STYLE_HOME_MANAGER_ROW)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACING_XS)

            top = QHBoxLayout()
            top.setContentsMargins(0, 0, 0, 0)
            top.setSpacing(SPACING_SM)

            indicator = QLabel()
            indicator.setFixedSize(8, 8)
            indicator.setStyleSheet(f"background-color: {ACCENT}; border-radius: 4px;")

            name_label = QLabel(key)
            name_label.setStyleSheet(STYLE_HOME_STAT_NAME)
            value_label = QLabel(value)
            value_label.setObjectName("HomeManagerValue")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setStyleSheet(STYLE_HOME_STAT_VALUE)
            value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            top.addWidget(indicator)
            top.addWidget(name_label)
            top.addStretch()
            top.addWidget(value_label)

            progress = QProgressBar()
            progress.setObjectName("HomeManagerBar")
            progress.setRange(0, 100)
            progress.setTextVisible(False)
            progress.setFixedHeight(4)
            progress.setStyleSheet(STYLE_HOME_MANAGER_BAR)
            progress.setValue(self._stat_value_to_percent(value))

            row_layout.addLayout(top)
            row_layout.addWidget(progress)
            self._manager_layout.addWidget(row)
            self._stat_rows[key] = (name_label, value_label, progress)

        self._manager_layout.addStretch()

    @staticmethod
    def _make_spell_button(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(32)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(STYLE_HOME_SPELL_BTN)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAccessibleName(f"Spell button {label}")
        return btn

    @staticmethod
    def _make_module_button(mod: ModuleEntry) -> QPushButton:
        btn = QPushButton(mod.label)
        btn.setFixedHeight(24)
        btn.setStyleSheet(STYLE_HOME_ATTACHMENT_PILL)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAccessibleName(f"Attachment toggle {mod.label}")
        if os.path.exists(mod.icon):
            btn.setIcon(QIcon(mod.icon))
            btn.setIconSize(ICON)
        return btn

    def _configure_accessibility(self) -> None:
        self.status_bar.setAccessibleName("Home status banner")
        self.status_bar.setAccessibleDescription(
            "Dynamic banner showing wand connection state"
        )
        self.mode_label.setAccessibleName("Current wand mode")
        self.wand_3d.setAccessibleName("3D wand orientation viewer")
        self.btn_simulate.setAccessibleName("Replay last input data")
        self.btn_sim_stop.setAccessibleName("Stop simulation playback")
        self.btn_calibrate.setAccessibleName("Calibrate wand sensor")
        self.btn_quick_test.setAccessibleName("Perform quick gesture test")

    @staticmethod
    def _stat_value_to_percent(value: str) -> int:
        stripped = value.strip().replace(",", "")
        numeric = "".join(ch for ch in stripped if ch.isdigit() or ch in ".-+")
        if not numeric:
            return 0
        try:
            number = float(numeric)
        except ValueError:
            return 0
        upper = stripped.upper()
        if "CPU" in upper or "%" in upper:
            return max(0, min(100, int(number)))
        if "RAM" in upper and "KB" in upper:
            return max(0, min(100, int(number / 8192.0 * 100)))
        if "RSSI" in upper or "DBM" in upper:
            return max(0, min(100, int(number + 100)))
        if "RATE" in upper or "HZ" in upper:
            return max(0, min(100, int(number)))
        return 0


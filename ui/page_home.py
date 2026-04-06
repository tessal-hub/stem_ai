"""PageHome — Main dashboard view."""
from __future__ import annotations
import os
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QScrollArea)
from ui.wand_3d_widget import Wand3DWidget
from ui.tokens import (
    # Colors
    ACCENT, ACCENT_TEXT, BG_DARK, BG_LIGHT, BG_WHITE, BORDER, BORDER_MID,
    DANGER,
    TEXT_BODY, TEXT_MUTED, HOVER_BG,
    # Sizes
    ICON, STATUS_H, MODE_BOX_H, MODULE_BAR_H, MGR_BOX_H,
    SPELL_BTN_H, MODULE_BTN_H, SIM_MIN_H, RIGHT_MAX_W,
    # Styles
    STYLE_HOME_MAIN_CONTAINER as STYLE_MAIN_CONTAINER,
    STYLE_WAND_CONTAINER,
    STYLE_CARD,
    STYLE_CARD_NO_BORDER,
    STYLE_SPELL_BTN,
    STYLE_MODULE_BTN,
    STYLE_MODULE_BAR,
    STYLE_TRANSPARENT_WIDGET,
)
from ui.component_factory import (
    make_section_frame,
    make_borderless_frame,
    make_stat_label,
)

@dataclass
class ModuleEntry:
    icon: str
    label: str

MODULES: list[ModuleEntry] = [
    ModuleEntry("assets/icon/fan.svg",      "FAN"),
    ModuleEntry("assets/icon/led.svg",      "LED"),
    ModuleEntry("assets/icon/speaker.svg",  "SPEAKER"),
    ModuleEntry("assets/icon/mouse.svg",    "MOUSE"),
    ModuleEntry("assets/icon/keyboard.svg", "KEY"),
]

class PageHome(QWidget):
    def __init__(self, data_store) -> None:
        super().__init__()
        self.data_store = data_store
        self._stat_labels: dict[str, QLabel] = {}
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

    def update_manager_stats(self, stats: dict[str, str]) -> None:
        for key, value in stats.items():
            label = self._stat_labels.get(key)
            if label:
                label.setText(f"■  {key}: {value}")

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.main_container = QFrame()
        self.main_container.setObjectName("MainBox")
        self.main_container.setStyleSheet(STYLE_MAIN_CONTAINER)

        inner = QVBoxLayout(self.main_container)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(12)

        inner.addWidget(self._build_status_bar())

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._build_left_column(), stretch=5)
        content.addWidget(self._build_right_column(), stretch=2)

        inner.addLayout(content, stretch=1)
        outer.addWidget(self.main_container)

    def _build_status_bar(self) -> QLabel:
        self.status_bar = QLabel("● WAND DISCONNECTED - WAITING FOR DEVICE")
        self.status_bar.setStyleSheet(self._status_style(DANGER, ACCENT_TEXT))
        self.status_bar.setFixedHeight(STATUS_H)
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

    def _build_left_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_simulation_box(), stretch=1)
        layout.addWidget(self._build_module_bar())
        return widget

    def _build_simulation_box(self) -> QFrame:
        box = QFrame()
        box.setObjectName("WandBox")
        box.setStyleSheet(STYLE_WAND_CONTAINER)
        
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header Strip
        header_layout = QHBoxLayout()
        header = QLabel("3D WAND ORIENTATION")
        header.setStyleSheet(f"color: {TEXT_BODY}; font-size: 14px; font-weight: 800; letter-spacing: 1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Real 3D wand viewer
        self.sim_view = QFrame()
        self.sim_view.setStyleSheet(f"background-color: {BG_WHITE}; border: 1px solid {BORDER_MID}; border-radius: 8px;")
        self.sim_view.setMinimumHeight(SIM_MIN_H)

        sim_inner = QVBoxLayout(self.sim_view)
        sim_inner.setContentsMargins(1, 1, 1, 1)
        self.wand_3d = Wand3DWidget()
        sim_inner.addWidget(self.wand_3d, stretch=1)

        layout.addWidget(self.sim_view, stretch=1)
        return box

    def _build_module_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(MODULE_BAR_H)
        bar.setStyleSheet(STYLE_MODULE_BAR)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        mod_lbl = QLabel("ATTACHMENTS:")
        mod_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 900; font-size: 11px; padding-right: 8px;")
        layout.addWidget(mod_lbl)
        
        for mod in MODULES:
            layout.addWidget(self._make_module_button(mod))
        layout.addStretch()
        return bar

    def _build_right_column(self) -> QWidget:
        widget = QWidget()
        widget.setMaximumWidth(RIGHT_MAX_W)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_mode_box())
        layout.addWidget(self._build_spellbook(), stretch=2)
        layout.addWidget(self._build_manager_box())
        return widget

    def _build_mode_box(self) -> QFrame:
        box = make_section_frame()
        box.setFixedHeight(MODE_BOX_H)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(16, 0, 16, 0)
        self.mode_label = QLabel("MODE:  IDLE")
        self.mode_label.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(self.mode_label)
        layout.addStretch()
        return box

    def _build_spellbook(self) -> QFrame:
        box = make_section_frame()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        title = QLabel("SPELLBOOK")
        title.setStyleSheet(f"color: {TEXT_BODY}; font-size: 12px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(title)
        
        # Scroll area for spells if they exceed height
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(STYLE_TRANSPARENT_WIDGET)
        spell_layout = QVBoxLayout(scroll_content)
        spell_layout.setContentsMargins(0, 0, 0, 0)
        spell_layout.setSpacing(8)

        # Sourced from DataStore - with limit to prevent UI hang
        spells = self.data_store.get_spell_list()
        max_display = 50  # Limit to prevent rendering huge lists
        
        if not spells:
            no_spell = QLabel("No spells recorded yet.")
            no_spell.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-style: italic;")
            spell_layout.addWidget(no_spell)
        else:
            for i, spell in enumerate(spells[:max_display]):
                spell_layout.addWidget(self._make_spell_button(f"✨ {spell}"))
            
            # Show count if list is truncated
            if len(spells) > max_display:
                overflow_lbl = QLabel(f"... and {len(spells) - max_display} more")
                overflow_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-style: italic; padding: 4px 0;")
                spell_layout.addWidget(overflow_lbl)
        
        spell_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)
        
        return box

    def _build_manager_box(self) -> QFrame:
        box = make_section_frame()
        box.setFixedHeight(MGR_BOX_H)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("SYSTEM MANAGER")
        title.setStyleSheet(f"color: {TEXT_BODY}; font-size: 11px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(title)

        # Sourced from DataStore
        for key, value in self.data_store.system_stats.items():
            lbl = make_stat_label(f"■  {key}: {value}")
            self._stat_labels[key.strip()] = lbl
            layout.addWidget(lbl)

        return box

    @staticmethod
    def _make_spell_button(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(SPELL_BTN_H)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(STYLE_SPELL_BTN)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAccessibleName(f"Spell button {label}")
        return btn

    @staticmethod
    def _make_module_button(mod: ModuleEntry) -> QPushButton:
        btn = QPushButton(mod.label)
        btn.setStyleSheet(STYLE_MODULE_BTN)
        btn.setFixedHeight(MODULE_BTN_H)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAccessibleName(f"Attachment toggle {mod.label}")
        if os.path.exists(mod.icon):
            btn.setIcon(QIcon(mod.icon))
            btn.setIconSize(ICON)
        return btn

    def _configure_accessibility(self) -> None:
        """Provide stable names for screen readers and keyboard focus."""
        self.status_bar.setAccessibleName("Home status banner")
        self.mode_label.setAccessibleName("Current wand mode")
        self.wand_3d.setAccessibleName("3D wand orientation viewer")


"""
ml_lab/ui/window_ml_lab.py — Cửa sổ Độc Lập ML Lab (Studio Học Máy Bản Chất Đa Tab).

Hệ thống Studio hoàn chỉnh phục vụ nghiên cứu & giảng dạy chuyên sâu về học máy:
1. Data & Feature Science Studio
2. Model Lab & Math Dissection
3. Bias-Variance & Sweep Curves Studio
4. Model Arena (So sánh 15 mô hình)
5. What-If Interactive Simulator & 1-Click C99 Exporter
6. Experiment History & Logs
7. Serial Monitor (Giám sát UART & HUD thời gian thực)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import ml_lab.ui.lab_style as ls
from ml_lab.core.experiment_store import ExperimentStore
from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.ui.tabs.tab_curves_studio import TabCurvesStudio
from ml_lab.ui.tabs.tab_data_studio import TabDataStudio
from ml_lab.ui.tabs.tab_history import TabHistory
from ml_lab.ui.tabs.tab_model_arena import TabModelArena
from ml_lab.ui.tabs.tab_model_lab import TabModelLab
from ml_lab.ui.tabs.tab_serial_monitor import TabSerialMonitor
from ml_lab.ui.tabs.tab_simulator_export import TabSimulatorExport
from ml_lab.ui.widgets.glossary_dialog import GlossaryDialog

log = logging.getLogger(__name__)

_TAB_TITLES = (
    "1 · Dữ liệu",
    "2 · Huấn luyện",
    "3 · Tham số",
    "4 · So sánh",
    "5 · Thử & nạp",
    "6 · Lịch sử",
    "7 · Kết nối",
)

_TAB_TOOLTIPS = (
    "Xem dữ liệu đã ghi: phân phối đặc trưng, tạo thêm dữ liệu mẫu",
    "Huấn luyện máy: chọn 1 trong 15 thuật toán và huấn luyện",
    "Thử tham số tốt nhất: quét cài đặt + thử cần bao nhiêu dữ liệu",
    "So sánh 15 thuật toán: xếp hạng chính xác, tốc độ, RAM",
    "Thử nhanh & nạp lên wand: What-If, xuất mã C++, nạp 1-click",
    "Lịch sử huấn luyện: các lần thử đã lưu + bảng vàng",
    "Kết nối wand: UART terminal + thử mô hình trực tiếp",
)


class MlLabWindow(QMainWindow):
    """Cửa sổ Studio Học Máy Bản Chất ML Lab."""

    def __init__(self, spell_dataset_dir: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spell_dataset_dir = Path(spell_dataset_dir)
        self.experiment_store = ExperimentStore()

        self.setWindowTitle("STEM ML Lab")
        self.resize(1260, 880)
        self.setMinimumSize(1020, 720)

        self._init_ui()
        self.refresh_dataset_info()

    def _init_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background-color: {ls.BG_APP};")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(ls.SP_4, ls.SP_3, ls.SP_4, ls.SP_3)
        main_layout.setSpacing(ls.SP_2)

        # ── Header ──────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f".QFrame {{ background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; border-radius: {ls.RADIUS_LG}px; }}"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(ls.SP_4, SP_HEADER_V := ls.SP_3, ls.SP_4, SP_HEADER_V)
        h_layout.setSpacing(ls.SP_3)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel("STEM ML Lab")
        lbl_title.setStyleSheet(ls.font(ls.FS_TITLE, 800) + f"color: {ls.INK}; border: none; background: transparent;")
        lbl_desc = QLabel("Từ dữ liệu vung wand của bạn → mô hình AI chạy thật trên ESP32, theo 7 bước dẫn dắt")
        lbl_desc.setStyleSheet(ls.font(ls.FS_BODY) + f"color: {ls.MUTED}; border: none; background: transparent;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_desc)
        h_layout.addLayout(title_vbox, stretch=1)

        self.lbl_dataset_chip = QLabel("Đang đọc dataset...")
        self.lbl_dataset_chip.setStyleSheet(ls.CHIP_INFO)
        h_layout.addWidget(self.lbl_dataset_chip)

        btn_glossary = QPushButton("Sổ tay thuật ngữ")
        btn_glossary.setStyleSheet(ls.BTN_PRIMARY.replace("padding: 10px 16px", "padding: 6px 14px"))
        btn_glossary.setCursor(self.cursor())
        btn_glossary.clicked.connect(self._open_glossary)
        h_layout.addWidget(btn_glossary)

        btn_refresh = QPushButton("Quét lại")
        btn_refresh.setStyleSheet(ls.BTN_SECONDARY)
        btn_refresh.clicked.connect(self.refresh_dataset_info)
        h_layout.addWidget(btn_refresh)

        main_layout.addWidget(header_frame)

        # ── Multi-Tab Studio Navigation ─────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(ls.TAB_BAR)

        # 1. Data & Feature Studio
        self.tab_data = TabDataStudio(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_data, _TAB_TITLES[0])

        # 2. Model Lab & Math Dissection
        self.tab_model = TabModelLab(self.spell_dataset_dir)
        self.tab_model.sig_model_trained.connect(self._on_model_trained_globally)
        self.tabs.addTab(self.tab_model, _TAB_TITLES[1])

        # 3. Bias-Variance Curves Studio
        self.tab_curves = TabCurvesStudio(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_curves, _TAB_TITLES[2])

        # 4. Model Arena
        self.tab_arena = TabModelArena(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_arena, _TAB_TITLES[3])

        # 5. What-If Simulator & C99 Exporter
        self.tab_sim = TabSimulatorExport(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_sim, _TAB_TITLES[4])

        # 6. History Logs
        self.tab_history = TabHistory()
        self.tabs.addTab(self.tab_history, _TAB_TITLES[5])

        # 7. Serial Monitor & Live Gesture HUD
        self.tab_serial = TabSerialMonitor()
        self.tabs.addTab(self.tab_serial, _TAB_TITLES[6])

        for i, tip in enumerate(_TAB_TOOLTIPS):
            self.tabs.setTabToolTip(i, tip)

        main_layout.addWidget(self.tabs, stretch=1)

    def refresh_dataset_info(self) -> None:
        """Đọc và cập nhật số lượng mẫu spell do user ghi."""
        counts = count_user_spell_samples(self.spell_dataset_dir)
        total_samples = sum(counts.values())
        num_classes = len(counts)
        self.lbl_dataset_chip.setText(f"Dataset · {num_classes} thần chú · {total_samples} mẫu")
        self.tab_data.reload_dataset()

    def _open_glossary(self) -> None:
        """Mở Sổ tay thuật ngữ và cẩm nang sư phạm AI."""
        dlg = GlossaryDialog(self)
        dlg.exec()

    def _on_model_trained_globally(self, result: TrainClassicResult) -> None:
        """Khi mô hình được huấn luyện, tự động lưu lịch sử và nạp sang Tab Giả lập."""
        try:
            self.experiment_store.save_experiment(result)
        except Exception as exc:
            log.warning("Không thể lưu experiment: %s", exc)

        self.tab_sim.set_trained_model(result)
        self.tab_serial.set_trained_model(result)
        self.tab_history.reload_history()

    def closeEvent(self, event: Any) -> None:
        if hasattr(self, "tab_serial") and self.tab_serial:
            self.tab_serial.disconnect_serial()
        if hasattr(self, "tab_data") and self.tab_data:
            self.tab_data.close()  # chờ worker phân tích nền, tránh crash khi teardown
        super().closeEvent(event)

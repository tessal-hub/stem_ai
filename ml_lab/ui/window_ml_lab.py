"""
ml_lab/ui/window_ml_lab.py — Cửa sổ Độc Lập ML Lab (Studio Học Máy Bản Chất Đa Tab).

Hệ thống Studio hoàn chỉnh phục vụ nghiên cứu & giảng dạy chuyên sâu về học máy:
1. Data & Feature Science Studio
2. Model Lab & Math Dissection
3. Bias-Variance & Sweep Curves Studio
4. Model Arena (Đấu trường 5 mô hình)
5. What-If Interactive Simulator & 1-Click C99 Exporter
6. Experiment History & Logs
7. Serial Monitor (Giám sát UART & HUD thời gian thực)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
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


class MlLabWindow(QMainWindow):
    """
    Cửa sổ Studio Học Máy Bản Chất ML Lab.
    """

    def __init__(self, spell_dataset_dir: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spell_dataset_dir = Path(spell_dataset_dir)
        self.experiment_store = ExperimentStore()

        self.setWindowTitle("🔮 STEM ML Lab — Classic Machine Learning Studio")
        self.resize(1260, 880)
        self.setMinimumSize(1020, 720)

        self._init_ui()
        self.refresh_dataset_info()

    def _init_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet("background-color: #f8fafc;")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # ── Header ──────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background: #ffffff; border-radius: 10px; padding: 6px 12px; border: 1px solid #e2e8f0; }"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 6, 10, 6)
        h_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel("🔮 STEM ML Lab — Framework Học Máy Bản Chất")
        lbl_title.setStyleSheet("font-weight: 800; font-size: 15px; color: #0f172a; font-family: 'Segoe UI', system-ui;")
        lbl_desc = QLabel("Khám phá dữ liệu • Mổ xẻ thuật toán • Bias-Variance • Đấu trường 5 mô hình • Giả lập What-If • Nạp Code 1-Click • Serial Monitor")
        lbl_desc.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_desc)
        h_layout.addLayout(title_vbox, stretch=1)

        self.lbl_dataset_chip = QLabel("📊 Đang đọc dataset...")
        self.lbl_dataset_chip.setStyleSheet(
            "font-weight: 600; padding: 6px 14px; border-radius: 14px; background: rgba(0, 122, 255, 0.08); color: #007aff; border: 1px solid rgba(0, 122, 255, 0.2); font-size: 11px;"
        )
        h_layout.addWidget(self.lbl_dataset_chip)

        btn_glossary = QPushButton("📖 Sổ Tay Thuật Ngữ AI")
        btn_glossary.setStyleSheet(
            "QPushButton { padding: 6px 14px; border-radius: 6px; background: #007aff; color: white; font-weight: 700; font-size: 11px; border: none; } "
            "QPushButton:hover { background: #0066d6; } "
            "QPushButton:pressed { background: #0052ad; }"
        )
        btn_glossary.clicked.connect(self._open_glossary)
        h_layout.addWidget(btn_glossary)

        btn_refresh = QPushButton("🔄 Quét Lại")
        btn_refresh.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 6px; background: #ffffff; border: 1px solid #cbd5e1; font-weight: 600; font-size: 11px; color: #334155; } "
            "QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; } "
            "QPushButton:pressed { background: #e2e8f0; }"
        )
        btn_refresh.clicked.connect(self.refresh_dataset_info)
        h_layout.addWidget(btn_refresh)

        main_layout.addWidget(header_frame)

        # ── Multi-Tab Studio Navigation ─────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; background: #ffffff; top: -1px; } "
            "QTabBar::tab { font-weight: 600; padding: 10px 18px; font-size: 12px; color: #64748b; background: #f1f5f9; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 3px; } "
            "QTabBar::tab:hover { background: #e2e8f0; color: #1e293b; } "
            "QTabBar::tab:selected { background: #ffffff; color: #007aff; border-bottom: 2px solid #007aff; font-weight: 700; }"
        )

        # 1. Data & Feature Studio
        self.tab_data = TabDataStudio(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_data, "📊 1. Dữ Liệu & Đặc Trưng")

        # 2. Model Lab & Math Dissection
        self.tab_model = TabModelLab(self.spell_dataset_dir)
        self.tab_model.sig_model_trained.connect(self._on_model_trained_globally)
        self.tabs.addTab(self.tab_model, "🧪 2. Huấn Luyện & Toán Học")

        # 3. Bias-Variance Curves Studio
        self.tab_curves = TabCurvesStudio(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_curves, "📈 3. Đường Cong Bias-Variance")

        # 4. Model Arena
        self.tab_arena = TabModelArena(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_arena, "⚔️ 4. Đấu Trường 5 Mô Hình")

        # 5. What-If Simulator & C99 Exporter
        self.tab_sim = TabSimulatorExport(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_sim, "🎮 5. Giả Lập & Nạp Code")

        # 6. History Logs
        self.tab_history = TabHistory()
        self.tabs.addTab(self.tab_history, "📜 6. Nhật Ký Thử Nghiệm")

        # 7. Serial Monitor & Live Gesture HUD
        self.tab_serial = TabSerialMonitor()
        self.tabs.addTab(self.tab_serial, "📟 7. Serial Monitor")

        main_layout.addWidget(self.tabs, stretch=1)

    def refresh_dataset_info(self) -> None:
        """Đọc và cập nhật số lượng mẫu spell do user ghi."""
        counts = count_user_spell_samples(self.spell_dataset_dir)
        total_samples = sum(counts.values())
        num_classes = len(counts)
        self.lbl_dataset_chip.setText(f"📊 Dataset: {num_classes} Thần chú ({total_samples} files)")
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
        self.tab_history.reload_history()

    def closeEvent(self, event: Any) -> None:
        if hasattr(self, "tab_serial") and self.tab_serial:
            self.tab_serial._disconnect_serial()
        super().closeEvent(event)

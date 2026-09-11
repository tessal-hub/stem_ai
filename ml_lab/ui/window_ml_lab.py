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
from ml_lab.ui.widgets.spell_filter_bar import SpellFilterBar

log = logging.getLogger(__name__)

_TAB_TITLES = (
    "0 · Thần chú",
    "1 · Dữ liệu",
    "2 · Huấn luyện",
    "3 · Tham số",
    "4 · So sánh",
    "5 · Thử & nạp",
    "6 · Lịch sử",
    "7 · Kết nối",
)

_TAB_TOOLTIPS = (
    "Chọn thần chú để luyện — chỉ thần chú đã chọn mới được huấn luyện, lưu lại cho lần sau",
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
        self.setMinimumSize(960, 600)

        self._init_ui()
        self.refresh_dataset_info()

    def _init_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background-color: {ls.BG_APP};")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        main_layout.setSpacing(ls.SP_4)

        # ── Header ──────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("MlLabHeader")
        header_frame.setStyleSheet(
            f"#MlLabHeader {{ background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_LG}px;}}"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(ls.SP_4, ls.SP_3, ls.SP_4, ls.SP_3)
        h_layout.setSpacing(ls.SP_3)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel("STEM ML Lab")
        lbl_title.setStyleSheet(ls.font(ls.FS_TITLE, 800) + f"color: {ls.INK}; border: none; background: transparent;")
        lbl_desc = QLabel("Từ dữ liệu vung wand của bạn → mô hình AI chạy thật trên ESP32, theo 7 bước dẫn dắt")
        lbl_desc.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_desc)
        h_layout.addLayout(title_vbox, stretch=1)

        self.lbl_dataset_chip = QLabel("Đang đọc dataset...")
        self.lbl_dataset_chip.setMinimumHeight(26)
        self.lbl_dataset_chip.setStyleSheet(ls.CHIP_INFO)
        self.lbl_dataset_chip.setToolTip("Số thần chú và mẫu đang được dùng để huấn luyện theo Tab 0 · Chọn thần chú")
        self.lbl_dataset_chip.setAccessibleName("Thông tin tóm tắt số lượng thần chú đang chọn")
        h_layout.addWidget(self.lbl_dataset_chip)

        btn_glossary = QPushButton("Sổ tay thuật ngữ")
        btn_glossary.setStyleSheet(ls.BTN_SECONDARY)
        btn_glossary.setToolTip("Tra cứu khái niệm, thuật toán và cách đọc kết quả")
        btn_glossary.setAccessibleName("Mở sổ tay giải thích thuật ngữ học máy")
        btn_glossary.setCursor(self.cursor())
        btn_glossary.clicked.connect(self._open_glossary)
        h_layout.addWidget(btn_glossary)

        main_layout.addWidget(header_frame)

        # ── Multi-Tab Studio Navigation (8 tabs) ────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(ls.TAB_BAR)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.setAccessibleName("Các bước học máy từ dữ liệu đến nạp ESP32")

        # 0 · Chọn spell — menu ngang hàng, embedded
        self.filter_bar = SpellFilterBar(self.spell_dataset_dir, embedded=True)
        self.filter_bar.sig_selection_changed.connect(self._on_spell_selection_changed)
        self.tabs.addTab(self.filter_bar, _TAB_TITLES[0])

        # 1. Data & Feature Studio
        self.tab_data = TabDataStudio(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_data, _TAB_TITLES[1])

        # 2. Model Lab & Math Dissection
        self.tab_model = TabModelLab(self.spell_dataset_dir)
        self.tab_model.sig_model_trained.connect(self._on_model_trained_globally)
        self.tabs.addTab(self.tab_model, _TAB_TITLES[2])

        # 3. Bias-Variance Curves Studio
        self.tab_curves = TabCurvesStudio(self.spell_dataset_dir)
        self.tab_curves.sig_apply_best.connect(self._on_apply_sweep_best)
        self.tabs.addTab(self.tab_curves, _TAB_TITLES[3])

        # 4. Model Arena
        self.tab_arena = TabModelArena(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_arena, _TAB_TITLES[4])

        # 5. What-If Simulator & C99 Exporter
        self.tab_sim = TabSimulatorExport(self.spell_dataset_dir)
        self.tabs.addTab(self.tab_sim, _TAB_TITLES[5])

        # 6. History Logs
        self.tab_history = TabHistory()
        self.tabs.addTab(self.tab_history, _TAB_TITLES[6])

        # 7. Serial Monitor & Live Gesture HUD
        self.tab_serial = TabSerialMonitor()
        self.tabs.addTab(self.tab_serial, _TAB_TITLES[7])

        for i, tip in enumerate(_TAB_TOOLTIPS):
            self.tabs.setTabToolTip(i, tip)

        main_layout.addWidget(self.tabs, stretch=1)

        # Đồng bộ bộ lọc ban đầu cho các tab (snapshot)
        try:
            init_sel = self.filter_bar.get_selected()
            for tab in (self.tab_data, self.tab_model, self.tab_curves, self.tab_arena):
                if hasattr(tab, "set_allowed_spells"):
                    tab.set_allowed_spells(init_sel)
            self._update_filter_tab_title()
        except Exception:
            pass

    def _current_allowed_spells(self) -> set[str] | None:
        """Tập spell đang chọn từ filter bar; None = tất cả."""
        if hasattr(self, "filter_bar"):
            try:
                sel = self.filter_bar.get_selected()
                # nếu chưa load hoặc chưa có gì thì coi như tất cả
                if not sel and len(self.filter_bar._counts) == 0:
                    return None
                return sel
            except Exception:
                return None
        return None

    def _update_filter_tab_title(self) -> None:
        try:
            n = len(self.filter_bar.get_selected())
            total = len(self.filter_bar._counts)
            if total == 0:
                self.tabs.setTabText(0, _TAB_TITLES[0])
            else:
                # Giữ tiêu đề ngắn để tránh tab bar overflow trên 1020px (8 tabs)
                label = _TAB_TITLES[0]
                if len(label) > 18:
                    label = label[:16] + "…"
                self.tabs.setTabText(0, f"{label} · {n}/{total}")
            self.tabs.setTabToolTip(0, f"Đang chọn {n}/{total} thần chú — bấm để đổi")
        except Exception:
            pass

    def _on_spell_selection_changed(self, selected: set[str]) -> None:
        """Khi filter bar đổi → phát lại cho các tab và làm mới chip."""
        # broadcast
        for tab in (self.tab_data, self.tab_model, self.tab_curves, self.tab_arena):
            if hasattr(tab, "set_allowed_spells"):
                try:
                    tab.set_allowed_spells(selected)
                except Exception:
                    pass
        self._update_filter_tab_title()
        self.refresh_dataset_info()

    def refresh_dataset_info(self, force_rescan: bool = False) -> None:
        """Đọc và cập nhật số lượng mẫu spell (dùng cache, watcher tự quét)."""
        # Nếu ép quét (nút Quét lại) thì reload filter trước để làm mới cache
        if force_rescan and hasattr(self, "filter_bar"):
            try:
                self.filter_bar.reload(force_rescan=True)
            except Exception:
                pass
        # Dùng cache từ filter_bar làm single source — tránh 2 glob
        if hasattr(self, "filter_bar") and self.filter_bar._counts:
            all_counts = dict(self.filter_bar._counts)
        else:
            all_counts = count_user_spell_samples(self.spell_dataset_dir)
            if hasattr(self, "filter_bar"):
                self.filter_bar._counts = dict(all_counts)
        total_available = len(all_counts)
        allowed = self._current_allowed_spells()
        if allowed is not None:
            counts = {k: v for k, v in all_counts.items() if k in allowed}
        else:
            counts = dict(all_counts)
        total_samples = sum(counts.values())
        num_classes = len(counts)

        # Phát hiện spell mới (trường hợp watcher chưa kịp debounced)
        if hasattr(self, "filter_bar") and total_available != len(getattr(self.filter_bar, "_counts", {})):
            try:
                self.filter_bar.reload(force_rescan=True)
                allowed = self.filter_bar.get_selected()
                for tab in (self.tab_data, self.tab_model, self.tab_curves, self.tab_arena):
                    if hasattr(tab, "set_allowed_spells"):
                        try:
                            tab.set_allowed_spells(allowed)
                        except Exception:
                            pass
                all_counts = dict(self.filter_bar._counts)
                total_available = len(all_counts)
                counts = {k: v for k, v in all_counts.items() if k in allowed} if allowed else dict(all_counts)
                total_samples = sum(counts.values())
                num_classes = len(counts)
            except Exception:
                pass

        if allowed is not None and len(allowed) != total_available:
            self.lbl_dataset_chip.setText(
                f"Đang luyện {num_classes}/{total_available} thần chú · {total_samples} mẫu (lọc)"
            )
        else:
            self.lbl_dataset_chip.setText(f"Dataset · {num_classes} thần chú · {total_samples} mẫu")
        if num_classes < 2:
            self.lbl_dataset_chip.setStyleSheet(
                f"{ls.font(ls.FS_CAPTION, 700)} color: {ls.WARNING}; background: {ls.WARNING_TINT}; "
                f"border-radius: {ls.RADIUS_PILL}px; padding: 5px {ls.SP_3}px;"
            )
        elif total_samples < 10:
            self.lbl_dataset_chip.setStyleSheet(
                f"{ls.font(ls.FS_CAPTION, 700)} color: {ls.WARNING}; background: {ls.WARNING_TINT}; "
                f"border-radius: {ls.RADIUS_PILL}px; padding: 5px {ls.SP_3}px;"
            )
        else:
            self.lbl_dataset_chip.setStyleSheet(ls.CHIP_INFO)
        self._update_filter_tab_title()
        self.tab_data.reload_dataset()

    def _open_glossary(self) -> None:
        """Mở Sổ tay thuật ngữ và cẩm nang sư phạm AI."""
        dlg = GlossaryDialog(self)
        dlg.exec()

    def _on_apply_sweep_best(self, algo_key: str, param_key: str, value: Any) -> None:
        """Tab 3 → Tab 2: điền giá trị tốt nhất rồi nhảy sang tab Huấn luyện."""
        try:
            self.tab_model.apply_sweep_value(algo_key, param_key, value)
            self.tabs.setCurrentIndex(2)
        except Exception as exc:
            log.warning("Apply sweep best failed: %s", exc)

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
        # Gỡ callback khỏi coordinator — tránh gọi vào widget đã xóa
        try:
            from ml_lab.core.serial_coordinator import ML_LAB_SERIAL, release, unregister_owner
            release(ML_LAB_SERIAL)
            unregister_owner(ML_LAB_SERIAL)
        except Exception:
            pass
        if hasattr(self, "tab_data") and self.tab_data:
            try:
                if hasattr(self.tab_data, "wait_for_workers"):
                    self.tab_data.wait_for_workers(4000)
                else:
                    self.tab_data.close()
            except Exception:
                pass
        super().closeEvent(event)

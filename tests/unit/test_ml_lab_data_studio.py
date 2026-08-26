"""
tests/unit/test_ml_lab_data_studio.py — Regression test cho TabDataStudio.

Phân tích đặc trưng chạy NỀN (DatasetAnalysisWorker) để mở app không bị đóng băng,
nên test phải chờ worker hoàn tất trước khi assert.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from ml_lab.ui.tabs.tab_data_studio import TabDataStudio


HEADER = "timestamp,ax,ay,az,gx,gy,gz\n"


def _write_csv(path: Path, n_rows: int = 70, offset: float = 0.0) -> None:
    lines = [HEADER]
    for i in range(n_rows):
        t = i / 10.0 + offset
        vals = [
            0.1 * i / n_rows + offset,
            0.5,
            1.0 + 0.2 * (i % 3) + offset,
            0.01 * (i % 5),
            -0.02 * (i % 7),
            0.03 * (i % 4),
        ]
        lines.append(f"{t:.3f}," + ",".join(f"{v:.4f}" for v in vals) + "\n")
    path.write_text("".join(lines), encoding="utf-8")


def _wait_analysis_done(tab: TabDataStudio, timeout_s: float = 30.0) -> None:
    app = QApplication.instance()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if app is not None:
            app.processEvents()
        if tab._analysis_done:
            return
        time.sleep(0.02)
    raise TimeoutError("DatasetAnalysisWorker không hoàn tất trong hạn chờ")


@pytest.fixture
def synthetic_dataset(tmp_path: Path) -> Path:
    for cls_name, off in (("lumos", 0.0), ("nox", 0.5)):
        cls_dir = tmp_path / cls_name
        cls_dir.mkdir()
        for f_idx in range(3):
            _write_csv(cls_dir / f"sample_{f_idx}.csv", offset=off)
    return tmp_path


def test_data_studio_populates_analysis(qapp, synthetic_dataset: Path):
    tab = TabDataStudio(synthetic_dataset)
    try:
        # Bảng lớp phải đổ NGAY (không chờ worker)
        assert tab.table_classes.rowCount() == 2

        _wait_analysis_done(tab)

        # Combo đặc trưng phải được đổ đầy (63 features mặc định)
        assert tab.combo_feat.count() > 0

        # Ma trận đặc trưng cache phải có dữ liệu & nhãn đủ 2 lớp
        assert tab._cached_X.shape[0] > 0
        assert set(tab._cached_y.tolist()) == {0, 1}

        # Augmentation preview phải chạy được với dict cửa sổ theo lớp
        assert sum(len(v) for v in tab._cached_wins_by_class.values()) == tab._total_windows
        tab._preview_augmentation()  # không được raise
        assert "mẫu tổng hợp" in tab.lbl_aug_result.text() or "x" in tab.lbl_aug_result.text()
    finally:
        tab.close()


def test_data_studio_empty_dataset_safe(qapp, tmp_path: Path):
    tab = TabDataStudio(tmp_path)
    try:
        _wait_analysis_done(tab)
        assert tab.combo_feat.count() == 0
        assert tab._cached_X.shape[0] == 0
        assert tab._cached_wins_by_class == {}
    finally:
        tab.close()

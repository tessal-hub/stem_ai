"""Unit tests for gesture consistency evaluation and consistency progress bar."""
from __future__ import annotations

import csv
from pathlib import Path
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from logic.data_store import DataStore
from logic.handler import Handler
from logic.prototypical_recognizer import PrototypicalRecognizer
from ui.page_record import PageRecord


def test_prototypical_recognizer_kinematic_fallback() -> None:
    """Verify analyze_spell_samples works seamlessly without neural encoder."""
    rec = PrototypicalRecognizer(encoder=None)

    # 3 consistent samples
    sample1 = np.ones((64, 6), dtype=np.float32) * 1.0
    sample2 = np.ones((64, 6), dtype=np.float32) * 1.05
    sample3 = np.ones((64, 6), dtype=np.float32) * 0.98

    res = rec.analyze_spell_samples([sample1, sample2, sample3])
    assert res["n_samples"] == 3
    assert res["overall_consistency"] is not None
    assert res["overall_consistency"] >= 0.85
    assert len(res["per_sample_scores"]) == 3
    assert all(s is not None and s >= 0.85 for s in res["per_sample_scores"])


def test_handler_load_samples_short_rows_interpolation(tmp_path: Path) -> None:
    """Verify samples with 16-63 rows are interpolated without dropping."""
    dataset_dir = tmp_path / "dataset"
    spell_dir = dataset_dir / "spells" / "LUMOS"
    spell_dir.mkdir(parents=True)

    # Create a 40-row sample CSV
    csv_file = spell_dir / "sample_001.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
        for i in range(40):
            writer.writerow([0.1, 0.2, 0.98, 0.05, 0.02, 0.01])

    results = Handler._load_samples_for_analysis_static(str(dataset_dir), "LUMOS", window_size=64)
    assert len(results) == 1
    fname, window, err = results[0]
    assert err is None
    assert window is not None
    assert window.shape == (64, 6)


def test_page_record_consistency_bar_updates(qapp: QApplication, tmp_path: Path) -> None:
    """Verify PageRecord.update_consistency_display updates consistency_bar value & style."""
    store = DataStore(dataset_dir=str(tmp_path))
    page = PageRecord(data_store=store)
    page.show()
    page.current_spell_name = "LUMOS"
    page._current_samples = ["s1.csv", "s2.csv", "s3.csv"]
    page.stacked_spells.setCurrentIndex(1)  # View samples list page

    # 1. Test < 3 samples (progress state)
    page.update_consistency_display({
        "n_samples": 2,
        "ready_to_register": False,
        "overall_consistency": None,
        "per_sample_scores": [None, None],
        "recommendation": "Cần thêm 1 mẫu nữa",
    })
    assert not page.consistency_bar.isHidden()
    assert "2/3" in page.consistency_bar.text() or "●●" in page.consistency_bar.text()

    # 2. Test >= 3 samples with high score
    page.update_consistency_display({
        "n_samples": 3,
        "ready_to_register": True,
        "overall_consistency": 0.92,
        "per_sample_scores": [0.95, 0.90, 0.91],
        "recommendation": "Độ đồng nhất rất tốt",
    })
    assert page.consistency_bar.value() == 92
    assert "92%" in page.consistency_bar.text()
    assert page.lbl_consistency.text() == "Độ đồng nhất rất tốt"
    page.close()

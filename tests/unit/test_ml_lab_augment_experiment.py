"""
tests/unit/test_ml_lab_augment_experiment.py — Unit test thí nghiệm A/B tăng cường dữ liệu.

Chạy trên dataset tổng hợp (2 lớp × 3 file CSV) đảm bảo:
1. Trả về đầy đủ số liệu, accuracy trong khoảng [0, 1].
2. Dữ liệu train sau tăng cường lớn hơn gốc đúng multiplier.
3. Lỗi rõ ràng khi dataset < 2 lớp.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ml_lab.core.augment_experiment import compare_augmentation_effect


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


@pytest.fixture
def synthetic_dataset(tmp_path: Path) -> Path:
    for cls_name, off in (("lumos", 0.0), ("nox", 0.5)):
        cls_dir = tmp_path / cls_name
        cls_dir.mkdir()
        for f_idx in range(3):
            _write_csv(cls_dir / f"sample_{f_idx}.csv", offset=off)
    return tmp_path


def test_compare_returns_valid_metrics(synthetic_dataset: Path):
    res = compare_augmentation_effect(synthetic_dataset, val_fraction=0.34, multiplier=3)

    assert set(res) >= {
        "baseline_val", "augmented_val", "baseline_train_size",
        "augmented_train_size", "val_size", "multiplier", "num_classes",
    }
    assert 0.0 <= res["baseline_val"] <= 1.0
    assert 0.0 <= res["augmented_val"] <= 1.0
    assert res["num_classes"] == 2
    assert res["augmented_train_size"] > res["baseline_train_size"]
    assert res["val_size"] > 0
    assert res["multiplier"] == 3


def test_compare_requires_two_classes(tmp_path: Path):
    solo = tmp_path / "lumos"
    solo.mkdir()
    _write_csv(solo / "a.csv")
    with pytest.raises(ValueError):
        compare_augmentation_effect(tmp_path)

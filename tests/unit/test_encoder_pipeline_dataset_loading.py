from __future__ import annotations

import csv

import numpy as np

from logic.tensorflow.encoder_pipeline import load_primitive_dataset


def _write_csv(path, rows: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["aX", "aY", "aZ", "gX", "gY", "gZ"])
        writer.writerows(rows)


def test_load_primitive_dataset_keeps_pre_normalized_csv_scale(tmp_path) -> None:
    dataset = tmp_path / "dataset"
    _write_csv(dataset / "PULSE" / "sample_1.csv", [[1, 2, 3, 4, 5, 6]] * 8)
    _write_csv(dataset / "ORBIT" / "sample_1.csv", [[2, 3, 4, 5, 6, 7]] * 8)

    X, y, class_names = load_primitive_dataset(
        str(dataset),
        primitive_names=["PULSE", "ORBIT"],
        window_size=4,
    )

    assert class_names == ["PULSE", "ORBIT"]
    assert X.dtype == np.float32
    assert len(X) > 0
    assert len(X) == len(y)
    assert float(np.max(np.abs(X))) >= 1.0

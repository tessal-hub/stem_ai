"""
tests/unit/test_ml_lab_experiment_store.py — Unit test ExperimentStore (ML Lab).

Đảm bảo:
1. Tên file experiment luôn duy nhất (không ghi đè khi lưu cùng 1 giây).
2. clear_all() xóa hết bản ghi.
3. delete_experiment() xóa đúng 1 file, chặn path traversal.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ml_lab.core.experiment_store import ExperimentStore
from ml_lab.core.pipeline import TrainClassicResult


def _make_result(algo: str = "knn") -> TrainClassicResult:
    return TrainClassicResult(
        algo=algo,
        algo_name="KNN",
        model=None,
        scaler=None,
        train_accuracy=0.9,
        val_accuracy=0.8,
        cv_mean=0.75,
        cv_std=0.05,
        confusion_matrix=np.eye(2, dtype=int),
        class_names=["lumos", "nox"],
        feature_names=[f"f{i}" for i in range(6)],
        pca_result={},
        benchmark={"mcu_latency_ms": 0.1},
        train_time_ms=12.5,
        config_dict={"k": 3},
    )


def test_save_experiment_unique_filenames(tmp_path: Path):
    store = ExperimentStore(root_dir=tmp_path)
    p1 = store.save_experiment(_make_result())
    p2 = store.save_experiment(_make_result())
    p3 = store.save_experiment(_make_result())
    assert p1.exists() and p2.exists() and p3.exists()
    assert len({p1.name, p2.name, p3.name}) == 3
    assert len(list(store.experiments_dir.glob("*.json"))) == 3


def test_list_and_leaderboard(tmp_path: Path):
    store = ExperimentStore(root_dir=tmp_path)
    low = _make_result("knn")
    low.val_accuracy = 0.4
    high = _make_result("knn")
    high.val_accuracy = 0.9
    tree = _make_result("tree")
    tree.val_accuracy = 0.7
    store.save_experiment(low)
    store.save_experiment(high)
    store.save_experiment(tree)

    exps = store.list_experiments()
    assert len(exps) == 3
    assert all("_file" in e for e in exps)

    board = store.get_leaderboard()
    assert len(board) == 2  # 1 best per algo
    knn_best = next(e for e in board if e["algo"] == "knn")
    assert knn_best["val_accuracy"] == 0.9


def test_clear_all(tmp_path: Path):
    store = ExperimentStore(root_dir=tmp_path)
    store.save_experiment(_make_result())
    store.save_experiment(_make_result("tree"))
    assert len(store.list_experiments()) == 2

    removed = store.clear_all()
    assert removed == 2
    assert len(store.list_experiments()) == 0


def test_delete_experiment_blocks_traversal(tmp_path: Path):
    store = ExperimentStore(root_dir=tmp_path)
    p = store.save_experiment(_make_result())

    assert store.delete_experiment(p.name) is True
    assert not p.exists()

    # Path traversal & sai đuôi -> từ chối an toàn
    assert store.delete_experiment("../secret.json") is False
    assert store.delete_experiment("not_json.txt") is False

# -*- coding: utf-8 -*-
"""
tests/unit/test_ml_lab_new_features.py — Test 3 tính năng mới:
1. LiveGesturePredictor (thử mô hình qua serial, không cần nạp)
2. AutoSelectWorker shortlist hợp lệ
3. DataSizeWorker trả về 4 mốc dữ liệu
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.hyperparam_schema import (
    AdaBoostConfig,
    DecisionTreeConfig,
    ExtraTreesConfig,
    KNNConfig,
    LDAConfig,
    LogisticRegressionConfig,
    NaiveBayesConfig,
    NearestCentroidConfig,
    RidgeConfig,
    SGDConfig,
)
from ml_lab.core.live_inference import WINDOW_SIZE, LiveGesturePredictor
from ml_lab.core.pipeline import TrainClassicResult, train_classic_model
from ml_lab.ui.ml_lab_worker import _SHORTLIST, AutoSelectWorker
from ml_lab.ui.tabs.tab_curves_studio import DataSizeWorker


# ── fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def trained_result():
    """Train trên cửa sổ IMU 64×6 thật để predictor trích cùng bộ đặc trưng."""
    rng = np.random.RandomState(42)
    windows: list = []
    labels: list = []
    for cls, center in ((0, -1.0), (1, 2.0)):
        for _ in range(10):
            w = rng.randn(64, 6).astype(np.float32) * 0.3 + center
            windows.append(w)
            labels.append(cls)

    from ml_lab.data.feature_extraction import ClassicFeatureExtractor
    extractor = ClassicFeatureExtractor()
    X = np.stack([extractor.extract_from_window(w) for w in windows])
    y = np.array(labels)
    X_train, y_train = X[:-4], y[:-4]
    X_val, y_val = X[-4:], y[-4:]

    return train_classic_model(
        X_train, y_train, X_val, y_val,
        ["lumos", "nox"], extractor.feature_names,
        algo="tree", config=DecisionTreeConfig(max_depth=3),
    )


def _make_result_with_model(model, scaler=None):
    """TrainClassicResult giả lập cho LiveGesturePredictor."""
    return TrainClassicResult(
        algo="tree",
        algo_name="Cây quyết định",
        model=model,
        scaler=scaler,
        train_accuracy=1.0,
        val_accuracy=0.9,
        cv_mean=0.9,
        cv_std=0.0,
        confusion_matrix=np.eye(2, dtype=int),
        class_names=["lumos", "nox"],
        feature_names=[f"f{i}" for i in range(8)],
        pca_result={},
        benchmark={},
        train_time_ms=1.0,
        config_dict={},
    )


# ── 1. LiveGesturePredictor ───────────────────────────────────────────

def test_live_predictor_returns_prediction_after_window(trained_result):
    predictor = LiveGesturePredictor(trained_result)
    rng = np.random.RandomState(0)
    out = None
    for _ in range(WINDOW_SIZE + 10):
        sample = rng.randn(6).astype(np.float32)
        out = predictor.feed(sample)
        if out is not None:
            break
    assert out is not None, "phải ra dự đoán sau khi gom đủ 64 mẫu"
    spell, conf = out
    assert spell in ("lumos", "nox")
    assert 0.0 <= conf <= 100.0


def test_live_predictor_respects_cooldown(trained_result):
    predictor = LiveGesturePredictor(trained_result, cooldown_samples=50)
    rng = np.random.RandomState(1)
    predictions = 0
    for _ in range(WINDOW_SIZE * 3):
        out = predictor.feed(rng.randn(6).astype(np.float32))
        if out is not None:
            predictions += 1
    # với cooldown 50, số lần dự đoán phải ít hơn nhiều so với số cửa sổ
    assert predictions < 4


def test_live_predictor_no_model_returns_none():
    predictor = LiveGesturePredictor(_make_result_with_model(None))
    assert not predictor.ready
    assert predictor.feed([0.0] * 6) is None


def test_live_predictor_bad_input_safe(trained_result):
    predictor = LiveGesturePredictor(trained_result)
    assert predictor.feed("rác") is None
    assert predictor.feed([1.0, 2.0]) is None  # thiếu trục


# ── 2. AutoSelectWorker shortlist ─────────────────────────────────────

def test_shortlist_keys_have_configs():
    """Mọi key trong shortlist đều phải build được config mặc định."""
    from ml_lab.core.hyperparam_schema import (
        DecisionTreeConfig, KNNConfig, LDAConfig, LogisticRegressionConfig,
        NaiveBayesConfig, NearestCentroidConfig, RandomForestConfig,
        RidgeConfig, SGDConfig, ExtraTreesConfig, AdaBoostConfig,
    )
    candidates = {
        "tree": DecisionTreeConfig, "logistic": LogisticRegressionConfig,
        "knn": KNNConfig, "forest": RandomForestConfig, "nb": NaiveBayesConfig,
        "lda": LDAConfig, "ridge": RidgeConfig, "sgd": SGDConfig,
        "nearest_centroid": NearestCentroidConfig,
        "extra_trees": ExtraTreesConfig, "adaboost": AdaBoostConfig,
    }
    assert {k for k, _ in _SHORTLIST} == set(candidates.keys())
    for key, _ in _SHORTLIST:
        assert candidates[key]().validate() == []


def test_auto_select_worker_class_exists(qapp):
    w = AutoSelectWorker(dataset_root=".")
    assert w.dataset_root == Path_like(".")


def Path_like(p):
    from pathlib import Path
    return Path(p)


# ── 3. DataSizeWorker ─────────────────────────────────────────────────

def test_datasize_worker_fractions():
    assert [int(f * 100) for f in DataSizeWorker.FRACTIONS] == [25, 50, 75, 100]

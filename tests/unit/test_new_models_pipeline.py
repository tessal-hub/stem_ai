"""
tests/unit/test_new_models_pipeline.py — Unit tests for new Classical ML models.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.hyperparam_schema import (
    GradientBoostingConfig,
    LDAConfig,
    MLPConfig,
    NaiveBayesConfig,
)
from ml_lab.core.pipeline import train_classic_model


@pytest.fixture
def dummy_data():
    np.random.seed(42)
    X_train = np.random.randn(30, 8).astype(np.float32)
    y_train = np.array([0] * 15 + [1] * 15, dtype=np.int64)
    X_val = np.random.randn(10, 8).astype(np.float32)
    y_val = np.array([0] * 5 + [1] * 5, dtype=np.int64)
    class_names = ["LUMOS", "NOX"]
    feature_names = [f"f_{i}" for i in range(8)]
    return X_train, y_train, X_val, y_val, class_names, feature_names


@pytest.mark.parametrize("algo,cfg", [
    ("nb", NaiveBayesConfig()),
    ("lda", LDAConfig()),
    ("mlp", MLPConfig(hidden_units=8, max_iter=50)),
    ("gbdt", GradientBoostingConfig(n_estimators=3)),
])
def test_train_new_algorithms_and_generate_c(dummy_data, algo, cfg):
    X_train, y_train, X_val, y_val, class_names, feature_names = dummy_data

    result = train_classic_model(
        X_train, y_train, X_val, y_val, class_names, feature_names, algo=algo, config=cfg
    )

    assert result.val_accuracy >= 0.0
    assert result.benchmark["mcu_latency_ms"] > 0
    assert result.benchmark["mcu_flash_kb"] > 0

    exporter = CCodeExporter()
    h_code = exporter.generate_header_string(result)
    cc_code = exporter.generate_source_string(result)

    assert "classic_predict" in h_code
    assert "classic_predict" in cc_code
    assert "LUMOS" in cc_code
    assert "NOX" in cc_code

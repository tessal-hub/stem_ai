"""
Unit test verifying C++ source (.cc) and header (.h) generation for all 5 Classic ML algorithms
and automated sync into the ESP32 project folder.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pytest

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.hyperparam_schema import (
    DecisionTreeConfig,
    KNNConfig,
    LogisticRegressionConfig,
    RandomForestConfig,
    SVMConfig,
)
from ml_lab.core.pipeline import train_classic_model


@pytest.fixture
def synthetic_data():
    np.random.seed(42)
    X_train = np.random.randn(40, 48).astype(np.float32)
    y_train = np.random.choice([0, 1, 2], size=40).astype(np.int64)
    X_val = np.random.randn(20, 48).astype(np.float32)
    y_val = np.random.choice([0, 1, 2], size=20).astype(np.int64)
    class_names = ["Lumos", "Nox", "Incendio"]
    feature_names = [f"f_{i}" for i in range(48)]
    return X_train, y_train, X_val, y_val, class_names, feature_names


@pytest.mark.parametrize("algo,config", [
    ("tree", DecisionTreeConfig(max_depth=3)),
    ("forest", RandomForestConfig(n_estimators=3, max_depth=3)),
    ("logistic", LogisticRegressionConfig(c=1.0)),
    ("svm", SVMConfig(c=1.0, kernel="rbf")),
    ("knn", KNNConfig(k=3)),
])
def test_c_exporter_generates_valid_h_and_cc(synthetic_data, algo, config):
    X_train, y_train, X_val, y_val, class_names, feature_names = synthetic_data
    result = train_classic_model(
        X_train, y_train, X_val, y_val, class_names, feature_names, algo=algo, config=config
    )

    exporter = CCodeExporter()
    h_code = exporter.generate_header_string(result)
    cc_code = exporter.generate_source_string(result)

    # 1. Kiểm tra Header
    assert "#ifndef MODEL_CLASSIC_H" in h_code
    assert "CLASSIC_NUM_CLASSES 3" in h_code
    assert "CLASSIC_NUM_FEATURES 48" in h_code
    assert "int classic_predict(const float* raw_features, float* out_confidence);" in h_code
    assert "const char* classic_get_class_name(int class_idx);" in h_code

    # 2. Kiểm tra Source .cc
    assert '#include "model_classic.h"' in cc_code
    assert "classic_predict" in cc_code
    assert "classic_get_class_name" in cc_code
    assert '"Lumos"' in cc_code
    assert '"Nox"' in cc_code
    assert '"Incendio"' in cc_code


def test_c_exporter_sync_to_esp32_project(synthetic_data):
    X_train, y_train, X_val, y_val, class_names, feature_names = synthetic_data
    result = train_classic_model(
        X_train, y_train, X_val, y_val, class_names, feature_names, algo="tree"
    )

    exporter = CCodeExporter()
    with tempfile.TemporaryDirectory() as tmp_dir:
        main_dir = Path(tmp_dir) / "main"
        h_file, cc_file = exporter.export_to_esp32_project(result, main_dir)

        assert h_file.exists()
        assert cc_file.exists()
        assert h_file.name == "model_classic.h"
        assert cc_file.name == "model_classic.cc"

        content_cc = cc_file.read_text(encoding="utf-8")
        assert "classic_predict" in content_cc

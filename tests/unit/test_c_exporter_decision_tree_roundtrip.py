"""
Test round-trip C code generation for Decision Tree in ML Lab.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.hyperparam_schema import DecisionTreeConfig
from ml_lab.core.pipeline import train_classic_model
from ml_lab.core.c_exporter import CCodeExporter


def test_c_exporter_decision_tree_roundtrip():
    np.random.seed(42)
    # Synthetic separable dataset
    X_train = np.vstack([
        np.random.randn(20, 10) + 3.0,
        np.random.randn(20, 10) - 3.0,
    ]).astype(np.float32)
    y_train = np.array([0] * 20 + [1] * 20, dtype=np.int64)

    X_val = np.vstack([
        np.random.randn(5, 10) + 3.0,
        np.random.randn(5, 10) - 3.0,
    ]).astype(np.float32)
    y_val = np.array([0] * 5 + [1] * 5, dtype=np.int64)

    classes = ["LUMOS", "NOX"]
    features = [f"feat_{i}" for i in range(10)]

    cfg = DecisionTreeConfig(max_depth=3, criterion="gini")
    result = train_classic_model(
        X_train, y_train, X_val, y_val, class_names=classes, feature_names=features, algo="tree", config=cfg
    )

    exporter = CCodeExporter()
    h_code = exporter.generate_header_string(result)
    cc_code = exporter.generate_source_string(result)

    # 1. Header checks
    assert "#ifndef MODEL_CLASSIC_H" in h_code
    assert "#define MODEL_CLASSIC_H" in h_code
    assert "CLASSIC_NUM_CLASSES 2" in h_code
    assert "CLASSIC_NUM_FEATURES 10" in h_code
    assert "classic_predict" in h_code
    assert "classic_get_class_name" in h_code

    # 2. Source checks
    assert "classic_predict" in cc_code
    assert "classic_get_class_name" in cc_code
    root_thresh = result.model.tree_.threshold[0]
    assert f"{root_thresh:.7f}" in cc_code

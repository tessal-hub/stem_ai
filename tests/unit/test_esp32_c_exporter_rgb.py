"""
tests/unit/test_esp32_c_exporter_rgb.py — Unit tests for per-spell RGB LED export in C exporter.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.hyperparam_schema import KNNConfig
from ml_lab.core.pipeline import train_classic_model


def test_c_exporter_includes_per_spell_rgb():
    np.random.seed(42)
    X_train = np.random.randn(20, 6).astype(np.float32)
    y_train = np.array([0] * 10 + [1] * 10, dtype=np.int64)
    X_val = np.random.randn(6, 6).astype(np.float32)
    y_val = np.array([0] * 3 + [1] * 3, dtype=np.int64)
    class_names = ["LUMOS", "NOX"]
    feature_names = [f"f_{i}" for i in range(6)]

    result = train_classic_model(
        X_train, y_train, X_val, y_val, class_names, feature_names, algo="knn", config=KNNConfig(k=3)
    )

    exporter = CCodeExporter()
    h_code = exporter.generate_header_string(result)
    cc_code = exporter.generate_source_string(result)

    assert "void classic_get_class_rgb(int class_idx, uint8_t* r, uint8_t* g, uint8_t* b);" in h_code
    assert "CLASS_RGB" in cc_code
    assert "void classic_get_class_rgb(int class_idx, uint8_t* r, uint8_t* g, uint8_t* b)" in cc_code

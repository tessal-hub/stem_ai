"""Unit tests for CCodeGenerator."""
from __future__ import annotations

import numpy as np
import pytest

from logic.classic_ml.c_generator import CCodeGenerator
from logic.classic_ml.trainer import ClassicMLTrainer


@pytest.fixture
def trained_results():
    """Train all 5 models on synthetic data."""
    np.random.seed(42)
    classes = ["LUMOS", "NOX"]
    X = np.vstack([
        np.random.randn(15, 10) + 2.0,
        np.random.randn(15, 10) - 2.0,
    ]).astype(np.float32)
    y = np.array([0] * 15 + [1] * 15, dtype=np.int64)
    feature_names = [f"feat_{i}" for i in range(10)]

    trainer = ClassicMLTrainer()
    results = {}
    for m in ["knn", "tree", "forest", "svm", "logistic"]:
        results[m] = trainer.train_and_evaluate(
            X, y, class_names=classes, feature_names=feature_names, model_type=m
        )
    return results


@pytest.mark.parametrize("model_type", ["knn", "tree", "forest", "svm", "logistic"])
def test_c_generator_generates_valid_header(trained_results, model_type):
    """Verify generated C code contains required declarations and functions."""
    result = trained_results[model_type]
    gen = CCodeGenerator()
    c_code = gen.generate_header(result)

    assert "#ifndef MODEL_CLASSIC_H" in c_code
    assert "#define MODEL_CLASSIC_H" in c_code
    assert "CLASSIC_NUM_CLASSES 2" in c_code
    assert "CLASSIC_NUM_FEATURES 10" in c_code
    assert "CLASSIC_CLASS_NAMES" in c_code
    assert "classic_scale_features" in c_code
    assert "classic_predict" in c_code
    assert "classic_get_class_name" in c_code
    assert "#endif // MODEL_CLASSIC_H" in c_code

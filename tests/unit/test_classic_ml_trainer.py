"""Unit tests for ClassicMLTrainer."""
from __future__ import annotations

import numpy as np
import pytest

from logic.classic_ml.trainer import ClassicMLTrainer


@pytest.fixture
def synthetic_dataset():
    """Create a multi-class synthetic feature matrix."""
    np.random.seed(42)
    n_samples_per_class = 20
    n_features = 40
    classes = ["LUMOS", "NOX", "ALOHOMORA"]

    X_list = []
    y_list = []
    for c_idx, _ in enumerate(classes):
        # Shift mean per class for separability
        class_samples = np.random.randn(n_samples_per_class, n_features) + (c_idx * 3.0)
        X_list.append(class_samples)
        y_list.extend([c_idx] * n_samples_per_class)

    X = np.vstack(X_list).astype(np.float32)
    y = np.array(y_list, dtype=np.int64)
    feature_names = [f"f_{i}" for i in range(n_features)]
    return X, y, classes, feature_names


@pytest.mark.parametrize("model_type", ["knn", "tree", "forest", "svm", "logistic"])
def test_trainer_all_models(synthetic_dataset, model_type):
    """Verify training, accuracy, and PCA computation for all supported models."""
    X, y, classes, feature_names = synthetic_dataset
    trainer = ClassicMLTrainer()

    result = trainer.train_and_evaluate(
        X, y, class_names=classes, feature_names=feature_names, model_type=model_type
    )

    assert result.accuracy > 0.6
    assert result.cv_mean > 0.5
    assert result.confusion_matrix.shape == (3, 3)
    assert len(result.class_names) == 3
    assert result.model_type == model_type
    assert "X_2d" in result.pca_result
    assert "Z" in result.pca_result
    assert "mcu_latency_ms" in result.benchmark
    assert result.benchmark["mcu_latency_ms"] > 0

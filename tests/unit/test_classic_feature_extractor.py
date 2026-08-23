"""Unit tests for ClassicFeatureExtractor."""
from __future__ import annotations

import numpy as np
import pytest

from logic.classic_ml.feature_extractor import ClassicFeatureExtractor, FeatureGroupConfig


def test_feature_extractor_output_dimension():
    """Verify feature extractor produces expected feature count."""
    cfg = FeatureGroupConfig()
    extractor = ClassicFeatureExtractor(cfg)
    assert extractor.num_features > 30
    assert len(extractor.feature_names) == extractor.num_features


def test_feature_extractor_synthetic_window():
    """Verify feature extraction on synthetic IMU window."""
    extractor = ClassicFeatureExtractor()
    # 64 samples, 6 channels
    window = np.random.randn(64, 6).astype(np.float32)
    features = extractor.extract_from_window(window)

    assert isinstance(features, np.ndarray)
    assert features.ndim == 1
    assert features.shape[0] == extractor.num_features
    assert not np.isnan(features).any()
    assert not np.isinf(features).any()


def test_feature_extractor_dataset():
    """Verify dataset extraction transforms samples into X and y arrays."""
    extractor = ClassicFeatureExtractor()
    samples = [
        (np.random.randn(64, 6).astype(np.float32), "LUMOS"),
        (np.random.randn(64, 6).astype(np.float32), "LUMOS"),
        (np.random.randn(64, 6).astype(np.float32), "NOX"),
        (np.random.randn(64, 6).astype(np.float32), "NOX"),
        (np.random.randn(64, 6).astype(np.float32), "ALOHOMORA"),
    ]

    X, y, class_names, feature_names = extractor.extract_dataset(samples)

    assert X.shape == (5, extractor.num_features)
    assert y.shape == (5,)
    assert class_names == ["ALOHOMORA", "LUMOS", "NOX"]
    assert len(feature_names) == extractor.num_features


def test_feature_extractor_invalid_input():
    """Verify appropriate error on invalid window shape."""
    extractor = ClassicFeatureExtractor()
    with pytest.raises(ValueError):
        extractor.extract_from_window(np.zeros((1, 6)))

    with pytest.raises(ValueError):
        extractor.extract_from_window(np.zeros((64, 3)))

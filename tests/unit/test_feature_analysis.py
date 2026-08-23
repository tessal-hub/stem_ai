"""
tests/unit/test_feature_analysis.py — Unit tests for feature correlation & attribution.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.data.feature_analysis import (
    compute_correlation_matrix,
    compute_feature_rankings,
    compute_local_feature_contributions,
)
from ml_lab.core.pipeline import train_classic_model


def test_compute_correlation_matrix():
    np.random.seed(42)
    f1 = np.random.randn(50)
    f2 = f1 * 0.99 + np.random.randn(50) * 0.01  # Very high correlation
    f3 = np.random.randn(50)
    X = np.column_stack([f1, f2, f3])
    names = ["feat1", "feat2", "feat3"]

    corr, high_pairs = compute_correlation_matrix(X, names)
    assert corr.shape == (3, 3)
    assert len(high_pairs) >= 1
    assert high_pairs[0]["feat_a"] in ("feat1", "feat2")


def test_compute_feature_rankings():
    np.random.seed(42)
    X = np.random.randn(40, 6)
    y = np.array([0] * 20 + [1] * 20)
    names = [f"f_{i}" for i in range(6)]

    ranks = compute_feature_rankings(X, y, names)
    assert len(ranks) == 6
    assert ranks[0]["importance"] >= ranks[-1]["importance"]


def test_compute_local_contributions():
    np.random.seed(42)
    X_train = np.random.randn(30, 6).astype(np.float32)
    y_train = np.array([0] * 15 + [1] * 15, dtype=np.int64)
    X_val = np.random.randn(6, 6).astype(np.float32)
    y_val = np.array([0] * 3 + [1] * 3, dtype=np.int64)
    names = [f"f_{i}" for i in range(6)]

    res = train_classic_model(
        X_train, y_train, X_val, y_val, ["LUMOS", "NOX"], names, algo="logistic"
    )

    sample = X_train[0]
    contribs = compute_local_feature_contributions(
        res.model, res.scaler, sample, names, algo="logistic", top_k=3
    )

    assert len(contribs) == 3
    assert "contribution" in contribs[0]
    assert "impact" in contribs[0]

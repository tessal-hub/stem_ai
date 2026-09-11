"""Peak trigger + margin gate for live inference (no Qt needed)."""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.live_inference import LiveGesturePredictor, window_motion_score
from ml_lab.core.pipeline import TrainClassicResult


class _PeakyModel:
    """Stub: class 1 với proba đỉnh khi cửa sổ có chuyển động mạnh."""

    def predict(self, X):
        return np.array([1])

    def predict_proba(self, X):
        return np.array([[0.05, 0.95]])


class _FlatModel:
    """Stub overconfident-flat: conf cao nhưng margin 0 → phải bị margin gate chặn."""

    def predict(self, X):
        return np.array([0])

    def predict_proba(self, X):
        return np.array([[0.5, 0.5]])


def _result(model):
    return TrainClassicResult(
        algo="t", algo_name="T", model=model, scaler=None,
        train_accuracy=1, val_accuracy=1, cv_mean=1, cv_std=0,
        confusion_matrix=np.eye(2), class_names=["A", "B"],
        feature_names=["ax_std", "ay_std", "az_std", "gx_std", "gy_std", "gz_std"],
        pca_result={}, benchmark={}, train_time_ms=1, config_dict={},
    )


def _motion_burst(n=200, amp=60.0):
    """Còn standby 64 mẫu, burst sin 64 mẫu, còn standby — như vung 1 cái."""
    out = []
    t = np.linspace(0, 2 * np.pi, 64)
    burst = (np.sin(t) * amp).astype(float)
    out += [[0.0] * 6] * 64
    for v in burst:
        out.append([0.02 + v * 0.01, -0.01 - v * 0.008, 1.0 + v * 0.012,
                    v, v * 0.5, -v * 0.3])
    out += [[0.0] * 6] * (n - 128)
    return out


def test_motion_score_standby_vs_gesture():
    still = np.zeros((64, 6), dtype=np.float32)
    assert window_motion_score(still) < 0.5
    burst = np.array(_motion_burst(), dtype=np.float32)[64:128]
    assert window_motion_score(burst) >= 2.0


def test_tremor_never_triggers():
    p = LiveGesturePredictor(_result(_PeakyModel()))
    rng = np.random.RandomState(0)
    hits = 0
    for _ in range(200):
        s = [float(rng.normal(0, 0.01)), float(rng.normal(0, 0.01)), 1.0,
             float(rng.normal(0, 1.0)), float(rng.normal(0, 1.0)), float(rng.normal(0, 1.0))]
        if p.feed(s) is not None:
            hits += 1
    assert hits == 0


def test_burst_triggers_once_at_peak():
    p = LiveGesturePredictor(_result(_PeakyModel()))
    hits = [p.feed(s) for s in _motion_burst()]
    got = [h for h in hits if h is not None]
    assert 1 <= len(got) <= 2
    assert all(g[0] == "B" and g[1] > 70.0 for g in got)


def test_flat_margin_blocked():
    p = LiveGesturePredictor(_result(_FlatModel()))
    hits = [p.feed(s) for s in _motion_burst()]
    assert all(h is None for h in hits)

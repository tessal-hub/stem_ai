"""Verify encoder loading doesn't block the main thread and uses fast NumPy path."""
import importlib
from pathlib import Path
import sys
import time
from unittest.mock import patch

import numpy as np

from logic.prototypical_recognizer import NumpyEncoder, PrototypicalRecognizer


def test_encoder_pipeline_defers_tf_import():
    """encoder_pipeline module must not import tensorflow at module level."""
    for key in list(sys.modules.keys()):
        if "logic.tensorflow.encoder_pipeline" in key:
            del sys.modules[key]

    with patch.dict(sys.modules, {"tensorflow": None}):
        try:
            importlib.import_module("logic.tensorflow.encoder_pipeline")
            imported_ok = True
        except (ImportError, AttributeError):
            imported_ok = False

    assert imported_ok, "encoder_pipeline imports tensorflow at module level"


def test_numpy_encoder_from_npz_instant_inference():
    """NumpyEncoder must load from npz and predict without tensorflow."""
    npz_path = Path("app_data/gesture_encoder_weights.npz")
    if not npz_path.exists():
        return

    t0 = time.perf_counter()
    encoder = NumpyEncoder.from_npz(npz_path)
    t_load_ms = (time.perf_counter() - t0) * 1000

    assert t_load_ms < 50, f"Load took too long: {t_load_ms:.2f}ms (expected < 50ms)"

    dummy_imu = np.random.randn(4, 64, 9).astype(np.float32)
    embs = encoder.predict(dummy_imu)
    assert embs.shape == (4, 16)
    norms = np.linalg.norm(embs, axis=-1)
    np.testing.assert_allclose(norms, np.ones(4), atol=1e-5)


def test_prototypical_recognizer_works_with_numpy_encoder():
    """PrototypicalRecognizer must operate normally with NumpyEncoder."""
    npz_path = Path("app_data/gesture_encoder_weights.npz")
    if not npz_path.exists():
        return

    encoder = NumpyEncoder.from_npz(npz_path)
    recognizer = PrototypicalRecognizer(encoder=encoder)

    sample_a = np.random.randn(5, 64, 6).astype(np.float32)
    sample_b = np.random.randn(5, 64, 6).astype(np.float32)

    registered = recognizer.register_spell("FIREBALL", list(sample_a))
    assert registered == 5
    assert "FIREBALL" in recognizer.get_registered_spells()

    pred_spell, conf = recognizer.predict(sample_a[0])
    assert pred_spell == "FIREBALL"
    assert conf > 0.0


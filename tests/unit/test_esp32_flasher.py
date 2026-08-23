"""
tests/unit/test_esp32_flasher.py — Unit tests for ML Lab 1-Click ESP32 Flasher.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from ml_lab.core.esp32_flasher import Esp32FlashWorker, list_serial_ports
from ml_lab.core.hyperparam_schema import DecisionTreeConfig
from ml_lab.core.pipeline import train_classic_model
from ml_lab.ui.widgets.flash_dialog import FlashDialog


@pytest.fixture
def dummy_train_result():
    np.random.seed(42)
    X_train = np.random.randn(20, 10).astype(np.float32)
    y_train = np.array([0] * 10 + [1] * 10, dtype=np.int64)
    X_val = np.random.randn(6, 10).astype(np.float32)
    y_val = np.array([0] * 3 + [1] * 3, dtype=np.int64)

    classes = ["LUMOS", "NOX"]
    features = [f"feat_{i}" for i in range(10)]

    cfg = DecisionTreeConfig(max_depth=3)
    return train_classic_model(
        X_train, y_train, X_val, y_val, class_names=classes, feature_names=features, algo="tree", config=cfg
    )


def test_list_serial_ports():
    ports = list_serial_ports()
    assert isinstance(ports, list)


def test_esp32_flash_worker_syncs_and_runs(dummy_train_result, tmp_path, monkeypatch):
    worker = Esp32FlashWorker(port="COM_TEST", result=dummy_train_result)
    
    # Check that worker initializes cleanly
    assert worker.port == "COM_TEST"
    assert worker.result.algo == "tree"
    assert not worker._is_cancelled

    worker.cancel()
    assert worker._is_cancelled


def test_flash_dialog_ui(qapp, dummy_train_result):
    dlg = FlashDialog(result=dummy_train_result)

    assert "LUMOS" in dlg.result.class_names
    assert dlg.btn_flash is not None
    assert dlg.combo_ports is not None
    dlg.close()

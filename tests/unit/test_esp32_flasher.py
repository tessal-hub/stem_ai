"""
tests/unit/test_esp32_flasher.py — Unit tests for ML Lab 1-Click ESP32 Flasher.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
import numpy as np
import pytest

import ml_lab.core.esp32_flasher as flasher_module
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


def test_missing_firmware_binary_is_not_reported_as_flash_success(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_module, "PROJECT_ROOT", tmp_path)
    worker = Esp32FlashWorker(port="COM_TEST", result=None)

    success, message = worker._flash_payload()

    assert not success
    assert "idf.py build" in message


def test_project_root_can_be_next_to_frozen_app(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    project = app_root / "esp32_classic_ml"
    (project / "main").mkdir(parents=True)
    (project / "CMakeLists.txt").write_text("", encoding="utf-8")
    (project / "main" / "CMakeLists.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(flasher_module, "__file__", str(tmp_path / "_internal" / "ml_lab" / "core" / "esp32_flasher.py"))
    monkeypatch.setattr(flasher_module.sys, "executable", str(app_root / "STEMSpellBook.exe"))

    assert flasher_module._find_project_root() == app_root


def test_missing_idf_project_stops_before_creating_firmware_files(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_module, "PROJECT_ROOT", tmp_path)
    worker = Esp32FlashWorker(port="COM_TEST", result=SimpleNamespace(algo_name="Tree"))
    finished = []
    worker.sig_finished.connect(lambda success, message: finished.append((success, message)))

    worker.run()

    assert finished and not finished[0][0]
    assert "source checkout" in finished[0][1]
    assert not (tmp_path / "esp32_classic_ml" / "main").exists()


def test_stale_firmware_binary_is_rejected_before_flash(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_module, "PROJECT_ROOT", tmp_path)
    main_dir = tmp_path / "esp32_classic_ml" / "main"
    build_dir = tmp_path / "esp32_classic_ml" / "build"
    main_dir.mkdir(parents=True)
    build_dir.mkdir()
    for name in ("main.cpp", "classic_features.h", "model_classic.h", "model_classic.cc"):
        (main_dir / name).write_text("source", encoding="utf-8")
    binary = build_dir / "esp32_classic_ml.bin"
    binary.write_bytes(b"old")
    os.utime(binary, (1, 1))
    worker = Esp32FlashWorker(port="COM_TEST", result=None)

    success, message = worker._flash_payload()

    assert not success
    assert "cũ hơn" in message
    assert "chưa nạp firmware" in message


def test_flash_dialog_ui(qapp, dummy_train_result):
    dlg = FlashDialog(result=dummy_train_result)

    assert "LUMOS" in dlg.result.class_names
    assert dlg.btn_flash is not None
    assert dlg.combo_ports is not None
    dlg.close()

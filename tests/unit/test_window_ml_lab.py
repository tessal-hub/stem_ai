"""
Unit tests for MlLabWindow and top-level studio integration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication

from ml_lab.ui.window_ml_lab import MlLabWindow


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_window_ml_lab_initialization(qapp):
    """Verify MlLabWindow initializes all 7 studio tabs without error."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        win = MlLabWindow(spell_dataset_dir=tmp_dir)
        assert win is not None
        assert win.tabs.count() == 7
        assert win.tab_data is not None
        assert win.tab_model is not None
        assert win.tab_curves is not None
        assert win.tab_arena is not None
        assert win.tab_sim is not None
        assert win.tab_history is not None
        assert win.tab_serial is not None


def test_window_ml_lab_model_switch(qapp):
    """Verify switching algorithms dynamically updates hyperparameter controls in TabModelLab."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        win = MlLabWindow(spell_dataset_dir=tmp_dir)
        tab_m = win.tab_model

        # Switch to KNN
        tab_m.combo_algo.setCurrentIndex(0)
        assert hasattr(tab_m, "slider_k")
        assert tab_m.slider_k.value() == 3

        # Switch to Tree
        tab_m.combo_algo.setCurrentIndex(1)
        assert hasattr(tab_m, "slider_depth")
        assert tab_m.slider_depth.value() == 4

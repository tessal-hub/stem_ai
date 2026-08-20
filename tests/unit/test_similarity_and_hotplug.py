"""Unit tests for USB hotplug detection and Spell Similarity & Confusion Matrix."""
from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from logic.prototypical_recognizer import PrototypicalRecognizer
from ui.similarity_matrix_dialog import SimilarityMatrixDialog


class MockEncoder:
    """Mock encoder returning deterministic 16-D embeddings based on input mean."""
    def __init__(self) -> None:
        self.input_shape = (None, 64, 6)

    def predict(self, x: np.ndarray, verbose: int = 0) -> np.ndarray:
        batch_size = x.shape[0]
        embeddings = np.zeros((batch_size, 16), dtype=np.float32)
        for i in range(batch_size):
            val = float(np.mean(x[i]))
            embeddings[i, 0] = np.cos(val)
            embeddings[i, 1] = np.sin(val)
            embeddings[i, 2:] = 0.1
        return embeddings


def test_prototypical_similarity_matrix_calculation() -> None:
    """Verify compute_similarity_matrix computes correct square symmetric cosine similarities."""
    encoder = MockEncoder()
    rec = PrototypicalRecognizer(encoder=encoder)

    # Register 3 distinct mock spells
    sample_lumos = [np.ones((64, 6), dtype=np.float32) * 0.0]
    sample_nox = [np.ones((64, 6), dtype=np.float32) * 1.57]  # ~pi/2 orthogonal
    sample_incendio = [np.ones((64, 6), dtype=np.float32) * 0.05]  # Very close to Lumos

    rec.register_spell("Lumos", sample_lumos)
    rec.register_spell("Nox", sample_nox)
    rec.register_spell("Incendio", sample_incendio)

    names, matrix = rec.compute_similarity_matrix()
    assert len(names) == 3
    assert matrix.shape == (3, 3)

    # Diagonal must be 1.0 (self-similarity)
    for i in range(3):
        assert np.isclose(matrix[i, i], 1.0, atol=1e-3)

    # Matrix must be symmetric
    assert np.allclose(matrix, matrix.T, atol=1e-5)

    # Conflict detection: Lumos and Incendio should be flagged as conflicting
    conflicts = rec.find_conflicting_spells(threshold=0.80)
    assert len(conflicts) >= 1
    spell_pair = (conflicts[0][0], conflicts[0][1])
    assert "Lumos" in spell_pair and "Incendio" in spell_pair
    assert conflicts[0][2] >= 0.80


def test_similarity_matrix_dialog_ui(qapp: QApplication) -> None:
    """Verify SimilarityMatrixDialog instantiates and populates table cells correctly."""
    names = ["Lumos", "Nox", "Incendio"]
    matrix = np.array([
        [1.0, 0.35, 0.88],
        [0.35, 1.0, 0.40],
        [0.88, 0.40, 1.0],
    ], dtype=np.float32)
    conflicts = [("Lumos", "Incendio", 0.88)]

    dlg = SimilarityMatrixDialog(spell_names=names, matrix=matrix, conflicts=conflicts)
    assert dlg.isVisible() is False or dlg.isEnabled()
    assert dlg._table.rowCount() == 3
    assert dlg._table.columnCount() == 3
    assert dlg._table.item(0, 0).text() == "100%"
    assert dlg._table.item(0, 2).text() == "88%"
    dlg.close()


def test_similarity_matrix_dialog_empty(qapp: QApplication) -> None:
    """Verify SimilarityMatrixDialog handles empty/single spell gracefully."""
    dlg = SimilarityMatrixDialog(spell_names=[], matrix=np.empty((0, 0)), conflicts=[])
    assert dlg._table.rowCount() == 0
    dlg.close()


def test_handler_usb_hotplug_check(qapp: QApplication, monkeypatch) -> None:
    """Verify _check_usb_hotplug triggers auto connect when new port appears."""
    from unittest.mock import MagicMock
    from logic.handler import Handler
    from logic.data_store import DataStore
    from ui.main_window import MainWindow

    store = DataStore()
    win = MainWindow(data_store=store)
    handler = Handler(win.page_wand, win.page_record, win.page_home, store, win.page_setting)

    # Mock initial ports
    monkeypatch.setattr("logic.handler.SerialWorker.get_available_ports", lambda: ["COM1"])
    handler._known_ports = {"COM1"}

    # Simulate plugging in new ESP32 Wand at COM5
    monkeypatch.setattr("logic.handler.SerialWorker.get_available_ports", lambda: ["COM1", "COM5"])
    handler.on_serial_connect = MagicMock()

    handler._check_usb_hotplug()
    assert handler.on_serial_connect.called
    assert handler.on_serial_connect.call_args[0][0] == "COM5"

    handler.shutdown()
    win.close()

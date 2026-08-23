"""
tests/unit/test_tab_serial_monitor.py — Unit test for Tab 7 Serial Monitor.
"""

from __future__ import annotations

import pytest
from ml_lab.ui.tabs.tab_serial_monitor import TabSerialMonitor, MlLabSerialWorker


def test_serial_worker_init():
    worker = MlLabSerialWorker(port="COM_TEST", baud_rate=115200)
    assert worker.port == "COM_TEST"
    assert worker.baud_rate == 115200
    assert not worker._running


def test_tab_serial_monitor_ui(qapp):
    tab = TabSerialMonitor()
    assert tab.combo_ports is not None
    assert tab.btn_connect is not None
    assert tab.term_edit is not None
    assert tab.lbl_spell_name is not None

    # Test parse incoming prediction
    tab._on_prediction_received("LUMOS", 98.5, 0.04)
    assert tab.lbl_spell_name.text() == "LUMOS"
    assert "98.5%" in tab.lbl_conf_text.text()
    assert tab.table_history.rowCount() == 1

    tab._clear_terminal()
    assert tab.term_edit.toPlainText() == ""
    tab.close()

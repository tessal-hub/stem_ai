"""
tests/unit/test_discard_current_sample.py — Unit tests for discarding/clearing current recording buffer.
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from logic.data_store import DataStore
from ui.page_record import PageRecord


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_discard_current_sample_after_recording_stops(qapp, tmp_path):
    store = DataStore(dataset_dir=str(tmp_path))
    page = PageRecord(store)
    page._setup_plots()
    page.load_spell_list({"ABC": 2})

    # Simulate having recorded data
    store.add_live_sample([0.1, 0.2, 0.3, 1.0, 2.0, 3.0])
    store.add_live_sample([0.2, 0.3, 0.4, 1.1, 2.1, 3.1])
    assert len(store.get_live_buffer_snapshot()) == 2

    # Stop recording
    page._on_btn_stop_clicked()
    assert page.btn_snip.isEnabled() is True
    assert page.btn_discard.isEnabled() is True
    assert page.crop_region.isVisible() is True

    # Track sig_clear_buffer
    cleared_signals = []
    page.sig_clear_buffer.connect(lambda: cleared_signals.append(True))

    # Click discard
    page.btn_discard.click()

    # Verify state after discard
    assert len(store.get_live_buffer_snapshot()) == 0
    assert page.btn_snip.isEnabled() is False
    assert page.btn_discard.isEnabled() is False
    assert page.crop_region.isVisible() is False
    assert len(cleared_signals) == 1
    assert page.lbl_record_count.text() == "0"
    assert page.lbl_record_duration.text() == "00:00"


def test_discard_while_live_recording(qapp, tmp_path):
    store = DataStore(dataset_dir=str(tmp_path))
    page = PageRecord(store)

    # Start recording
    page.set_recording_state(True)
    assert page.is_live is True
    assert page.btn_discard.isEnabled() is True

    stopped_signals = []
    page.sig_stop_record.connect(lambda: stopped_signals.append(True))

    # Discard while live
    page.btn_discard.click()

    assert page.is_live is False
    assert page.btn_discard.isEnabled() is False
    assert len(stopped_signals) == 1
    assert len(store.get_live_buffer_snapshot()) == 0

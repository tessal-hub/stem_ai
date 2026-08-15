"""
tests/unit/test_advanced_mode_and_stream.py

Unit tests for:
1. _RealtimeStreamCapture in FlashWorker (live progress and output streaming).
2. Advanced mode toggle across PageSetting and PageWand.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from logic.data_store import DataStore
from logic.flash_worker import _RealtimeStreamCapture
from ui.page_setting import PageSetting
from ui.page_wand import PageWand


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_realtime_stream_capture_newline_and_carriage_return():
    lines_received = []
    progress_received = []

    stream = _RealtimeStreamCapture(
        on_line_cb=lines_received.append,
        on_progress_cb=progress_received.append,
    )

    stream.write("Connecting....\n")
    stream.write("Chip is ESP32-S3 (QFN56)\n")
    assert "Connecting...." in lines_received
    assert "Chip is ESP32-S3 (QFN56)" in lines_received

    stream.write("Writing at 0x00010000... (8 %)\r")
    assert 8 in progress_received
    assert any("8 %" in line for line in lines_received)

    stream.write("Writing at 0x00018000... (25 %)\r")
    assert 25 in progress_received

    stream.write("Writing at 0x00058000... (100 %)\n")
    assert 100 in progress_received

    stream.flush()
    assert "Connecting...." in stream.getvalue()


def test_page_setting_advanced_mode_toggle(qapp):
    store = DataStore()
    page = PageSetting(store)

    page.set_advanced_mode(True)
    assert page.console_log.isHidden() is False
    assert page.quality_card_widget.isHidden() is False
    assert page._left_col.count() >= 3
    assert page._right_col.count() >= 2

    page.set_advanced_mode(False)
    assert page.console_log.isHidden() is True
    assert page.quality_card_widget.isHidden() is True
    # 2 cards on left, 2 cards on right (balanced)
    assert page._left_col.count() >= 2
    assert page._right_col.count() >= 2

    assert "nâng cao" in page.lbl_show_primitives.text().lower() or "advanced" in page.lbl_show_primitives.text().lower()


def test_page_wand_advanced_mode_toggle(qapp):
    store = DataStore()
    page = PageWand(store)

    page.set_advanced_mode(True)
    assert page.terminal_panel.isHidden() is False
    assert page._left_col.itemAt(1).widget() == page.payload_panel

    page.set_advanced_mode(False)
    assert page.terminal_panel.isHidden() is True
    assert page._right_col.itemAt(0).widget() == page.payload_panel


def test_session_loaded_spells_in_home_page(qapp):
    from ui.page_home import PageHome
    store = DataStore()
    store.spell_counts = {"WINGARDIUM": 15, "ALOHOMORA": 20, "LUMOS": 10, "FIREBALL": 5}
    home = PageHome(store)

    # Initially empty
    assert home._loaded_empty_card.isVisible() or home._loaded_empty_card.isHidden() is False
    assert len(home._last_loaded_spells) == 0

    # Simulate NVS payload built with 2 selected spells
    store.set_registered_prototypes({"WINGARDIUM", "LUMOS"})
    home.update_loaded_spells(store.registered_prototypes)

    assert home._loaded_empty_card.isHidden() is True
    assert home._last_loaded_spells == {"WINGARDIUM", "LUMOS"}
    assert home._loaded_spells_content_layout.count() >= 2

    # Simulate creating a second NVS in the SAME session with different spells (e.g. only FIREBALL)
    store.set_registered_prototypes(set())
    home.update_loaded_spells(store.registered_prototypes)
    assert home._loaded_empty_card.isHidden() is False

    store.set_registered_prototypes({"FIREBALL"})
    home.update_loaded_spells(store.registered_prototypes)
    assert home._loaded_empty_card.isHidden() is True
    assert home._last_loaded_spells == {"FIREBALL"}

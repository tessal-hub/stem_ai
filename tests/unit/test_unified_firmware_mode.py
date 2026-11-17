"""
tests/unit/test_unified_firmware_mode.py — Test unified firmware runtime mode switching.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QObject
from logic.serial_worker import SerialWorker
from logic.firmware_detector import FirmwareDetector, FW_DATA, FW_INFERENCE
from logic.data_store import DataStore


def test_serial_worker_set_wand_mode_queues_command():
    worker = SerialWorker(port="COM3")
    worker._running = True

    # Valid data mode
    ok = worker.set_wand_mode("data")
    assert ok is True
    cmd = worker._outbound_commands.get_nowait()
    assert cmd == "CMD:SET_MODE:DATA\n"

    # Valid inference mode
    ok = worker.set_wand_mode("inference")
    assert ok is True
    cmd = worker._outbound_commands.get_nowait()
    assert cmd == "CMD:SET_MODE:INFERENCE\n"

    # Invalid mode
    ok = worker.set_wand_mode("unknown_mode")
    assert ok is False


def test_serial_worker_query_wand_mode():
    worker = SerialWorker(port="COM3")
    worker._running = True
    ok = worker.query_wand_mode()
    assert ok is True
    cmd = worker._outbound_commands.get_nowait()
    assert cmd == "CMD:GET_MODE\n"


def test_firmware_detector_ack_mode_switch():
    detector = FirmwareDetector()
    detector.on_connection_status(True, "COM3")

    # Simulate ACK for DATA mode
    detector.on_raw_line("ACK:MODE:DATA")
    assert detector.current_firmware == FW_DATA

    # Simulate ACK for INFERENCE mode
    detector.on_raw_line("ACK:MODE:INFERENCE")
    assert detector.current_firmware == FW_INFERENCE


def test_firmware_detector_on_wand_mode_changed():
    detector = FirmwareDetector()
    detector.on_connection_status(True, "COM3")

    detector.on_wand_mode_changed("data")
    assert detector.current_firmware == FW_DATA

    detector.on_wand_mode_changed("inference")
    assert detector.current_firmware == FW_INFERENCE


def test_data_store_wand_mode(tmp_path):
    store = DataStore(dataset_dir=str(tmp_path))
    received_modes = []
    store.sig_wand_mode_changed.connect(received_modes.append)

    store.set_wand_mode("data")
    assert store.get_wand_mode() == "data"
    assert "data" in received_modes

    store.set_wand_mode("inference")
    assert store.get_wand_mode() == "inference"
    assert "inference" in received_modes

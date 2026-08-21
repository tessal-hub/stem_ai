"""Unit tests for FirmwareDetector and firmware identification flow."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from logic.data_store import DataStore
from logic.firmware_detector import (
    FW_DATA,
    FW_DETECTING,
    FW_DISCONNECTED,
    FW_INFERENCE,
    FW_UNKNOWN,
    FirmwareDetector,
)
from ui.wand_panels.connection_panel import WandConnectionPanel


def test_firmware_detector_initial_state(qapp: QApplication, tmp_path) -> None:
    """Verify FirmwareDetector starts in disconnected state."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)
    assert detector.current_firmware == FW_DISCONNECTED
    assert store.get_detected_firmware() == FW_DISCONNECTED


def test_firmware_detector_connect_starts_detecting(qapp: QApplication, tmp_path) -> None:
    """Verify connecting serial transitions detector into detecting state."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    events: list[str] = []
    detector.sig_firmware_changed.connect(events.append)

    detector.on_connection_status(True, "COM3")
    assert detector.current_firmware == FW_DETECTING
    assert store.get_detected_firmware() == FW_DETECTING
    assert events == [FW_DETECTING]


def test_firmware_detector_identifies_data_firmware(qapp: QApplication, tmp_path) -> None:
    """Verify continuous sensor CSV frames confirm Data Collection firmware."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    # First frame
    detector.on_sensor_frame([0.05, -0.02, 1.01, 0.1, -0.2, 0.0])
    assert detector.current_firmware == FW_DETECTING

    # Second frame confirms streaming data firmware
    detector.on_sensor_frame([0.06, -0.01, 1.00, 0.1, -0.1, 0.0])
    assert detector.current_firmware == FW_DATA
    assert store.get_detected_firmware() == FW_DATA


def test_firmware_detector_identifies_inference_from_tflm_logs(qapp: QApplication, tmp_path) -> None:
    """Verify TFLM and ESP-IDF log lines identify AI Inference firmware."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_raw_line("I (1234) SPELLBOOK: TFLM ready, arena used: 34500 / 98304")
    assert detector.current_firmware == FW_INFERENCE
    assert store.get_detected_firmware() == FW_INFERENCE


def test_firmware_detector_identifies_inference_from_nvs_logs(qapp: QApplication, tmp_path) -> None:
    """Verify Loaded gestures from NVS log line identifies AI Inference firmware."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_raw_line("I (1500) SPELLBOOK: Loaded 4 gestures from NVS")
    assert detector.current_firmware == FW_INFERENCE


def test_firmware_detector_identifies_inference_from_prediction(qapp: QApplication, tmp_path) -> None:
    """Verify prediction frames identify AI Inference firmware."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_raw_line("FINAL PREDICT:LUMOS:0.95")
    assert detector.current_firmware == FW_INFERENCE


def test_firmware_detector_prediction_slot(qapp: QApplication, tmp_path) -> None:
    """Verify on_prediction_received identifies AI Inference firmware."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_prediction_received("ALOHOMORA", 0.88)
    assert detector.current_firmware == FW_INFERENCE


def test_firmware_detector_identifies_from_flash_completion(qapp: QApplication, tmp_path) -> None:
    """Verify on_flash_completed sets firmware state immediately."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_flash_completed("data")
    assert detector.current_firmware == FW_DATA
    assert store.get_detected_firmware() == FW_DATA

    detector.on_flash_completed("inference")
    assert detector.current_firmware == FW_INFERENCE
    assert store.get_detected_firmware() == FW_INFERENCE


def test_firmware_detector_timeout_to_unknown(qapp: QApplication, tmp_path) -> None:
    """Verify detector transitions to unknown if probing window times out."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    assert detector.current_firmware == FW_DETECTING

    # Manually trigger timeout
    detector._on_detect_timeout()
    assert detector.current_firmware == FW_UNKNOWN
    assert store.get_detected_firmware() == FW_UNKNOWN


def test_firmware_detector_disconnect(qapp: QApplication, tmp_path) -> None:
    """Verify disconnect resets detector to disconnected state."""
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    detector = FirmwareDetector(data_store=store)

    detector.on_connection_status(True, "COM3")
    detector.on_flash_completed("data")
    assert detector.current_firmware == FW_DATA

    detector.on_connection_status(False, "Disconnected")
    assert detector.current_firmware == FW_DISCONNECTED
    assert store.get_detected_firmware() == FW_DISCONNECTED


def test_wand_connection_panel_firmware_display(qapp: QApplication) -> None:
    """Verify WandConnectionPanel updates its firmware status badge."""
    panel = WandConnectionPanel()

    # Initially disconnected
    panel.set_firmware_status(FW_DISCONNECTED)
    assert panel.lbl_firmware_status.property("status") == "muted"

    # Connected with data firmware
    panel.set_serial_status(True, "COM3")
    panel.set_firmware_status(FW_DATA)
    assert "collect.bin" in panel.lbl_firmware_status.text()
    assert panel.lbl_firmware_status.property("status") == "success"

    # Connected with inference firmware
    panel.set_firmware_status(FW_INFERENCE)
    assert "inference.bin" in panel.lbl_firmware_status.text()
    assert panel.lbl_firmware_status.property("status") == "accent"

    # Detecting
    panel.set_firmware_status(FW_DETECTING)
    assert panel.lbl_firmware_status.property("status") == "warning"

    # Unknown
    panel.set_firmware_status(FW_UNKNOWN)
    assert panel.lbl_firmware_status.property("status") == "warning"

    panel.close()

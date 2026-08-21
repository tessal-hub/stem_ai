"""
logic/firmware_detector.py — Real-time firmware identification from serial traffic.

Architecture:
    - Spots whether the connected ESP32 is running:
        1. 'data' (Data Collection firmware / collect.bin): streams 6-axis CSV lines (ax,ay,az,gx,gy,gz) at 50Hz.
        2. 'inference' (On-device AI inference / inference.bin): outputs PREDICT / TFLM / SPELLBOOK logs.
        3. 'detecting': initial probing window upon connection.
        4. 'unknown': unrecognized stream or quiet port.
        5. 'disconnected': serial port is closed.
    - Publishes state changes reactively to DataStore.
    - Time-bounded transition from 'detecting' to 'unknown' if no signature arrives.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from .data_store import DataStore

log = logging.getLogger(__name__)

FW_DISCONNECTED = "disconnected"
FW_DETECTING = "detecting"
FW_DATA = "data"
FW_INFERENCE = "inference"
FW_UNKNOWN = "unknown"

# Signature patterns for on-device TinyML AI firmware (inference.bin)
_INFERENCE_KEYWORDS: tuple[str, ...] = (
    "PREDICT:",
    "FINAL PREDICT:",
    "SPELLBOOK",
    "TFLM",
    "TFLITE",
    "TENSORFLOW LITE",
    "GESTURES FROM NVS",
    "SAMPLING + INFERENCE TASKS STARTED",
    "GESTURE_INFERENCE",
    "IMU_SAMPLING",
    "DEBUG_MOTION",
    "DEBUG_BLACKHOLE",
    "DEBUG_TIMING",
    "ONSPELLDETECTED",
    "INITIALIZESPELLRUNTIME",
    "ARENA USED:",
    "LABELS NVS PARTITION",
)


class FirmwareDetector(QObject):
    """
    Real-time firmware classifier for connected ESP32 devices.
    Listens to raw UART lines, sensor CSV frames, and flash events.
    """

    sig_firmware_changed = pyqtSignal(str)  # fw_type: "disconnected"|"detecting"|"data"|"inference"|"unknown"

    def __init__(self, data_store: DataStore | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = data_store
        self._current_firmware: str = FW_DISCONNECTED
        self._is_connected: bool = False
        self._sensor_frame_count: int = 0

        self._detect_timer = QTimer(self)
        self._detect_timer.setSingleShot(True)
        self._detect_timer.setInterval(2500)  # 2.5s detection window
        self._detect_timer.timeout.connect(self._on_detect_timeout)

    @property
    def current_firmware(self) -> str:
        """Return the currently detected firmware type."""
        return self._current_firmware

    def on_connection_status(self, connected: bool, _port_or_msg: str = "") -> None:
        """Handle serial connection and disconnection events."""
        if connected:
            self._is_connected = True
            self._sensor_frame_count = 0
            self._set_firmware(FW_DETECTING)
            self._detect_timer.start()
        else:
            self._is_connected = False
            self._detect_timer.stop()
            self._sensor_frame_count = 0
            self._set_firmware(FW_DISCONNECTED)

    def on_sensor_frame(self, values: Sequence[float]) -> None:
        """Process one valid sensor frame (ax, ay, az, gx, gy, gz)."""
        if not self._is_connected:
            return

        if len(values) >= 6:
            self._sensor_frame_count += 1
            # 2 consecutive valid frames confirm active 50Hz CSV stream (collect.bin)
            if self._sensor_frame_count >= 2 and self._current_firmware != FW_DATA:
                self._detect_timer.stop()
                self._set_firmware(FW_DATA)

    def on_raw_line(self, line: str) -> None:
        """Inspect a raw UART text line for known firmware signatures."""
        if not self._is_connected or not line:
            return

        line_upper = line.upper()
        for kw in _INFERENCE_KEYWORDS:
            if kw in line_upper:
                self._detect_timer.stop()
                self._set_firmware(FW_INFERENCE)
                return

    def on_prediction_received(self, action: str, _confidence: float) -> None:
        """Receive a parsed prediction from on-device inference."""
        if not self._is_connected:
            return

        if action and action != "None":
            self._detect_timer.stop()
            self._set_firmware(FW_INFERENCE)

    def on_flash_completed(self, bin_type: str) -> None:
        """Update firmware type immediately upon successful firmware flash."""
        self._detect_timer.stop()
        if bin_type == "data":
            self._set_firmware(FW_DATA)
        elif bin_type in ("inference", "model", "nvs"):
            self._set_firmware(FW_INFERENCE)

    def _on_detect_timeout(self) -> None:
        """Called when probing window expires without identifying signatures."""
        if self._is_connected and self._current_firmware == FW_DETECTING:
            self._set_firmware(FW_UNKNOWN)

    def _set_firmware(self, fw_type: str) -> None:
        """Set firmware state, update store, and emit change signal."""
        if self._current_firmware == fw_type:
            return
        log.info("ESP Firmware detected: %s -> %s", self._current_firmware, fw_type)
        self._current_firmware = fw_type
        if self.store is not None and hasattr(self.store, "set_detected_firmware"):
            self.store.set_detected_firmware(fw_type)
        self.sig_firmware_changed.emit(fw_type)

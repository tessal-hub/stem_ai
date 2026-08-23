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
FW_INFERENCE_NO_NVS = "inference_no_nvs"
FW_UNKNOWN = "unknown"

# Patterns indicating AI Inference firmware with NVS uninitialized, empty, or missing
_INFERENCE_NO_NVS_PATTERNS: tuple[str, ...] = (
    "FAILED TO OPEN NVS NAMESPACE",
    "FAILED TO READ COUNT FROM NVS",
    "INVALID GESTURE COUNT",
    "0 GESTURES PARSED",
    "RUNTIME INITIALIZATION FAILED",
    "NVS_FLASH_INIT_PARTITION",
    "NVS_FLASH_ERASE_PARTITION",
    "MODEL PARTITION NOT FOUND",
    "FAILED TO MMAP MODEL PARTITION",
    "MODEL SCHEMA MISMATCH",
    "ALLOCATETENSORS FAILED",
    "FAILED TO CREATE BUFFER MUTEX",
    "RUNTIME INITIALIZATION FAILED - HALTING",
)

# Patterns confirming AI Inference firmware is loaded with active NVS gestures and ready
_INFERENCE_READY_PATTERNS: tuple[str, ...] = (
    "PREDICT:",
    "FINAL PREDICT:",
    "SAMPLING + INFERENCE TASKS STARTED",
    "ONSPELLDETECTED",
    "DEBUG_MOTION",
    "DEBUG_BLACKHOLE",
    "DEBUG_TIMING",
)

# General AI firmware signatures
_INFERENCE_GENERAL_PATTERNS: tuple[str, ...] = (
    "SPELLBOOK",
    "TFLM",
    "TFLITE",
    "TENSORFLOW LITE",
    "GESTURE_INFERENCE",
    "IMU_SAMPLING",
    "INITIALIZESPELLRUNTIME",
    "ARENA USED:",
    "MPU6050 READY",
    "I2C BUS READY",
    "MPU6050 ADD DEVICE",
)


class FirmwareDetector(QObject):
    """
    Real-time firmware classifier for connected ESP32 devices.
    Listens to raw UART lines, sensor CSV frames, and flash events.
    """

    sig_firmware_changed = pyqtSignal(str)  # fw_type: "disconnected"|"detecting"|"data"|"inference"|"inference_no_nvs"|"unknown"

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

        # 1. Check for uninitialized / missing NVS patterns in AI firmware
        for pat in _INFERENCE_NO_NVS_PATTERNS:
            if pat in line_upper:
                self._detect_timer.stop()
                self._set_firmware(FW_INFERENCE_NO_NVS)
                return

        # 2. Check for active inference and prediction patterns
        for pat in _INFERENCE_READY_PATTERNS:
            if pat in line_upper:
                self._detect_timer.stop()
                self._set_firmware(FW_INFERENCE)
                return

        # 3. Check for gesture count in NVS logs (e.g. "Loaded 4 gestures from NVS" vs "Loaded 0 gestures")
        if "LOADED" in line_upper and "GESTURE" in line_upper:
            self._detect_timer.stop()
            if "LOADED 0 GESTURE" in line_upper:
                self._set_firmware(FW_INFERENCE_NO_NVS)
            else:
                self._set_firmware(FW_INFERENCE)
            return

        # 4. General AI firmware signatures
        for pat in _INFERENCE_GENERAL_PATTERNS:
            if pat in line_upper:
                self._detect_timer.stop()
                # If already identified as inference ready or inference no nvs, preserve it; otherwise default to inference_no_nvs until ready signature seen
                if self._current_firmware not in (FW_INFERENCE, FW_INFERENCE_NO_NVS):
                    self._set_firmware(FW_INFERENCE_NO_NVS)
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
        elif bin_type == "inference":
            # Standalone inference.bin flash has no NVS labels yet until model upload
            self._set_firmware(FW_INFERENCE_NO_NVS)
        elif bin_type in ("model", "nvs", "trained"):
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

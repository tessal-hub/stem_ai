"""
logic/serial_worker.py — Background thread for high-speed ESP32 serial communication.

Architecture:
    - Runs in a separate QThread to avoid UI freezing.
    - Handles 115200 baud rate.
    - Normalises sensor data (Accel / 16 384, Gyro / 131).
    - Detects:
        1. PREDICT:<Action>:<Conf> → real-time inference result.
        2. aX,aY,aZ,gX,gY,gZ     → 6-axis training/streaming data.
"""

from __future__ import annotations

import logging

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MPU-6050 normalisation divisors
# ---------------------------------------------------------------------------
_ACCEL_SCALE = 16_384.0   # +-2 g   full-scale -> 1 g    = 16 384 LSB
_GYRO_SCALE  =    131.0   # +-250 dps full-scale -> 1 dps = 131 LSB

_BAUD = 115_200


class SerialWorker(QThread):
    """Background UART listener and frame processor."""

    # ── Signals ─────────────────────────────────────────────────────────
    # sig_ prefix is consistent with the rest of the codebase.
    sig_data_received       = pyqtSignal(list)         # [ax, ay, az, gx, gy, gz] normalised
    sig_prediction_received = pyqtSignal(str, float)   # (label, confidence)
    sig_connection_status   = pyqtSignal(bool, str)    # (is_connected, message)
    sig_raw_line_received   = pyqtSignal(str)          # every decoded line -> terminal

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.port     = port
        self._serial: serial.Serial | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_command(self, cmd: str) -> bool:
        """Encode and transmit *cmd* over the open serial port.

        Returns True on success, False if the port is closed or the write fails.
        Only emits a status signal on genuine failure, not on success.
        """
        if self._serial is None or not self._serial.is_open:
            return False
        try:
            if not cmd.endswith("\n"):
                cmd += "\n"
            self._serial.write(cmd.encode("utf-8"))
            return True
        except Exception:
            log.exception("SerialWorker.send_command failed")
            self.sig_connection_status.emit(False, "Send failed — port may have disconnected.")
            return False

    def stop(self) -> None:
        """Request the event loop to exit and wait up to 3 s for it to finish.

        A bounded wait prevents the UI thread from hanging indefinitely if the
        serial port stalls mid-read.
        """
        self._running = False
        if not self.wait(3_000):
            log.warning("SerialWorker did not stop within timeout; terminating.")
            self.terminate()

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Open the port and read frames until stop() is called."""
        try:
            self._serial  = serial.Serial(self.port, _BAUD, timeout=1.0)
            self._running = True
            self.sig_connection_status.emit(
                True, f"Connected to {self.port} at {_BAUD} baud"
            )
            self._read_loop()
        except serial.SerialException:
            log.exception("SerialWorker: could not open port %s", self.port)
            self.sig_connection_status.emit(False, f"Cannot open {self.port}")
        finally:
            self._cleanup()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _read_loop(self) -> None:
        """Inner loop: read one line per iteration, dispatch by frame type."""
        assert self._serial is not None

        while self._running:
            if not self._serial.in_waiting:
                self.msleep(10)     # yield CPU; _running checked ~100x/s
                continue

            try:
                line = self._serial.readline().decode("utf-8", errors="ignore").strip()
            except Exception:
                log.exception("SerialWorker: readline failed")
                continue

            if not line:
                continue

            self.sig_raw_line_received.emit(line)   # forward to terminal unconditionally

            if line.startswith("PREDICT:"):
                self._handle_prediction(line)
            elif "," in line and not line.startswith("ACK:"):
                self._handle_sensor_csv(line)

    def _handle_prediction(self, line: str) -> None:
        """Parse PREDICT:<label>:<confidence> frames.

        maxsplit=2 ensures labels that contain colons (e.g. 'SPELL:ACCIO')
        are captured in full rather than being silently truncated.
        """
        parts = line.split(":", maxsplit=2)
        if len(parts) < 3:
            log.debug("Malformed PREDICT frame: %r", line)
            return
        label = parts[1]
        try:
            conf = float(parts[2])
        except ValueError:
            log.debug("Non-numeric confidence in PREDICT frame: %r", line)
            return
        self.sig_prediction_received.emit(label, conf)

    def _handle_sensor_csv(self, line: str) -> None:
        """Parse aX,aY,aZ,gX,gY,gZ CSV frames and emit normalised float list."""
        parts = line.split(",")
        if len(parts) != 6:
            log.debug("Unexpected CSV field count (%d): %r", len(parts), line)
            return
        try:
            raw = [float(p) for p in parts]
        except ValueError:
            log.debug("Non-numeric CSV field in: %r", line)
            return

        norm: list[float] = [
            raw[0] / _ACCEL_SCALE,
            raw[1] / _ACCEL_SCALE,
            raw[2] / _ACCEL_SCALE,
            raw[3] / _GYRO_SCALE,
            raw[4] / _GYRO_SCALE,
            raw[5] / _GYRO_SCALE,
        ]
        self.sig_data_received.emit(norm)

    def _cleanup(self) -> None:
        """Close the serial port and broadcast disconnected status."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                log.exception("SerialWorker: error closing port")
        self._serial  = None
        self._running = False
        self.sig_connection_status.emit(False, "Disconnected")

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_available_ports() -> list[str]:
        """Return a sorted list of available serial port device paths."""
        return sorted(p.device for p in serial.tools.list_ports.comports())
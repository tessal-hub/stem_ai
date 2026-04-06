"""
logic/serial_worker.py — Background thread for high-speed ESP32 serial communication.

Architecture:
    - Runs in a separate QThread to avoid UI freezing.
    - Handles 115200 baud rate.
    - Uses shared frame validators and one canonical normalization path.
    - Detects:
        1. PREDICT:<Action>:<Conf> -> real-time inference result.
        2. aX,aY,aZ,gX,gY,gZ     -> 6-axis training/streaming data.
"""

from __future__ import annotations

import logging
import queue

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal

from .frame_protocol import (
    DEFAULT_SCALE_PROFILE,
    FrameValidationError,
    SensorScaleProfile,
    parse_prediction_frame,
    parse_sensor_csv_frame,
)

log = logging.getLogger(__name__)

_BAUD = 115_200


class SerialWorker(QThread):
    """Background UART listener and frame processor."""

    # ── Signals ─────────────────────────────────────────────────────────
    # sig_ prefix is consistent with the rest of the codebase.
    sig_data_received       = pyqtSignal(list)         # [ax, ay, az, gx, gy, gz] normalised
    sig_prediction_received = pyqtSignal(str, float)   # (label, confidence)
    sig_connection_status   = pyqtSignal(bool, str)    # (is_connected, message)
    sig_raw_line_received   = pyqtSignal(str)          # every decoded line -> terminal
    sig_error               = pyqtSignal(str)          # standardized worker error channel
    sig_finished            = pyqtSignal(bool, str)    # standardized worker completion channel

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.port     = port
        self._serial: serial.Serial | None = None
        self._running = False
        self._outbound_commands: queue.Queue[str] = queue.Queue()
        self._scale_profile = DEFAULT_SCALE_PROFILE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_command(self, cmd: str) -> bool:
        """Encode and transmit *cmd* over the open serial port.

        Returns True on success, False if the port is closed or the write fails.
        Only emits a status signal on genuine failure, not on success.
        """
        if not self._running:
            return False
        try:
            if not cmd.endswith("\n"):
                cmd += "\n"
            self._outbound_commands.put_nowait(cmd)
            return True
        except queue.Full:
            self.sig_error.emit("Send queue full; command dropped")
            return False
        except Exception as e:
            log.exception("SerialWorker.send_command failed")
            self.sig_error.emit(f"Serial command queue failed: {type(e).__name__}: {e}")
            return False

    def stop(self) -> None:
        """Request the event loop to exit and wait up to 3 s for it to finish.

        A bounded wait prevents the UI thread from hanging indefinitely if the
        serial port stalls mid-read.
        """
        self._running = False

    def set_scale_profile(self, profile: SensorScaleProfile) -> None:
        """Update accel/gyro normalization divisors used for CSV frames."""
        self._scale_profile = profile

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Open the port and read frames until stop() is called."""
        success = False
        message = "Disconnected"
        try:
            self._serial  = serial.Serial(self.port, _BAUD, timeout=1.0)
            self._running = True
            self.sig_connection_status.emit(
                True, f"Connected to {self.port} at {_BAUD} baud"
            )
            self._read_loop()
            success = True
            message = "Serial worker stopped"
        except serial.SerialException:
            log.exception("SerialWorker: could not open port %s", self.port)
            message = f"Cannot open {self.port}"
            self.sig_error.emit(message)
            self.sig_connection_status.emit(False, message)
        except Exception as e:
            log.exception("SerialWorker: run failed")
            message = f"Serial worker exception: {type(e).__name__}: {e}"
            self.sig_error.emit(message)
        finally:
            self._cleanup()
            self.sig_finished.emit(success, message)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _read_loop(self) -> None:
        """Inner loop: read one line per iteration, dispatch by frame type."""
        assert self._serial is not None

        while self._running:
            self._drain_outbound_commands()

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
        """Parse one prediction frame using the shared protocol validator."""
        try:
            label, conf = parse_prediction_frame(line)
        except FrameValidationError:
            log.debug("Malformed PREDICT frame: %r", line)
            return
        self.sig_prediction_received.emit(label, conf)

    def _handle_sensor_csv(self, line: str) -> None:
        """Parse one sensor CSV frame with shared validation + normalization."""
        try:
            norm = parse_sensor_csv_frame(line, self._scale_profile)
        except FrameValidationError:
            log.debug("Malformed sensor CSV frame: %r", line)
            return
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

    def _drain_outbound_commands(self) -> None:
        """Write queued outbound commands from within the worker thread."""
        if self._serial is None or not self._serial.is_open:
            return

        while True:
            try:
                cmd = self._outbound_commands.get_nowait()
            except queue.Empty:
                return

            try:
                self._serial.write(cmd.encode("utf-8"))
            except Exception as e:
                message = f"Send failed — port may have disconnected: {type(e).__name__}: {e}"
                self.sig_error.emit(message)
                self.sig_connection_status.emit(False, message)
                self._running = False
                return

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_available_ports() -> list[str]:
        """Return a sorted list of available serial port device paths."""
        return sorted(p.device for p in serial.tools.list_ports.comports())
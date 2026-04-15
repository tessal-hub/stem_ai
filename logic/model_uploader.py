"""
logic/model_uploader.py — Binary TFLite Upload Worker for ESP32-S3.

Architecture:
    - Runs in a background QThread to prevent UI blocking.
    - Optimized for 115200 baud.
    - Protocol:
        1. Sends 'CMD:UPLOAD_MODEL:<filesize>\n'.
        2. Waits for 'ACK:READY\n' (within 5s).
        3. Sends data in 4096-byte chunks.
        4. Waits for 'ACK:CHUNK_RECEIVED\n' after each chunk (Flow Control, 2s timeout).
        5. Waits for 'ACK:UPLOAD_COMPLETE\n' at the end.
"""

import os
import serial
from PyQt6.QtCore import QThread, pyqtSignal
from config import DEFAULT_MODEL_PATH


class ModelUploader(QThread):
    """Handles chunked binary uploads to ESP32."""

    # ── Signals ─────────────────────────────────────────────────────────
    status_msg   = pyqtSignal(str)
    sig_progress = pyqtSignal(int)         # 0-100 progress percent
    sig_error    = pyqtSignal(str)         # error message
    sig_finished = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.port = port
        self.file_path = str(DEFAULT_MODEL_PATH)
        self._serial: serial.Serial | None = None
        self._is_running = False
        self._cancel_requested = False

    def upload_file(self, port: str, file_path: str) -> None:
        """Configure parameters and start the background thread."""
        self.port = port
        self.file_path = file_path
        self._cancel_requested = False
        if not self.isRunning():
            self.start()

    def stop(self) -> None:
        """Request upload cancellation. The run loop checks this flag cooperatively."""
        self._cancel_requested = True

    def run(self) -> None:
        """Core upload loop with CHUNK-ACK flow control."""
        try:
            if not self._validate_upload_inputs():
                return
            self._perform_upload()
        except Exception as e:
            message = f"Fatal Error: {e}"
            self.status_msg.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
        finally:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            self._is_running = False
            self._cancel_requested = False

    def _fail(self, message: str) -> None:
        """Emit status, error, and finished-failure signals in one call."""
        self.status_msg.emit(message)
        self.sig_error.emit(message)
        self.sig_finished.emit(False, message)

    def _validate_upload_inputs(self) -> bool:
        """Return True if file exists; emit error signals and return False otherwise."""
        if not os.path.exists(self.file_path):
            self._fail(f"Error: File not found: {self.file_path}")
            return False
        return True

    def _perform_upload(self) -> None:
        """Open serial port, handshake, stream chunks, and confirm completion."""
        self._serial = serial.Serial(self.port, 115200, timeout=5)
        self._is_running = True

        file_size = os.path.getsize(self.file_path)
        self.status_msg.emit(f"Flasher: Starting upload for {file_size} bytes...")

        self._serial.write(f"CMD:UPLOAD_MODEL:{file_size}\n".encode("utf-8"))
        self._serial.flush()

        ack = self._serial.readline().decode("utf-8", errors="ignore").strip()
        if ack != "ACK:READY":
            self._fail(f"Error: No ACK:READY received. Got: {ack}")
            return

        self.status_msg.emit("ACK:READY received. Sending chunks...")
        if not self._send_chunks(file_size):
            return

        self._serial.timeout = 5.0
        final_ack = self._serial.readline().decode("utf-8", errors="ignore").strip()
        if final_ack != "ACK:UPLOAD_COMPLETE":
            self._fail("Error: All chunks sent but final confirmation failed.")
            return

        self.status_msg.emit("Flasher: Upload Success! Rebooting ESP32.")
        self.sig_finished.emit(True, "Upload successful")

    def _send_chunks(self, file_size: int) -> bool:
        """Stream file in 4 KB chunks with per-chunk ACK flow control.

        Returns True on success, False on cancellation or ACK error.
        """
        chunk_size = 4096
        bytes_sent = 0

        with open(self.file_path, "rb") as f:
            while bytes_sent < file_size:
                if self._cancel_requested:
                    self._fail("Upload cancelled")
                    return False

                chunk = f.read(chunk_size)
                if not chunk:
                    break

                self._serial.write(chunk)
                self._serial.flush()

                self._serial.timeout = 2.0
                chunk_ack = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if chunk_ack != "ACK:CHUNK_RECEIVED":
                    self._fail(
                        f"Error: Packet sync failed. Expected ACK:CHUNK_RECEIVED, got: {chunk_ack}"
                    )
                    return False

                bytes_sent += len(chunk)
                self.sig_progress.emit(int((bytes_sent / file_size) * 100))

        return True

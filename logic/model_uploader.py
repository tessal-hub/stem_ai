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
import time
import serial
from PyQt6.QtCore import QThread, pyqtSignal
from config import DEFAULT_MODEL_PATH


class ModelUploader(QThread):
    """Handles chunked binary uploads to ESP32."""

    # ── Signals ─────────────────────────────────────────────────────────
    progress_updated = pyqtSignal(int)
    status_msg       = pyqtSignal(str)
    finished         = pyqtSignal(bool)
    sig_progress     = pyqtSignal(int)         # standardized progress channel
    sig_error        = pyqtSignal(str)         # standardized error channel
    sig_finished     = pyqtSignal(bool, str)   # standardized completion channel

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
            if not os.path.exists(self.file_path):
                message = f"Error: File not found: {self.file_path}"
                self.status_msg.emit(message)
                self.sig_error.emit(message)
                self.finished.emit(False)
                self.sig_finished.emit(False, message)
                return

            # Open port with 5s timeout for handshakes
            self._serial = serial.Serial(self.port, 115200, timeout=5)
            self._is_running = True
            
            file_size = os.path.getsize(self.file_path)
            self.status_msg.emit(f"Flasher: Starting upload for {file_size} bytes...")

            # 1. Initiate Protocol: CMD:UPLOAD_MODEL:<size>\n
            init_cmd = f"CMD:UPLOAD_MODEL:{file_size}\n"
            self._serial.write(init_cmd.encode('utf-8'))
            self._serial.flush()

            # 2. Wait for ACK:READY
            ack = self._serial.readline().decode('utf-8', errors='ignore').strip()
            if ack != "ACK:READY":
                message = f"Error: No ACK:READY received. Got: {ack}"
                self.status_msg.emit(message)
                self.sig_error.emit(message)
                self.finished.emit(False)
                self.sig_finished.emit(False, message)
                return

            self.status_msg.emit("ACK:READY received. Sending chunks...")

            # 3. Chunked Upload loop (4 KB chunks)
            chunk_size = 4096
            bytes_sent = 0
            
            with open(self.file_path, 'rb') as f:
                while bytes_sent < file_size:
                    if self._cancel_requested:
                        message = "Upload cancelled"
                        self.status_msg.emit(message)
                        self.sig_error.emit(message)
                        self.finished.emit(False)
                        self.sig_finished.emit(False, message)
                        return

                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Write binary chunk
                    self._serial.write(chunk)
                    self._serial.flush()
                    
                    # 4. Wait for ACK:CHUNK_RECEIVED (Flow Control, 2s timeout)
                    # We temporarily set a shorter timeout for chunk ACKs
                    self._serial.timeout = 2.0
                    chunk_ack = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if chunk_ack != "ACK:CHUNK_RECEIVED":
                        message = f"Error: Packet sync failed. Expected ACK:CHUNK_RECEIVED, got: {chunk_ack}"
                        self.status_msg.emit(message)
                        self.sig_error.emit(message)
                        self.finished.emit(False)
                        self.sig_finished.emit(False, message)
                        return

                    bytes_sent += len(chunk)
                    progress = int((bytes_sent / file_size) * 100)
                    self.progress_updated.emit(progress)
                    self.sig_progress.emit(progress)

            # 5. Wait for ACK:UPLOAD_COMPLETE
            self._serial.timeout = 5.0
            final_ack = self._serial.readline().decode('utf-8', errors='ignore').strip()
            if final_ack != "ACK:UPLOAD_COMPLETE":
                message = "Error: All chunks sent but final confirmation failed."
                self.status_msg.emit(message)
                self.sig_error.emit(message)
                self.finished.emit(False)
                self.sig_finished.emit(False, message)
                return

            success_message = "Flasher: Upload Success! Rebooting ESP32."
            self.status_msg.emit(success_message)
            self.finished.emit(True)
            self.sig_finished.emit(True, "Upload successful")

        except Exception as e:
            message = f"Fatal Error: {e}"
            self.status_msg.emit(message)
            self.sig_error.emit(message)
            self.finished.emit(False)
            self.sig_finished.emit(False, message)
        finally:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            self._is_running = False
            self._cancel_requested = False

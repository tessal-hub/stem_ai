"""
logic/model_uploader.py — Binary TFLite Upload Worker for ESP32-S3.

Architecture:
    - Runs in a background QThread to prevent UI blocking.
    - Optimized for 921600 baud.
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


class ModelUploader(QThread):
    """Handles chunked binary uploads to ESP32."""

    # ── Signals ─────────────────────────────────────────────────────────
    progress_updated = pyqtSignal(int)
    status_msg       = pyqtSignal(str)
    finished         = pyqtSignal(bool)

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.port = port
        self.file_path = "model.tflite"
        self._serial: serial.Serial | None = None
        self._is_running = False

    def upload_file(self, port: str, file_path: str) -> None:
        """Configure parameters and start the background thread."""
        self.port = port
        self.file_path = file_path
        if not self.isRunning():
            self.start()

    def run(self) -> None:
        """Core upload loop with CHUNK-ACK flow control."""
        try:
            if not os.path.exists(self.file_path):
                self.status_msg.emit(f"Error: File not found: {self.file_path}")
                self.finished.emit(False)
                return

            # Open port with 5s timeout for handshakes
            self._serial = serial.Serial(self.port, 921600, timeout=5)
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
                self.status_msg.emit(f"Error: No ACK:READY received. Got: {ack}")
                self.finished.emit(False)
                return

            self.status_msg.emit("ACK:READY received. Sending chunks...")

            # 3. Chunked Upload loop (4 KB chunks)
            chunk_size = 4096
            bytes_sent = 0
            
            with open(self.file_path, 'rb') as f:
                while bytes_sent < file_size:
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
                        self.status_msg.emit(f"Error: Packet sync failed. Expected ACK:CHUNK_RECEIVED, got: {chunk_ack}")
                        self.finished.emit(False)
                        return

                    bytes_sent += len(chunk)
                    self.progress_updated.emit(int((bytes_sent / file_size) * 100))

            # 5. Wait for ACK:UPLOAD_COMPLETE
            self._serial.timeout = 5.0
            final_ack = self._serial.readline().decode('utf-8', errors='ignore').strip()
            if final_ack != "ACK:UPLOAD_COMPLETE":
                self.status_msg.emit("Error: All chunks sent but final confirmation failed.")
                self.finished.emit(False)
                return

            self.status_msg.emit("Flasher: Upload Success! Rebooting ESP32.")
            self.finished.emit(True)

        except Exception as e:
            self.status_msg.emit(f"Fatal Error: {e}")
            self.finished.emit(False)
        finally:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            self._is_running = False

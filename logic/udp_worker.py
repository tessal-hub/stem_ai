"""
logic/udp_worker.py — Background network listener for ESP32 telemetry.

Architecture:
-------------
* Runs completely independent of the main GUI thread.
* Uses standard Python `socket` for robust blocking `recvfrom`.
* Emits strictly-typed PyQt Signals to transfer data across thread boundaries safely.
"""

import json
import socket
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal


class UdpWorker(QThread):
    """Listens for incoming UDP packets and emits parsed data safely to the GUI."""

    # Outbound signals (Cross-thread safe)
    sig_data_received = pyqtSignal(dict)  # Emits parsed JSON payload
    sig_status_change = pyqtSignal(bool)  # Emits True when receiving, False if timeout/disconnected
    sig_error         = pyqtSignal(str)

    def __init__(self, host: str = "0.0.0.0", port: int = 5555, parent=None) -> None:
        super().__init__(parent)
        self.host = host
        self.port = port
        self._is_running = False
        self._sock: socket.socket | None = None

    def run(self) -> None:
        """Main thread loop. Blocks on recvfrom() but does not block the UI."""
        self._is_running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set timeout to periodically check if thread should stop
        self._sock.settimeout(1.0)
        
        try:
            self._sock.bind((self.host, self.port))
        except Exception as e:
            self.sig_error.emit(f"Failed to bind UDP socket on {self.host}:{self.port} -> {e}")
            self._is_running = False
            return

        while self._is_running:
            try:
                data, addr = self._sock.recvfrom(4096)  # Buffer size 4KB
                
                # Signal connection status if we successfully got data
                self.sig_status_change.emit(True)

                # Assuming ESP32 sends JSON data. E.g., {"accel_x": 1.2, "gyro_z": -45.1}
                payload_str = data.decode("utf-8").strip()
                payload_dict = json.loads(payload_str)
                
                self.sig_data_received.emit(payload_dict)

            except socket.timeout:
                # Normal behavior every 1 second if no data arrives
                pass
            except json.JSONDecodeError:
                self.sig_error.emit("Received malformed JSON from ESP32.")
            except Exception as e:
                self.sig_error.emit(f"UDP Error: {e}")

        # Cleanup when thread stops
        if self._sock:
            self._sock.close()

    def stop(self) -> None:
        """Gracefully asks the thread to terminate."""
        self._is_running = False
        self.wait()  # Block until the thread actually finishes
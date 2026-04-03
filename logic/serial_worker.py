"""
logic/serial_worker.py — Background thread for high-speed ESP32 serial communication.

Architecture:
    - Runs in a separate QThread to avoid UI freezing.
    - Handles 921600 baud rate.
    - Normalizes sensor data (Accel/16384, Gyro/131).
    - Detects:
        1. PREDICT:<Action>:<Conf> -> for real-time inference.
        2. aX,aY,aZ,gX,gY,gZ -> for training data.
"""

import time
import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal


class SerialWorker(QThread):
    """Background UART listener and processor."""
    
    # ── Signals ─────────────────────────────────────────────────────────
    data_received       = pyqtSignal(dict)   # {'ax': f, 'ay': f, ...}
    prediction_received = pyqtSignal(str, float)
    connection_status   = pyqtSignal(bool, str) # (is_connected, message)

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.port = port
        self.baudrate = 921600
        self._serial: serial.Serial | None = None
        self._is_running = False

    def send_command(self, cmd: str) -> bool:
        """Encode and send a string to the serial port."""
        if self._serial and self._serial.is_open:
            try:
                # Add newline if missing
                if not cmd.endswith('\n'):
                    cmd += '\n'
                self._serial.write(cmd.encode('utf-8'))
                return True
            except Exception as e:
                self.connection_status.emit(True, f"Send error: {e}")
        return False

    def stop(self) -> None:
        """Stop the event loop and close the serial connection."""
        self._is_running = False
        self.wait()

    def run(self) -> None:
        """Core listener loop. Opens 921600 baud serial connection."""
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self._is_running = True
            self.connection_status.emit(True, f"Connected to {self.port} at {self.baudrate}")

            while self._is_running:
                if self._serial.in_waiting:
                    try:
                        # Handle noise or garbled data with errors='ignore'
                        line = self._serial.readline().decode('utf-8', errors='ignore').strip()
                        if not line:
                            continue
                        
                        # 1. Inference result from ESP32
                        # Format: PREDICT:<Label>:<Conf>\n
                        if line.startswith("PREDICT:"):
                            parts = line.split(":")
                            if len(parts) >= 3:
                                label = parts[1]
                                try:
                                    conf = float(parts[2])
                                    self.prediction_received.emit(label, conf)
                                except ValueError: pass
                            continue
                        
                        # 2. Raw sensor CSV data (aX,aY,aZ,gX,gY,gZ\n)
                        # Filter out ACKs or non-data lines
                        if "," in line and not line.startswith("ACK:"):
                            parts = line.split(",")
                            if len(parts) == 6:
                                try:
                                    raw = [float(p) for p in parts]
                                    # Normalize MPU6050: Accel / 16384.0 (±2g), Gyro / 131.0 (±250dps)
                                    norm_dict = {
                                        'ax': raw[0] / 16384.0, 'ay': raw[1] / 16384.0, 'az': raw[2] / 16384.0,
                                        'gx': raw[3] / 131.0,   'gy': raw[4] / 131.0,   'gz': raw[5] / 131.0
                                    }
                                    self.data_received.emit(norm_dict)
                                except ValueError:
                                    pass
                    except Exception:
                        pass # Ignore garbled bytes during binary uploads
                else:
                    # Brief yield to reduce CPU load
                    self.msleep(2)

        except Exception as e:
            self.connection_status.emit(False, f"Serial error: {e}")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Ensure serial port is closed safely."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._is_running = False
        self.connection_status.emit(False, "Disconnected")

    @staticmethod
    def get_available_ports() -> list[str]:
        return [p.device for p in serial.tools.list_ports.comports()]
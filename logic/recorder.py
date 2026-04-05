"""
logic/recorder.py — Data recording manager for dataset collection.

Responsibilities:
    - Accept sensor data events from SerialWorker.
    - Save samples to CSV files under dataset/<label>/*.csv.
    - Expose recording state and written-row counter for UI.
    - Robust error handling for file I/O operations.

CSV Format: ax, ay, az, gx, gy, gz
Directory: dataset/<label>/sample_YYYYMMDD_HHMMSS_MMMMMM.csv
"""

import csv
import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class DataRecorder(QObject):
    """Manages real-time CSV recording of sensor data."""

    # ── Signals ──────────────────────────────────────────────────────────
    sig_record_count = pyqtSignal(int)              # Emitted per row written
    sig_status_text = pyqtSignal(str)               # Status updates
    sig_recording_state = pyqtSignal(bool)          # Recording started/stopped

    def __init__(self, dataset_dir: str = "dataset", parent=None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        
        # Ensure dataset directory exists
        try:
            Path(self.dataset_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.sig_status_text.emit(f"[WARN] Could not create dataset dir: {e}")

        # Recording state
        self._file = None
        self._writer = None
        self._label_name = ""
        self._row_count = 0
        self._is_recording = False

    @staticmethod
    def _sanitize_label(label: str) -> str:
        """Convert label to filesystem-safe name."""
        if not isinstance(label, str):
            label = str(label)
        
        name = label.strip() or "unknown"
        # Replace non-alphanumeric chars with underscore
        name = re.sub(r"[^0-9a-zA-Z_\-]", "_", name)
        # Remove leading/trailing underscores
        name = name.strip("_")
        # Ensure name is not empty
        return name or "unknown"

    def start_recording(self, label_name: str) -> bool:
        """
        Start recording a new CSV file for the given label.

        Args:
            label_name: Spell/action name (will be sanitized)

        Returns:
            bool: True if recording started successfully, False otherwise
        """
        # Prevent double recording
        if self._is_recording:
            self.sig_status_text.emit("[WARN] Already recording")
            return False

        try:
            # Sanitize the label name for filesystem safety
            label = self._sanitize_label(label_name)
            
            # Create label folder if needed
            label_folder = os.path.join(self.dataset_dir, label)
            Path(label_folder).mkdir(parents=True, exist_ok=True)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(label_folder, f"sample_{timestamp}.csv")

            # Open file in write mode
            self._file = open(file_path, mode="w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)

            # Write header row
            self._writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
            self._file.flush()

            # Update state
            self._label_name = label
            self._row_count = 0
            self._is_recording = True

            # Emit signals
            self.sig_record_count.emit(0)
            filename = os.path.basename(file_path)
            self.sig_status_text.emit(f"[RECORD] Started: {label}/{filename}")
            self.sig_recording_state.emit(True)

            return True

        except PermissionError as e:
            self.sig_status_text.emit(f"[ERROR] Permission denied: {e}")
            self._is_recording = False
            return False
        except OSError as e:
            self.sig_status_text.emit(f"[ERROR] OS error: {e}")
            self._is_recording = False
            return False
        except Exception as e:
            self.sig_status_text.emit(f"[ERROR] Failed to start recording: {type(e).__name__}: {e}")
            self._is_recording = False
            return False

    def stop_recording(self) -> None:
        """Stop the current recording and close the file."""
        if not self._is_recording:
            self.sig_status_text.emit("[WARN] Not currently recording")
            return

        try:
            if self._file is not None:
                self._file.flush()
                self._file.close()

            self._file = None
            self._writer = None
            self._is_recording = False

            # Emit completion signal
            self.sig_status_text.emit(f"[RECORD] Stopped. Saved {self._row_count} samples to {self._label_name}")
            self.sig_recording_state.emit(False)

        except Exception as e:
            self.sig_status_text.emit(f"[ERROR] Failed to close file: {type(e).__name__}: {e}")
            self._is_recording = False

    def add_row(self, data_list: list[float]) -> None:
        """
        Write a single row of 6-axis sensor data.

        Args:
            data_list: [ax, ay, az, gx, gy, gz] normalized values
        """
        # Guard: Only write if actively recording
        if not self._is_recording or self._writer is None:
            return

        # Guard: Validate input
        if not isinstance(data_list, (list, tuple)):
            return
        if len(data_list) != 6:
            return

        try:
            # Format all values to 6 decimal places
            formatted_row = [
                f"{float(data_list[0]):.6f}",
                f"{float(data_list[1]):.6f}",
                f"{float(data_list[2]):.6f}",
                f"{float(data_list[3]):.6f}",
                f"{float(data_list[4]):.6f}",
                f"{float(data_list[5]):.6f}",
            ]

            # Write row and flush immediately
            self._writer.writerow(formatted_row)
            if self._file is not None:
                self._file.flush()

            self._row_count += 1
            self.sig_record_count.emit(self._row_count)

        except ValueError:
            # Skip rows that can't be converted to float
            pass
        except OSError as e:
            self.sig_status_text.emit(f"[ERROR] Disk write failed: {e}")
            self._is_recording = False
        except Exception as e:
            self.sig_status_text.emit(f"[ERROR] Failed to write row: {type(e).__name__}: {e}")


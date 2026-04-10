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
import queue
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from config import DATASET_DIR, ensure_data_dir
from constants import canonical_system_spell, is_system_spell, normalize_spell_name


class DataRecorder(QThread):
    """Manages real-time CSV recording of sensor data in a worker thread."""

    # ── Signals ──────────────────────────────────────────────────────────
    sig_record_count = pyqtSignal(int)              # Emitted per row written
    sig_status_text = pyqtSignal(str)               # Status updates
    sig_recording_state = pyqtSignal(bool)          # Recording started/stopped
    sig_progress = pyqtSignal(int)                  # standardized progress channel
    sig_error = pyqtSignal(str)                     # standardized error channel
    sig_finished = pyqtSignal(bool, str)            # standardized completion channel

    def __init__(self, dataset_dir: str | None = None, parent=None) -> None:
        super().__init__(parent)
        ensure_data_dir()
        resolved_dataset_dir = Path(dataset_dir) if dataset_dir else DATASET_DIR
        self.dataset_dir = str(resolved_dataset_dir)
        
        # Ensure dataset directory exists
        try:
            Path(self.dataset_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.sig_status_text.emit(f"[WARN] Could not create dataset dir: {e}")

        # Recording state (accessed by worker loop)
        self._file = None
        self._writer = None
        self._label_name = ""
        self._row_count = 0
        self._is_recording = False
        self._start_pending = False
        self._stop_requested = False
        self._pending_label = ""

        # Command/data queues: main thread enqueues, worker thread performs I/O.
        self._command_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._row_queue: queue.Queue[list[float]] = queue.Queue(maxsize=2000)

    def stop(self) -> None:
        """Stop the recorder worker thread cooperatively."""
        self._stop_requested = True
        self._command_queue.put(("stop", None))
        if self.isRunning():
            self.wait(3000)

    @staticmethod
    def _sanitize_label(label: str) -> str:
        """Convert label to filesystem-safe name."""
        if not isinstance(label, str):
            label = str(label)

        normalized = normalize_spell_name(label)
        if is_system_spell(normalized):
            return canonical_system_spell(normalized)

        name = label.strip() or "unknown"
        # Keep spaces for readability while replacing unsafe characters.
        name = re.sub(r"[^0-9a-zA-Z _\-]", "_", name)
        name = " ".join(name.split())
        # Remove leading/trailing separators
        name = name.strip("_-")
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
        if self._is_recording or self._start_pending:
            self.sig_status_text.emit("[WARN] Already recording")
            return False

        try:
            # Sanitize the label name for filesystem safety
            label = self._sanitize_label(label_name)

            if not self.isRunning():
                self._stop_requested = False
                self.start()

            self._start_pending = True
            self._pending_label = label
            self._command_queue.put(("start", label))
            return True

        except Exception as e:
            message = f"[ERROR] Failed to queue recording start: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
            return False

    def stop_recording(self) -> None:
        """Stop the current recording and close the file."""
        if not self._is_recording:
            self.sig_status_text.emit("[WARN] Not currently recording")
            return
        self._command_queue.put(("stop", None))

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
            self._row_queue.put_nowait([float(v) for v in data_list])
        except queue.Full:
            message = "[WARN] Recorder queue full; dropping sample"
            self.sig_status_text.emit(message)
        except Exception as e:
            message = f"[ERROR] Failed to enqueue row: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)

    def run(self) -> None:
        """Worker loop: execute file I/O and lifecycle commands off the main thread."""
        try:
            while not self._stop_requested:
                self._process_commands()
                self._drain_rows_once()
                self.msleep(5)
        except Exception as e:
            message = f"[ERROR] Recorder worker crashed: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
        finally:
            self._close_recording(success=True)

    def _process_commands(self) -> None:
        while True:
            try:
                cmd, payload = self._command_queue.get_nowait()
            except queue.Empty:
                return

            if cmd == "start" and payload is not None:
                self._open_recording(payload)
            elif cmd == "stop":
                self._close_recording(success=True)

    def _drain_rows_once(self) -> None:
        if not self._is_recording or self._writer is None:
            return

        try:
            row = self._row_queue.get_nowait()
        except queue.Empty:
            return

        try:
            formatted_row = [f"{float(v):.6f}" for v in row]
            self._writer.writerow(formatted_row)
            if self._file is not None:
                self._file.flush()
            self._row_count += 1
            self.sig_record_count.emit(self._row_count)
            self.sig_progress.emit(self._row_count)
        except OSError as e:
            message = f"[ERROR] Disk write failed: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self._close_recording(success=False, error_message=message)
        except Exception as e:
            message = f"[ERROR] Failed to write row: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self._close_recording(success=False, error_message=message)

    def _open_recording(self, label: str) -> None:
        self._start_pending = False
        if self._is_recording:
            self.sig_status_text.emit("[WARN] Already recording")
            return

        try:
            label_folder = os.path.join(self.dataset_dir, label)
            Path(label_folder).mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(label_folder, f"sample_{timestamp}.csv")

            self._file = open(file_path, mode="w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
            self._file.flush()

            self._label_name = label
            self._row_count = 0
            self._is_recording = True

            self.sig_record_count.emit(0)
            filename = os.path.basename(file_path)
            self.sig_status_text.emit(f"[RECORD] Started: {label}/{filename}")
            self.sig_recording_state.emit(True)
        except PermissionError as e:
            message = f"[ERROR] Permission denied: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
            self._is_recording = False
        except OSError as e:
            message = f"[ERROR] OS error: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
            self._is_recording = False
        except Exception as e:
            message = f"[ERROR] Failed to start recording: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
            self._is_recording = False

    def _close_recording(self, success: bool, error_message: str = "") -> None:
        if not self._is_recording and self._file is None and self._writer is None:
            return

        try:
            if self._file is not None:
                self._file.flush()
                self._file.close()
        except Exception as e:
            message = f"[ERROR] Failed to close file: {type(e).__name__}: {e}"
            self.sig_status_text.emit(message)
            self.sig_error.emit(message)
            success = False
            error_message = message
        finally:
            self._file = None
            self._writer = None

            if self._is_recording:
                self._is_recording = False
                self.sig_recording_state.emit(False)

                if success:
                    message = f"[RECORD] Stopped. Saved {self._row_count} samples to {self._label_name}"
                    self.sig_status_text.emit(message)
                    self.sig_finished.emit(True, message)
                else:
                    fail_message = error_message or "Recorder stopped with error"
                    self.sig_finished.emit(False, fail_message)


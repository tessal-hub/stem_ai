"""
logic/data_store.py — Centralized state management for the application.

Architecture:
    - Single source of truth for sensor data and hardware state.
    - Uses collections.deque for high-speed, thread-safe buffering.
"""

import os
import csv
import glob
import collections
from threading import Lock
from datetime import datetime
from typing import Any, Mapping

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from .frame_protocol import FrameValidationError, validate_six_axis_values


# DataStore schema versioning contract:
# - Bump SCHEMA_VERSION when changing persisted/session-facing data schema.
# - Add migration notes for backward compatibility at bump time.
# - Keep version 1 as the baseline for current live buffer/state structure.
SCHEMA_VERSION = 1


class SettingsStore:
    """Typed persistence wrapper around QSettings for app preferences."""

    _ORG_NAME = "STEMSpellBook"
    _APP_NAME = "Reboot"

    _DEFAULTS: dict[str, Any] = {
        "sample_rate": "50 Hz",
        "accel_scale": "±2g",
        "gyro_scale": "±250 dps",
        "window_size": 10,
        "window_overlap": 0,
        "ml_pipeline": "Random Forest (Edge)",
        "project_name": "",
        "auto_save": False,
        "selected_port": "",
        "baud_rate": "115200",
        "model_path": "model.tflite",
        "firmware_mode": "data",
    }

    def __init__(self) -> None:
        self._settings = QSettings(self._ORG_NAME, self._APP_NAME)

    @staticmethod
    def _to_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_str(self, key: str, default: str) -> str:
        value = self._settings.value(key, default)
        if value is None:
            return default
        return str(value)

    def get_int(self, key: str, default: int) -> int:
        value = self._settings.value(key, default)
        return self._to_int(value, default)

    def get_bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        return self._to_bool(value, default)

    def set_str(self, key: str, value: str) -> None:
        self._settings.setValue(key, str(value))

    def set_int(self, key: str, value: int) -> None:
        self._settings.setValue(key, int(value))

    def set_bool(self, key: str, value: bool) -> None:
        self._settings.setValue(key, bool(value))

    def load(self) -> dict[str, Any]:
        """Load all persisted settings with typed values and defaults."""
        return {
            "sample_rate": self.get_str("sample_rate", self._DEFAULTS["sample_rate"]),
            "accel_scale": self.get_str("accel_scale", self._DEFAULTS["accel_scale"]),
            "gyro_scale": self.get_str("gyro_scale", self._DEFAULTS["gyro_scale"]),
            "window_size": self.get_int("window_size", self._DEFAULTS["window_size"]),
            "window_overlap": self.get_int("window_overlap", self._DEFAULTS["window_overlap"]),
            "ml_pipeline": self.get_str("ml_pipeline", self._DEFAULTS["ml_pipeline"]),
            "project_name": self.get_str("project_name", self._DEFAULTS["project_name"]),
            "auto_save": self.get_bool("auto_save", self._DEFAULTS["auto_save"]),
            "selected_port": self.get_str("selected_port", self._DEFAULTS["selected_port"]),
            "baud_rate": self.get_str("baud_rate", self._DEFAULTS["baud_rate"]),
            "model_path": self.get_str("model_path", self._DEFAULTS["model_path"]),
            "firmware_mode": self.get_str("firmware_mode", self._DEFAULTS["firmware_mode"]),
        }

    def _normalize(self, config: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(self._DEFAULTS)
        merged.update(dict(config))
        return {
            "sample_rate": str(merged["sample_rate"]),
            "accel_scale": str(merged["accel_scale"]),
            "gyro_scale": str(merged["gyro_scale"]),
            "window_size": self._to_int(merged["window_size"], self._DEFAULTS["window_size"]),
            "window_overlap": self._to_int(merged["window_overlap"], self._DEFAULTS["window_overlap"]),
            "ml_pipeline": str(merged["ml_pipeline"]),
            "project_name": str(merged["project_name"]),
            "auto_save": self._to_bool(merged["auto_save"], self._DEFAULTS["auto_save"]),
            "selected_port": str(merged["selected_port"]),
            "baud_rate": str(merged["baud_rate"]),
            "model_path": str(merged["model_path"]),
            "firmware_mode": str(merged["firmware_mode"]),
        }

    def save(self, config: Mapping[str, Any]) -> dict[str, Any]:
        """Persist all known settings and return the normalized snapshot."""
        normalized = self._normalize(config)

        self.set_str("sample_rate", normalized["sample_rate"])
        self.set_str("accel_scale", normalized["accel_scale"])
        self.set_str("gyro_scale", normalized["gyro_scale"])
        self.set_int("window_size", normalized["window_size"])
        self.set_int("window_overlap", normalized["window_overlap"])
        self.set_str("ml_pipeline", normalized["ml_pipeline"])
        self.set_str("project_name", normalized["project_name"])
        self.set_bool("auto_save", normalized["auto_save"])
        self.set_str("selected_port", normalized["selected_port"])
        self.set_str("baud_rate", normalized["baud_rate"])
        self.set_str("model_path", normalized["model_path"])
        self.set_str("firmware_mode", normalized["firmware_mode"])
        self._settings.sync()
        return normalized


class DataStore(QObject):
    """Centralized reactive state container."""

    # ── Signals ─────────────────────────────────────────────────────────
    sig_db_updated            = pyqtSignal(dict)   # spell_counts changed
    sig_sensor_data_updated   = pyqtSignal(dict)   # Granular dict of deques for UI
    sig_stats_updated         = pyqtSignal(dict)
    sig_prediction_updated    = pyqtSignal(str, float)
    sig_live_buffer_updated   = pyqtSignal(list)   # Rolling snapshot for live plotting
    sig_recording_state_updated = pyqtSignal(bool)
    sig_mode_updated          = pyqtSignal(str)
    sig_connection_state_updated = pyqtSignal(bool, str)

    def __init__(self, dataset_dir: str = "dataset", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        os.makedirs(self.dataset_dir, exist_ok=True)
        self._state_lock = Lock()
        self._buffer_lock = Lock()

        # 1. State Variables (Requested Fix)
        self.system_stats: dict[str, str] = {
            "CPU": "0%",
            "RAM": "0%",
            "Port": "None",
            "Baudrate": "115200",
        }

        # 2. ESP32 Hardware Stats (Required by PageWand)
        self.esp32_stats: dict[str, str] = {
            "Battery": "--",
            "Chip": "ESP32-S3",
            "Flash": "16MB",
            "RAM Free": "8MB PSRAM",
        }

        # 3. Application Settings (QSettings-backed persistence)
        self.settings_store = SettingsStore()
        self.settings: dict[str, Any] = self.settings_store.load()
        
        # 4. Connection & Mode Flags
        self.is_connected: bool = False
        self.current_mode: str = "IDLE"
        self.last_prediction: str = "None"
        self.prediction_confidence: float = 0.0
        self.is_recording: bool = False

        # 5. Spell Database — dynamically loaded from filesystem
        self.spell_counts: dict[str, int] = {}

        # 6. Sensor Buffers (Dictionary of Deques)
        self.sensor_buffers: dict[str, collections.deque] = {
            key: collections.deque(maxlen=100) 
            for key in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
        }
        self.live_buffer: collections.deque[list[float]] = collections.deque(maxlen=500)

        # Initial filesystem scan
        self.refresh_database()

    # ── State Mutation ──────────────────────────────────────────────────

    def update_sensor_data(self, data_dict: dict[str, float]) -> None:
        """Update sensor deques with a new sample and notify UI."""
        with self._buffer_lock:
            for key, value in data_dict.items():
                if key in self.sensor_buffers:
                    self.sensor_buffers[key].append(value)
        self.sig_sensor_data_updated.emit(self.sensor_buffers)

    def add_live_sample(self, sample: list[float]) -> list[list[float]]:
        """Append one 6-axis sample to rolling live buffer and emit snapshot."""
        try:
            normalized_sample = validate_six_axis_values(sample)
        except FrameValidationError:
            return []
        with self._buffer_lock:
            self.live_buffer.append(normalized_sample)
            snapshot = [list(row) for row in self.live_buffer]
        self.sig_live_buffer_updated.emit(snapshot)
        return snapshot

    def get_live_buffer_snapshot(self) -> list[list[float]]:
        """Return a thread-safe shallow copy of the rolling live buffer."""
        with self._buffer_lock:
            return [list(row) for row in self.live_buffer]

    def clear_live_buffer(self) -> None:
        """Clear the rolling live buffer."""
        with self._buffer_lock:
            self.live_buffer.clear()

    def update_prediction(self, action: str, confidence: float) -> None:
        """Update the latest AI inference result."""
        with self._state_lock:
            self.last_prediction = action
            self.prediction_confidence = confidence
        self.sig_prediction_updated.emit(action, confidence)

    def get_prediction_state(self) -> tuple[str, float]:
        """Return thread-safe prediction state tuple."""
        with self._state_lock:
            return self.last_prediction, self.prediction_confidence

    def set_connection_status(self, connected: bool, port: str = "None") -> None:
        """Update hardware connection state and stats."""
        with self._state_lock:
            self.is_connected = connected
            self.system_stats["Port"] = port
        self.sig_stats_updated.emit(self.system_stats)
        self.sig_connection_state_updated.emit(connected, port)

    def get_connection_state(self) -> tuple[bool, str]:
        """Return thread-safe connection state tuple."""
        with self._state_lock:
            return self.is_connected, self.system_stats.get("Port", "None")

    def set_recording_state(self, recording: bool) -> None:
        """Update thread-safe recording state."""
        with self._state_lock:
            self.is_recording = recording
        self.sig_recording_state_updated.emit(recording)

    def get_recording_state(self) -> bool:
        """Return thread-safe recording state."""
        with self._state_lock:
            return self.is_recording

    def set_current_mode(self, mode: str) -> None:
        """Set current runtime mode and notify subscribers."""
        normalized = str(mode).strip().upper() or "IDLE"
        with self._state_lock:
            self.current_mode = normalized
        self.sig_mode_updated.emit(normalized)

    def get_current_mode(self) -> str:
        """Return thread-safe current runtime mode."""
        with self._state_lock:
            return self.current_mode

    def update_esp_stats(self, updates: dict[str, str]) -> None:
        """Merge ESP telemetry values and notify UI subscribers."""
        if not updates:
            return
        self.esp32_stats.update(updates)
        self.sig_stats_updated.emit(self.esp32_stats)

    # ── Settings Persistence ───────────────────────────────────────────

    def get_settings_snapshot(self) -> dict[str, Any]:
        """Return a thread-safe copy of current runtime settings."""
        with self._state_lock:
            return dict(self.settings)

    def reload_settings(self) -> dict[str, Any]:
        """Reload settings from persistent storage into runtime memory."""
        with self._state_lock:
            self.settings = self.settings_store.load()
            return dict(self.settings)

    def save_settings(self, updates: Mapping[str, Any]) -> dict[str, Any]:
        """Persist updates via SettingsStore and refresh in-memory settings."""
        with self._state_lock:
            merged = dict(self.settings)
            merged.update(dict(updates))
            self.settings = self.settings_store.save(merged)
            return dict(self.settings)

    # ── Database ────────────────────────────────────────────────────────

    def refresh_database(self) -> None:
        """Scan dataset/ folder structure to rebuild spell_counts."""
        self.spell_counts.clear()
        if os.path.exists(self.dataset_dir):
            for item in os.listdir(self.dataset_dir):
                spell_path = os.path.join(self.dataset_dir, item)
                if os.path.isdir(spell_path):
                    csv_files = glob.glob(os.path.join(spell_path, "*.csv"))
                    self.spell_counts[item] = len(csv_files)
        self.sig_db_updated.emit(self.spell_counts)

    def get_spell_list(self) -> list[str]:
        return list(self.spell_counts.keys())

    def get_samples_for_spell(self, spell_name: str) -> list[str]:
        spell_path = os.path.join(self.dataset_dir, spell_name)
        if not os.path.isdir(spell_path):
            return []
        return sorted(f for f in os.listdir(spell_path) if f.endswith(".csv"))

    def save_cropped_data(self, spell_name: str, data: list[list[float]]) -> bool:
        """Save a cropped 6-axis sample block as a single CSV file."""
        if not data or not spell_name.strip():
            return False

        folder = os.path.join(self.dataset_dir, spell_name.strip().upper())
        os.makedirs(folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(folder, f"sample_{timestamp}.csv")

        try:
            with open(file_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["aX", "aY", "aZ", "gX", "gY", "gZ"])
                writer.writerows(data)
            self.refresh_database()
            return True
        except Exception as e:
            print(f"[DataStore] Save error: {e}")
            return False

    def delete_spell(self, spell_name: str) -> bool:
        """Delete a spell and all its associated CSV files."""
        if not spell_name.strip():
            return False

        spell_path = os.path.join(self.dataset_dir, spell_name.strip().upper())
        if not os.path.exists(spell_path):
            return False

        try:
            # Remove all files in the spell directory
            for filename in os.listdir(spell_path):
                file_path = os.path.join(spell_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            # Remove the directory itself
            os.rmdir(spell_path)
            
            # Refresh the database
            self.refresh_database()
            return True
        except Exception as e:
            print(f"[DataStore] Delete spell error: {e}")
            return False
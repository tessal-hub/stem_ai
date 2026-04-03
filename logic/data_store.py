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
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal


class DataStore(QObject):
    """Centralized reactive state container."""

    # ── Signals ─────────────────────────────────────────────────────────
    sig_db_updated            = pyqtSignal(dict)   # spell_counts changed
    sig_sensor_data_updated   = pyqtSignal(dict)   # Granular dict of deques for UI
    sig_stats_updated         = pyqtSignal(dict)
    sig_prediction_updated    = pyqtSignal(str, float)

    def __init__(self, dataset_dir: str = "dataset", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        os.makedirs(self.dataset_dir, exist_ok=True)

        # 1. State Variables (Requested Fix)
        self.system_stats: dict[str, str] = {
            "CPU": "0%",
            "RAM": "0%",
            "Port": "None",
            "Baudrate": "921600",
        }

        # 2. ESP32 Hardware Stats (Required by PageWand)
        self.esp32_stats: dict[str, str] = {
            "Battery": "--",
            "Chip": "ESP32-S3",
            "Flash": "16MB",
            "RAM Free": "8MB PSRAM",
        }

        # 3. Application Settings (Standard context)
        self.settings: dict[str, str] = {
            "sample_rate": "50 Hz",
            "accel_scale": "±2g",
            "gyro_scale": "±250 dps",
        }
        
        # 4. Connection & Mode Flags
        self.is_connected: bool = False
        self.current_mode: str = "IDLE"
        self.last_prediction: str = "None"
        self.prediction_confidence: float = 0.0

        # 5. Spell Database — dynamically loaded from filesystem
        self.spell_counts: dict[str, int] = {}

        # 6. Sensor Buffers (Dictionary of Deques)
        self.sensor_buffers: dict[str, collections.deque] = {
            key: collections.deque(maxlen=100) 
            for key in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
        }

        # Initial filesystem scan
        self.refresh_database()

    # ── State Mutation ──────────────────────────────────────────────────

    def update_sensor_data(self, data_dict: dict[str, float]) -> None:
        """Update sensor deques with a new sample and notify UI."""
        for key, value in data_dict.items():
            if key in self.sensor_buffers:
                self.sensor_buffers[key].append(value)
        self.sig_sensor_data_updated.emit(self.sensor_buffers)

    def update_prediction(self, action: str, confidence: float) -> None:
        """Update the latest AI inference result."""
        self.last_prediction = action
        self.prediction_confidence = confidence
        self.sig_prediction_updated.emit(action, confidence)

    def set_connection_status(self, connected: bool, port: str = "None") -> None:
        """Update hardware connection state and stats."""
        self.is_connected = connected
        self.system_stats["Port"] = port
        self.sig_stats_updated.emit(self.system_stats)

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
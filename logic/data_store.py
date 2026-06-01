"""
logic/data_store.py — Quản lý trạng thái tập trung cho toàn bộ ứng dụng.

Trách nhiệm:
    - Lưu trữ duy nhất các dữ liệu cảm biến và trạng thái phần cứng.
    - Sử dụng collections.deque để lưu đệm dữ liệu tốc độ cao, an toàn đa luồng.
    - Quản lý cấu hình (Settings) và cơ sở dữ liệu mẫu cử chỉ (Spell Database).
"""

from __future__ import annotations

import collections
import csv
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from config import DATASET_DIR, DEFAULT_MODEL_PATH, ensure_data_dir
from constants import SYSTEM_SPELL_NAMES

from .dataset_layout import (discover_class_directories, spell_write_dir,
                             storage_dirs_for_spell)
from .frame_protocol import FrameValidationError, validate_six_axis_values

log = logging.getLogger(__name__)
SCHEMA_VERSION = 1


class SettingsStore:
    """Lớp bao bọc QSettings để lưu trữ cấu hình người dùng có kiểu dữ liệu."""

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
        "model_path": str(DEFAULT_MODEL_PATH),
        "firmware_mode": "data",
        "idf_main_dir": "",
        "demo_spell_cleanup_done": False,
        "theme": "light",
        "ui_language": "en",
    }

    def __init__(self) -> None:
        self._settings = QSettings(self._ORG_NAME, self._APP_NAME)

    def load(self) -> dict[str, Any]:
        """Tải toàn bộ cấu hình đã lưu với giá trị mặc định."""
        model_path = self.get_str("model_path", self._DEFAULTS["model_path"]).strip()
        if not model_path or model_path == "model.tflite":
            model_path = self._DEFAULTS["model_path"]

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
            "model_path": model_path,
            "firmware_mode": self.get_str("firmware_mode", self._DEFAULTS["firmware_mode"]),
            "idf_main_dir": self.get_str("idf_main_dir", ""),
            "demo_spell_cleanup_done": self.get_bool("demo_spell_cleanup_done", False),
            "theme": self.get_str("theme", "light"),
            "ui_language": self.get_str("ui_language", "en"),
        }

    def save(self, config: Mapping[str, Any]) -> dict[str, Any]:
        """Lưu cấu hình vào bộ nhớ vĩnh viễn."""
        for key, val in config.items():
            self._settings.setValue(key, val)
        self._settings.sync()
        return self.load()

    def get_str(self, key: str, default: str) -> str:
        return str(self._settings.value(key, default))

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(self._settings.value(key, default))
        except:
            return default

    def get_bool(self, key: str, default: bool) -> bool:
        val = self._settings.value(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in {"true", "1", "yes"}


class DataStore(QObject):
    """Kho lưu trữ trạng thái phản ứng (reactive state container)."""

    # ── Signals ──────────────────────────────────
    sig_db_updated = pyqtSignal(dict)
    sig_primitive_stats_updated = pyqtSignal(dict)
    sig_sensor_data_updated = pyqtSignal(dict)
    sig_stats_updated = pyqtSignal(dict)
    sig_prediction_updated = pyqtSignal(str, float)
    sig_live_buffer_updated = pyqtSignal(list)
    sig_live_features_updated = pyqtSignal(dict)
    sig_recording_state_updated = pyqtSignal(bool)
    sig_mode_updated = pyqtSignal(str)
    sig_connection_state_updated = pyqtSignal(bool, str)
    sig_udp_health_updated = pyqtSignal(dict)

    def __init__(self, dataset_dir: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        ensure_data_dir()
        self.dataset_dir = str(Path(dataset_dir) if dataset_dir else DATASET_DIR)

        self._state_lock = Lock()
        self._buffer_lock = Lock()
        self._db_write_lock = Lock()

        self._init_state()
        self.refresh_database()

    def _init_state(self) -> None:
        """Khởi tạo các biến trạng thái nội bộ."""
        self.system_stats = {"CPU": "0%", "RAM": "0%", "Port": "None", "UDP Rate": "0 Hz"}
        self.esp32_stats = {"Battery": "--", "Chip": "ESP32-S3", "RAM Free": "8MB"}
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()

        self.is_connected = False
        self.current_mode = "IDLE"
        self.is_recording = False
        self.spell_counts: dict[str, int] = {}
        self.udp_health = {"udp_rate_hz": 0.0, "udp_loss_pct": 0.0}

        self.sensor_buffers = {k: collections.deque(maxlen=100) for k in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']}
        self.live_buffer = collections.deque(maxlen=500)

        self._last_sensor_emit = 0.0
        self._last_live_emit = 0.0

    # ── Public methods ──────────────────────────

    def update_sensor_data(self, data: dict[str, float]) -> None:
        """Cập nhật dữ liệu cảm biến và phát signal cho UI."""
        now = time.perf_counter()
        snapshot = None
        with self._buffer_lock:
            for k, v in data.items():
                if k in self.sensor_buffers:
                    self.sensor_buffers[k].append(v)
            if now - self._last_sensor_emit >= 0.1:
                self._last_sensor_emit = now
                snapshot = {k: list(v) for k, v in self.sensor_buffers.items()}
        if snapshot:
            self.sig_sensor_data_updated.emit(snapshot)

    def add_live_sample(self, sample: list[float], *, emit: bool = True) -> None:
        """Thêm mẫu dữ liệu vào bộ đệm hiển thị đồ thị."""
        try:
            valid_sample = validate_six_axis_values(sample)
        except FrameValidationError:
            return

        now = time.perf_counter()
        with self._buffer_lock:
            self.live_buffer.append(valid_sample)
            if emit and now - self._last_live_emit >= 0.05:
                self._last_live_emit = now
                snapshot = [list(r) for r in self.live_buffer]
                self.sig_live_buffer_updated.emit(snapshot)

    def get_live_buffer_snapshot(self) -> list[list[float]]:
        """Lấy bản sao an toàn của bộ đệm live."""
        with self._buffer_lock:
            return [list(r) for r in self.live_buffer]

    def set_connection_status(self, connected: bool, port: str = "None") -> None:
        """Cập nhật trạng thái kết nối thiết bị."""
        with self._state_lock:
            self.is_connected = connected
            self.system_stats["Port"] = port
        self.sig_stats_updated.emit(self.system_stats)
        self.sig_connection_state_updated.emit(connected, port)

    def get_connection_state(self) -> tuple[bool, str]:
        """Lấy trạng thái kết nối an toàn đa luồng."""
        with self._state_lock:
            return self.is_connected, self.system_stats.get("Port", "None")

    def get_current_mode(self) -> str:
        """Lấy chế độ hoạt động hiện tại."""
        with self._state_lock:
            return self.current_mode

    def set_current_mode(self, mode: str) -> None:
        """Thiết lập chế độ hoạt động mới."""
        with self._state_lock:
            self.current_mode = mode
        self.sig_mode_updated.emit(mode)

    def get_recording_state(self) -> bool:
        """Kiểm tra xem hệ thống có đang ghi hay không."""
        with self._state_lock:
            return self.is_recording

    def set_recording_state(self, recording: bool) -> None:
        """Thiết lập trạng thái ghi dữ liệu."""
        with self._state_lock:
            self.is_recording = recording
        self.sig_recording_state_updated.emit(recording)

    def clear_live_buffer(self) -> None:
        """Xóa sạch bộ đệm dữ liệu hiển thị đồ thị."""
        with self._buffer_lock:
            self.live_buffer.clear()
        self.sig_live_buffer_updated.emit([])

    def save_settings(self, updates: Mapping[str, Any]) -> dict[str, Any]:
        """Lưu và cập nhật cấu hình ứng dụng."""
        with self._state_lock:
            self.settings.update(dict(updates))
            self.settings = self.settings_store.save(self.settings)
            return dict(self.settings)

    def get_settings_snapshot(self) -> dict[str, Any]:
        """Lấy bản sao cấu hình hiện tại."""
        with self._state_lock:
            return dict(self.settings)

    def refresh_database(self, *, force: bool = False) -> None:
        """Quét thư mục dataset để cập nhật số lượng mẫu."""
        self._ensure_dirs()
        self.spell_counts.clear()
        if os.path.exists(self.dataset_dir):
            class_map = discover_class_directories(Path(self.dataset_dir))
            for name, paths in class_map.items():
                count = 0
                for p in paths:
                    for f in p.glob("*.csv"):
                        count += 1
                        parts = f.name.split("_sample_")
                        if len(parts) == 2 and parts[0]:
                            group_key = f"{name}::{parts[0]}"
                            self.spell_counts[group_key] = self.spell_counts.get(group_key, 0) + 1
                self.spell_counts[name] = count

        for name in SYSTEM_SPELL_NAMES:
            self.spell_counts.setdefault(name, 0)

        self.sig_db_updated.emit(self.spell_counts)
        self.sig_primitive_stats_updated.emit(self.get_primitive_collection_stats())

    def refresh_primitive_stats(self) -> None:
        """Force re-emit sig_primitive_stats_updated with current filesystem state.

        Called when the Primitives page becomes visible to ensure stale
        zero-initialized stats are replaced with the real sample counts,
        regardless of whether a save/delete event has occurred.

        This is a lightweight emit — it does not re-scan the filesystem,
        it reads the already-current spell_counts dict.
        """
        self.sig_primitive_stats_updated.emit(self.get_primitive_collection_stats())

    def get_primitive_collection_stats(self) -> dict[str, int]:
        """Lấy thống kê riêng cho các cử chỉ cơ bản (primitives)."""
        names = ["SWIPE_RIGHT", "SWIPE_UP", "THRUST", "CIRCLE_CW", "CIRCLE_CCW", "WRIST_FLICK", "ZIGZAG"]
        stats = {n: self.spell_counts.get(n, 0) for n in names}
        # Check all known folder name variants for STAND BY
        stand_by_count = (
            self.spell_counts.get("STAND BY", 0)
            or self.spell_counts.get("STAND_BY", 0)
            or self.spell_counts.get("Stand By", 0)
        )
        stats["STAND_BY"] = stand_by_count
        
        # Include group counts
        for k, v in self.spell_counts.items():
            if "::" in k:
                stats[k] = v
                
        return stats

    def save_cropped_data(self, spell: str, data: list[list[float]]) -> bool:
        """Lưu vùng dữ liệu đã cắt vào file CSV mới."""
        if not data or not spell.strip():
            return False
        folder = spell_write_dir(Path(self.dataset_dir), spell)
        folder.mkdir(parents=True, exist_ok=True)

        path = folder / f"sample_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.csv"
        try:
            with open(path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
                writer.writerows(data)
            self.refresh_database(force=True)
            return True
        except Exception as exc:
            log.error("DataStore: Save failed: %s", exc)
            return False

    def get_samples_for_spell(self, spell: str) -> list[str]:
        """Lấy danh sách các file mẫu của một spell."""
        files = []
        for d in storage_dirs_for_spell(Path(self.dataset_dir), spell):
            files.extend(f.name for f in sorted(d.glob("*.csv")))
        return sorted(files)

    # ── Private methods ─────────────────────────

    def _ensure_dirs(self) -> None:
        """Đảm bảo các thư mục hệ thống luôn tồn tại."""
        with self._db_write_lock:
            for name in SYSTEM_SPELL_NAMES:
                spell_write_dir(Path(self.dataset_dir), name).mkdir(parents=True, exist_ok=True)

    # ── Slots ───────────────────────────────────

    def update_esp_stats(self, updates: dict[str, str]) -> None:
        """Cập nhật thông số từ thiết bị ESP32."""
        self.esp32_stats.update(updates)
        self.sig_stats_updated.emit(self.esp32_stats)

    def update_live_features(self, features: dict) -> None:
        """Cập nhật các đặc trưng sensor mới nhất."""
        self.sig_live_features_updated.emit(features)

    def update_udp_health(self, updates: dict[str, Any]) -> None:
        """Cập nhật sức khỏe kết nối UDP telemetry."""
        with self._state_lock:
            self.udp_health.update(updates)
            self.system_stats["UDP Rate"] = f"{self.udp_health.get('udp_rate_hz', 0.0)} Hz"
        self.sig_stats_updated.emit(self.system_stats)
        self.sig_udp_health_updated.emit(dict(self.udp_health))

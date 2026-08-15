# -*- coding: utf-8 -*-
"""
logic/handler.py - Bộ điều phối trung tâm (MVC Controller).

Trách nhiệm:
    - Kết nối signal từ các Worker nền tới các trang giao diện UI.
    - Điều phối luồng dữ liệu cảm biến thời gian thực.
    - Quản lý quá trình ghi mẫu, huấn luyện mô hình và nạp firmware.
    - Đảm bảo các tiến trình chạy không đồng bộ (non-blocking).
"""

from __future__ import annotations

import csv
import logging
import numpy as np
from pathlib import Path
from threading import Lock

from PyQt6.QtCore import QObject, Qt, QTimer

from config import APP_DATA_DIR, WORKSPACE_ROOT, FIRMWARE_BIN_DIR
from constants import is_system_spell, canonical_system_spell, normalize_spell_name
from ui.asset_utils import resolve_asset_path

from .data_io_worker import DataIOWorker
from .data_store import DataStore
from .feature_worker import FeatureWorker
from .flash_worker import FlashWorker
from .frame_protocol import build_scale_profile
from .model_uploader import ModelUploader
from .prototypical_recognizer import PrototypicalRecognizer
from .recorder import DataRecorder
from .serial_worker import SerialWorker
from .tensorflow.pipeline import GestureModelBuildWorker
from .primitive_quality_worker import PrimitiveQualityWorker
from logic.dataset_layout import (
    discover_class_directories,
    _routes_to_primitives,
    _PRIMITIVE_LOGICAL_NAMES,
    storage_dirs_for_spell,
)
from logic.tensorflow.nvs_builder import build_config_bin
from PyQt6.QtCore import QThread, pyqtSignal

class NVSBuildWorker(QThread):
    sig_status = pyqtSignal(str)
    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal(bool, str)

    def __init__(self, spell_names: list[str], dataset_dir: str, spell_recognizer, app_data_dir) -> None:
        super().__init__()
        self.spell_names = spell_names
        self.dataset_dir = dataset_dir
        self.spell_recognizer = spell_recognizer
        self.app_data_dir = app_data_dir

    def run(self) -> None:
        try:

            self.sig_status.emit(">> [NVS] Discovering dataset classes...")
            self.sig_progress.emit(10)
            dataset_root = Path(self.dataset_dir)
            all_classes = discover_class_directories(dataset_root)

            # Trích xuất primitives
            primitives = []
            for c_name in all_classes.keys():
                canon = canonical_system_spell(normalize_spell_name(c_name))
                if _routes_to_primitives(canon) or c_name.upper() in _PRIMITIVE_LOGICAL_NAMES:
                    primitives.append(c_name)

            if "STAND BY" not in primitives and "STAND_BY" not in primitives:
                primitives.append("STAND BY")

            # Gộp danh sách cử chỉ không trùng lặp
            seen = set()
            final_gestures = []
            for g in primitives + self.spell_names:
                g_clean = g.strip()
                if not g_clean:
                    continue
                g_upper = g_clean.upper()
                if g_upper not in seen:
                    seen.add(g_upper)
                    final_gestures.append(g_clean)

            gesture_names = []
            centroids = []
            is_spell_flags = []
            thresholds = []

            total_gestures = len(final_gestures)
            for idx, g in enumerate(final_gestures):
                is_spell = g not in primitives
                if is_spell:
                    self.sig_status.emit(f">> [NVS] Embedding spell '{g}'...")
                self.sig_progress.emit(10 + int(70 * (idx / total_gestures)))

                # Load samples locally
                from logic.dataset_layout import storage_dirs_for_spell
                dirs = storage_dirs_for_spell(dataset_root, g)
                csv_files = []
                for d in dirs:
                    csv_files.extend(sorted(d.glob("*.csv")))

                samples = []
                for fpath in csv_files:
                    rows = []
                    try:
                        with open(fpath, "r", encoding="utf-8", newline="") as f:
                            reader = csv.reader(f)
                            next(reader, None)  # skip header
                            for line in reader:
                                if len(line) >= 6:
                                    try:
                                        rows.append([float(v) for v in line[:6]])
                                    except ValueError:
                                        continue
                    except Exception:
                        continue

                    if len(rows) < 64:
                        continue

                    best_window = None
                    max_energy = -1.0
                    for start_idx in range(0, len(rows) - 64 + 1, 2):
                        w_list = rows[start_idx:start_idx + 64]
                        energy = sum(
                            abs(row[0]) + abs(row[1]) + abs(row[2]) + 
                            abs(row[3]) + abs(row[4]) + abs(row[5])
                            for row in w_list
                        )
                        if energy > max_energy:
                            max_energy = energy
                            window = np.asarray(w_list, dtype=np.float32)
                            window[:, 3] /= 125.0
                            window[:, 4] /= 125.0
                            window[:, 5] /= 125.0
                            window = np.clip(window, -2.0, 2.0)
                            best_window = window
                    if best_window is not None:
                        samples.append(best_window)

                if not samples:
                    if is_spell:
                        self.sig_status.emit(f">> [WARN] No samples found for spell '{g}', using default zero centroid.")
                    centroid = [0.0] * 16
                    thresh = 0.45
                else:
                    batch = np.asarray(samples, dtype=np.float32)
                    embeddings = self.spell_recognizer._embed_batch(batch)
                    
                    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                    norms[norms == 0] = 1e-10
                    normalized = embeddings / norms
                    
                    mean_emb = np.mean(normalized, axis=0)
                    m_norm = np.linalg.norm(mean_emb)
                    if m_norm > 0:
                        mean_emb = mean_emb / m_norm
                    centroid = mean_emb.tolist()
                    thresh = 0.45

                gesture_names.append(g)
                centroids.append(centroid)
                is_spell_flags.append(is_spell)
                thresholds.append(thresh)

            self.sig_status.emit(">> [NVS] Compiling labels.bin...")
            self.sig_progress.emit(90)

            out_bin = Path(self.app_data_dir) / "labels.bin"
            build_config_bin(
                gesture_names=gesture_names,
                centroids=centroids,
                is_spell_flags=is_spell_flags,
                thresholds=thresholds,
                out_path=str(out_bin)
            )
            self.sig_finished.emit(True, f"labels.bin generated successfully w/ {len(self.spell_names)} spells.")
        except Exception as e:
            self.sig_finished.emit(False, str(e))

log = logging.getLogger(__name__)


class _EncoderLoadWorker(QThread):
    sig_done = pyqtSignal(object, object)

    def __init__(self, app_data_dir):
        super().__init__()
        self.app_data_dir = app_data_dir

    def run(self):
        try:
            path = self.app_data_dir / "gesture_encoder.keras"
            proto_path = self.app_data_dir / "spell_prototypes.json"
            if not path.exists():
                self.sig_done.emit(None, None)
                return

            import tensorflow as tf
            from logic.tensorflow.encoder_pipeline import _get_l2_normalize_layer_class
            
            try:
                encoder = tf.keras.models.load_model(
                    str(path), compile=False,
                    custom_objects={"L2NormalizeLayer": _get_l2_normalize_layer_class()},
                )
            except Exception:
                log.warning("Loading legacy Lambda encoder — retrain to upgrade.")
                encoder = tf.keras.models.load_model(
                    str(path), compile=False, safe_mode=False,
                )
            
            p_path = str(proto_path) if proto_path.exists() else None
            self.sig_done.emit(encoder, p_path)
        except Exception as e:
            log.error(f"Background encoder load failed: {e}")
            self.sig_done.emit(None, None)


class Handler(QObject):
    """
    Bộ não điều phối chính của ứng dụng.
    Kết nối dữ liệu từ phần cứng (Serial/UDP) tới giao diện người dùng.
    """

    _MODE_IDLE = "IDLE"
    _MODE_INFER = "INFER"
    _MODE_RECORD = "RECORD"
    _MODE_UPDATE = "UPDATE"

    _ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        "IDLE": {"IDLE", "INFER", "RECORD", "UPDATE"},
        "INFER": {"IDLE", "INFER", "RECORD", "UPDATE"},
        "RECORD": {"IDLE", "INFER", "RECORD"},
        "UPDATE": {"IDLE", "INFER", "UPDATE"},
    }

    _DEVICE_MODE_BY_RUNTIME: dict[str, str] = {
        "IDLE": "IDLE",
        "INFER": "IDLE",
        "RECORD": "RECORD",
        "UPDATE": "UPDATE",
    }

    def __init__(
        self,
        ui_page_wand,
        ui_page_record,
        ui_page_home,
        data_store: DataStore,
        ui_page_setting=None,
        ui_primitive_collect=None,
    ) -> None:
        super().__init__()
        self.ui_wand = ui_page_wand
        self.ui_record = ui_page_record
        self.ui_home = ui_page_home
        self.ui_setting = ui_page_setting
        self.ui_primitive_collect = ui_primitive_collect
        self.store = data_store

        self._init_workers()
        self._init_state()
        self._connect_signals()
        self._load_initial_state()

    def _init_workers(self) -> None:
        """Khởi tạo các luồng xử lý nền (Workers)."""
        self.serial_worker = SerialWorker()
        self.uploader = ModelUploader()
        self.recorder = DataRecorder(dataset_dir=self.store.dataset_dir)
        self.flash_worker = FlashWorker()

        self.data_io_worker = DataIOWorker(dataset_dir=self.store.dataset_dir)
        if not self.data_io_worker.isRunning():
            self.data_io_worker.start()

        self.feature_worker = FeatureWorker()
        if not self.feature_worker.isRunning():
            self.feature_worker.start()

    def _init_state(self) -> None:
        """Khởi tạo trạng thái nội bộ."""
        self._port_owner = None
        self._port_lock = Lock()
        self._mode_lock = Lock()
        self._mode = self.store.get_current_mode() or self._MODE_IDLE

        self._project_root = WORKSPACE_ROOT

        self._feature_timer = QTimer(self)
        self._feature_timer.setInterval(200)
        self._feature_timer.timeout.connect(self._on_feature_timer_tick)

        self.spell_recognizer: PrototypicalRecognizer | None = None
        self._model_build_worker: GestureModelBuildWorker | None = None
        self._nvs_build_worker: NVSBuildWorker | None = None
        self._primitive_active = False
        self._quality_worker: PrimitiveQualityWorker | None = None
        self.encoder_trainer = None

        self._pending_save_spell = ""
        self._pending_save_context = ""
        self._primitive_collect_gesture = ""
        self._primitive_collect_group = ""
        self._primitive_collect_active = False

        self._pending_flash_bin_type = ""
        self._pending_flash_port = ""
        self._pending_flash_bin_path = None
        self._pending_upload_port = ""
        self._pending_upload_model_path = None

        self._shutdown_done = False

    def _load_initial_state(self) -> None:
        """Nạp trạng thái ban đầu sau khi khởi tạo."""
        self._start_async_encoder_load()
        self.on_serial_scan()
        self.ui_home.set_mode(self._mode)
        self._feature_timer.start()

    # ── Signal Wiring ────────────────────────────

    def _connect_signals(self) -> None:
        """Kết nối toàn bộ hệ thống signal/slot."""
        self._connect_ui_signals()
        self._connect_worker_signals()
        self._connect_store_signals()

    def _connect_ui_signals(self) -> None:
        """Kết nối tín hiệu từ giao diện."""
        self.ui_wand.sig_serial_scan.connect(self.on_serial_scan)
        self.ui_wand.sig_serial_connect.connect(self.on_serial_connect)
        self.ui_wand.sig_serial_disconnect.connect(self.on_serial_disconnect)
        self.ui_wand.sig_flash_upload.connect(self.on_flash_upload)

        self.ui_record.sig_data_cropped.connect(self.on_data_cropped)
        self.ui_record.sig_start_record.connect(self.on_record_start)
        self.ui_record.sig_stop_record.connect(self.on_record_stop)
        self.ui_record.sig_spell_selected.connect(self.on_spell_selected)
        self.ui_record.sig_spell_deleted.connect(self.on_spell_deleted)

        self.ui_record.sig_clear_buffer.connect(self.on_clear_buffer)
        if hasattr(self.ui_record, 'sig_export_csv'):
            self.ui_record.sig_export_csv.connect(self.on_export_csv)

        self.ui_wand.sig_train_build_firmware_requested.connect(self.on_build_firmware)

        self.ui_setting.sig_settings_saved.connect(self.on_settings_saved)
        if hasattr(self.ui_setting, 'sig_clear_database'):
            self.ui_setting.sig_clear_database.connect(self.on_clear_database)
        self.ui_setting.sig_flash_data_firmware.connect(self.on_flash_data_firmware)
        self.ui_setting.sig_flash_inference_firmware.connect(self.on_flash_inference_firmware)
        self.ui_setting.sig_scan_primitive_quality.connect(self.on_primitive_quality_scan_requested)
        self.ui_setting.sig_stop_primitive_scan.connect(self.on_primitive_quality_scan_stop)

        if self.ui_primitive_collect:
            self.ui_primitive_collect.sig_start_collection.connect(self.on_start_collection)
            self.ui_primitive_collect.sig_stop_collection.connect(self.on_stop_collection)
            self.ui_primitive_collect.sig_capture_collection.connect(self.on_capture_collection)
            self.ui_primitive_collect.sig_train_encoder_requested.connect(self.on_train_encoder_requested)

    def _connect_worker_signals(self) -> None:
        """Kết nối tín hiệu từ các worker nền."""
        self.serial_worker.sig_data_received.connect(self._on_serial_frame, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_connection_status.connect(
            self._on_serial_status, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_raw_line_received.connect(
            self._route_raw_line, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_prediction_received.connect(
            self.store.update_prediction, type=Qt.ConnectionType.QueuedConnection)

        self.data_io_worker.sig_save_done.connect(self._on_io_done, type=Qt.ConnectionType.QueuedConnection)
        self.data_io_worker.sig_db_refreshed.connect(self.store.update_counts_from_worker, type=Qt.ConnectionType.QueuedConnection)
        self.data_io_worker.sig_delete_sample_done.connect(self._on_io_delete_sample_done, type=Qt.ConnectionType.QueuedConnection)
        self.data_io_worker.sig_export_done.connect(self._on_export_done, type=Qt.ConnectionType.QueuedConnection)
        self.data_io_worker.sig_queue_warning.connect(
            self.ui_wand.append_terminal_text, type=Qt.ConnectionType.QueuedConnection)
        self.feature_worker.sig_features_ready.connect(self.store.update_live_features, type=Qt.ConnectionType.QueuedConnection)

        if hasattr(self, "recorder") and self.recorder:
            self.recorder.sig_finished.connect(self._on_recorder_finished, type=Qt.ConnectionType.QueuedConnection)

        # Uploader signals
        self.uploader.status_msg.connect(self.ui_wand.append_terminal_text, type=Qt.ConnectionType.QueuedConnection)
        self.uploader.sig_progress.connect(self.ui_wand.update_flash_progress, type=Qt.ConnectionType.QueuedConnection)
        self.uploader.sig_finished.connect(self._on_upload_finished, type=Qt.ConnectionType.QueuedConnection)

        # Flash worker signals
        self.flash_worker.log_msg.connect(self._flash_log_to_console, type=Qt.ConnectionType.QueuedConnection)
        self.flash_worker.sig_progress.connect(self.ui_setting.update_flash_progress, type=Qt.ConnectionType.QueuedConnection)
        self.flash_worker.sig_finished.connect(self._on_firmware_flash_finished, type=Qt.ConnectionType.QueuedConnection)

    def _connect_store_signals(self) -> None:
        """Kết nối tín hiệu từ kho dữ liệu."""
        self.store.sig_db_updated.connect(self._on_db_refreshed)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)
        self.store.sig_spell_history_updated.connect(self.ui_home.update_spell_history)
        self.store.sig_registered_prototypes_updated.connect(self.ui_home.update_loaded_spells)
        self.store.sig_prediction_updated.connect(self.ui_home.show_recognized_spell)

    # ── Action Handlers ──────────────────────────

    def on_serial_scan(self) -> None:
        """Quét tìm cổng Serial khả dụng."""
        ports = SerialWorker.get_available_ports()
        self.ui_wand.update_serial_port_list(ports)

    def on_serial_connect(self, port: str) -> None:
        """Bắt đầu kết nối Serial tới cổng đã chọn."""
        if not port:
            return
        with self._port_lock:
            if self._port_owner and self._port_owner != "serial":
                return
            self._port_owner = "serial"

        settings = self.store.get_settings_snapshot()
        self.serial_worker.set_scale_profile(build_scale_profile(settings))
        self.serial_worker.port = port
        if not self.serial_worker.isRunning():
            self.serial_worker.start()

    def on_serial_disconnect(self) -> None:
        """Ngắt kết nối Serial (non-blocking)."""
        if self.serial_worker.isRunning():
            self.serial_worker.finished.connect(self._on_serial_stopped)
            self.serial_worker.stop()

    def on_record_start(self, spell: str) -> None:
        """Bắt đầu ghi mẫu cử chỉ mới."""
        if not spell.strip() or self.store.get_recording_state():
            return
        connected, _ = self.store.get_connection_state()
        if not connected:
            self.ui_wand.append_terminal_text("[ERROR] Serial connection is required.")
            return
        if self._mode == self._MODE_UPDATE:
            self.ui_wand.append_terminal_text("[ERROR] Cannot start recording while update mode is active.")
            return
        self._recording_raw_file = None
        if self.recorder.start_recording(spell):
            self.store.clear_live_buffer()
            self.ui_record.is_live = True
            self._set_mode(self._MODE_RECORD)

    def _on_recorder_finished(self, success: bool, message: str) -> None:
        """Nhận sự kiện hoàn tất ghi file từ DataRecorder."""
        if success and hasattr(self.recorder, "last_recorded_file") and self.recorder.last_recorded_file:
            self._recording_raw_file = self.recorder.last_recorded_file
        else:
            self._recording_raw_file = None

    def on_record_stop(self) -> None:
        """Dừng quá trình ghi mẫu."""
        self.recorder.stop_recording()
        self.ui_record.is_live = False
        next_mode = self._MODE_INFER if self.serial_worker.isRunning() else self._MODE_IDLE
        self._transition_mode(
            next_mode,
            reason="record stop",
            push_to_device=True,
        )
        self.ui_wand.append_terminal_text(">> RECORD STOPPED - Ready to snip")

    def on_data_cropped(self, data: list, spell: str) -> None:
        """Gửi yêu cầu lưu dữ liệu đã cắt vào dataset."""
        if data and spell.strip():
            raw_file = getattr(self, "_recording_raw_file", None)
            if raw_file:
                try:
                    p = Path(raw_file)
                    if p.exists():
                        p.unlink()
                        log.info("Removed uncropped raw sample %s in favor of snipped sample.", p.name)
                except Exception as exc:
                    log.warning("Could not remove raw recording file %s: %s", raw_file, exc)
                self._recording_raw_file = None

            self._pending_save_context = "record"
            self._pending_save_spell = spell
            self.data_io_worker.enqueue_save(spell, data)

    def on_clear_buffer(self) -> None:
        """Xóa sạch bộ đệm dữ liệu đang ghi và reset trạng thái."""
        self.store.clear_live_buffer()
        if hasattr(self, "ui_record") and self.ui_record:
            self.ui_record.is_live = False
            if hasattr(self.ui_record, "clear_plots"):
                self.ui_record.clear_plots()
        self.ui_wand.append_terminal_text(">> RECORD BUFFER CLEARED")

    def on_export_csv(self) -> None:
        """Xuất dữ liệu trong live buffer ra file CSV."""
        buf = self.store.get_live_buffer_snapshot()
        if not buf:
            self.ui_wand.append_terminal_text("[WARN] Live buffer is empty. Nothing to export.")
            return

        from PyQt6.QtWidgets import QFileDialog
        parent_widget = getattr(self, "ui_record", None)
        path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Live Buffer to CSV",
            "recorded_samples.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        self.data_io_worker.enqueue_export(buf, path)

    def _on_export_done(self, success: bool, message: str) -> None:
        """Nhận kết quả xuất CSV từ DataIOWorker."""
        prefix = ">> [EXPORT DONE]" if success else ">> [EXPORT ERROR]"
        self.ui_wand.append_terminal_text(f"{prefix} {message}")

    def on_clear_database(self) -> None:
        """Xóa sạch live buffer và refresh lại dataset."""
        self.store.clear_live_buffer()
        if hasattr(self, "ui_record") and self.ui_record:
            self.ui_record.is_live = False
            if hasattr(self.ui_record, "clear_plots"):
                self.ui_record.clear_plots()
        self.data_io_worker.enqueue_refresh()
        self.ui_wand.append_terminal_text(">> ALL COLLECTED DATA CLEARED")

    def on_udp_sensor_data(self, values: list[float]) -> None:
        """Route normalized UDP sensor frame through the standard data path.

        Called from MainWindow when a UDP packet contains 6-axis sensor
        data. Reuses the same fan-in path as SerialWorker to ensure
        recording, 3D orientation, and DataStore buffers are all updated
        consistently regardless of transport.

        Args:
            values: [ax, ay, az, gx, gy, gz] normalized sensor readings.
        """
        self._on_serial_frame(values)

    def on_udp_esp_stats(self, stats: dict[str, str]) -> None:
        """Route UDP hardware telemetry to DataStore.

        Args:
            stats: Dict of ESP32 hardware stats (Battery, RAM Free, etc.)
        """
        self.store.update_esp_stats(stats)

    # ── Internal Slots ──────────────────────────

    def on_build_firmware(self, spell_names: list[str]) -> None:
        """Sinh ra file labels.bin chứa cấu hình NVS động cho các spell và primitive."""
        if not self.spell_recognizer or not self.spell_recognizer.encoder:
            self.ui_wand.append_terminal_text(">> [ERROR] Encoder is not trained or loaded. Please train encoder in Primitive page first.")
            self.ui_wand.update_flash_progress(0, "Failed")
            return

        if self._nvs_build_worker and self._nvs_build_worker.isRunning():
            self.ui_wand.append_terminal_text(">> [ERROR] NVS Build already in progress.")
            return

        self.ui_wand.append_terminal_text(">> [START] Building NVS labels configuration (labels.bin)...")
        self.ui_wand.update_flash_progress(0, "Building...")
        # Reset session loaded spells when starting new NVS build
        self.store.set_registered_prototypes(set())

        self._nvs_build_worker = NVSBuildWorker(
            spell_names=spell_names,
            dataset_dir=self.store.dataset_dir,
            spell_recognizer=self.spell_recognizer,
            app_data_dir=APP_DATA_DIR
        )
        self._nvs_build_worker.sig_status.connect(self.ui_wand.append_terminal_text)
        self._nvs_build_worker.sig_progress.connect(self.ui_wand.update_flash_progress)
        self._nvs_build_worker.sig_finished.connect(self._on_nvs_build_finished)
        if not self._nvs_build_worker.isRunning():
            self._nvs_build_worker.start()

    def _on_nvs_build_finished(self, success: bool, message: str) -> None:
        if success:
            if self._nvs_build_worker and hasattr(self._nvs_build_worker, "spell_names"):
                self.store.set_registered_prototypes(set(self._nvs_build_worker.spell_names))
            self.ui_wand.append_terminal_text(f">> [DONE] {message}")
            self.ui_wand.update_flash_progress(100, "Success")
        else:
            self.ui_wand.append_terminal_text(f">> [ERROR] Failed to generate labels.bin: {message}")
            self.ui_wand.update_flash_progress(0, "Failed")

    def _on_serial_frame(self, values: list[float]) -> None:
        """Xử lý một khung dữ liệu sensor từ Serial."""
        if len(values) < 6:
            return

        # 1. Đẩy vào DataStore
        self.store.update_sensor_data({
            "ax": values[0], "ay": values[1], "az": values[2],
            "gx": values[3], "gy": values[4], "gz": values[5]
        })

        # 3. Ghi vào buffer Record (nếu đang bật)
        if self.ui_record.is_live:
            self.store.add_live_sample(values)

        # 4. Đưa vào recorder (nếu đang record)
        self.recorder.add_row(values)

    def _on_serial_status(self, connected: bool, msg: str) -> None:
        """Xử lý thay đổi trạng thái kết nối phần cứng."""
        self.ui_wand.set_serial_status(connected, self.serial_worker.port if connected else "")
        self.store.set_connection_status(connected, self.serial_worker.port if connected else "None")
        if hasattr(self, "ui_record") and self.ui_record:
            if hasattr(self.ui_record, "set_wand_ready"):
                self.ui_record.set_wand_ready(connected)
        if not connected:
            self._set_mode(self._MODE_IDLE)
            with self._port_lock:
                self._port_owner = None

    def _route_raw_line(self, line: str) -> None:
        """Phân luồng log UART: Primitive sang màn hình thu thập, Spell sang Wand."""
        if not line:
            return
        # Lọc bỏ các dòng CSV cảm biến thô để tránh gây nghẽn giao diện Terminal
        first = line[0]
        if (first.isdigit() or first in "-+") and "," in line and not line.startswith("ACK:"):
            return

        line_upper = line.upper()
        if "DEBUG_BLACKHOLE" in line_upper or "PRIMITIVE" in line_upper:
            if self.ui_primitive_collect and hasattr(self.ui_primitive_collect, "console"):
                self.ui_primitive_collect.console.append_line(line)
        else:
            self.ui_wand.append_terminal_text(line)

    def _on_feature_timer_tick(self) -> None:
        """Kích hoạt trích xuất đặc trưng định kỳ."""
        arr = self.store.get_live_buffer_numpy()
        if arr.size > 0:
            self.feature_worker.enqueue(arr)

    def _on_serial_stopped(self) -> None:
        """Dọn dẹp sau khi luồng Serial dừng hẳn."""
        try:
            self.serial_worker.finished.disconnect(self._on_serial_stopped)
        except TypeError:
            pass
        with self._port_lock:
            self._port_owner = None
        self.serial_worker = SerialWorker()
        
        self.serial_worker.sig_data_received.connect(self._on_serial_frame, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_connection_status.connect(
            self._on_serial_status, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_raw_line_received.connect(
            self._route_raw_line, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_prediction_received.connect(
            self.store.update_prediction, type=Qt.ConnectionType.QueuedConnection)

    # ── Private methods ─────────────────────────

    def _set_port_owner(self, owner: str | None) -> None:
        """Track which subsystem currently owns the serial port."""
        with self._port_lock:
            self._port_owner = owner

    def _get_port_owner(self) -> str | None:
        """Read current serial-port owner under lock."""
        with self._port_lock:
            return self._port_owner

    def _set_mode(self, mode: str) -> None:
        """Chuyển đổi chế độ hoạt động an toàn."""
        with self._mode_lock:
            self._mode = mode
            self.store.set_current_mode(mode)
            self.ui_home.set_mode(mode)

    def _start_async_encoder_load(self) -> None:
        self._encoder_worker = _EncoderLoadWorker(APP_DATA_DIR)
        self._encoder_worker.sig_done.connect(self._on_encoder_loaded)
        if not self._encoder_worker.isRunning():
            self._encoder_worker.start()

    def _on_encoder_loaded(self, encoder, proto_path):
        if not encoder:
            return
        
        try:
            self.spell_recognizer = PrototypicalRecognizer(encoder)
            if proto_path:
                self.spell_recognizer.load(proto_path)
            else:
                # Cập nhật prototypes từ dataset nếu chưa có file cache spell_prototypes.json
                self._update_spell_prototypes()
            
            log.info(f"Loaded encoder and {len(self.spell_recognizer.prototypes) if self.spell_recognizer else 0} prototypes.")
            
            # Re-run consistency analysis for currently selected spell on Record Page
            current_spell = getattr(self.ui_record, 'current_spell_name', None)
            if current_spell:
                self._run_consistency_analysis(current_spell)
        except Exception as e:
            log.error(f"Failed to initialize recognizer: {e}")
            if hasattr(self, 'ui_wand') and self.ui_wand:
                self.ui_wand.append_terminal_text(f"[ERROR] Recognizer init failed: {e}")


    def _on_db_refreshed(self, counts: dict) -> None:
        """Cập nhật dữ liệu từ DB vào các trang UI."""
        self.ui_record.load_spell_list(counts)
        self.ui_wand.load_spell_payload_list(counts)

        # Reload selected spell samples and re-run consistency analysis
        current_spell = getattr(self.ui_record, 'current_spell_name', None)
        if current_spell:
            samples = self.store.get_samples_for_spell(current_spell)
            self.ui_record.load_samples_for_spell(current_spell, samples)
            self._run_consistency_analysis(current_spell)

    def _compute_spell_consistency(self, spell_name: str) -> float | str:
        """Tính toán độ đồng nhất (consistency) của các mẫu trong spell.
        
        Trả về giá trị từ 0.0 đến 1.0, hoặc chuỗi trạng thái nếu không đủ dữ liệu/không có encoder.
        """
        if not self.spell_recognizer:
            return "no_encoder"
        if not spell_name:
            return "need_samples"
            
        from logic.tensorflow.pipeline import _read_csv_rows, _windowize
        from logic.dataset_layout import storage_dirs_for_spell
        
        dataset_root = Path(self.store.dataset_dir)
        dirs = storage_dirs_for_spell(dataset_root, spell_name)
        csv_files = []
        for d in dirs:
            csv_files.extend(sorted(d.glob("*.csv")))
            
        if len(csv_files) < 2:
            return "need_samples"
            
        embeddings = []
        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            if not rows:
                continue
            windows = _windowize(rows, window_size=64, step=4)
            for window in windows:
                data = np.asarray(window, dtype=np.float32)
                data = np.clip(data, -2.0, 2.0)
                emb = self.spell_recognizer._embed_batch(np.expand_dims(data, axis=0))[0]
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                embeddings.append(emb)
                
        if len(embeddings) < 2:
            return None
            
        embeddings = np.array(embeddings)
        dot_matrix = np.dot(embeddings, embeddings.T)
        
        triu_indices = np.triu_indices(len(embeddings), k=1)
        similarities = dot_matrix[triu_indices]
        
        if len(similarities) == 0:
            return None
            
        mean_sim = float(np.mean(similarities))
        consistency = max(0.0, min(1.0, (mean_sim - 0.5) / 0.5)) if mean_sim >= 0.5 else 0.0
        return consistency

    def _update_spell_prototypes(self) -> None:
        """Cập nhật prototypes cho toàn bộ spell từ dataset hiện tại."""
        if not self.spell_recognizer:
            return

        import os
        from logic.tensorflow.pipeline import _read_csv_rows, _windowize
        from logic.dataset_layout import storage_dirs_for_spell

        dataset_root = Path(self.store.dataset_dir)
        spells_dir = dataset_root / "spells"
        
        spell_names = []
        if spells_dir.exists():
            spell_names = [d.name for d in spells_dir.iterdir() if d.is_dir()]
            
        all_spells = set(spell_names) | set(self.spell_recognizer.prototypes.keys())
        
        updated_any = False
        
        for spell in all_spells:
            dirs = storage_dirs_for_spell(dataset_root, spell)
            csv_files = []
            for d in dirs:
                csv_files.extend(sorted(d.glob("*.csv")))
            
            samples = []
            for csv_file in csv_files:
                rows = _read_csv_rows(csv_file)
                if not rows:
                    continue
                # Cắt windows
                windows = _windowize(rows, window_size=64, step=4)
                for window in windows:
                    data = np.asarray(window, dtype=np.float32)
                    data = np.clip(data, -2.0, 2.0)
                    samples.append(data)
            
            if samples:
                try:
                    self.spell_recognizer.register_spell(spell, samples)
                    updated_any = True
                except Exception as e:
                    log.error(f"Failed to register spell '{spell}': {e}")
            else:
                if spell in self.spell_recognizer.prototypes:
                    self.spell_recognizer.remove_spell(spell)
                    updated_any = True
                    
        if updated_any:
            proto_path = APP_DATA_DIR / "spell_prototypes.json"
            self.spell_recognizer.save(str(proto_path))
            log.info(f"Updated spell prototypes in {proto_path}")

    def _on_io_done(self, success: bool, msg: str) -> None:
        """Phản hồi sau khi thao tác I/O hoàn tất."""
        if success:
            self.ui_wand.append_terminal_text(f">> Success: {msg}")
        self._on_io_save_done(success, msg)

    def on_flash_upload(self) -> None:
        """Khởi động nạp model TFLite (non-blocking)."""
        settings = self.store.get_settings_snapshot()
        model_path = settings.get("model_path")
        if not model_path:
            self.ui_wand.append_terminal_text("[ERROR] Model file not found in settings.")
            self.ui_wand.update_flash_progress(0, "Error")
            return

        import os
        import shutil
        if not os.path.exists(model_path):
            self.ui_wand.append_terminal_text(f"[ERROR] Model file not found: {model_path}")
            self.ui_wand.update_flash_progress(0, "Error")
            return

        # Copy external model into APP_DATA_DIR to pass FlashWorker's
        # security whitelist (only allows files inside allowed_roots).
        model_p = Path(model_path).resolve()
        if not model_p.is_relative_to(APP_DATA_DIR.resolve()):
            dest = APP_DATA_DIR / model_p.name
            try:
                APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(model_p), str(dest))
                self.ui_wand.append_terminal_text(
                    f"[INFO] Copied external model to {dest}"
                )
                model_path = str(dest)
            except (OSError, shutil.SameFileError) as e:
                self.ui_wand.append_terminal_text(
                    f"[ERROR] Failed to copy model to app_data: {e}"
                )
                self.ui_wand.update_flash_progress(0, "Error")
                return

        if self.store.get_recording_state() or self._mode == self._MODE_RECORD:
            self.ui_wand.append_terminal_text("[ERROR] Stop recording before starting model upload.")
            return

        connected, port = self.store.get_connection_state()
        if not connected or not port:
            if hasattr(self.ui_wand, "combo_serial_ports"):
                port = self.ui_wand.combo_serial_ports.currentText()
            if not port:
                self.ui_wand.append_terminal_text("[ERROR] Serial port not connected.")
                return

        if not self._transition_mode(self._MODE_UPDATE, reason="start upload"):
            return

        if not self._can_use_port("upload", allow_owner="serial"):
            self._set_mode(self._MODE_IDLE)
            return

        self._pending_upload_port = port
        self._pending_upload_model_path = model_path

        if self.serial_worker.isRunning():
            self.serial_worker.finished.connect(self._on_serial_stopped_start_upload)
            self.serial_worker.stop()
        else:
            self._start_upload_immediately()

    def _on_serial_stopped_start_upload(self) -> None:
        """Called when SerialWorker stops, starts the model upload."""
        try:
            self.serial_worker.finished.disconnect(self._on_serial_stopped_start_upload)
        except TypeError:
            pass
        self._start_upload_immediately()

    def _start_upload_immediately(self) -> None:
        port = self._pending_upload_port
        path = self._pending_upload_model_path

        if not port or not path:
            self._clear_pending_upload_context()
            self._set_port_owner(None)
            self.ui_wand.update_flash_progress(0, "Handoff failed")
            self.ui_wand.append_terminal_text("[ERROR] Upload handoff failed: missing pending upload context.")
            return

        self.ui_wand.append_terminal_text(f">> [START] Building & Flashing Firmware to {port}...")
        self.ui_wand.update_flash_progress(0, "Building...")
        
        from logic.flash_worker import FlashWorker
        from config import APP_DATA_DIR
        
        self._model_flash_worker = FlashWorker()
        self._model_flash_worker.log_msg.connect(self.ui_wand.append_terminal_text)
        self._model_flash_worker.sig_progress.connect(
            lambda p: self.ui_wand.update_flash_progress(p, f"Flashing {p}%")
        )
        self._model_flash_worker.sig_finished.connect(self._on_upload_finished)
        
        labels_path = APP_DATA_DIR / "labels.bin"
        self._model_flash_worker.flash_firmware(
            port=port,
            flash_parts={
                "0x290000": str(path),
                "0x390000": str(labels_path)
            }
        )

    def _on_upload_finished(self, success: bool, message: str) -> None:
        """Called when ModelUploader finishes uploading."""
        port = self._pending_upload_port
        self._clear_pending_upload_context()
        self._set_port_owner(None)
        self._set_mode(self._MODE_IDLE)

        if success:
            self.ui_wand.append_terminal_text(f">> [DONE] Model upload COMPLETE: {message}")
            self.ui_wand.update_flash_progress(100, "Success")
            if port:
                self.on_serial_connect(port)
        else:
            self.ui_wand.append_terminal_text(f">> [FAIL] Model upload FAILED: {message}")
            self.ui_wand.update_flash_progress(0, "Failed")

    def _clear_pending_upload_context(self) -> None:
        self._pending_upload_port = ""
        self._pending_upload_model_path = None

    def on_spell_selected(self, name: str) -> None:
        """Khi một spell được chọn từ thư viện."""
        samples = self.store.get_samples_for_spell(name)
        self.ui_record.load_samples_for_spell(name, samples)
        self._run_consistency_analysis(name)

    def on_spell_deleted(self, name: str) -> None:
        """Yêu cầu xóa spell."""
        if not name.strip():
            self.ui_wand.append_terminal_text("[ERROR] Invalid spell name for deletion.")
            return

        if is_system_spell(name):
            blocked_message = "[ERROR] STAND BY is a protected system spell and cannot be deleted."
            self.ui_wand.append_terminal_text(blocked_message)
            if hasattr(self.ui_record, "show_protected_spell_warning"):
                self.ui_record.show_protected_spell_warning(canonical_system_spell(name))
            return

        self.data_io_worker.enqueue_delete(name)

    def on_delete_latest_sample(self, spell_name: str) -> None:
        """Yêu cầu xóa mẫu mới nhất của spell."""
        if not spell_name.strip():
            return
        self.data_io_worker.enqueue_delete_latest_sample(spell_name)

    def _on_io_delete_sample_done(self, success: bool, message: str) -> None:
        """Sau khi xóa mẫu xong: re-run consistency nếu đang xem spell đó."""
        current_spell = getattr(self.ui_record, 'current_spell_name', None)
        if success and current_spell:
            self._run_consistency_analysis(current_spell)

    def on_primitive_quality_scan_requested(self) -> None:
        """Start off-thread primitive dataset quality scan.

        Reuses the existing dataset_dir from DataStore. Results are
        streamed line-by-line to PageSetting console_log via signals.
        """
        if self._quality_worker and self._quality_worker.isRunning():
            self.ui_wand.append_terminal_text("[WARN] Quality scan already running.")
            return

        self._quality_worker = PrimitiveQualityWorker(
            dataset_dir=self.store.dataset_dir
        )
        self._quality_worker.sig_report_line.connect(self.ui_setting.append_console_text)
        self._quality_worker.sig_progress.connect(self.ui_setting.update_scan_progress)
        self._quality_worker.sig_finished.connect(self._on_quality_scan_finished)
        if not self._quality_worker.isRunning():
            self._quality_worker.start()

    def on_primitive_quality_scan_stop(self) -> None:
        """Request cooperative cancellation of running quality scan."""
        if self._quality_worker and self._quality_worker.isRunning():
            self._quality_worker.stop()

    def _on_quality_scan_finished(self, success: bool, message: str) -> None:
        """Called when quality scan completes or is stopped."""
        if self.ui_setting:
            self.ui_setting.set_scan_running(False)
            self.ui_setting.append_console_text(
                f"[{'DONE' if success else 'STOPPED'}] {message}"
            )
            if success:
                from config import APP_DATA_DIR
                save_path = APP_DATA_DIR / "embedding_space_scan.png"
                if save_path.exists():
                    self.ui_setting.append_console_text(f"[INFO] Opening visualization plot: {save_path}")
                    import os
                    import platform
                    import subprocess
                    try:
                        if platform.system() == "Windows":
                            os.startfile(str(save_path))
                        elif platform.system() == "Darwin":
                            subprocess.Popen(["open", str(save_path)])
                        else:
                            subprocess.Popen(["xdg-open", str(save_path)])
                    except Exception as e:
                        self.ui_setting.append_console_text(f"[WARN] Could not open image: {e}")
        self._quality_worker = None

    def on_start_collection(self, gesture_name: str, group_name: str) -> None:
        self.on_primitive_collection_start(gesture_name, group_name)

    def on_stop_collection(self) -> None:
        self.on_primitive_collection_stop()

    def on_capture_collection(self, gesture_name: str, group_name: str) -> None:
        self.on_primitive_collection_capture(gesture_name, group_name)

    def on_primitive_collection_start(self, gesture_name: str, group_name: str) -> None:
        connected, _ = self.store.get_connection_state()
        if not connected:
            self.ui_wand.append_terminal_text(
                "[ERROR] Serial connection is required before primitive collection."
            )
            if self.ui_primitive_collect:
                self.ui_primitive_collect.set_collection_state(False)
            return

        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text("[WARN] Recorder is already running.")
            return

        if self._mode == self._MODE_UPDATE:
            self.ui_wand.append_terminal_text(
                "[ERROR] Cannot start primitive collection while update mode is active."
            )
            return

        if not self._transition_mode(
            self._MODE_RECORD,
            reason="primitive collect start",
            push_to_device=True,
        ):
            return

        self._primitive_collect_gesture = str(gesture_name).strip().upper()
        self._primitive_collect_group = str(group_name).strip()
        self._primitive_collect_active = True
        self.store.clear_live_buffer()
        self._primitive_active = True
        self.ui_record.is_live = True
        if self.ui_primitive_collect:
            self.ui_primitive_collect.set_collection_state(True)
            self.ui_primitive_collect.set_capture_ready(False)
            if hasattr(self.ui_primitive_collect, "reset_quality_evaluation"):
                self.ui_primitive_collect.reset_quality_evaluation(collecting=True)
        self.ui_wand.append_terminal_text(
            f">> PRIMITIVE COLLECT STARTED: {self._primitive_collect_gesture} / {self._primitive_collect_group}"
        )

    def on_primitive_collection_stop(self) -> None:
        if not self._primitive_collect_active:
            if self.ui_primitive_collect:
                self.ui_primitive_collect.set_collection_state(False)
                self.ui_primitive_collect.set_capture_ready(False)
            return

        snapshot = self.store.get_live_buffer_snapshot()
        self.ui_record.is_live = False
        self._primitive_collect_active = False
        self._primitive_active = False
        if self.ui_primitive_collect:
            self.ui_primitive_collect.set_collection_state(False)
            if hasattr(self.ui_primitive_collect, "update_quality_assessment"):
                self.ui_primitive_collect.update_quality_assessment(snapshot)
            self.ui_primitive_collect.set_capture_ready(bool(snapshot))

        if not snapshot:
            self.ui_wand.append_terminal_text("[WARN] Primitive buffer is empty after STOP. Capture is disabled.")

        next_mode = self._MODE_INFER if self.serial_worker.isRunning() else self._MODE_IDLE
        self._transition_mode(
            next_mode,
            reason="primitive collect stop",
            push_to_device=True,
        )
        self.ui_wand.append_terminal_text(">> PRIMITIVE COLLECT STOPPED - Ready to capture")

    def on_primitive_collection_capture(self, gesture_name: str, group_name: str) -> None:
        if self._primitive_collect_active:
            self.ui_wand.append_terminal_text("[WARN] Stop primitive collection before capturing.")
            return

        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text("[WARN] Recorder is busy. Stop current recording first.")
            return

        snapshot = self.store.get_live_buffer_snapshot()
        if not snapshot:
            self.ui_wand.append_terminal_text("[WARN] No buffered primitive data to capture.")
            if self.ui_primitive_collect:
                self.ui_primitive_collect.set_capture_ready(False)
            return

        folder_name = self._primitive_folder_name(gesture_name)
        self._pending_save_spell = folder_name
        self._pending_save_context = "primitive"
        self.data_io_worker.enqueue_save(folder_name, snapshot, prefix=group_name)
        self.ui_wand.append_terminal_text(
            f">> Capturing primitive sample: {folder_name}/{group_name} ({len(snapshot)} frames)"
        )

    @staticmethod
    def _primitive_folder_name(gesture_name: str) -> str:
        normalized = str(gesture_name).strip().upper()
        if normalized == "STAND_BY":
            return "STAND BY"
        return normalized

    def _transition_mode(
        self,
        target_mode: str,
        *,
        reason: str,
        push_to_device: bool = False,
    ) -> bool:
        """Validate and apply one explicit runtime mode transition."""
        next_mode = str(target_mode).strip().upper() or self._MODE_IDLE

        with self._mode_lock:
            current_mode = self._mode
            allowed = self._ALLOWED_TRANSITIONS.get(current_mode, {self._MODE_IDLE})
            if next_mode not in allowed:
                self.ui_wand.append_terminal_text(
                    f"[ERROR] Mode transition blocked: {current_mode} -> {next_mode} ({reason})."
                )
                return False
            if current_mode == next_mode:
                return True
            self._mode = next_mode
            self.store.set_current_mode(next_mode)
            self.ui_home.set_mode(next_mode)
            if push_to_device:
                self._send_mode_command_for_state(next_mode)
            log.info("Mode transition complete: %s -> %s (%s)", current_mode, next_mode, reason)
            return True

    def _send_mode_command_for_state(self, runtime_mode: str) -> None:
        """Map runtime mode to device command and send if serial is active."""
        device_mode = self._DEVICE_MODE_BY_RUNTIME.get(runtime_mode)
        if not device_mode or not self.serial_worker.isRunning():
            return
        if not self.serial_worker.send_command(f"CMD:MODE={device_mode}"):
            self.ui_wand.append_terminal_text(
                f"[WARN] Could not send mode command: {device_mode}."
            )

    # ── Consistency Analysis ────────────────────────────────────────────

    _PRIMITIVE_NAMES: frozenset[str] = frozenset([
        "SWIPE_RIGHT", "SWIPE_UP", "THRUST", "CIRCLE_CW",
        "CIRCLE_CCW", "WRIST_FLICK", "ZIGZAG", "STAND_BY", "STAND BY",
        "SWIPE_LEFT", "SWIPE_DOWN", "ROLL_WAND", "SHAKE_VIOLENT", "INFINITY_8", "V_SHAPE",
        "PULL", "YAW_SWISH", "LASSO", "WHEEL", "SQUARE", "U_SHAPE", "WHIP", "TAP", "SPIRAL"
    ])

    def _load_samples_for_analysis(self, spell_name: str, window_size: int = 64) -> list[tuple[str, np.ndarray | None, str | None]]:
        """Đọc và trích xuất window đặc trưng cho từng file mẫu của spell.

        Trả về danh sách tuple (filename, window_array_hoặc_None, error_reason_hoặc_None)
        theo đúng thứ tự file trên đĩa để tránh lệch index trong UI.
        """
        from logic.dataset_layout import storage_dirs_for_spell

        dataset_root = Path(self.store.dataset_dir)
        dirs = storage_dirs_for_spell(dataset_root, spell_name)
        fnames = self.store.get_samples_for_spell(spell_name)

        results: list[tuple[str, np.ndarray | None, str | None]] = []
        for fname in fnames:
            fpath = None
            for d in dirs:
                candidate = d / fname
                if candidate.exists() and candidate.is_file():
                    fpath = candidate
                    break

            if not fpath:
                results.append((fname, None, "File không tồn tại"))
                continue

            rows: list[list[float]] = []
            try:
                with open(fpath, "r", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)  # skip header
                    for line in reader:
                        if len(line) >= 6:
                            try:
                                rows.append([float(v) for v in line[:6]])
                            except ValueError:
                                continue
            except Exception as exc:
                results.append((fname, None, f"Lỗi đọc file: {exc}"))
                continue

            if len(rows) < window_size:
                results.append((fname, None, f"< {window_size} hàng ({len(rows)})"))
                continue

            # Quét tìm window có tổng năng lượng (L1) lớn nhất
            best_window = None
            max_energy = -1.0

            for start_idx in range(0, len(rows) - window_size + 1, 2):
                w_list = rows[start_idx:start_idx + window_size]
                energy = sum(
                    abs(row[0]) + abs(row[1]) + abs(row[2]) +
                    abs(row[3]) + abs(row[4]) + abs(row[5])
                    for row in w_list
                )
                if energy > max_energy:
                    max_energy = energy
                    window = np.asarray(w_list, dtype=np.float32)
                    window[:, 3] /= 125.0
                    window[:, 4] /= 125.0
                    window[:, 5] /= 125.0
                    window = np.clip(window, -2.0, 2.0)
                    best_window = window

            if best_window is not None:
                if float(np.max(np.abs(best_window))) > 20.0:
                    results.append((fname, None, "Dữ liệu raw chưa chuẩn hóa"))
                    continue
                results.append((fname, best_window, None))
            else:
                results.append((fname, None, "Không tìm thấy window hợp lệ"))

        return results

    def _run_consistency_analysis(self, spell_name: str) -> None:
        """Load mẫu, chạy analyze, đẩy kết quả lên UI."""
        if not spell_name:
            return
        # Bỏ qua primitives — không hiển thị consistency cho chúng
        norm = spell_name.replace("_", " ").strip().upper()
        if norm in {n.replace("_", " ") for n in self._PRIMITIVE_NAMES}:
            return

        # Encoder input cố định 64 samples (shape=(None,64,6))
        window_size = 64

        def _do_analysis() -> None:
            entries = self._load_samples_for_analysis(spell_name, window_size)
            n = len(entries)
            if n == 0:
                result = dict(
                    n_samples=0,
                    ready_to_register=False,
                    overall_consistency=None,
                    per_sample_scores=[],
                    per_sample_status={},
                    worst_sample_idx=None,
                    recommendation="",
                )
            elif self.spell_recognizer is None or getattr(self.spell_recognizer, "encoder", None) is None:
                per_status = {fname: r for fname, _, r in entries if r}
                result = dict(
                    n_samples=n,
                    ready_to_register=False,
                    overall_consistency=None,
                    per_sample_scores=[None] * n,
                    per_sample_status=per_status,
                    worst_sample_idx=None,
                    recommendation="⚙️ Encoder chưa được load. Train encoder trước để xem phân tích.",
                )
            else:
                valid_entries = [(idx, fname, w) for idx, (fname, w, r) in enumerate(entries) if w is not None]
                per_scores: list[float | None] = [0.0 if r else None for _, _, r in entries]
                per_status = {fname: r for fname, _, r in entries if r}

                if len(valid_entries) < 3:
                    invalid_indices = [i for i, (_, w, _) in enumerate(entries) if w is None]
                    rec = f"📥 {len(valid_entries)}/3 mẫu hợp lệ — cần thêm {max(0, 3 - len(valid_entries))} mẫu nữa để bắt đầu đánh giá."
                    if invalid_indices:
                        rec += f" (Phát hiện {len(invalid_indices)} mẫu lỗi)"
                    result = dict(
                        n_samples=n,
                        ready_to_register=False,
                        overall_consistency=None,
                        per_sample_scores=per_scores,
                        per_sample_status=per_status,
                        worst_sample_idx=invalid_indices[0] if invalid_indices else None,
                        recommendation=rec,
                    )
                else:
                    valid_samples = [w for _, _, w in valid_entries]
                    sub_result = self.spell_recognizer.analyze_spell_samples(valid_samples)

                    sub_scores = sub_result.get("per_sample_scores", [])
                    for sub_i, (orig_i, _, _) in enumerate(valid_entries):
                        if sub_i < len(sub_scores):
                            per_scores[orig_i] = sub_scores[sub_i]

                    invalid_indices = [i for i, (_, w, _) in enumerate(entries) if w is None]
                    if invalid_indices:
                        worst_orig_idx = invalid_indices[0]
                        rec = f"🔴 Có {len(invalid_indices)} mẫu lỗi/quá ngắn. Xem xét xóa để hoàn thiện dataset."
                    else:
                        worst_valid_idx = sub_result.get("worst_sample_idx")
                        worst_orig_idx = valid_entries[worst_valid_idx][0] if (worst_valid_idx is not None and worst_valid_idx < len(valid_entries)) else None
                        rec = sub_result.get("recommendation", "")

                    result = dict(
                        n_samples=n,
                        ready_to_register=sub_result.get("ready_to_register", False) and not invalid_indices,
                        overall_consistency=sub_result.get("overall_consistency"),
                        per_sample_scores=per_scores,
                        per_sample_status=per_status,
                        worst_sample_idx=worst_orig_idx,
                        recommendation=rec,
                    )

            if hasattr(self.ui_record, 'update_consistency_display'):
                self.ui_record.update_consistency_display(result)

        # Non-blocking: defer to next event loop tick
        QTimer.singleShot(0, _do_analysis)

    def on_register_spell_prototype(self, spell_name: str) -> None:
        """Đăng ký prototype khi user nhấn nút trên UI."""
        if not self.spell_recognizer:
            self.ui_wand.append_terminal_text(
                "[ERROR] Encoder not loaded. Train encoder first."
            )
            return

        # Encoder input cố định 64 samples
        window_size = 64

        samples = self._load_samples_for_analysis(spell_name, window_size)
        if not samples:
            self.ui_wand.append_terminal_text(
                f"[ERROR] No valid samples found for '{spell_name}'."
            )
            return

        try:
            self.spell_recognizer.register_spell(spell_name, samples)
        except Exception as exc:
            self.ui_wand.append_terminal_text(
                f"[ERROR] register_spell failed: {exc}"
            )
            return

        proto_path = APP_DATA_DIR / "spell_prototypes.json"
        self.spell_recognizer.save(str(proto_path))
        n_protos = len(self.spell_recognizer.prototypes)
        self.ui_wand.append_terminal_text(
            f"[PROTO] '{spell_name}' registered. Prototypes saved: {n_protos} spells"
        )

        if hasattr(self.ui_record, 'on_spell_registered'):
            self.ui_record.on_spell_registered(spell_name)

        self.store.refresh_database(force=True)

    # ── IO Save Done ──────────────────────────────────────────────────

    def _on_io_save_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker finishes a save job."""
        saved_spell = self._pending_save_spell
        saved_context = self._pending_save_context
        if success:
            if saved_context == "record":
                self.on_spell_selected(saved_spell)
                if hasattr(self.ui_record, 'set_save_status'):
                    self.ui_record.set_save_status(saved_spell)
            elif saved_context == "primitive" and self.ui_primitive_collect:
                self.ui_primitive_collect.on_capture_saved(True, message)
        elif saved_context == "primitive" and self.ui_primitive_collect:
            self.ui_primitive_collect.on_capture_saved(False, message)
        self._pending_save_context = ""
        self._pending_save_spell = ""

        # Trigger consistency analysis sau khi save thành công
        if success and saved_context == "record" and saved_spell:
            self._run_consistency_analysis(saved_spell)

    def handle_firmware_flash(self, bin_type: str) -> None:
        """Common entry point for flashing firmware binaries."""
        if self.store.get_recording_state():
            if self.ui_setting:
                self.ui_setting.append_console_text("Stop recording before starting firmware flash.")
            return

        connected, port = self.store.get_connection_state()
        if not connected or not port:
            if hasattr(self.ui_wand, "combo_serial_ports"):
                port = self.ui_wand.combo_serial_ports.currentText()
            if not port:
                if self.ui_setting:
                    self.ui_setting.append_console_text("[ERROR] No serial port selected.")
                return

        filename = "collect.bin" if bin_type == "data" else "inference.bin"
        custom_bin_path = FIRMWARE_BIN_DIR / filename
        if custom_bin_path.exists():
            bin_path = custom_bin_path
        else:
            bin_path = Path(resolve_asset_path(f"assets/firmware/{filename}"))

        if not self._validate_required_file(bin_path):
            if self.ui_setting:
                self.ui_setting.append_console_text(f"[ERROR] Firmware binary not found: {bin_path}")
            return

        if self._mode == self._MODE_UPDATE:
            if self.ui_setting:
                self.ui_setting.append_console_text("[ERROR] Flash already in progress.")
            return

        if not self._transition_mode(self._MODE_UPDATE, reason="start flash"):
            return

        if not self._can_use_port("flash", allow_owner="serial"):
            self._transition_mode(self._MODE_IDLE, reason="flash port unavailable")
            return

        if self.ui_setting:
            self.ui_setting.set_flash_buttons_enabled(False)

        self._pending_flash_bin_type = bin_type
        self._pending_flash_port = port
        self._pending_flash_bin_path = bin_path

        if self.serial_worker.isRunning():
            self.serial_worker.finished.connect(self._on_serial_stopped_start_flash)
            self.serial_worker.stop()
        else:
            self._start_flash_immediately()

    def on_flash_data_firmware(self) -> None:
        """Flash data collection firmware."""
        self.handle_firmware_flash("data")

    def on_flash_inference_firmware(self) -> None:
        """Flash inference firmware."""
        self.handle_firmware_flash("inference")

    def _on_serial_stopped_start_flash(self) -> None:
        """Called when SerialWorker stops, starts the firmware flash."""
        try:
            self.serial_worker.finished.disconnect(self._on_serial_stopped_start_flash)
        except TypeError:
            pass
        self._start_flash_immediately()

    def _start_flash_immediately(self) -> None:
        port = self._pending_flash_port
        bin_path = self._pending_flash_bin_path

        if not port or not bin_path:
            self._clear_pending_flash_context()
            self._set_port_owner(None)
            self._set_mode(self._MODE_IDLE)
            if self.ui_setting:
                self.ui_setting.append_console_text("[ERROR] Flash handoff failed: missing pending flash context.")
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        if self.ui_setting:
            self.ui_setting.append_console_text(f">> [START] Flashing {self._pending_flash_bin_type} firmware to {port}...")
            self.ui_setting.update_flash_progress(0)
            self.ui_setting.set_flash_buttons_enabled(False)

        self.flash_worker.flash_firmware(port, str(bin_path))

    def _flash_log_to_console(self, text: str) -> None:
        """Forward flash log messages to setting console."""
        if self.ui_setting:
            self.ui_setting.append_console_text(text)

    def _on_firmware_flash_finished(self, success: bool, message: str) -> None:
        """Called when FlashWorker finishes flashing."""
        self._clear_pending_flash_context()
        self._set_port_owner(None)
        self._set_mode(self._MODE_IDLE)

        if self.ui_setting:
            self.ui_setting.set_flash_buttons_enabled(True)
            if success:
                self.ui_setting.append_console_text(f">> [DONE] Firmware flash COMPLETE: {message}")
                self.ui_setting.update_flash_progress(100)
            else:
                self.ui_setting.append_console_text(f">> [FAIL] Firmware flash FAILED: {message}")
                self.ui_setting.update_flash_progress(0)

    def _clear_pending_flash_context(self) -> None:
        self._pending_flash_bin_type = ""
        self._pending_flash_port = ""
        self._pending_flash_bin_path = None

    def _can_use_port(self, requester: str, allow_owner: str | None = None) -> bool:
        """Arbitrate port access between different subsystems."""
        with self._port_lock:
            if self._port_owner is None or self._port_owner == requester:
                self._port_owner = requester
                return True
            if allow_owner and self._port_owner == allow_owner:
                self._port_owner = requester
                return True
            self.ui_wand.append_terminal_text(f"[ERROR] Port is busy with {self._port_owner}.")
            return False

    @staticmethod
    def _validate_required_file(path: str | Path | None) -> bool:
        """Check if file path exists."""
        if not path:
            return False
        import os
        return os.path.exists(str(path))

    def on_train_encoder_requested(self, preset: str = "original") -> None:
        log.debug("on_train_encoder_requested CALLED with preset=%s", preset)
        try:
            import tensorflow as tf  # Fix: import in main thread to avoid QThread crash
            from .tensorflow.pipeline import GestureModelBuildWorker
            log.debug("GestureModelBuildWorker imported successfully")
            
            self.encoder_trainer = GestureModelBuildWorker(
                dataset_dir=self.store.dataset_dir,
                force_retrain=True,
                preset=preset
            )
            log.debug("GestureModelBuildWorker initialized")
            if self.ui_primitive_collect:
                self.encoder_trainer.sig_status.connect(self.ui_primitive_collect.on_encoder_training_status)
                self.encoder_trainer.sig_progress.connect(self.ui_primitive_collect.on_encoder_training_progress)
            self.encoder_trainer.sig_finished.connect(self._on_encoder_training_finished)
            log.debug("Starting encoder_trainer")
            if not self.encoder_trainer.isRunning():
                self.encoder_trainer.start()
        except Exception as e:
            log.error("ERROR in on_train_encoder_requested: %s", e)

    def _on_encoder_training_finished(self, success: bool, message: str) -> None:
        if success:
            self._start_async_encoder_load()
            # Refresh consistency display for whichever spell is open so the
            # "Encoder chưa được load" message is replaced immediately —
            # without this the user has to back-out and re-select the spell.
            if self.spell_recognizer is not None:
                current_spell = getattr(self.ui_record, 'current_spell_name', None)
                if current_spell:
                    self._run_consistency_analysis(current_spell)
        if self.ui_primitive_collect:
            self.ui_primitive_collect.on_encoder_training_finished(success, message)


    def on_settings_saved(self, config: dict) -> None:
        """Called when settings are saved - update runtime components.

        Note: DataStore persistence is handled by MainWindow._on_settings_saved.
        This method updates only the live worker state.
        """
        dataset_dir = config.get("dataset_dir")
        if dataset_dir:
            self.recorder.dataset_dir = dataset_dir
            self.data_io_worker.dataset_dir = dataset_dir

        # Propagate updated IMU scale profile to serial worker immediately
        self.serial_worker.set_scale_profile(build_scale_profile(config))

    def shutdown(self) -> None:
        """Dừng toàn bộ hệ thống an toàn không gây nghẽn GUI."""
        if getattr(self, '_shutdown_done', False):
            return
        self._shutdown_done = True
        if hasattr(self, '_feature_timer') and self._feature_timer:
            self._feature_timer.stop()

        for worker in (
            getattr(self, "serial_worker", None),
            getattr(self, "recorder", None),
            getattr(self, "data_io_worker", None),
            getattr(self, "feature_worker", None),
            getattr(self, "_quality_worker", None),
        ):
            if worker is not None:
                try:
                    worker.stop()
                except Exception:
                    pass

        for async_worker_name in ("_nvs_build_worker", "_encoder_worker", "_model_build_worker"):
            w = getattr(self, async_worker_name, None)
            if w is not None and w.isRunning():
                try:
                    w.requestInterruption()
                    w.wait(100)
                    if w.isRunning():
                        w.terminate()
                except Exception:
                    pass

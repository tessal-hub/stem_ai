"""
logic/handler.py — Bộ điều phối trung tâm (MVC Controller).

Trách nhiệm:
    - Kết nối signal từ các Worker nền tới các trang giao diện UI.
    - Điều phối luồng dữ liệu cảm biến thời gian thực.
    - Quản lý quá trình ghi mẫu, huấn luyện mô hình và nạp firmware.
    - Đảm bảo các tiến trình chạy không đồng bộ (non-blocking).
"""

from __future__ import annotations

import logging
from threading import Lock

from PyQt6.QtCore import QObject, Qt, QTimer

from config import APP_DATA_DIR, WORKSPACE_ROOT
from constants import is_system_spell, canonical_system_spell
from ui.asset_utils import resolve_asset_path
from pathlib import Path


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

log = logging.getLogger(__name__)


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
        self.data_io_worker.start()

        self.feature_worker = FeatureWorker()
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
        self._try_load_encoder()
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

        if hasattr(self, 'on_delete_latest_sample'):
            self.ui_record.sig_delete_latest_sample.connect(self.on_delete_latest_sample)
        if hasattr(self, 'on_clear_buffer'):
            self.ui_record.sig_clear_buffer.connect(self.on_clear_buffer)
        if hasattr(self, 'on_export_csv'):
            self.ui_record.sig_export_csv.connect(self.on_export_csv)

        if hasattr(self, 'on_build_tflite'):
            self.ui_wand.sig_train_build_tflite_requested.connect(self.on_build_tflite)
        if hasattr(self, 'on_build_cc'):
            self.ui_wand.sig_train_build_cc_requested.connect(self.on_build_cc)

        if hasattr(self, 'on_settings_saved'):
            self.ui_setting.sig_settings_saved.connect(self.on_settings_saved)
        if hasattr(self, 'on_clear_database'):
            self.ui_setting.sig_clear_database.connect(self.on_clear_database)
        if hasattr(self, 'on_flash_data_firmware'):
            self.ui_setting.sig_flash_data_firmware.connect(self.on_flash_data_firmware)
        if hasattr(self, 'on_flash_inference_firmware'):
            self.ui_setting.sig_flash_inference_firmware.connect(self.on_flash_inference_firmware)
        
        if self.ui_setting:
            if hasattr(self.ui_setting, 'sig_scan_primitive_quality'):
                self.ui_setting.sig_scan_primitive_quality.connect(self.on_primitive_quality_scan_requested)
            if hasattr(self.ui_setting, 'sig_stop_primitive_scan'):
                self.ui_setting.sig_stop_primitive_scan.connect(self.on_primitive_quality_scan_stop)

        if self.ui_primitive_collect:
            if hasattr(self, 'on_start_collection'):
                self.ui_primitive_collect.sig_start_collection.connect(self.on_start_collection)
            if hasattr(self, 'on_stop_collection'):
                self.ui_primitive_collect.sig_stop_collection.connect(self.on_stop_collection)
            if hasattr(self, 'on_capture_collection'):
                self.ui_primitive_collect.sig_capture_collection.connect(self.on_capture_collection)
            if hasattr(self, 'on_train_encoder_requested'):
                self.ui_primitive_collect.sig_train_encoder_requested.connect(self.on_train_encoder_requested)

    def _connect_worker_signals(self) -> None:
        """Kết nối tín hiệu từ các worker nền."""
        self.serial_worker.sig_data_received.connect(self._on_serial_frame, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_connection_status.connect(
            self._on_serial_status, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_raw_line_received.connect(
            self.ui_wand.append_terminal_text, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_prediction_received.connect(
            self.store.update_prediction, type=Qt.ConnectionType.QueuedConnection)

        self.data_io_worker.sig_save_done.connect(self._on_io_done)
        self.data_io_worker.sig_queue_warning.connect(
            self.ui_wand.append_terminal_text, type=Qt.ConnectionType.QueuedConnection)
        self.feature_worker.sig_features_ready.connect(self.store.update_live_features)

        # Uploader signals
        self.uploader.status_msg.connect(self.ui_wand.append_terminal_text)
        self.uploader.sig_progress.connect(self.ui_wand.update_flash_progress)
        self.uploader.sig_finished.connect(self._on_upload_finished)

        # Flash worker signals
        self.flash_worker.log_msg.connect(self._flash_log_to_console)
        self.flash_worker.sig_progress.connect(self.ui_setting.update_flash_progress)
        self.flash_worker.sig_finished.connect(self._on_firmware_flash_finished)

    def _connect_store_signals(self) -> None:
        """Kết nối tín hiệu từ kho dữ liệu."""
        self.store.sig_db_updated.connect(self._on_db_refreshed)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)

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
        if self.recorder.start_recording(spell):
            self.store.clear_live_buffer()
            self.ui_record.is_live = True
            self._set_mode(self._MODE_RECORD)

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
            self.data_io_worker.enqueue_save(spell, data)

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

    def on_build_tflite(self, spell_names: list[str]) -> None:
        """Kích hoạt tiến trình xây dựng mô hình .tflite."""
        self._start_model_build(spell_names, mode="tflite")

    def on_build_cc(self, spell_names: list[str]) -> None:
        """Kích hoạt tiến trình xây dựng mô hình .cc (C++ Header)."""
        self._start_model_build(spell_names, mode="cc")

    def _start_model_build(self, spell_names: list[str], mode: str) -> None:
        """Khởi tạo worker huấn luyện mô hình."""
        if self._model_build_worker and self._model_build_worker.isRunning():
            self.ui_wand.append_terminal_text(">> [ERROR] Build already in progress.")
            return

        self.ui_wand.append_terminal_text(f">> [START] Building model ({mode})...")
        self.ui_wand.update_flash_progress(0, "Initializing...")

        self._model_build_worker = GestureModelBuildWorker(
            dataset_dir=self.store.dataset_dir,
            output_mode=mode,
            selected_spells=spell_names
        )
        self._model_build_worker.sig_status.connect(self.ui_wand.append_terminal_text)
        self._model_build_worker.sig_progress.connect(self.ui_wand.update_flash_progress)
        self._model_build_worker.sig_finished.connect(self._on_model_build_finished)
        self._model_build_worker.start()

    def _on_model_build_finished(self, success: bool, msg: str) -> None:
        """Xử lý sau khi kết thúc huấn luyện."""
        if success:
            self.ui_wand.append_terminal_text(f">> [DONE] Build success: {msg}")
            self.ui_wand.update_flash_progress(100, "Success")
        else:
            self.ui_wand.append_terminal_text(f">> [FAIL] Build failed: {msg}")
            self.ui_wand.update_flash_progress(0, "Failed")

    def _on_serial_frame(self, values: list[float]) -> None:
        """Xử lý một khung dữ liệu sensor từ Serial."""
        if len(values) < 6:
            return

        # 1. Cập nhật 3D Dashboard
        self.ui_home.wand_3d.update_orientation(*values)

        # 2. Đẩy vào DataStore
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
        if not connected:
            self._set_mode(self._MODE_IDLE)
            with self._port_lock:
                self._port_owner = None

    def _on_feature_timer_tick(self) -> None:
        """Kích hoạt trích xuất đặc trưng định kỳ."""
        snapshot = self.store.get_live_buffer_snapshot()
        if snapshot:
            self.feature_worker.enqueue(snapshot)

    def _on_serial_stopped(self) -> None:
        """Dọn dẹp sau khi luồng Serial dừng hẳn."""
        self.serial_worker.finished.disconnect(self._on_serial_stopped)
        with self._port_lock:
            self._port_owner = None
        self.serial_worker = SerialWorker()
        self._connect_signals()

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

    def _try_load_encoder(self) -> None:
        """Nạp mô hình mã hóa cử chỉ nếu có sẵn."""
        path = APP_DATA_DIR / "gesture_encoder.keras"
        proto_path = APP_DATA_DIR / "spell_prototypes.json"
        
        if path.exists():
            try:
                import tensorflow as tf
                encoder = tf.keras.models.load_model(str(path), compile=False)
                self.spell_recognizer = PrototypicalRecognizer(encoder)
                
                if proto_path.exists():
                    self.spell_recognizer.load(str(proto_path))
                log.info(f"Loaded encoder and {len(self.spell_recognizer.prototypes) if self.spell_recognizer else 0} prototypes.")
            except Exception as e:
                log.error(f"Failed to load encoder: {e}")

    def _on_db_refreshed(self, counts: dict) -> None:
        """Cập nhật dữ liệu từ DB vào các trang UI."""
        self.ui_record.load_spell_list(counts)
        self.ui_wand.load_spell_payload_list(counts)

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
        if not os.path.exists(model_path):
            self.ui_wand.append_terminal_text(f"[ERROR] Model file not found: {model_path}")
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

        self.ui_wand.append_terminal_text(f">> [START] Uploading model to {port}...")
        self.ui_wand.update_flash_progress(0, "Uploading...")
        self.uploader.upload_file(port, path)

    def _on_upload_finished(self, success: bool, message: str) -> None:
        """Called when ModelUploader finishes uploading."""
        self._clear_pending_upload_context()
        self._set_port_owner(None)
        self._set_mode(self._MODE_IDLE)

        if success:
            self.ui_wand.append_terminal_text(f">> [DONE] Model upload COMPLETE: {message}")
            self.ui_wand.update_flash_progress(100, "Success")
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
        self.data_io_worker.enqueue_save(folder_name, snapshot)
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

    def _on_io_save_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker finishes a save job."""
        if success:
            if self._pending_save_context == "record":
                self.ui_record.set_save_status(self._pending_save_spell)
            elif self._pending_save_context == "primitive" and self.ui_primitive_collect:
                self.ui_primitive_collect.on_capture_saved(True, message)
        elif self._pending_save_context == "primitive" and self.ui_primitive_collect:
            self.ui_primitive_collect.on_capture_saved(False, message)
        self._pending_save_context = ""
        self._pending_save_spell = ""

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
        bin_path = Path(resolve_asset_path(f"assets/firmware/{filename}"))

        if not self._validate_required_file(bin_path):
            if self.ui_setting:
                self.ui_setting.append_console_text(f"[ERROR] Firmware binary not found: {bin_path}")
            return

        if not self._transition_mode(self._MODE_UPDATE, reason="start flash"):
            return

        if not self._can_use_port("flash", allow_owner="serial"):
            return

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

    def on_train_encoder_requested(self) -> None:
        log.debug("on_train_encoder_requested CALLED")
        try:
            from .encoder_trainer import EncoderTrainerWorker
            log.debug("EncoderTrainerWorker imported successfully")
            
            primitive_names = [
                "SWIPE_RIGHT", "SWIPE_UP", "THRUST",
                "CIRCLE_CW", "CIRCLE_CCW", "WRIST_FLICK",
                "ZIGZAG", "STAND_BY"
            ]
            
            self.encoder_trainer = EncoderTrainerWorker(
                dataset_dir=self.store.dataset_dir,
                primitive_names=primitive_names
            )
            log.debug("EncoderTrainerWorker initialized")
            if self.ui_primitive_collect:
                self.encoder_trainer.sig_status.connect(self.ui_primitive_collect.on_encoder_training_status)
                self.encoder_trainer.sig_progress.connect(self.ui_primitive_collect.on_encoder_training_progress)
            self.encoder_trainer.sig_finished.connect(self._on_encoder_training_finished)
            log.debug("Starting encoder_trainer")
            self.encoder_trainer.start()
        except Exception as e:
            log.error("ERROR in on_train_encoder_requested: %s", e)

    def _on_encoder_training_finished(self, success: bool, message: str) -> None:
        if success:
            self._try_load_encoder()
        if self.ui_primitive_collect:
            self.ui_primitive_collect.on_encoder_training_finished(success, message)

    def on_settings_saved(self, config: dict) -> None:
        """Called when settings are saved to update components."""
        dataset_dir = config.get("dataset_dir")
        if dataset_dir:
            self.recorder.dataset_dir = dataset_dir
            self.data_io_worker.dataset_dir = dataset_dir

    def shutdown(self) -> None:
        """Dừng toàn bộ hệ thống an toàn."""
        if getattr(self, '_shutdown_done', False):
            return
        self._shutdown_done = True
        self._feature_timer.stop()
        self.serial_worker.stop()
        self.recorder.stop()
        self.data_io_worker.stop()
        self.feature_worker.stop()
        if self._quality_worker and self._quality_worker.isRunning():
            self._quality_worker.stop()

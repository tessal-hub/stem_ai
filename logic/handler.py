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
import shutil
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from config import APP_DATA_DIR, DEFAULT_MODEL_PATH, GESTURE_MODEL_CC_OUTPUT, WORKSPACE_ROOT
from constants import canonical_system_spell, is_system_spell
from .data_io_worker import DataIOWorker
from .data_store import DataStore
from .encoder_trainer import EncoderTrainerWorker
from .feature_worker import FeatureWorker
from .firmware_main_generator import sync_firmware_sources
from .flash_worker import FlashWorker
from .frame_protocol import build_scale_profile
from .model_uploader import ModelUploader
from .prototypical_recognizer import PrototypicalRecognizer
from .recorder import DataRecorder
from .serial_worker import SerialWorker
from .tensorflow.pipeline import GestureModelBuildWorker


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
        
        self._feature_timer = QTimer(self)
        self._feature_timer.setInterval(200)
        self._feature_timer.timeout.connect(self._on_feature_timer_tick)
        
        self.spell_recognizer: PrototypicalRecognizer | None = None
        self._model_build_worker: GestureModelBuildWorker | None = None
        self._primitive_active = False

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
        
        if hasattr(self, 'on_delete_latest_sample'): self.ui_record.sig_delete_latest_sample.connect(self.on_delete_latest_sample)
        if hasattr(self, 'on_clear_buffer'): self.ui_record.sig_clear_buffer.connect(self.on_clear_buffer)
        if hasattr(self, 'on_export_csv'): self.ui_record.sig_export_csv.connect(self.on_export_csv)
        
        if hasattr(self, 'on_build_tflite'): self.ui_wand.sig_train_build_tflite_requested.connect(self.on_build_tflite)
        if hasattr(self, 'on_build_cc'): self.ui_wand.sig_train_build_cc_requested.connect(self.on_build_cc)
        
        if hasattr(self, 'on_settings_saved'): self.ui_setting.sig_settings_saved.connect(self.on_settings_saved)
        if hasattr(self, 'on_clear_database'): self.ui_setting.sig_clear_database.connect(self.on_clear_database)
        if hasattr(self, 'on_flash_data_firmware'): self.ui_setting.sig_flash_data_firmware.connect(self.on_flash_data_firmware)
        if hasattr(self, 'on_flash_inference_firmware'): self.ui_setting.sig_flash_inference_firmware.connect(self.on_flash_inference_firmware)
        
        if hasattr(self, 'on_start_collection'): self.ui_primitive_collect.sig_start_collection.connect(self.on_start_collection)
        if hasattr(self, 'on_stop_collection'): self.ui_primitive_collect.sig_stop_collection.connect(self.on_stop_collection)
        if hasattr(self, 'on_capture_collection'): self.ui_primitive_collect.sig_capture_collection.connect(self.on_capture_collection)

    def _connect_worker_signals(self) -> None:
        """Kết nối tín hiệu từ các worker nền."""
        self.serial_worker.sig_data_received.connect(self._on_serial_frame, type=Qt.ConnectionType.QueuedConnection)
        self.serial_worker.sig_connection_status.connect(self._on_serial_status, type=Qt.ConnectionType.QueuedConnection)
        
        self.data_io_worker.sig_save_done.connect(self._on_io_done)
        self.feature_worker.sig_features_ready.connect(self.store.update_live_features)

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
        if not port: return
        with self._port_lock:
            if self._port_owner and self._port_owner != "serial": return
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
        if not spell.strip() or self.store.get_recording_state(): return
        if self.recorder.start_recording(spell):
            self.store.clear_live_buffer()
            self.ui_record.is_live = True
            self._set_mode(self._MODE_RECORD)

    def on_record_stop(self) -> None:
        """Dừng quá trình ghi mẫu."""
        self.recorder.stop_recording()
        self.ui_record.is_live = False
        self._set_mode(self._MODE_INFER)

    def on_data_cropped(self, data: list, spell: str) -> None:
        """Gửi yêu cầu lưu dữ liệu đã cắt vào dataset."""
        if data and spell.strip():
            self.data_io_worker.enqueue_save(spell, data)

    # ── Internal Slots ──────────────────────────

    def _on_serial_frame(self, values: list[float]) -> None:
        """Xử lý một khung dữ liệu sensor từ Serial."""
        if len(values) < 6: return
        
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
            with self._port_lock: self._port_owner = None

    def _on_feature_timer_tick(self) -> None:
        """Kích hoạt trích xuất đặc trưng định kỳ."""
        snapshot = self.store.get_live_buffer_snapshot()
        if snapshot: self.feature_worker.enqueue(snapshot)

    def _on_serial_stopped(self) -> None:
        """Dọn dẹp sau khi luồng Serial dừng hẳn."""
        self.serial_worker.finished.disconnect(self._on_serial_stopped)
        with self._port_lock: self._port_owner = None
        self.serial_worker = SerialWorker()
        self._connect_signals()

    # ── Private methods ─────────────────────────

    def _set_mode(self, mode: str) -> None:
        """Chuyển đổi chế độ hoạt động an toàn."""
        with self._mode_lock:
            self._mode = mode
            self.store.set_current_mode(mode)
            self.ui_home.set_mode(mode)

    def _try_load_encoder(self) -> None:
        """Nạp mô hình mã hóa cử chỉ nếu có sẵn."""
        path = APP_DATA_DIR / "gesture_encoder.keras"
        if path.exists():
            # Logic nạp model (giản lược)
            pass

    def _on_db_refreshed(self, counts: dict) -> None:
        """Cập nhật dữ liệu từ DB vào các trang UI."""
        self.ui_record.load_spell_list(counts)
        self.ui_wand.load_spell_payload_list(counts)

    def _on_io_done(self, success: bool, msg: str) -> None:
        """Phản hồi sau khi thao tác I/O hoàn tất."""
        if success: self.ui_wand.append_terminal_text(f">> Success: {msg}")

    def on_flash_upload(self) -> None:
        """Khởi động nạp model TFLite (giản lược)."""
        pass

    def on_spell_selected(self, name: str) -> None:
        """Khi một spell được chọn từ thư viện."""
        samples = self.store.get_samples_for_spell(name)
        self.ui_record.load_samples_for_spell(name, samples)

    def on_spell_deleted(self, name: str) -> None:
        """Yêu cầu xóa spell."""
        if not is_system_spell(name):
            self.data_io_worker.enqueue_delete(name)

    def shutdown(self) -> None:
        """Dừng toàn bộ hệ thống an toàn."""
        self._feature_timer.stop()
        self.serial_worker.stop()
        self.recorder.stop()
        self.data_io_worker.stop()
        self.feature_worker.stop()

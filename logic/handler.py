"""
logic/handler.py — Centralized handler coordinating DataStore, Workers, and UI signals.

Architecture (MVC Controller):
    - Wires SerialWorker signals → UI pages (no direct coupling)
    - Manages rolling buffer for PageRecord plot timeline
    - Routes real-time 3D orientation updates to Wand3DWidget
    - Coordinates recording, flashing, uploading, and data cropping
    - All threads and signals are non-blocking

Data Flow:
    1. SerialWorker.sig_data_received(list) -> Handler._on_data_received
       → Wand3DWidget.update_orientation (3D animation)
    
    2. SerialWorker.sig_data_received(list) -> Handler._on_raw_data_received
       → rolling buffer → PageRecord.update_plot_data (graph plotting)
"""

from pathlib import Path
import logging
import shutil
from datetime import datetime
from threading import Lock

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtWidgets import QFileDialog
from config import APP_DATA_DIR, DEFAULT_MODEL_PATH, GESTURE_MODEL_CC_OUTPUT, WORKSPACE_ROOT
from constants import canonical_system_spell, is_system_spell
from .data_store import DataStore
from .frame_protocol import build_scale_profile
from .firmware_main_generator import sync_firmware_sources
from .serial_worker import SerialWorker
from .model_uploader import ModelUploader
from .recorder import DataRecorder
from .flash_worker import FlashWorker
from .data_io_worker import DataIOWorker
from .feature_worker import FeatureWorker
from .tensorflow.pipeline import GestureModelBuildWorker
from .encoder_trainer import EncoderTrainerWorker
from .prototypical_recognizer import PrototypicalRecognizer


class Handler(QObject):
    """Central controller: wires Workers → UI pages via signals."""

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
        ui_page_statistics=None,
        ui_primitive_collect=None,
    ) -> None:
        super().__init__()
        self.ui_wand = ui_page_wand          # Hardware config, stats, terminal
        self.ui_record = ui_page_record      # Recording, plotting, snipping
        self.ui_home = ui_page_home          # Dashboard with 3D wand
        self.ui_setting = ui_page_setting    # Firmware flashing UI
        self.ui_statistics = ui_page_statistics
        self.ui_primitive_collect = ui_primitive_collect
        self.store = data_store

        # ── Background Workers ──────────────────────────────────────────
        self.serial_worker = SerialWorker()
        self.uploader = ModelUploader()
        self.recorder = DataRecorder(dataset_dir=self.store.dataset_dir)
        self.flash_worker = FlashWorker()
        self.data_io_worker = DataIOWorker(dataset_dir=self.store.dataset_dir)
        self.data_io_worker.start()
        self.feature_worker = FeatureWorker()
        self.feature_worker.start()

        # ── State Management ────────────────────────────────────────────
        self.current_selected_spell: str = ""
        self._pending_save_spell: str = ""
        self._pending_save_context: str = ""
        self._pending_flash_bin_type: str = ""
        self._pending_flash_port: str = ""
        self._pending_flash_bin_path = None
        self._pending_upload_port: str = ""
        self._pending_upload_model_path = None
        self._port_owner: str | None = None
        self._port_lock = Lock()
        self._mode_lock = Lock()
        self._mode = self.store.get_current_mode().strip().upper()
        if self._mode not in self._ALLOWED_TRANSITIONS:
            self._mode = self._MODE_IDLE
            self.store.set_current_mode(self._mode)
        self._project_root = Path(__file__).resolve().parents[1]
        self._feature_timer = QTimer(self)
        self._feature_timer.setInterval(200)
        self._feature_timer.timeout.connect(self._emit_live_features)
        self._model_build_worker: GestureModelBuildWorker | None = None
        self._model_build_mode: str = "both"
        self._shutdown_done: bool = False
        self.encoder_trainer: EncoderTrainerWorker | None = None
        self.spell_recognizer: PrototypicalRecognizer | None = None
        self._primitive_collect_gesture: str = ""
        self._primitive_collect_group: str = ""
        self._primitive_collect_active: bool = False

        # ── Initialize connections ──────────────────────────────────────
        self._connect_signals()
        self._try_load_existing_encoder()
        self.on_serial_scan()
        self.ui_home.set_mode(self._mode)
        self._feature_timer.start()

    @staticmethod
    def _primitive_folder_name(gesture_name: str) -> str:
        normalized = str(gesture_name).strip().upper()
        if normalized == "STAND_BY":
            return "STAND BY"
        return normalized

    def _try_load_existing_encoder(self) -> None:
        encoder_path = APP_DATA_DIR / "gesture_encoder.keras"
        prototypes_path = APP_DATA_DIR / "spell_prototypes.json"
        if not encoder_path.exists():
            self.ui_wand.append_terminal_text("[ENCODER] No existing gesture encoder found.")
            return

        try:
            import tensorflow as tf

            encoder = tf.keras.models.load_model(str(encoder_path), compile=False)
            self.spell_recognizer = PrototypicalRecognizer(encoder=encoder)
            self.ui_wand.append_terminal_text(f"[ENCODER] Loaded encoder: {encoder_path}")

            if prototypes_path.exists():
                self.spell_recognizer.load(str(prototypes_path))
                self.ui_wand.append_terminal_text(
                    f"[ENCODER] Loaded spell prototypes: {prototypes_path}"
                )
        except Exception as exc:
            self.spell_recognizer = None
            self.ui_wand.append_terminal_text(
                f"[ENCODER] Failed to load encoder/prototypes: {type(exc).__name__}: {exc}"
            )

    def _can_use_port(self, requester: str, *, allow_owner: str | None = None) -> bool:
        """Atomically claim serial-port ownership for *requester*.

        Returns True when the caller can proceed and ownership has been claimed
        (or was already owned by the same requester). Optionally allows takeover
        from one specific owner (used when flash/upload intentionally pause serial).
        """
        with self._port_lock:
            current_owner = self._port_owner
            if (
                current_owner is None
                or current_owner == requester
                or (allow_owner is not None and current_owner == allow_owner)
            ):
                self._port_owner = requester
                return True

        self.ui_wand.append_terminal_text(
            f"[ERROR] Port is busy with {current_owner}."
        )
        return False

    def _set_port_owner(self, owner: str | None) -> None:
        """Track which subsystem currently owns the serial port."""
        with self._port_lock:
            self._port_owner = owner

    def _get_port_owner(self) -> str | None:
        """Read current serial-port owner under lock."""
        with self._port_lock:
            return self._port_owner

    def _connect_queued(self, signal, slot) -> None:
        """Connect one signal-slot pair with Qt queued connection semantics."""
        signal.connect(slot, type=Qt.ConnectionType.QueuedConnection)

    def _connect_many_queued(self, bindings: list[tuple]) -> None:
        """Connect multiple signal-slot pairs using queued semantics."""
        for signal, slot in bindings:
            self._connect_queued(signal, slot)

    def _disconnect_serial_finished(self, slot) -> None:
        """Best-effort disconnect for temporary serial finished callbacks."""
        try:
            self.serial_worker.finished.disconnect(slot)
        except (RuntimeError, TypeError) as exc:
            logging.getLogger(__name__).debug(
                "serial finished callback already disconnected (%s)", exc
            )

    def _clear_pending_flash_context(self) -> None:
        self._pending_flash_bin_type = ""
        self._pending_flash_port = ""
        self._pending_flash_bin_path = None

    def _clear_pending_upload_context(self) -> None:
        self._pending_upload_port = ""
        self._pending_upload_model_path = None

    def _configure_serial_scale_profile(self) -> None:
        """Apply accel/gyro normalization profile from persisted settings."""
        settings = self.store.get_settings_snapshot()
        self.serial_worker.set_scale_profile(build_scale_profile(settings))

    def _send_mode_command_for_state(self, runtime_mode: str) -> None:
        """Map runtime mode to device command and send if serial is active."""
        device_mode = self._DEVICE_MODE_BY_RUNTIME.get(runtime_mode)
        if not device_mode or not self.serial_worker.isRunning():
            return
        if not self.serial_worker.send_command(f"CMD:MODE={device_mode}"):
            self.ui_wand.append_terminal_text(
                f"[WARN] Could not send mode command: {device_mode}."
            )

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
        self.ui_wand.append_terminal_text(
            f">> MODE {current_mode} -> {next_mode} ({reason})"
        )

        if push_to_device:
            self._send_mode_command_for_state(next_mode)

        return True

    def _resolve_project_path(self, raw_path: str) -> Path:
        """Resolve an absolute file path from a project-relative setting value."""
        candidate = Path(raw_path.strip())
        if not candidate.is_absolute():
            app_data_candidate = (APP_DATA_DIR / candidate).resolve()
            if app_data_candidate.exists():
                return app_data_candidate
            candidate = self._project_root / candidate
        return candidate.resolve()

    @staticmethod
    def _validate_required_file(file_path: Path, *, label: str) -> tuple[bool, str]:
        """Validate that a required file exists, is regular, and non-empty."""
        try:
            if not file_path.exists():
                return False, f"{label} file not found: {file_path}"
            if not file_path.is_file():
                return False, f"{label} path is not a file: {file_path}"
            if file_path.stat().st_size <= 0:
                return False, f"{label} file is empty: {file_path}"
        except OSError as exc:
            return False, f"{label} file check failed: {exc}"
        return True, ""

    @staticmethod
    def _parse_sensor_frame_6d(
        norm_values,
    ) -> "tuple[float, float, float, float, float, float] | None":
        """Unpack and validate a 6-element sensor frame.

        Returns ``(ax, ay, az, gx, gy, gz)`` as floats, or ``None`` if the
        input is not a 6-element sequence of numeric values.
        """
        if not isinstance(norm_values, (list, tuple)) or len(norm_values) != 6:
            return None
        try:
            return tuple(float(v) for v in norm_values)
        except (TypeError, ValueError):
            return None

    def _log_io_result(self, operation: str, success: bool, message: str) -> None:
        """Log the outcome of an off-thread I/O operation to the terminal."""
        if success:
            self.ui_wand.append_terminal_text(f">> {operation}: {message}")
        else:
            self.ui_wand.append_terminal_text(f"[ERROR] {operation} failed: {message}")

    # ── Signal Wiring (MVC Controller Pattern) ──────────────────────────

    def _connect_signals(self) -> None:
        """Wire all component signals for non-blocking MVC architecture."""
        self._connect_ui_action_signals()
        self._connect_signals_serial_worker()
        self._connect_store_and_home_signals()
        self._connect_worker_output_signals()

    def _connect_ui_action_signals(self) -> None:
        """Wire user-action signals from all UI pages to handler slots."""
        # UI Wand → Handler
        self.ui_wand.sig_serial_scan.connect(self.on_serial_scan)
        self.ui_wand.sig_serial_connect.connect(self.on_serial_connect)
        self.ui_wand.sig_serial_disconnect.connect(self.on_serial_disconnect)
        self.ui_wand.sig_flash_upload.connect(self.on_flash_upload)
        self.ui_wand.sig_train_build_tflite_requested.connect(self.on_train_build_tflite_requested)
        self.ui_wand.sig_train_build_cc_requested.connect(self.on_train_build_cc_requested)
        self.ui_wand.sig_train_build_requested.connect(self.on_train_build_model_requested)

        # UI Setting → Handler (firmware flashing)
        if self.ui_setting:
            self.ui_setting.sig_flash_data_firmware.connect(
                lambda: self.handle_firmware_flash("data")
            )
            self.ui_setting.sig_flash_inference_firmware.connect(
                lambda: self.handle_firmware_flash("inference")
            )

        # UI Record → Handler (recording & data cropping)
        self.ui_record.sig_data_cropped.connect(self.on_data_cropped)
        self.ui_record.sig_spell_selected.connect(self.on_spell_selected)
        self.ui_record.sig_spell_deleted.connect(self.on_spell_deleted)
        delete_latest_signal = getattr(self.ui_record, "sig_delete_latest_sample", None)
        if delete_latest_signal is not None:
            delete_latest_signal.connect(self.on_delete_latest_sample)
        self.ui_record.sig_start_record.connect(self.on_record_start)
        self.ui_record.sig_stop_record.connect(self.on_record_stop)
        self.ui_record.sig_clear_buffer.connect(self.on_clear_buffer)
        self.ui_record.sig_export_csv.connect(self.on_export_csv)

        # UI Statistics → Handler (optional)
        if self.ui_statistics:
            self.ui_statistics.sig_train_build_requested.connect(self.on_train_build_model_requested)

        if self.ui_primitive_collect:
            self.ui_primitive_collect.sig_start_collection.connect(
                self.on_primitive_collection_start
            )
            self.ui_primitive_collect.sig_stop_collection.connect(
                self.on_primitive_collection_stop
            )
            self.ui_primitive_collect.sig_capture_collection.connect(
                self.on_primitive_collection_capture
            )
            self.ui_primitive_collect.sig_train_encoder_requested.connect(
                self.on_train_encoder_requested
            )

    def _connect_store_and_home_signals(self) -> None:
        """Wire DataStore state-update signals and Home page interaction signals."""
        # DataStore → UI (state updates)
        self.store.sig_db_updated.connect(self._on_db_updated)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)
        self.store.sig_prediction_updated.connect(self._on_prediction_received)
        self.store.sig_live_buffer_updated.connect(self.ui_record.update_plot_data)
        if self.ui_primitive_collect:
            self.store.sig_primitive_stats_updated.connect(
                self.ui_primitive_collect.update_collection_stats
            )

    def _connect_worker_output_signals(self) -> None:
        """Wire background-worker output signals to UI/handler slots (all queued for thread safety)."""
        # Model Uploader → UI/Handler
        self._connect_many_queued(
            [
                (self.uploader.sig_progress, self.ui_wand.update_flash_progress),
                (self.uploader.status_msg, self.ui_wand.append_terminal_text),
                (self.uploader.sig_error, self.ui_wand.append_terminal_text),
                (self.uploader.sig_finished, self._on_upload_finished),
            ]
        )

        # Flash Worker → UI/Handler
        if self.ui_setting:
            self._connect_many_queued(
                [
                    (self.flash_worker.log_msg, self.ui_setting.append_console_text),
                    (self.flash_worker.sig_progress, self.ui_setting.update_flash_progress),
                    (self.flash_worker.sig_error, self.ui_setting.append_console_text),
                    (self.flash_worker.sig_finished, self._on_firmware_flash_finished),
                ]
            )

        # Data Recorder → UI
        self._connect_many_queued(
            [
                (self.recorder.sig_record_count, self.ui_record.update_record_count),
                (self.recorder.sig_status_text, self.ui_wand.append_terminal_text),
                (self.recorder.sig_error, self.ui_wand.append_terminal_text),
                (self.recorder.sig_finished, self._on_recording_finished),
                (self.recorder.sig_recording_state, self.ui_record.set_recording_state),
                (self.recorder.sig_recording_state, self._on_recorder_state_changed),
            ]
        )
        # DataIOWorker → Handler/UI (off-thread file I/O results)
        self._connect_many_queued(
            [
                (self.data_io_worker.sig_save_done, self._on_io_save_done),
                (self.data_io_worker.sig_delete_done, self._on_io_delete_done),
                (self.data_io_worker.sig_delete_sample_done, self._on_io_delete_sample_done),
                (self.data_io_worker.sig_export_done, self._on_io_export_done),
                (self.data_io_worker.sig_db_refreshed, self.store.apply_db_refresh),
                (self.data_io_worker.sig_queue_warning, self._on_io_queue_warning),
            ]
        )

        # FeatureWorker → DataStore (off-thread FFT / stat features)
        self._connect_queued(
            self.feature_worker.sig_features_ready,
            self.store.update_live_features,
        )

    def _connect_signals_serial_worker(self) -> None:
        """
        Wire SerialWorker signals with QueuedConnection.
        Called during init and after reconnect to rebuild connections.
        
        CRITICAL FIX: Use QueuedConnection to marshal slot calls
        from SerialWorker's QThread back to the main Qt event loop.
        This is essential for thread-safe UI updates (pyqtgraph, OpenGL).
        """
        # KEY: fan-in all high-frequency frame handling into one queued slot.
        # This keeps cross-thread dispatch at one callback/frame while preserving
        # the same downstream behavior (3D update, sensor buffers, live buffer,
        # and recorder ingestion).
        self._connect_queued(self.serial_worker.sig_data_received, self._on_serial_data_received)

        # Raw UART line logging for terminal visibility
        self._connect_queued(self.serial_worker.sig_raw_line_received, self.ui_wand.append_terminal_text)

        # AI predictions
        self._connect_queued(self.serial_worker.sig_prediction_received, self.store.update_prediction)

        # Connection status
        self._connect_queued(self.serial_worker.sig_connection_status, self._on_connection_status_changed)
        self._connect_queued(self.serial_worker.sig_error, self.ui_wand.append_terminal_text)

    def _on_serial_data_received(self, norm_values: list[float]) -> None:
        """Route one normalized frame through all standard data paths."""
        self._on_data_received(norm_values)
        self._on_sensor_frame_received(norm_values)
        self._on_raw_data_received(norm_values)
        self.recorder.add_row(norm_values)

    # ── Serial Connection Actions ───────────────────────────────────────

    def on_serial_scan(self) -> None:
        """Scan available UART ports and update UI."""
        ports = SerialWorker.get_available_ports()
        self.ui_wand.update_serial_port_list(ports)
        self.ui_wand.append_terminal_text(f">> Scanned {len(ports)} UART port(s).")

    def on_serial_connect(self, port: str) -> None:
        """Start serial worker on the selected port."""
        if not port:
            self.ui_wand.append_terminal_text("[ERROR] Select a port first.")
            return

        if not self._can_use_port("serial"):
            return

        # SAFETY: Prevent double-start (can't restart a finished QThread)
        if self.serial_worker.isRunning():
            self.ui_wand.append_terminal_text("[ERROR] Serial already connected. Disconnect first.")
            return

        self.ui_wand.append_terminal_text(f">> Connecting to {port} @ 115200 baud...")
        self._configure_serial_scale_profile()
        self.serial_worker.port = port
        try:
            self.serial_worker.start()
        except Exception as exc:
            self._set_port_owner(None)
            self.ui_wand.append_terminal_text(
                f"[ERROR] Failed to start serial worker: {type(exc).__name__}: {exc}"
            )

    def on_serial_disconnect(self) -> None:
        """Stop serial worker and prepare for restart (non-blocking).

        Uses a deferred callback connected to the worker's ``finished`` signal
        so the UI thread is never blocked waiting for the thread to exit.
        """
        if self.serial_worker.isRunning():
            # One-shot: finish teardown once the worker thread has actually exited.
            self.serial_worker.finished.connect(self._on_serial_worker_stopped_for_disconnect)
            self.serial_worker.stop()
        else:
            self._on_serial_worker_stopped_for_disconnect()

    def _on_serial_worker_stopped_for_disconnect(self) -> None:
        """Complete serial disconnect after the worker thread finishes."""
        try:
            self.serial_worker.finished.disconnect(self._on_serial_worker_stopped_for_disconnect)
        except (RuntimeError, TypeError) as exc:
            logging.getLogger(__name__).debug(
                "serial disconnect: signal already disconnected (%s)", exc
            )

        self.ui_wand.append_terminal_text(">> Serial connection stopped")
        # CRITICAL FIX: Recreate SerialWorker so it can be started again
        # (Can't call start() on a finished QThread - must create new instance)
        self.serial_worker = SerialWorker()
        self._connect_signals_serial_worker()  # Rewire signals to new instance
        if self._get_port_owner() == "serial":
            self._set_port_owner(None)

        if self._mode != self._MODE_UPDATE:
            self._transition_mode(self._MODE_IDLE, reason="manual disconnect")

        self.ui_wand.append_terminal_text(">> Ready to reconnect")

    # ── Data Reception (Main Data Flow) ─────────────────────────────────

    def _on_data_received(self, norm_values: list[float]) -> None:
        """
        Route normalized sensor data to 3D wand animation.
        
        Called immediately on every serial data frame (50 Hz).
        Updates Wand3DWidget with real-time orientation.
        
        Args:
            norm_values: [ax, ay, az, gx, gy, gz] normalized sensor readings
        """
        frame = self._parse_sensor_frame_6d(norm_values)
        if frame is None:
            return
        ax, ay, az, gx, gy, gz = frame
        try:
            # Update 3D wand orientation (PageHome)
            self.ui_home.wand_3d.update_orientation(ax, ay, az, gx, gy, gz)
        except Exception as e:
            self.ui_wand.append_terminal_text(f"[ERROR] 3D wand update failed: {e}")

    def _on_sensor_frame_received(self, norm_values: list[float]) -> None:
        """Mirror normalized sensor samples into DataStore sensor buffers."""
        frame = self._parse_sensor_frame_6d(norm_values)
        if frame is None:
            return
        ax, ay, az, gx, gy, gz = frame
        self.store.update_sensor_data(
            {"ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz}
        )

    def _on_sensor_data_updated(self, sensor_buffers: dict) -> None:
        """Receive updated sensor buffer data from DataStore."""
        # Currently not used in UI, but available for future sensor value display
        pass

    def _on_raw_data_received(self, norm_values: list[float]) -> None:
        """Route sensor samples into DataStore rolling live buffer for PageRecord.

        Only buffers when PageRecord is in live mode (is_live=True); the buffer
        freezes on STOP so crop/snip operations have a stable snapshot.

        Args:
            norm_values: [ax, ay, az, gx, gy, gz] normalized sensor readings
        """
        if not self.ui_record.is_live:
            return
        if self._parse_sensor_frame_6d(norm_values) is None:
            return
        try:
            self.store.add_live_sample(list(norm_values))
        except Exception as e:
            self.ui_wand.append_terminal_text(f"[ERROR] Buffer update failed: {e}")

    def _emit_live_features(self) -> None:
        """Enqueue the current live buffer snapshot for off-thread feature extraction.

        The actual FFT and statistical computation runs in FeatureWorker to keep
        the Qt event loop free.  Results arrive back in the main thread via
        ``sig_features_ready`` → ``store.update_live_features``.
        """
        snapshot = self.store.get_live_buffer_snapshot()
        if not snapshot:
            return
        self.feature_worker.set_sample_rate(self._get_sample_rate_hz())
        self.feature_worker.enqueue(snapshot)

    def _get_sample_rate_hz(self) -> int:
        settings = self.store.get_settings_snapshot()
        raw_rate = str(settings.get("sample_rate", "50"))
        digits = "".join(ch for ch in raw_rate if ch.isdigit())
        try:
            return max(1, int(digits))
        except ValueError:
            return 50

    def _on_prediction_received(self, label: str, confidence: float) -> None:
        """Log AI inference result to terminal."""
        text = f"[PREDICT] {label} ({confidence*100:.1f}%)"
        self.ui_wand.append_terminal_text(text)

    def _on_connection_status_changed(self, connected: bool, message: str) -> None:
        """Update UI components on serial connection status change."""
        self.ui_wand.set_serial_status(connected, self.serial_worker.port if connected else "")
        self.ui_record.set_wand_ready(connected)
        self.store.set_connection_status(connected, self.serial_worker.port if connected else "None")
        self.ui_wand.append_terminal_text(f">> {message}")

        if connected:
            self._configure_serial_scale_profile()
            if self._mode != self._MODE_UPDATE:
                self._transition_mode(
                    self._MODE_INFER,
                    reason="serial connected",
                    push_to_device=True,
                )
            return
        
        if self._primitive_collect_active:
            self._primitive_collect_active = False
            self.ui_record.is_live = False
            if self.ui_primitive_collect:
                self.ui_primitive_collect.set_collection_state(False)
                self.ui_primitive_collect.set_capture_ready(False)

        # Clear buffer on disconnect
        self.store.clear_live_buffer()
        if self._get_port_owner() == "serial":
            self._set_port_owner(None)
        if self._mode != self._MODE_UPDATE:
            self._transition_mode(self._MODE_IDLE, reason="serial disconnected")

    # ── Recording Actions ──────────────────────────────────────────────

    def on_record_start(self, label_name: str) -> None:
        """Start recording with the given spell/action label."""
        if self._primitive_collect_active:
            self.ui_wand.append_terminal_text(
                "[WARN] Stop primitive collection before starting regular recording."
            )
            return

        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text(">> Already recording")
            return

        if not label_name.strip():
            self.ui_wand.append_terminal_text(">> Record label is required")
            return

        connected, _ = self.store.get_connection_state()
        if not connected:
            self.ui_wand.append_terminal_text("[ERROR] Serial connection is required before recording.")
            return

        if self._mode == self._MODE_UPDATE:
            self.ui_wand.append_terminal_text("[ERROR] Cannot start recording while update mode is active.")
            return

        if not self._transition_mode(
            self._MODE_RECORD,
            reason="record start",
            push_to_device=True,
        ):
            return

        # Start CSV recorder
        success = self.recorder.start_recording(label_name)
        if success:
            # Clear buffer when starting new recording
            self.store.clear_live_buffer()
            self.ui_record.is_live = True
            self.ui_wand.append_terminal_text(f">> RECORDING: {label_name}")
        else:
            self.ui_wand.append_terminal_text(">> RECORD FAILED")
            self._transition_mode(
                self._MODE_INFER,
                reason="record start failed",
                push_to_device=True,
            )

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

    def on_train_encoder_requested(self) -> None:
        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text(
                "[ERROR] Stop recording before training encoder."
            )
            return

        if self.encoder_trainer and self.encoder_trainer.isRunning():
            self.ui_wand.append_terminal_text("[WARN] Encoder training is already running.")
            return

        primitive_names = [
            "SWIPE_RIGHT",
            "SWIPE_UP",
            "THRUST",
            "CIRCLE_CW",
            "CIRCLE_CCW",
            "WRIST_FLICK",
            "ZIGZAG",
            "STAND BY",
        ]
        self.encoder_trainer = EncoderTrainerWorker(
            dataset_dir=self.store.dataset_dir,
            primitive_names=primitive_names,
            window_size=64,
            epochs=50,
            embedding_dim=32,
            n_triplets=10_000,
        )
        connections = [
            (self.encoder_trainer.sig_status, self.ui_wand.append_terminal_text),
            (self.encoder_trainer.sig_error, self.ui_wand.append_terminal_text),
            (self.encoder_trainer.sig_finished, self._on_encoder_training_finished),
        ]
        if self.ui_primitive_collect:
            connections.extend(
                [
                    (
                        self.encoder_trainer.sig_status,
                        self.ui_primitive_collect.on_encoder_training_status,
                    ),
                    (
                        self.encoder_trainer.sig_progress,
                        self.ui_primitive_collect.on_encoder_training_progress,
                    ),
                    (
                        self.encoder_trainer.sig_finished,
                        self.ui_primitive_collect.on_encoder_training_finished,
                    ),
                ]
            )
        self._connect_many_queued(connections)
        self.ui_wand.append_terminal_text(">> Starting encoder training...")
        self.encoder_trainer.start()

    def _on_encoder_training_finished(self, success: bool, message: str) -> None:
        self.ui_wand.append_terminal_text(
            f"[ENCODER] Training {'SUCCESS' if success else 'FAILED'}: {message}"
        )
        if success:
            self._try_load_existing_encoder()
        self.encoder_trainer = None

    def on_record_stop(self) -> None:
        """Stop recording and finalize CSV file."""
        if not self.store.get_recording_state():
            self.ui_wand.append_terminal_text(">> Not currently recording")
            return
        
        # Stop recorder
        self.recorder.stop_recording()
        
        # Freeze buffer for crop/snip operations
        self.ui_record.is_live = False

        next_mode = self._MODE_INFER if self.serial_worker.isRunning() else self._MODE_IDLE
        self._transition_mode(
            next_mode,
            reason="record stop",
            push_to_device=True,
        )
        
        self.ui_wand.append_terminal_text(">> RECORD STOPPED - Ready to snip")

    def on_spell_selected(self, spell_name: str) -> None:
        """Handle spell selection from library."""
        self.current_selected_spell = spell_name
        samples = self.store.get_samples_for_spell(spell_name)
        self.ui_record.load_samples_for_spell(spell_name, samples)

    def on_data_cropped(self, cropped_data: list, spell_name: str) -> None:
        """Enqueue cropped data sample save to background DataIOWorker."""
        if not spell_name.strip():
            self.ui_wand.append_terminal_text("[WARN] Missing spell label. Snip discarded.")
            return

        # Optimistic UI feedback; actual confirmation arrives via sig_save_done.
        display_spell = canonical_system_spell(spell_name)
        self.ui_wand.append_terminal_text(
            f">> Saving {len(cropped_data)} samples → {display_spell}..."
        )
        self._pending_save_spell = display_spell
        self._pending_save_context = "record"
        self.data_io_worker.enqueue_save(display_spell, cropped_data)

    def _on_io_save_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker finishes a save job."""
        if success:
            if self._pending_save_context == "record":
                self.ui_record.set_save_status(self._pending_save_spell)
            elif self._pending_save_context == "primitive" and self.ui_primitive_collect:
                self.ui_primitive_collect.on_capture_saved(True, message)
        elif self._pending_save_context == "primitive" and self.ui_primitive_collect:
            self.ui_primitive_collect.on_capture_saved(False, message)
        self._log_io_result("SAVED", success, message)
        self._pending_save_spell = ""
        self._pending_save_context = ""

    def on_spell_deleted(self, spell_name: str) -> None:
        """Enqueue spell deletion to background DataIOWorker."""
        if not spell_name.strip():
            self.ui_wand.append_terminal_text("[ERROR] Invalid spell name for deletion.")
            return

        if is_system_spell(spell_name):
            blocked_message = "[ERROR] STAND BY is a protected system spell and cannot be deleted."
            self.ui_wand.append_terminal_text(blocked_message)
            if hasattr(self.ui_record, "show_protected_spell_warning"):
                self.ui_record.show_protected_spell_warning(canonical_system_spell(spell_name))
            return

        if self.current_selected_spell == spell_name:
            self.current_selected_spell = ""

        self.data_io_worker.enqueue_delete(spell_name)

    def on_delete_latest_sample(self, spell_name: str) -> None:
        """Enqueue quick deletion of the latest sample for the given spell."""
        normalized = canonical_system_spell(spell_name)
        if not normalized.strip():
            self.ui_wand.append_terminal_text("[ERROR] Select a spell before deleting a sample.")
            if hasattr(self.ui_record, "set_quick_delete_feedback"):
                self.ui_record.set_quick_delete_feedback(False, "Select a spell first")
            return

        self.current_selected_spell = normalized
        self.data_io_worker.enqueue_delete_latest_sample(normalized)

    def _on_io_delete_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker finishes a delete job."""
        self._log_io_result("DELETED", success, message)

    def _on_io_delete_sample_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker deletes one latest sample."""
        self._log_io_result("SAMPLE DELETE", success, message)
        if hasattr(self.ui_record, "set_quick_delete_feedback"):
            self.ui_record.set_quick_delete_feedback(success, message)

    def _on_io_export_done(self, success: bool, message: str) -> None:
        """Called in the main thread when DataIOWorker finishes an export job."""
        self._log_io_result("EXPORT", success, message)

    def _on_io_queue_warning(self, message: str) -> None:
        """Surface DataIOWorker backpressure drops to the UI terminal."""
        self.ui_wand.append_terminal_text(f"[WARN] {message}")

    # ── Firmware Flash Actions ─────────────────────────────────────────

    def handle_firmware_flash(self, bin_type: str) -> None:
        """
        Initiate firmware flashing for the specified binary type.

        Args:
            bin_type: Either "data" (collect.bin) or "inference" (inference.bin)
        """
        # Get port from UI wand
        port = self.ui_wand.combo_serial_ports.currentText() if self.ui_wand else None
        if not port:
            self._flash_log_to_console("[ERROR] No serial port selected. Please select a port first.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        if self.flash_worker.isRunning():
            self._flash_log_to_console("[ERROR] Flash is already running.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        if self.store.get_recording_state():
            self._flash_log_to_console("[ERROR] Stop recording before starting firmware flash.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Map bin_type to firmware file path
        bin_map = {
            "data": self._project_root / "assets" / "firmware" / "collect.bin",
            "inference": self._project_root / "assets" / "firmware" / "inference.bin",
        }

        bin_path = bin_map.get(bin_type)
        if not bin_path:
            self._flash_log_to_console(f"[ERROR] Unknown firmware type: {bin_type}")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        valid_file, validation_message = self._validate_required_file(
            bin_path,
            label=f"{bin_type} firmware",
        )
        if not valid_file:
            self._flash_log_to_console(f"[ERROR] {validation_message}")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        if not self._can_use_port("flash", allow_owner="serial"):
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Must release the COM port before flashing.  Stop the serial worker and
        # defer the actual flash start to a callback that fires once the worker
        # thread has fully exited (non-blocking — avoids stalling the UI thread).
        if self.serial_worker.isRunning():
            self._flash_log_to_console(">> Stopping serial connection to release COM port...")
            # Store args for the deferred callback, then connect the named slot
            # so it can be disconnected by reference (no lambdas).
            self._pending_flash_bin_type = bin_type
            self._pending_flash_port = port
            self._pending_flash_bin_path = bin_path
            self.serial_worker.finished.connect(self._on_serial_stopped_start_flash)
            self.serial_worker.stop()
        else:
            self._start_flash_immediately(bin_type, port, bin_path)

    def _on_serial_stopped_start_flash(self) -> None:
        """Callback: serial worker has exited — now safe to open COM port for flashing."""
        self._disconnect_serial_finished(self._on_serial_stopped_start_flash)
        pending_bin_type = str(self._pending_flash_bin_type).strip()
        pending_port = str(self._pending_flash_port).strip()
        pending_bin_path = self._pending_flash_bin_path
        self._clear_pending_flash_context()

        if not pending_bin_type or not pending_port or pending_bin_path is None:
            self._set_port_owner(None)
            self._flash_log_to_console("[ERROR] Flash handoff failed: missing pending flash context.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        if self._get_port_owner() == "serial":
            self._set_port_owner(None)
        self._flash_log_to_console(">> COM port released, ready to flash\n")
        self._start_flash_immediately(
            pending_bin_type,
            pending_port,
            pending_bin_path,
        )

    def _start_flash_immediately(self, bin_type: str, port: str, bin_path) -> None:
        """Start the flash worker — called once the COM port is free."""
        if not self._transition_mode(
            self._MODE_UPDATE,
            reason=f"{bin_type} firmware flash",
        ):
            self._set_port_owner(None)
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        self._flash_log_to_console(f"\n{'='*60}")
        self._flash_log_to_console(f"[INFO] Begin flashing {bin_type.upper()} firmware to {port}")
        self._flash_log_to_console(f"{'='*60}\n")

        # Start the flash worker
        self._set_port_owner("flash")
        self.store.save_settings({"firmware_mode": bin_type})
        self.flash_worker.flash_firmware(port, str(bin_path))

    def _flash_log_to_console(self, message: str) -> None:
        """Route flash logging to the UI console."""
        if self.ui_setting:
            self.ui_setting.append_console_text(message)

    def on_flash_upload(self) -> None:
        """Stop serial stream and start binary model upload."""
        port = self.ui_wand.combo_serial_ports.currentText()
        if not port:
            self.ui_wand.append_terminal_text("[ERROR] Serial port required for upload.")
            return

        if self.uploader.isRunning():
            self.ui_wand.append_terminal_text("[ERROR] Upload is already running.")
            return

        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text("[ERROR] Stop recording before model upload.")
            return

        settings_snapshot = self.store.get_settings_snapshot()
        configured_model_path = str(settings_snapshot.get("model_path", str(DEFAULT_MODEL_PATH))).strip()
        if not configured_model_path or configured_model_path == "model.tflite":
            configured_model_path = str(DEFAULT_MODEL_PATH)
        model_path = self._resolve_project_path(configured_model_path)

        valid_model, model_validation_message = self._validate_required_file(
            model_path,
            label="Model",
        )
        if not valid_model:
            self.ui_wand.append_terminal_text(f"[ERROR] {model_validation_message}")
            self.ui_wand.update_flash_progress(0)
            return

        if not self._can_use_port("upload", allow_owner="serial"):
            return

        # Stop serial if running — defer upload start until the worker thread
        # has fully exited so both operations don't race on the same COM port.
        if self.serial_worker.isRunning():
            self.ui_wand.append_terminal_text(">> Temporarily pausing live data for upload...")
            # Store args for the deferred callback, then connect the named slot
            # so it can be disconnected by reference (no lambdas).
            self._pending_upload_port = port
            self._pending_upload_model_path = model_path
            self.serial_worker.finished.connect(self._on_serial_stopped_start_upload)
            self.serial_worker.stop()
        else:
            self._start_upload_immediately(port, model_path)

    def _on_serial_stopped_start_upload(self) -> None:
        """Callback: serial worker has exited — now safe to open COM port for upload."""
        self._disconnect_serial_finished(self._on_serial_stopped_start_upload)
        pending_port = str(self._pending_upload_port).strip()
        pending_model_path = self._pending_upload_model_path
        self._clear_pending_upload_context()

        if not pending_port or pending_model_path is None:
            self._set_port_owner(None)
            self.ui_wand.append_terminal_text("[ERROR] Upload handoff failed: missing pending upload context.")
            self.ui_wand.update_flash_progress(0)
            return

        if self._get_port_owner() == "serial":
            self._set_port_owner(None)
        self._start_upload_immediately(
            pending_port,
            pending_model_path,
        )

    def _start_upload_immediately(self, port: str, model_path) -> None:
        """Begin the model upload — called once the COM port is free."""
        if not self._transition_mode(
            self._MODE_UPDATE,
            reason="model upload",
        ):
            self._set_port_owner(None)
            return

        self.ui_wand.append_terminal_text(f">> Initiating model upload for {model_path}...")
        self._set_port_owner("upload")
        self.uploader.upload_file(port, str(model_path))

    def _on_upload_finished(self, success: bool, message: str) -> None:
        """Callback when model upload completes."""
        if self._get_port_owner() == "upload":
            self._set_port_owner(None)
        self._transition_mode(self._MODE_IDLE, reason="model upload finished")
        if success:
            self.ui_wand.append_terminal_text(">> Model upload COMPLETE!")
            self.ui_wand.update_flash_progress(100)
        else:
            self.ui_wand.append_terminal_text(f">> Model upload FAILED. {message}")
            self.ui_wand.update_flash_progress(0)

    def _on_recorder_state_changed(self, recording: bool) -> None:
        """Keep DataStore recording flag synchronized with recorder worker state."""
        self.store.set_recording_state(recording)

    def _on_recording_finished(self, success: bool, message: str) -> None:
        """Log recorder lifecycle completion messages."""
        if not success:
            self.ui_wand.append_terminal_text(f">> RECORD FAILED: {message}")
            target_mode = self._MODE_INFER if self.serial_worker.isRunning() else self._MODE_IDLE
            self._transition_mode(
                target_mode,
                reason="recording failed",
                push_to_device=True,
            )

    def _on_firmware_flash_finished(self, success: bool, message: str) -> None:
        """Callback when firmware flash completes."""
        if self._get_port_owner() == "flash":
            self._set_port_owner(None)
        self._transition_mode(self._MODE_IDLE, reason="firmware flash finished")
        if success:
            self._flash_log_to_console(f"\n[SUCCESS] {message}")
            self._flash_log_to_console(f"{'='*60}\n")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
        else:
            self._flash_log_to_console(f"\n[FAILED] {message}")
            self._flash_log_to_console(f"{'='*60}\n")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)

    # ── Lifecycle Cleanup ───────────────────────────────────────────────

    def shutdown(self) -> None:
        """Stop timers and background workers for clean application exit.

        This method is idempotent and safe to call from multiple shutdown paths
        (for example: ``QApplication.aboutToQuit`` and ``MainWindow.closeEvent``).
        """
        if self._shutdown_done:
            return
        self._shutdown_done = True

        # Stop periodic timers first to prevent new work from being enqueued.
        if self._feature_timer.isActive():
            self._feature_timer.stop()

        # Stop serial stream and recorder ingestion before stopping workers.
        try:
            if self.serial_worker.isRunning():
                self.serial_worker.stop()
                self.serial_worker.wait(2000)
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: serial stop failed: %s", exc)

        try:
            self.recorder.stop()
            if self.recorder.isRunning():
                self.recorder.wait(2000)
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: recorder stop failed: %s", exc)

        # Stop long-lived worker threads.
        try:
            self.data_io_worker.stop()
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: data I/O worker stop failed: %s", exc)

        try:
            self.feature_worker.stop()
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: feature worker stop failed: %s", exc)

        # Stop transient workers if currently active.
        try:
            self.flash_worker.stop()
            if self.flash_worker.isRunning():
                self.flash_worker.wait(2000)
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: flash worker stop failed: %s", exc)

        try:
            self.uploader.stop()
            if self.uploader.isRunning():
                self.uploader.wait(2000)
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: uploader stop failed: %s", exc)

        # Build worker has no cooperative cancel hook yet; best-effort wait.
        try:
            if self._model_build_worker and self._model_build_worker.isRunning():
                self._model_build_worker.requestInterruption()
                self._model_build_worker.wait(500)
        except Exception as exc:
            logging.getLogger(__name__).warning("Handler shutdown: model build worker wait failed: %s", exc)

        self._set_port_owner(None)

    # ── Database Callbacks ─────────────────────────────────────────────

    def _on_db_updated(self, spell_counts: dict) -> None:
        """Relay database changes to UI pages."""
        self.ui_record.load_spell_list(spell_counts)
        self.ui_wand.load_spell_payload_list(spell_counts)
        if self.ui_statistics:
            self.ui_statistics.update_spell_stats(spell_counts)
        
        # If currently selecting a spell on Record page, refresh its sample list
        if self.current_selected_spell:
            samples = self.store.get_samples_for_spell(self.current_selected_spell)
            self.ui_record.load_samples_for_spell(self.current_selected_spell, samples)

    def on_train_build_tflite_requested(self, selected_spells: list[str]) -> None:
        """Build only .tflite model from currently selected spells."""
        self._start_model_build(output_mode="tflite", selected_spells=selected_spells)

    def on_train_build_cc_requested(self, selected_spells: list[str]) -> None:
        """Build .cc model payload from currently selected spells."""
        self._start_model_build(output_mode="cc", selected_spells=selected_spells)

    def on_train_build_model_requested(self) -> None:
        """Legacy trigger for statistics page: build both .tflite and .cc artifacts."""
        self._start_model_build(output_mode="both", selected_spells=[])

    def _start_model_build(self, *, output_mode: str, selected_spells: list[str]) -> None:
        """Start asynchronous model build pipeline for requested output mode."""
        if self._model_build_worker and self._model_build_worker.isRunning():
            self.ui_wand.append_terminal_text("[WARN] Model build is already running.")
            return

        if self.store.get_recording_state():
            self.ui_wand.append_terminal_text("[ERROR] Stop recording before training/building model.")
            if self.ui_statistics:
                self.ui_statistics.set_training_finished(False, "recording is active")
            return

        normalized_spells = [s.strip() for s in selected_spells if str(s).strip()]
        self._model_build_mode = output_mode
        self._model_build_worker = GestureModelBuildWorker(
            dataset_dir=self.store.dataset_dir,
            output_mode=output_mode,
            selected_spells=normalized_spells,
        )
        self._connect_many_queued(
            [
                (self._model_build_worker.sig_status, self._on_model_build_status),
                (self._model_build_worker.sig_progress, self._on_model_build_progress),
                (self._model_build_worker.sig_finished, self._on_model_build_finished),
            ]
        )

        if self.ui_statistics:
            self.ui_statistics.set_training_state(True)

        selected_summary = (
            ", ".join(normalized_spells) if normalized_spells else "ALL SPELLS"
        )
        self.ui_wand.append_terminal_text(
            f">> Starting model build ({output_mode}) from dataset: {self.store.dataset_dir} | spells: {selected_summary}"
        )
        self._model_build_worker.start()

    def _on_model_build_status(self, message: str) -> None:
        self.ui_wand.append_terminal_text(message)
        if self.ui_statistics:
            self.ui_statistics.update_training_status(message)

    def _on_model_build_progress(self, value: int) -> None:
        if self.ui_statistics:
            self.ui_statistics.update_training_progress(value)

    def _on_model_build_finished(self, success: bool, message: str) -> None:
        if success:
            self.ui_wand.append_terminal_text(f"[MODEL] Build success: {message}")
            self.store.save_settings({"model_path": str(DEFAULT_MODEL_PATH)})

            build_result = self._model_build_worker.build_result if self._model_build_worker else None
            settings = self.store.get_settings_snapshot()
            idf_main_dir = str(settings.get("idf_main_dir", "")).strip()
            should_sync_firmware = self._model_build_mode in {"cc", "both"}

            if not should_sync_firmware:
                self.ui_wand.append_terminal_text(
                    "[MODEL] TFLite-only build selected. Skipping firmware source synchronization."
                )

            if should_sync_firmware and not idf_main_dir:
                self.ui_wand.append_terminal_text("[MODEL] IDF main directory is not configured. Skip firmware sync.")
            elif should_sync_firmware and not build_result:
                self.ui_wand.append_terminal_text("[MODEL] Build result metadata missing. Skip firmware sync.")
            elif should_sync_firmware:
                cc_source = Path(build_result.cc_path)
                template_path = WORKSPACE_ROOT / "assets" / "firmware" / "main.cpp.template"
                try:
                    sync = sync_firmware_sources(
                        idf_main_dir=Path(idf_main_dir),
                        generated_cc_path=cc_source,
                        class_names=list(build_result.classes),
                        template_path=template_path,
                    )
                    if sync.backup_path:
                        self.ui_wand.append_terminal_text(f"[MODEL] Backup main.cpp: {sync.backup_path}")
                    self.ui_wand.append_terminal_text(f"[MODEL] Synced gesture_model.cc: {sync.gesture_cc_path}")
                    self.ui_wand.append_terminal_text(
                        f"[MODEL] Generated main.cpp ({sync.class_count} classes): {sync.main_cpp_path}"
                    )
                except Exception as exc:
                    self.ui_wand.append_terminal_text(f"[MODEL] Firmware sync failed: {exc}")
        else:
            self.ui_wand.append_terminal_text(f"[MODEL] Build failed: {message}")

        if self.ui_statistics:
            self.ui_statistics.set_training_finished(success, message)

    def _prompt_save_cc_output(self) -> None:
        """Prompt for where to persist converted .cc file after successful build."""
        source_cc = Path(GESTURE_MODEL_CC_OUTPUT)
        valid_cc, reason = self._validate_required_file(source_cc, label="Model .cc")
        if not valid_cc:
            self.ui_wand.append_terminal_text(f"[MODEL] Could not open save dialog: {reason}")
            return

        selected_path, _ = QFileDialog.getSaveFileName(
            self.ui_wand,
            "Save Converted .cc File",
            str(GESTURE_MODEL_CC_OUTPUT),
            "C++ Source (*.cc);;All Files (*)",
        )
        if not selected_path:
            self.ui_wand.append_terminal_text("[MODEL] Save .cc cancelled by user.")
            return

        target = Path(selected_path)
        if not target.suffix:
            target = target.with_suffix(".cc")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.resolve() != source_cc.resolve():
                shutil.copyfile(source_cc, target)
            self.ui_wand.append_terminal_text(f"[MODEL] .cc saved to: {target}")
        except OSError as exc:
            self.ui_wand.append_terminal_text(f"[MODEL] Failed to save .cc: {exc}")

    # ── Data Export & Clearing ─────────────────────────────────────────

    def on_clear_buffer(self) -> None:
        """Clear the live recording buffer."""
        self.store.clear_live_buffer()
        self.ui_wand.append_terminal_text("[REC] Recording buffer cleared")
        self.ui_record.lbl_record_count.setText("0")

    def on_export_csv(self) -> None:
        """Enqueue export of the current live buffer to a CSV file (non-blocking)."""
        buf = self.store.get_live_buffer_snapshot()
        if not buf:
            self.ui_wand.append_terminal_text("[EXPORT] No samples to export")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"export_{timestamp}.csv"
        csv_path = str(Path(self.store.dataset_dir) / csv_filename)

        self.ui_wand.append_terminal_text(f"[EXPORT] Exporting {len(buf)} samples to {csv_filename}...")
        self.data_io_worker.enqueue_export(buf, csv_path)

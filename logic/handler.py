"""
logic/handler.py — Centralized handler coordinating DataStore, Workers, and UI signals.

Architecture (MVC Controller):
    - Wires SerialWorker signals → UI pages (no direct coupling)
    - Manages rolling buffer for PageRecord plot timeline
    - Routes real-time 3D orientation updates to Wand3DWidget
    - Coordinates recording, flashing, uploading, and data cropping
    - All threads and signals are non-blocking

Data Flow:
    1. SerialWorker.sig_data_received(list) → Handler._on_data_received 
       → Wand3DWidget.update_orientation (3D animation)
    
    2. SerialWorker.sig_data_received(list) → Handler._on_raw_data_received 
       → rolling buffer → PageRecord.update_plot_data (graph plotting)
"""

import os
from PyQt6.QtCore import QObject, Qt
from .data_store import DataStore
from .serial_worker import SerialWorker
from .model_uploader import ModelUploader
from .recorder import DataRecorder
from .flash_worker import FlashWorker


class Handler(QObject):
    """Central controller: wires Workers → UI pages via signals."""

    def __init__(self, ui_page_wand, ui_page_record, ui_page_home, data_store: DataStore, ui_page_setting=None) -> None:
        super().__init__()
        self.ui_wand = ui_page_wand          # Hardware config, stats, terminal
        self.ui_record = ui_page_record      # Recording, plotting, snipping
        self.ui_home = ui_page_home          # Dashboard with 3D wand
        self.ui_setting = ui_page_setting    # Firmware flashing UI
        self.store = data_store

        # ── Background Workers ──────────────────────────────────────────
        self.serial_worker = SerialWorker()
        self.uploader = ModelUploader()
        self.recorder = DataRecorder()
        self.flash_worker = FlashWorker()

        # ── State Management ────────────────────────────────────────────
        self.current_selected_spell: str = ""
        self.is_recording: bool = False
        
        # Rolling buffer for PageRecord plot (500 samples ≈ 10sec @ 50Hz)
        self._buffer: list[list[float]] = []
        self._MAX_BUFFER_SIZE = 500

        # ── Initialize connections ──────────────────────────────────────
        self._connect_signals()
        self.on_serial_scan()

    # ── Signal Wiring (MVC Controller Pattern) ──────────────────────────

    def _connect_signals(self) -> None:
        """Wire all component signals for non-blocking MVC architecture."""

        # --- UI Wand → Handler (user actions) ---
        self.ui_wand.sig_serial_scan.connect(self.on_serial_scan)
        self.ui_wand.sig_serial_connect.connect(self.on_serial_connect)
        self.ui_wand.sig_serial_disconnect.connect(self.on_serial_disconnect)
        self.ui_wand.sig_flash_upload.connect(self.on_flash_upload)

        # --- UI Setting → Handler (firmware flashing) ---
        if self.ui_setting:
            self.ui_setting.sig_flash_data_firmware.connect(
                lambda: self.handle_firmware_flash("data")
            )
            self.ui_setting.sig_flash_inference_firmware.connect(
                lambda: self.handle_firmware_flash("inference")
            )

        # --- UI Record → Handler (recording & data cropping) ---
        self.ui_record.sig_data_cropped.connect(self.on_data_cropped)
        self.ui_record.sig_spell_selected.connect(self.on_spell_selected)
        self.ui_record.sig_spell_deleted.connect(self.on_spell_deleted)
        self.ui_record.sig_start_record.connect(self.on_record_start)
        self.ui_record.sig_stop_record.connect(self.on_record_stop)

        # ┌─── SERIAL WORKER SIGNALS (hardware input) ───────────────┐
        # │  CRITICAL: Use QueuedConnection for thread safety!       │
        # │  SerialWorker runs in its own QThread and emits signals  │
        # │  in that thread. Without QueuedConnection, slots run in  │
        # │  SerialWorker's thread, updating UI from wrong thread.   │
        # │  This causes PyQtGraph & OpenGL to silently fail.        │
        # └─────────────────────────────────────────────────────────┘
        self._connect_signals_serial_worker()

        # --- DataStore → UI (state updates) ---
        self.store.sig_db_updated.connect(self._on_db_updated)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)
        self.store.sig_prediction_updated.connect(self._on_prediction_received)

        # --- Model Uploader → UI/Handler ---
        self.uploader.progress_updated.connect(self.ui_wand.update_flash_progress)
        self.uploader.status_msg.connect(self.ui_wand.append_terminal_text)
        self.uploader.finished.connect(self._on_upload_finished)

        # --- Flash Worker → UI/Handler ---
        if self.ui_setting:
            self.flash_worker.log_msg.connect(self.ui_setting.append_console_text)
            self.flash_worker.progress.connect(self.ui_setting.update_flash_progress)
            self.flash_worker.finished.connect(self._on_firmware_flash_finished)

        # --- Data Recorder → UI ---
        self.recorder.sig_record_count.connect(self.ui_record.update_record_count)
        self.recorder.sig_status_text.connect(self.ui_wand.append_terminal_text)
        self.recorder.sig_recording_state.connect(self.ui_record.set_recording_state)

    def _connect_signals_serial_worker(self) -> None:
        """
        Wire SerialWorker signals with QueuedConnection.
        Called during init and after reconnect to rebuild connections.
        
        CRITICAL FIX: Use type=2 (QueuedConnection) to marshal slot calls
        from SerialWorker's QThread back to the main Qt event loop.
        This is essential for thread-safe UI updates (pyqtgraph, OpenGL).
        """
        # KEY: sig_data_received → 3D wand and recording buffer
        self.serial_worker.sig_data_received.connect(self._on_data_received)
        self.serial_worker.sig_data_received.connect(self._on_raw_data_received)

        # Also: same normalized list is used for CSV recording
        self.serial_worker.sig_data_received.connect(self.recorder.add_row)

        # AI predictions
        self.serial_worker.sig_prediction_received.connect(self._on_prediction_received)

        # Connection status
        self.serial_worker.sig_connection_status.connect(self._on_connection_status_changed)

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

        # SAFETY: Prevent double-start (can't restart a finished QThread)
        if self.serial_worker.isRunning():
            self.ui_wand.append_terminal_text("[ERROR] Serial already connected. Disconnect first.")
            return

        self.ui_wand.append_terminal_text(f">> Connecting to {port} @ 115200 baud...")
        self.serial_worker.port = port
        self.serial_worker.start()

    def on_serial_disconnect(self) -> None:
        """Stop serial worker and prepare for restart."""
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker.wait()  # Wait for thread to fully exit
            self.ui_wand.append_terminal_text(">> Serial connection stopped")
        
        # CRITICAL FIX: Recreate SerialWorker so it can be started again
        # (Can't call start() on a finished QThread - must create new instance)
        self.serial_worker = SerialWorker()
        self._connect_signals_serial_worker()  # Rewire signals to new instance
        
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
        try:
            if not isinstance(norm_values, (list, tuple)) or len(norm_values) != 6:
                return

            ax, ay, az, gx, gy, gz = [float(v) for v in norm_values]

            # Update 3D wand orientation (PageHome)
            self.ui_home.wand_3d.update_orientation(ax, ay, az, gx, gy, gz)

        except Exception as e:
            self.ui_wand.append_terminal_text(f"[ERROR] 3D wand update failed: {e}")

    def _on_sensor_data_updated(self, sensor_buffers: dict) -> None:
        """Receive updated sensor buffer data from DataStore."""
        # Currently not used in UI, but available for future sensor value display
        pass

    def _on_raw_data_received(self, norm_values: list[float]) -> None:
        """
        Accumulate sensor samples into rolling buffer for PageRecord.
        
        Called on every serial data frame (50 Hz).
        Maintains FIFO buffer of last 500 samples (~10 seconds).
        Only updates when PageRecord is in LIVE mode (is_live=True).
        When STOP pressed, buffer freezes for crop/snip operations.
        
        Args:
            norm_values: [ax, ay, az, gx, gy, gz] normalized sensor readings
        """
        try:
            # Guard: Only buffer if PageRecord is in live/recording mode
            if not self.ui_record.is_live:
                return
            
            if not isinstance(norm_values, (list, tuple)) or len(norm_values) != 6:
                return
            
            # Append sample to buffer
            self._buffer.append(list(norm_values))
            
            # Maintain maximum buffer size (FIFO)
            if len(self._buffer) > self._MAX_BUFFER_SIZE:
                self._buffer = self._buffer[-self._MAX_BUFFER_SIZE:]
            
            # Send shallow copy to PageRecord (avoid race conditions)
            self.ui_record.update_plot_data(list(self._buffer))
            
            if len(self._buffer) % 50 == 0:  # Debug every 50 samples
                print(f"[Handler._on_raw_data_received] Buffer size: {len(self._buffer)}, sample: {norm_values}")
            
        except Exception as e:
            self.ui_wand.append_terminal_text(f"[ERROR] Buffer update failed: {e}")

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
        
        # Clear buffer on disconnect
        if not connected:
            self._buffer.clear()

    # ── Recording Actions ──────────────────────────────────────────────

    def on_record_start(self, label_name: str) -> None:
        """Start recording with the given spell/action label."""
        if self.is_recording:
            self.ui_wand.append_terminal_text(">> Already recording")
            return

        if not label_name.strip():
            self.ui_wand.append_terminal_text(">> Record label is required")
            return

        # Notify ESP32 to enter RECORD mode
        self.serial_worker.send_command("CMD:MODE=RECORD")

        # Start CSV recorder
        success = self.recorder.start_recording(label_name)
        if success:
            self.is_recording = True
            # Clear buffer when starting new recording
            self._buffer.clear()
            self.ui_record.is_live = True
            self.ui_wand.append_terminal_text(f">> RECORDING: {label_name}")
        else:
            self.ui_wand.append_terminal_text(">> RECORD FAILED")

    def on_record_stop(self) -> None:
        """Stop recording and finalize CSV file."""
        if not self.is_recording:
            self.ui_wand.append_terminal_text(">> Not currently recording")
            return

        # Notify ESP32 to enter IDLE mode
        self.serial_worker.send_command("CMD:MODE=IDLE")
        
        # Stop recorder
        self.recorder.stop_recording()
        self.is_recording = False
        
        # Freeze buffer for crop/snip operations
        self.ui_record.is_live = False
        
        self.ui_wand.append_terminal_text(">> RECORD STOPPED - Ready to snip")

    def on_spell_selected(self, spell_name: str) -> None:
        """Handle spell selection from library."""
        self.current_selected_spell = spell_name
        samples = self.store.get_samples_for_spell(spell_name)
        self.ui_record.load_samples_for_spell(spell_name, samples)

    def on_data_cropped(self, cropped_data: list, spell_name: str) -> None:
        """Save cropped data sample to dataset folder."""
        if not spell_name.strip():
            self.ui_wand.append_terminal_text("[WARN] Missing spell label. Snip discarded.")
            return

        success = self.store.save_cropped_data(spell_name, cropped_data)
        if success:
            self.ui_record.set_save_status(spell_name)
            self.ui_wand.append_terminal_text(f">> SAVED: {len(cropped_data)} samples → {spell_name}")

    def on_spell_deleted(self, spell_name: str) -> None:
        """Delete a spell and all its training data."""
        if not spell_name.strip():
            self.ui_wand.append_terminal_text("[ERROR] Invalid spell name for deletion.")
            return

        # Check if this spell is currently selected
        if self.current_selected_spell == spell_name:
            self.current_selected_spell = ""

        success = self.store.delete_spell(spell_name)
        if success:
            self.ui_wand.append_terminal_text(f">> DELETED: Spell '{spell_name}' and all its training data.")
        else:
            self.ui_wand.append_terminal_text(f"[ERROR] Failed to delete spell '{spell_name}'.")

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

        # Map bin_type to firmware file path
        bin_map = {
            "data": "assets/firmware/collect.bin",
            "inference": "assets/firmware/inference.bin",
        }

        bin_path = bin_map.get(bin_type)
        if not bin_path:
            self._flash_log_to_console(f"[ERROR] Unknown firmware type: {bin_type}")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # CRITICAL: Stop serial connection and WAIT for port to close
        # (FlashWorker and SerialWorker cannot share the same COM port)
        if self.serial_worker.isRunning():
            self._flash_log_to_console(">> Stopping serial connection to release COM port...")
            self.serial_worker.stop()
            self.serial_worker.wait()  # Wait for serial thread to fully exit
            self._flash_log_to_console(">> COM port released, ready to flash\n")

        self._flash_log_to_console(f"\n{'='*60}")
        self._flash_log_to_console(f"[INFO] Begin flashing {bin_type.upper()} firmware to {port}")
        self._flash_log_to_console(f"{'='*60}\n")

        # Start the flash worker
        self.flash_worker.flash_firmware(port, bin_path)

    def _flash_log_to_console(self, message: str) -> None:
        """Route flash logging to the UI console."""
        if self.ui_setting:
            self.ui_setting.append_console_text(message)

    def flash_esp32(self, mode: str) -> None:
        """
        Flash firmware to ESP32-S3 (alternative public API).

        Args:
            mode: 'DATA' for collect.bin or 'AI' for inference.bin
        """
        # Validate mode
        mode_upper = mode.upper() if mode else ""
        if mode_upper not in ("DATA", "AI"):
            self._flash_log_to_console(f"[ERROR] Invalid mode: {mode}. Use 'DATA' or 'AI'.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Get selected port
        port = self.ui_wand.combo_serial_ports.currentText() if self.ui_wand else None
        if not port:
            self._flash_log_to_console("[ERROR] No serial port selected. Please select a port first.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Map mode to firmware file
        firmware_map: dict[str, str] = {
            "DATA": "assets/firmware/collect.bin",
            "AI": "assets/firmware/inference.bin",
        }
        bin_path: str = firmware_map.get(mode_upper, "")

        if not bin_path:
            self._flash_log_to_console("[ERROR] Invalid firmware mode mapping.")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Use absolute path for validation
        abs_bin_path = os.path.abspath(bin_path)
        
        # Check file exists
        if not os.path.exists(abs_bin_path):
            self._flash_log_to_console(f"[ERROR] Firmware file not found: {abs_bin_path}")
            if self.ui_setting:
                self.ui_setting.set_flash_buttons_enabled(True)
            return

        # Stop serial worker to free the port
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self._flash_log_to_console("[INFO] Stopped serial connection to free COM port.\n")

        self._flash_log_to_console(f"\n{'='*60}")
        self._flash_log_to_console(f"[FLASH] Starting {mode.upper()} firmware flash to {port}")
        self._flash_log_to_console(f"{'='*60}\n")

        # Start the flash worker with absolute path
        self.flash_worker.flash_firmware(port, abs_bin_path)

    def on_flash_upload(self) -> None:
        """Stop serial stream and start binary model upload."""
        port = self.ui_wand.combo_serial_ports.currentText()
        if not port:
            self.ui_wand.append_terminal_text("[ERROR] Serial port required for upload.")
            return

        # Stop serial if running
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.ui_wand.append_terminal_text(">> Temporarily pausing live data for upload...")

        model_path = "model.tflite"
        self.ui_wand.append_terminal_text(f">> Initiating model upload for {model_path}...")
        self.uploader.upload_file(port, model_path)

    def _on_upload_finished(self, success: bool) -> None:
        """Callback when model upload completes."""
        if success:
            self.ui_wand.append_terminal_text(">> Model upload COMPLETE!")
            self.ui_wand.update_flash_progress(100)
        else:
            self.ui_wand.append_terminal_text(">> Model upload FAILED. Check connection.")
            self.ui_wand.update_flash_progress(0)

    def _on_firmware_flash_finished(self, success: bool, message: str) -> None:
        """Callback when firmware flash completes."""
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

    # ── Database Callbacks ─────────────────────────────────────────────

    def _on_db_updated(self, spell_counts: dict) -> None:
        """Relay database changes to UI pages."""
        self.ui_record.load_spell_list(list(spell_counts.keys()))
        self.ui_wand.load_spell_payload_list(spell_counts)
        
        # If currently selecting a spell on Record page, refresh its sample list
        if self.current_selected_spell:
            samples = self.store.get_samples_for_spell(self.current_selected_spell)
            self.ui_record.load_samples_for_spell(self.current_selected_spell, samples)
        # --- UI Wand → Handler ---
        self.ui_wand.sig_serial_scan.connect(self.on_serial_scan)
        self.ui_wand.sig_serial_connect.connect(self.on_serial_connect)
        self.ui_wand.sig_serial_disconnect.connect(self.on_serial_disconnect)
        self.ui_wand.sig_flash_upload.connect(self.on_flash_upload)

        # --- UI Setting → Handler (if available) ---
        if self.ui_setting:
            self.ui_setting.sig_flash_data_firmware.connect(
                lambda: self.handle_firmware_flash("data")
            )
            self.ui_setting.sig_flash_inference_firmware.connect(
                lambda: self.handle_firmware_flash("inference")
            )

        # --- UI Record → Handler ---
        self.ui_record.sig_data_cropped.connect(self.on_data_cropped)
        self.ui_record.sig_spell_selected.connect(self.on_spell_selected)
        self.ui_record.sig_start_record.connect(self.on_record_start)
        self.ui_record.sig_stop_record.connect(self.on_record_stop)

        # --- Serial Worker → Handler/DataStore ---
        # Single stream of normalized sensor samples as a list
        self.serial_worker.sig_data_received.connect(self.store.update_sensor_data)
        self.serial_worker.sig_data_received.connect(self.recorder.add_row)
        self.serial_worker.sig_data_received.connect(self._on_raw_data_received)
        # AI Inference stream
        self.serial_worker.sig_prediction_received.connect(self.store.update_prediction)
        # Status/Connection
        self.serial_worker.sig_connection_status.connect(self._on_connection_status_changed)

        # --- DataStore → UI (Reactive Updates) ---
        self.store.sig_sensor_data_updated.connect(self._on_sensor_data_updated)
        self.store.sig_db_updated.connect(self._on_db_updated)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)
        self.store.sig_prediction_updated.connect(self._on_prediction_received)

        # --- Model Uploader → UI/Handler ---
        self.uploader.progress_updated.connect(self.ui_wand.update_flash_progress)
        self.uploader.status_msg.connect(self.ui_wand.append_terminal_text)
        self.uploader.finished.connect(self._on_upload_finished)

        # --- Flash Worker → UI/Handler ---
        if self.ui_setting:
            self.flash_worker.log_msg.connect(self.ui_setting.append_console_text)
            self.flash_worker.progress.connect(self.ui_setting.update_flash_progress)
            self.flash_worker.finished.connect(self._on_firmware_flash_finished)

        # --- Data Recorder → UI ---
        self.recorder.sig_record_count.connect(self.ui_record.update_record_count)
        self.recorder.sig_status_text.connect(self.ui_wand.append_terminal_text)
        self.recorder.sig_recording_state.connect(self.ui_record.set_recording_state)


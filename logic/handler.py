"""
logic/handler.py — Centralized handler coordinating DataStore, Workers, and UI signals.

Architecture:
    - LogicHandler acts as the "Controller" (MVC Pattern).
    - Connects hardware-level Workers to the DataStore state container.
    - Bridges UI signals to hardware-level commands.
    - Ensures non-blocking execution by managing background threads.
"""

from PyQt6.QtCore import QObject
from .data_store import DataStore
from .serial_worker import SerialWorker
from .model_uploader import ModelUploader


class Handler(QObject):
    """Wires together Hardware workers, DataStore, and UI pages."""

    def __init__(self, ui_page_wand, ui_page_record, ui_page_home, data_store: DataStore) -> None:
        super().__init__()
        self.ui_wand = ui_page_wand
        self.ui_record = ui_page_record
        self.ui_home = ui_page_home
        self.store = data_store

        # 1. Background Workers (Initialised without active port)
        # Fixes base-init errors by providing default port="" in Workers
        self.serial_worker = SerialWorker()
        self.uploader = ModelUploader()

        # 2. Track UI navigation and selection
        self.current_selected_spell: str = ""

        # 3. Connection & Logic Wiring
        self._connect_signals()
        
        # Initial scan of available ports
        self.on_serial_scan()

    # ── Signal Wiring ───────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # --- UI Wand → Handler ---
        self.ui_wand.sig_serial_scan.connect(self.on_serial_scan)
        self.ui_wand.sig_serial_connect.connect(self.on_serial_connect)
        self.ui_wand.sig_serial_disconnect.connect(self.on_serial_disconnect)
        self.ui_wand.sig_flash_upload.connect(self.on_flash_upload)

        # --- UI Record → Handler ---
        self.ui_record.sig_data_cropped.connect(self.on_data_cropped)
        self.ui_record.sig_spell_selected.connect(self.on_spell_selected)

        # --- Serial Worker → Handler/DataStore ---
        # Data stream (Requested dict logic)
        self.serial_worker.data_received.connect(self.store.update_sensor_data)
        # AI Inference stream
        self.serial_worker.prediction_received.connect(self.store.update_prediction)
        # Status/Connection
        self.serial_worker.connection_status.connect(self._on_connection_status_changed)

        # --- DataStore → UI (Reactive Updates) ---
        self.store.sig_sensor_data_updated.connect(self.ui_record.update_plot_data)
        self.store.sig_sensor_data_updated.connect(self.ui_home.wand_3d.update_orientation)
        self.store.sig_db_updated.connect(self._on_db_updated)
        self.store.sig_stats_updated.connect(self.ui_wand.update_esp_stats)
        self.store.sig_prediction_updated.connect(self._on_prediction_received)

        # --- Model Uploader → UI/Handler ---
        self.uploader.progress_updated.connect(self.ui_wand.update_flash_progress)
        self.uploader.status_msg.connect(self.ui_wand.append_terminal_text)
        self.uploader.finished.connect(self._on_upload_finished)

    # ── Serial Actions ──────────────────────────────────────────────────

    def on_serial_scan(self) -> None:
        ports = SerialWorker.get_available_ports()
        self.ui_wand.update_serial_port_list(ports)
        self.ui_wand.append_terminal_text(f">> Scanned {len(ports)} UART port(s).")

    def on_serial_connect(self, port: str) -> None:
        """Start the non-blocking UART worker."""
        if not port:
            self.ui_wand.append_terminal_text("[ERROR] Select a port first.")
            return

        self.ui_wand.append_terminal_text(f">> Connecting to {port} @ 921600 baud...")
        self.serial_worker.port = port
        self.serial_worker.start()

    def on_serial_disconnect(self) -> None:
        self.serial_worker.stop()
        self.ui_wand.append_terminal_text(">> Disconnecting serial...")

    # ── Flash / Uploader Actions ──────────────────────────────────────────

    def on_flash_upload(self) -> None:
        """Stop serial stream and start binary upload."""
        port = self.ui_wand.combo_serial_ports.currentText()
        if not port:
            self.ui_wand.append_terminal_text("[ERROR] Serial port required for upload.")
            return

        # Always stop serial before using the port for uploading
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.ui_wand.append_terminal_text(">> Temporarily pausing live data for upload...")

        # Find the .tflite model in the root (mock or path from UI)
        model_path = "model.tflite" 
        self.ui_wand.append_terminal_text(f">> Initiating upload for {model_path} to ESP32...")
        self.uploader.upload_file(port, model_path)

    def _on_upload_finished(self, success: bool) -> None:
        if success:
            self.ui_wand.append_terminal_text(">> Flash COMPLETE! Model updated.")
            self.ui_wand.update_flash_progress(100)
        else:
            self.ui_wand.append_terminal_text(">> Flash FAILED. Check connection.")
            self.ui_wand.update_flash_progress(0)

    # ── Worker Callbacks ────────────────────────────────────────────────

    def _on_connection_status_changed(self, connected: bool, message: str) -> None:
        self.ui_wand.set_serial_status(connected, self.serial_worker.port if connected else "")
        self.ui_record.set_wand_ready(connected)
        self.store.set_connection_status(connected, self.serial_worker.port if connected else "None")
        self.ui_wand.append_terminal_text(f">> {message}")

    def _on_prediction_received(self, label: str, confidence: float) -> None:
        text = f"PREDICTION: {label} ({confidence*100:.1f}%)"
        self.ui_wand.append_terminal_text(f">> {text}")

    # ── Database Callbacks ──────────────────────────────────────────────

    def _on_db_updated(self, spell_counts: dict) -> None:
        """Relay database changes to UI pages."""
        self.ui_record.load_spell_list(list(spell_counts.keys()))
        self.ui_wand.load_spell_payload_list(spell_counts)
        
        # If currently selecting a spell on Record page, refresh its sample list
        if self.current_selected_spell:
            samples = self.store.get_samples_for_spell(self.current_selected_spell)
            self.ui_record.load_samples_for_spell(self.current_selected_spell, samples)

    # ── Record Actions ──────────────────────────────────────────────────

    def on_spell_selected(self, spell_name: str) -> None:
        self.current_selected_spell = spell_name
        samples = self.store.get_samples_for_spell(spell_name)
        self.ui_record.load_samples_for_spell(spell_name, samples)

    def on_data_cropped(self, cropped_data: list, spell_name: str) -> None:
        """Save a training sample through the DataStore."""
        if not spell_name.strip():
            self.ui_wand.append_terminal_text("[WARN] Missing spell label. Snip discarded.")
            return

        success = self.store.save_cropped_data(spell_name, cropped_data)
        if success:
            self.ui_record.set_save_status(spell_name)
from __future__ import annotations

from dataclasses import dataclass

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from logic.data_store import DataStore
from logic.handler import Handler


class _ComboBoxStub:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def currentText(self) -> str:
        return self._text

    def setCurrentText(self, text: str) -> None:
        self._text = text


class _Wand3DStub:
    def __init__(self) -> None:
        self.updates: list[tuple[float, float, float, float, float, float]] = []

    def update_orientation(
        self,
        ax: float,
        ay: float,
        az: float,
        gx: float,
        gy: float,
        gz: float,
    ) -> None:
        self.updates.append((ax, ay, az, gx, gy, gz))


class _SerialRuntimeStub:
    def __init__(self, running: bool) -> None:
        self._running = running
        self.port = "COM9"

    def isRunning(self) -> bool:
        return self._running

    def stop(self) -> None:
        self._running = False

    def wait(self, _timeout: int | None = None) -> bool:
        return True

    def send_command(self, _command: str) -> bool:
        return True


class WandStub(QObject):
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()
    sig_flash_upload = pyqtSignal()
    sig_bt_scan = pyqtSignal()
    sig_bt_connect = pyqtSignal(str)
    sig_bt_disconnect = pyqtSignal()
    sig_flash_compile = pyqtSignal(list)
    sig_train_build_requested = pyqtSignal()
    sig_train_build_tflite_requested = pyqtSignal(list)
    sig_train_build_cc_requested = pyqtSignal(list)
    sig_term_clear = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.combo_serial_ports = _ComboBoxStub("COM9")
        self.logs: list[str] = []
        self.flash_progress: list[tuple[int, str]] = []
        self.serial_status: list[tuple[bool, str]] = []
        self.serial_ports: list[str] = []
        self.stats_updates: list[dict] = []
        self.payload_updates: list[dict] = []

    def append_terminal_text(self, text: str) -> None:
        self.logs.append(text)

    def update_flash_progress(self, percentage: int, status_text: str = "") -> None:
        self.flash_progress.append((percentage, status_text))

    def set_serial_status(self, connected: bool, port_name: str = "") -> None:
        self.serial_status.append((connected, port_name))

    def update_serial_port_list(self, ports: list[str]) -> None:
        self.serial_ports = list(ports)

    def update_esp_stats(self, stats: dict) -> None:
        self.stats_updates.append(dict(stats))

    def load_spell_payload_list(self, spell_counts: dict) -> None:
        self.payload_updates.append(dict(spell_counts))


class RecordStub(QObject):
    sig_data_cropped = pyqtSignal(list, str)
    sig_spell_selected = pyqtSignal(str)
    sig_spell_deleted = pyqtSignal(str)
    sig_start_record = pyqtSignal(str)
    sig_stop_record = pyqtSignal()
    sig_clear_buffer = pyqtSignal()
    sig_export_csv = pyqtSignal()
    sig_register_prototype = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.is_live = True
        self.current_spell_name = ""
        self.record_count_events: list[int] = []
        self.recording_state_events: list[bool] = []
        self.wand_ready_events: list[bool] = []
        self.plot_updates: list[list] = []
        self.loaded_spell_lists: list[list[str]] = []
        self.protected_spell_warnings: list[str] = []
        self.consistency_results: list[dict] = []

    def update_record_count(self, count: int) -> None:
        self.record_count_events.append(count)

    def set_recording_state(self, recording: bool) -> None:
        self.recording_state_events.append(recording)

    def set_wand_ready(self, ready: bool) -> None:
        self.wand_ready_events.append(ready)

    def update_plot_data(self, data: list) -> None:
        self.plot_updates.append(data)

    def load_spell_list(self, names: list[str] | dict[str, int], consistencies: dict | None = None) -> None:
        self.loaded_spell_lists.append(list(names))

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        self.current_spell_name = spell_name

    def set_save_status(self, spell_name: str) -> None:
        pass

    def update_consistency_display(self, result: dict) -> None:
        self.consistency_results.append(result)

    def on_spell_registered(self, spell_name: str) -> None:
        pass

    def show_protected_spell_warning(self, spell_name: str) -> None:
        self.protected_spell_warnings.append(spell_name)


class HomeStub(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.wand_3d = _Wand3DStub()
        self.mode_events: list[str] = []
        self.sensor_readouts: list[list[float]] = []

    def set_mode(self, mode: str) -> None:
        self.mode_events.append(mode)

    def set_sensor_readout(self, values: list[float]) -> None:
        self.sensor_readouts.append(list(values))

    def _on_sensor_data_updated(self, sensor_buffers: dict) -> None:
        latest = []
        for key in ("ax", "ay", "az", "gx", "gy", "gz"):
            values = sensor_buffers.get(key)
            if values is None or len(values) == 0:
                return
            latest.append(float(values[-1]))
        self.set_sensor_readout(latest)


class SettingStub(QObject):
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()
    sig_settings_saved = pyqtSignal(dict)


    def __init__(self) -> None:
        super().__init__()
        self.console_messages: list[str] = []
        self.flash_button_states: list[bool] = []
        self.flash_progress_values: list[int] = []

    def append_console_text(self, text: str) -> None:
        self.console_messages.append(text)

    def set_flash_buttons_enabled(self, enabled: bool) -> None:
        self.flash_button_states.append(enabled)

    def update_flash_progress(self, value: int) -> None:
        self.flash_progress_values.append(value)


class PrimitiveCollectStub(QObject):
    sig_start_collection = pyqtSignal(str, str)
    sig_stop_collection = pyqtSignal()
    sig_capture_collection = pyqtSignal(str, str)
    sig_train_encoder_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.collection_state_events: list[bool] = []
        self.capture_ready_events: list[bool] = []
        self.capture_saved_events: list[tuple[bool, str]] = []
        self.collection_stats_events: list[dict] = []
        self.quality_reset_events: list[bool] = []
        self.quality_assessment_events: list[int] = []

    def set_collection_state(self, collecting: bool) -> None:
        self.collection_state_events.append(bool(collecting))

    def set_capture_ready(self, ready: bool) -> None:
        self.capture_ready_events.append(bool(ready))

    def on_capture_saved(self, success: bool, message: str) -> None:
        self.capture_saved_events.append((bool(success), str(message)))

    def update_collection_stats(self, stats: dict) -> None:
        self.collection_stats_events.append(dict(stats))

    def reset_quality_evaluation(self, *, collecting: bool = False) -> None:
        self.quality_reset_events.append(bool(collecting))

    def update_quality_assessment(self, buffer_snapshot: list) -> None:
        self.quality_assessment_events.append(len(buffer_snapshot))

    def update_signal_preview(self, _buffer_snapshot: list) -> None:
        # No-op for tests.
        pass

    def on_encoder_training_status(self, _message: str) -> None:
        # No-op for tests.
        pass

    def on_encoder_training_progress(self, _value: int) -> None:
        # No-op for tests.
        pass

    def on_encoder_training_finished(self, _success: bool, _message: str) -> None:
        # No-op for tests.
        pass


@dataclass
class HandlerHarness:
    handler: Handler
    store: DataStore
    wand: WandStub
    record: RecordStub
    home: HomeStub
    setting: SettingStub
    primitive: PrimitiveCollectStub | None = None


@pytest.fixture
def handler_harness(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "logic.handler.SerialWorker.get_available_ports",
        staticmethod(lambda: ["COM9"]),
    )

    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    wand = WandStub()
    record = RecordStub()
    home = HomeStub()
    setting = SettingStub()

    handler = Handler(wand, record, home, store, setting)
    harness = HandlerHarness(
        handler=handler,
        store=store,
        wand=wand,
        record=record,
        home=home,
        setting=setting,
        primitive=None,
    )

    yield harness
    handler.shutdown()


@pytest.fixture
def handler_harness_with_primitive(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "logic.handler.SerialWorker.get_available_ports",
        staticmethod(lambda: ["COM9"]),
    )

    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    wand = WandStub()
    record = RecordStub()
    home = HomeStub()
    setting = SettingStub()
    primitive = PrimitiveCollectStub()

    handler = Handler(wand, record, home, store, setting, ui_primitive_collect=primitive)
    harness = HandlerHarness(
        handler=handler,
        store=store,
        wand=wand,
        record=record,
        home=home,
        setting=setting,
        primitive=primitive,
    )

    yield harness
    handler.shutdown()


def test_record_start_requires_active_connection(handler_harness: HandlerHarness) -> None:
    harness = handler_harness

    harness.handler.on_record_start("accio")

    assert any("Serial connection is required" in msg for msg in harness.wand.logs)
    assert harness.store.get_recording_state() is False
    assert harness.handler._mode != harness.handler._MODE_RECORD


def test_model_upload_preflight_rejects_missing_file(
    handler_harness: HandlerHarness,
    monkeypatch,
) -> None:
    harness = handler_harness
    harness.store.save_settings({"model_path": "missing_model.tflite"})

    upload_calls: list[tuple[str, str]] = []

    def fake_upload(port: str, path: str) -> None:
        upload_calls.append((port, path))

    monkeypatch.setattr(harness.handler.uploader, "upload_file", fake_upload)

    harness.handler.on_flash_upload()

    assert upload_calls == []
    assert any("Model file not found" in msg for msg in harness.wand.logs)
    assert harness.wand.flash_progress and harness.wand.flash_progress[-1][0] == 0
    assert harness.handler._mode != harness.handler._MODE_UPDATE


def test_firmware_flash_is_blocked_while_recording(handler_harness: HandlerHarness) -> None:
    harness = handler_harness
    harness.store.set_recording_state(True)

    harness.handler.handle_firmware_flash("data")

    assert any(
        "Stop recording before starting firmware flash" in msg
        for msg in harness.setting.console_messages
    )
    assert harness.handler._mode != harness.handler._MODE_UPDATE


def test_runtime_mode_transition_blocks_record_to_update(handler_harness: HandlerHarness) -> None:
    harness = handler_harness

    assert harness.handler._transition_mode(harness.handler._MODE_INFER, reason="test")
    assert harness.handler._transition_mode(harness.handler._MODE_RECORD, reason="test")
    assert not harness.handler._transition_mode(harness.handler._MODE_UPDATE, reason="blocked")

    assert harness.handler._mode == harness.handler._MODE_RECORD
    assert any("Mode transition blocked" in msg for msg in harness.wand.logs)


def test_raw_uart_lines_are_forwarded_to_terminal(handler_harness: HandlerHarness, qapp) -> None:
    harness = handler_harness

    harness.handler.serial_worker.sig_raw_line_received.emit("RAW:1,2,3,4,5,6")
    qapp.processEvents()

    assert any("RAW:1,2,3,4,5,6" in msg for msg in harness.wand.logs)


def test_handler_shutdown_is_idempotent(handler_harness: HandlerHarness) -> None:
    harness = handler_harness

    harness.handler.shutdown()
    harness.handler.shutdown()

    assert harness.handler._shutdown_done is True
    assert harness.handler._feature_timer.isActive() is False


def test_data_io_queue_warning_is_forwarded_to_terminal(
    handler_harness: HandlerHarness,
    qapp,
) -> None:
    harness = handler_harness

    harness.handler.data_io_worker.sig_queue_warning.emit("DataIOWorker queue full: save job dropped")
    qapp.processEvents()

    assert any("DataIOWorker queue full" in msg for msg in harness.wand.logs)


def test_port_claim_allows_flash_takeover_from_serial_owner(
    handler_harness: HandlerHarness,
) -> None:
    harness = handler_harness
    harness.handler._set_port_owner("serial")

    assert harness.handler._can_use_port("flash", allow_owner="serial") is True
    assert harness.handler._get_port_owner() == "flash"


def test_port_claim_blocks_when_owned_by_other_subsystem(
    handler_harness: HandlerHarness,
) -> None:
    harness = handler_harness
    harness.handler._set_port_owner("upload")

    assert harness.handler._can_use_port("flash", allow_owner="serial") is False
    assert harness.handler._get_port_owner() == "upload"
    assert any("Port is busy with upload" in msg for msg in harness.wand.logs)


def test_record_start_is_blocked_in_update_mode(
    handler_harness: HandlerHarness,
    monkeypatch,
) -> None:
    harness = handler_harness
    harness.store.set_connection_status(True, "COM9")
    assert harness.handler._transition_mode(harness.handler._MODE_UPDATE, reason="setup")

    start_calls: list[str] = []

    def fake_start_recording(label_name: str) -> bool:
        start_calls.append(label_name)
        return True

    monkeypatch.setattr(harness.handler.recorder, "start_recording", fake_start_recording)

    harness.handler.on_record_start("accio")

    assert start_calls == []
    assert harness.handler._mode == harness.handler._MODE_UPDATE
    assert any(
        "Cannot start recording while update mode is active" in msg
        for msg in harness.wand.logs
    )


def test_record_stop_transitions_to_infer_when_serial_running(
    handler_harness: HandlerHarness,
) -> None:
    harness = handler_harness
    harness.handler.serial_worker = _SerialRuntimeStub(running=True)
    assert harness.handler._transition_mode(harness.handler._MODE_RECORD, reason="setup")
    harness.store.set_recording_state(True)
    harness.record.is_live = True

    harness.handler.on_record_stop()

    assert harness.record.is_live is False
    assert harness.handler._mode == harness.handler._MODE_INFER
    assert any("RECORD STOPPED - Ready to snip" in msg for msg in harness.wand.logs)


def test_record_stop_transitions_to_idle_when_serial_disconnected(
    handler_harness: HandlerHarness,
) -> None:
    harness = handler_harness
    harness.handler.serial_worker = _SerialRuntimeStub(running=False)
    assert harness.handler._transition_mode(harness.handler._MODE_RECORD, reason="setup")
    harness.store.set_recording_state(True)
    harness.record.is_live = True

    harness.handler.on_record_stop()

    assert harness.record.is_live is False
    assert harness.handler._mode == harness.handler._MODE_IDLE
    assert any("RECORD STOPPED - Ready to snip" in msg for msg in harness.wand.logs)


def test_primitive_stop_sets_capture_ready_and_mode(
    handler_harness_with_primitive: HandlerHarness,
) -> None:
    harness = handler_harness_with_primitive
    primitive = harness.primitive
    assert primitive is not None
    harness.store.set_connection_status(True, "COM9")
    harness.handler.serial_worker = _SerialRuntimeStub(running=True)

    harness.handler.on_primitive_collection_start("SWIPE_RIGHT", "A_standard")
    harness.store.add_live_sample([0.1, 0.2, 0.3, 1.0, 1.1, 1.2], emit=False)
    harness.handler.on_primitive_collection_stop()

    assert harness.handler._mode == harness.handler._MODE_INFER
    assert harness.record.is_live is False
    assert primitive.collection_state_events[-1] is False
    assert primitive.capture_ready_events[-1] is True
    assert primitive.quality_reset_events and primitive.quality_reset_events[-1] is True
    assert primitive.quality_assessment_events and primitive.quality_assessment_events[-1] == 1
    assert any("PRIMITIVE COLLECT STOPPED - Ready to capture" in msg for msg in harness.wand.logs)


def test_primitive_stop_without_samples_disables_capture(
    handler_harness_with_primitive: HandlerHarness,
) -> None:
    harness = handler_harness_with_primitive
    primitive = harness.primitive
    assert primitive is not None
    harness.store.set_connection_status(True, "COM9")
    harness.handler.serial_worker = _SerialRuntimeStub(running=True)

    harness.handler.on_primitive_collection_start("SWIPE_RIGHT", "A_standard")
    harness.handler.on_primitive_collection_stop()

    assert primitive.capture_ready_events[-1] is False
    assert any("Primitive buffer is empty after STOP" in msg for msg in harness.wand.logs)


def test_primitive_capture_enqueues_save_and_notifies_ui(
    handler_harness_with_primitive: HandlerHarness,
    monkeypatch,
) -> None:
    harness = handler_harness_with_primitive
    primitive = harness.primitive
    assert primitive is not None
    harness.store.set_connection_status(True, "COM9")
    harness.handler.serial_worker = _SerialRuntimeStub(running=True)

    harness.handler.on_primitive_collection_start("SWIPE_RIGHT", "A_standard")
    harness.store.add_live_sample([0.1, 0.2, 0.3, 1.0, 1.1, 1.2], emit=False)
    harness.store.add_live_sample([0.4, 0.5, 0.6, 2.0, 2.1, 2.2], emit=False)
    harness.handler.on_primitive_collection_stop()

    enqueued: list[tuple[str, list[list[float]]]] = []
    monkeypatch.setattr(
        harness.handler.data_io_worker,
        "enqueue_save",
        lambda spell, data, **kwargs: enqueued.append((spell, data)),
    )

    harness.handler.on_primitive_collection_capture("SWIPE_RIGHT", "A_standard")

    assert enqueued
    spell, data = enqueued[-1]
    assert spell == "SWIPE_RIGHT"
    assert len(data) == 2
    assert harness.handler._pending_save_context == "primitive"

    harness.handler._on_io_save_done(True, "Saved 2 samples → SWIPE_RIGHT")
    assert primitive.capture_saved_events[-1][0] is True
    assert harness.handler._pending_save_context == ""


def test_primitive_capture_rejects_empty_buffer(
    handler_harness_with_primitive: HandlerHarness,
) -> None:
    harness = handler_harness_with_primitive
    primitive = harness.primitive
    assert primitive is not None
    harness.store.set_connection_status(True, "COM9")
    harness.handler.serial_worker = _SerialRuntimeStub(running=True)

    harness.handler.on_primitive_collection_start("SWIPE_RIGHT", "A_standard")
    harness.handler.on_primitive_collection_stop()
    harness.handler.on_primitive_collection_capture("SWIPE_RIGHT", "A_standard")

    assert primitive.capture_ready_events[-1] is False
    assert any("No buffered primitive data to capture" in msg for msg in harness.wand.logs)


def test_upload_finish_releases_owner_resets_mode_and_reports_status(
    handler_harness: HandlerHarness,
) -> None:
    harness = handler_harness

    assert harness.handler._transition_mode(harness.handler._MODE_UPDATE, reason="setup")
    harness.handler._set_port_owner("upload")
    harness.handler._on_upload_finished(True, "ok")

    assert harness.handler._port_owner is None
    assert harness.handler._mode == harness.handler._MODE_IDLE
    assert harness.wand.flash_progress and harness.wand.flash_progress[-1][0] == 100
    assert any("Model upload COMPLETE" in msg for msg in harness.wand.logs)


def test_flash_handoff_rejects_missing_pending_context(
    handler_harness: HandlerHarness,
    monkeypatch,
) -> None:
    harness = handler_harness
    flash_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        harness.handler.flash_worker,
        "flash_firmware",
        lambda port, path: flash_calls.append((port, path)),
    )

    harness.handler._set_port_owner("flash")
    harness.handler._pending_flash_bin_type = ""
    harness.handler._pending_flash_port = ""
    harness.handler._pending_flash_bin_path = None

    harness.handler._on_serial_stopped_start_flash()

    assert flash_calls == []
    assert harness.handler._get_port_owner() is None
    assert any(
        "Flash handoff failed: missing pending flash context." in msg
        for msg in harness.setting.console_messages
    )
    assert harness.setting.flash_button_states and harness.setting.flash_button_states[-1] is True


def test_upload_handoff_rejects_missing_pending_context(
    handler_harness: HandlerHarness,
    monkeypatch,
) -> None:
    harness = handler_harness
    upload_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        harness.handler.uploader,
        "upload_file",
        lambda port, path: upload_calls.append((port, path)),
    )

    harness.handler._set_port_owner("upload")
    harness.handler._pending_upload_port = ""
    harness.handler._pending_upload_model_path = None

    harness.handler._on_serial_stopped_start_upload()

    assert upload_calls == []
    assert harness.handler._get_port_owner() is None
    assert harness.wand.flash_progress and harness.wand.flash_progress[-1][0] == 0
    assert any(
        "Upload handoff failed: missing pending upload context." in msg
        for msg in harness.wand.logs
    )


def test_delete_system_spell_is_blocked_with_feedback(handler_harness: HandlerHarness) -> None:
    harness = handler_harness

    harness.handler.on_spell_deleted("STAND BY")

    assert any("protected system spell" in msg for msg in harness.wand.logs)
    assert harness.record.protected_spell_warnings == ["STAND BY"]

    assert harness.handler._transition_mode(harness.handler._MODE_UPDATE, reason="setup")
    harness.handler._set_port_owner("upload")
    harness.handler._on_upload_finished(False, "boom")

    assert harness.handler._port_owner is None
    assert harness.handler._mode == harness.handler._MODE_IDLE
    assert harness.wand.flash_progress and harness.wand.flash_progress[-1][0] == 0
    assert any("Model upload FAILED" in msg for msg in harness.wand.logs)

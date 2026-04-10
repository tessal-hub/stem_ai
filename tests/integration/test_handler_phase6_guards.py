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

    def __init__(self) -> None:
        super().__init__()
        self.is_live = True
        self.record_count_events: list[int] = []
        self.recording_state_events: list[bool] = []
        self.wand_ready_events: list[bool] = []
        self.plot_updates: list[list] = []
        self.loaded_spell_lists: list[list[str]] = []
        self.protected_spell_warnings: list[str] = []

    def update_record_count(self, count: int) -> None:
        self.record_count_events.append(count)

    def set_recording_state(self, recording: bool) -> None:
        self.recording_state_events.append(recording)

    def set_wand_ready(self, ready: bool) -> None:
        self.wand_ready_events.append(ready)

    def update_plot_data(self, data: list) -> None:
        self.plot_updates.append(data)

    def load_spell_list(self, names: list[str]) -> None:
        self.loaded_spell_lists.append(list(names))

    def load_samples_for_spell(self, spell_name: str, samples: list[str]) -> None:
        # No-op for test harness.
        pass

    def set_save_status(self, spell_name: str) -> None:
        # No-op for test harness.
        pass

    def show_protected_spell_warning(self, spell_name: str) -> None:
        self.protected_spell_warnings.append(spell_name)


class HomeStub(QObject):
    sig_simulation_replay_requested = pyqtSignal()
    sig_simulation_stop_requested = pyqtSignal()
    sig_calibrate_requested = pyqtSignal()
    sig_quick_test_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.wand_3d = _Wand3DStub()
        self.mode_events: list[str] = []
        self.sensor_readouts: list[list[float]] = []
        self.simulation_events: list[bool] = []

    def set_mode(self, mode: str) -> None:
        self.mode_events.append(mode)

    def set_sensor_readout(self, values: list[float]) -> None:
        self.sensor_readouts.append(list(values))

    def set_simulation_running(self, active: bool) -> None:
        self.simulation_events.append(active)

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


@dataclass
class HandlerHarness:
    handler: Handler
    store: DataStore
    wand: WandStub
    record: RecordStub
    home: HomeStub
    setting: SettingStub


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
    )

    yield harness

    handler.uploader.stop()
    handler.uploader.wait(100)
    handler.flash_worker.stop()
    handler.flash_worker.wait(100)
    handler.serial_worker.stop()
    handler.serial_worker.wait(100)
    handler.recorder.stop()


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


def test_simulation_replays_recent_input_frames(handler_harness: HandlerHarness) -> None:
    harness = handler_harness

    harness.store.update_sensor_data({"ax": 0.1, "ay": 0.2, "az": 0.3, "gx": 1.0, "gy": 2.0, "gz": 3.0})
    harness.store.update_sensor_data({"ax": 0.4, "ay": 0.5, "az": 0.6, "gx": 4.0, "gy": 5.0, "gz": 6.0})

    harness.handler._on_simulation_replay_requested()
    harness.handler._step_simulation_playback()

    assert harness.home.simulation_events[0] is True
    assert harness.home.wand_3d.updates[0] == (0.1, 0.2, 0.3, 1.0, 2.0, 3.0)
    assert harness.home.wand_3d.updates[1] == (0.4, 0.5, 0.6, 4.0, 5.0, 6.0)

    harness.handler._step_simulation_playback()

    assert harness.home.simulation_events[-1] is False


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

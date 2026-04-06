import pytest

from logic.data_store import DataStore


def test_add_live_sample_validates_shape_and_updates_buffer(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    invalid_snapshot = store.add_live_sample([1.0, 2.0, 3.0])
    assert invalid_snapshot == []
    assert store.get_live_buffer_snapshot() == []

    valid_snapshot = store.add_live_sample([1, 2, 3, 4, 5, 6])
    assert len(valid_snapshot) == 1
    assert valid_snapshot[0] == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


def test_live_buffer_respects_fixed_maxlen(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    for i in range(600):
        store.add_live_sample([i, i, i, i, i, i])

    snapshot = store.get_live_buffer_snapshot()
    assert len(snapshot) == 500
    assert snapshot[0][0] == pytest.approx(100.0)
    assert snapshot[-1][0] == pytest.approx(599.0)


def test_mode_and_recording_state_emit_updates(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    mode_events: list[str] = []
    recording_events: list[bool] = []

    store.sig_mode_updated.connect(mode_events.append)
    store.sig_recording_state_updated.connect(recording_events.append)

    store.set_current_mode("record")
    assert store.get_current_mode() == "RECORD"
    assert mode_events[-1] == "RECORD"

    store.set_recording_state(True)
    assert store.get_recording_state() is True
    assert recording_events[-1] is True


def test_save_settings_normalizes_and_merges_values(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    saved = store.save_settings(
        {
            "window_size": "12",
            "model_path": "models/test_model.tflite",
            "auto_save": "true",
        }
    )

    assert saved["window_size"] == 12
    assert saved["model_path"] == "models/test_model.tflite"
    assert saved["auto_save"] is True

    snapshot = store.get_settings_snapshot()
    assert snapshot["window_size"] == 12
    assert snapshot["model_path"] == "models/test_model.tflite"

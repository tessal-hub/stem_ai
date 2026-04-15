import os

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
            "idf_main_dir": str(tmp_path / "idf_project" / "main"),
        }
    )

    assert saved["window_size"] == 12
    assert saved["model_path"] == "models/test_model.tflite"
    assert saved["auto_save"] is True
    assert saved["idf_main_dir"].endswith("main")

    snapshot = store.get_settings_snapshot()
    assert snapshot["window_size"] == 12
    assert snapshot["model_path"] == "models/test_model.tflite"
    assert snapshot["idf_main_dir"].endswith("main")


# ── Sensor data ────────────────────────────────────────────────────────────────


def test_update_sensor_data_populates_all_six_buffers(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    store.update_sensor_data({"ax": 1.0, "ay": 2.0, "az": 3.0, "gx": 4.0, "gy": 5.0, "gz": 6.0})

    expected_values = {"ax": 1.0, "ay": 2.0, "az": 3.0, "gx": 4.0, "gy": 5.0, "gz": 6.0}
    for key, expected in expected_values.items():
        assert list(store.sensor_buffers[key])[-1] == pytest.approx(expected)


def test_update_sensor_data_appends_to_frame_history(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    store.update_sensor_data({"ax": 0.1, "ay": 0.2, "az": 0.3, "gx": 1.0, "gy": 2.0, "gz": 3.0})

    frames = store.get_recent_sensor_frames_snapshot()
    assert len(frames) == 1
    assert frames[0] == pytest.approx([0.1, 0.2, 0.3, 1.0, 2.0, 3.0])


def test_update_sensor_data_partial_dict_does_not_append_frame_history(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))

    store.update_sensor_data({"ax": 0.1, "ay": 0.2})

    frames = store.get_recent_sensor_frames_snapshot()
    assert frames == []


def test_clear_live_buffer_empties_the_buffer(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    store.add_live_sample([1, 2, 3, 4, 5, 6])
    store.add_live_sample([7, 8, 9, 10, 11, 12])

    store.clear_live_buffer()

    assert store.get_live_buffer_snapshot() == []


# ── Prediction state ────────────────────────────────────────────────────────────


def test_update_prediction_sets_state_and_emits_signal(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    received: list[tuple[str, float]] = []
    store.sig_prediction_updated.connect(lambda a, c: received.append((a, c)))

    store.update_prediction("SWIPE", 0.95)

    label, confidence = store.get_prediction_state()
    assert label == "SWIPE"
    assert confidence == pytest.approx(0.95)
    assert received == [("SWIPE", pytest.approx(0.95))]


# ── Connection state ────────────────────────────────────────────────────────────


def test_set_connection_status_updates_state_and_emits_signal(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    connection_events: list[tuple[bool, str]] = []
    store.sig_connection_state_updated.connect(lambda c, p: connection_events.append((c, p)))

    store.set_connection_status(True, "COM5")

    connected, port = store.get_connection_state()
    assert connected is True
    assert port == "COM5"
    assert connection_events[-1] == (True, "COM5")


def test_set_connection_status_disconnect_updates_state(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    store.set_connection_status(True, "COM5")

    store.set_connection_status(False, "None")

    connected, port = store.get_connection_state()
    assert connected is False


# ── ESP stats ──────────────────────────────────────────────────────────────────


def test_update_esp_stats_merges_values(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    stats_events: list[dict] = []
    store.sig_stats_updated.connect(lambda s: stats_events.append(dict(s)))

    store.update_esp_stats({"Battery": "80%"})

    assert store.esp32_stats["Battery"] == "80%"
    assert stats_events


def test_update_esp_stats_noop_for_empty_dict(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    stats_events: list[dict] = []
    store.sig_stats_updated.connect(lambda s: stats_events.append(dict(s)))

    store.update_esp_stats({})

    assert stats_events == []


# ── UDP health ─────────────────────────────────────────────────────────────────


def test_update_udp_health_updates_snapshot_and_emits_signal(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    udp_events: list[dict] = []
    store.sig_udp_health_updated.connect(lambda h: udp_events.append(dict(h)))

    store.update_udp_health({"udp_rate_hz": 50.0, "udp_loss_pct": 1.5})

    assert store.udp_health["udp_rate_hz"] == pytest.approx(50.0)
    assert store.udp_health["udp_loss_pct"] == pytest.approx(1.5)
    assert udp_events


def test_update_udp_health_noop_for_empty_dict(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    udp_events: list[dict] = []
    store.sig_udp_health_updated.connect(lambda h: udp_events.append(dict(h)))

    store.update_udp_health({})

    assert udp_events == []


# ── Live features ──────────────────────────────────────────────────────────────


def test_update_live_features_stores_and_emits(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    feature_events: list[dict] = []
    store.sig_live_features_updated.connect(lambda f: feature_events.append(dict(f)))

    store.update_live_features({"mean_ax": 0.5, "std_gx": 1.2})

    assert store.live_features == {"mean_ax": 0.5, "std_gx": 1.2}
    assert feature_events == [{"mean_ax": 0.5, "std_gx": 1.2}]


def test_update_live_features_noop_for_empty_dict(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    feature_events: list[dict] = []
    store.sig_live_features_updated.connect(lambda f: feature_events.append(dict(f)))

    store.update_live_features({})

    assert feature_events == []


# ── Database operations ─────────────────────────────────────────────────────────


def test_refresh_database_counts_csv_files_per_spell(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    spell_dir = dataset / "ACCIO"
    spell_dir.mkdir(parents=True)
    (spell_dir / "sample_1.csv").write_text("data")
    (spell_dir / "sample_2.csv").write_text("data")
    (spell_dir / "not_csv.txt").write_text("data")

    store = DataStore(dataset_dir=str(dataset))

    assert store.spell_counts.get("ACCIO") == 2


def test_get_spell_list_returns_known_spells(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    for spell in ("ACCIO", "WINGARDIUM"):
        (dataset / spell).mkdir(parents=True)

    store = DataStore(dataset_dir=str(dataset))

    spells = store.get_spell_list()
    assert set(spells) == {"ACCIO", "WINGARDIUM", "STAND BY"}


def test_get_samples_for_spell_returns_sorted_csv_names(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    spell_dir = dataset / "ACCIO"
    spell_dir.mkdir(parents=True)
    (spell_dir / "sample_b.csv").write_text("x")
    (spell_dir / "sample_a.csv").write_text("x")
    (spell_dir / "not_csv.txt").write_text("x")

    store = DataStore(dataset_dir=str(dataset))
    samples = store.get_samples_for_spell("ACCIO")

    assert samples == ["sample_a.csv", "sample_b.csv"]


def test_get_samples_for_nonexistent_spell_returns_empty(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    assert store.get_samples_for_spell("DOESNOTEXIST") == []


def test_save_cropped_data_creates_csv_file(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    data = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0], [7.0, 8.0, 9.0, 10.0, 11.0, 12.0]]

    result = store.save_cropped_data("accio", data)

    assert result is True
    spell_dir = tmp_path / "dataset" / "ACCIO"
    csv_files = list(spell_dir.glob("*.csv"))
    assert len(csv_files) == 1
    assert store.spell_counts.get("ACCIO") == 1


def test_save_cropped_data_does_not_write_meta_json(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    data = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]

    store.save_cropped_data("accio", data)

    spell_dir = tmp_path / "dataset" / "ACCIO"
    meta_files = list(spell_dir.glob("*.meta.json"))
    assert len(meta_files) == 0


def test_save_cropped_data_rejects_empty_data(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    assert store.save_cropped_data("accio", []) is False


def test_save_cropped_data_rejects_blank_spell_name(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    data = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]
    assert store.save_cropped_data("   ", data) is False


def test_delete_spell_removes_directory_and_files(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    spell_dir = dataset / "ACCIO"
    spell_dir.mkdir(parents=True)
    (spell_dir / "sample_1.csv").write_text("data")

    store = DataStore(dataset_dir=str(dataset))
    assert "ACCIO" in store.spell_counts

    result = store.delete_spell("ACCIO")

    assert result is True
    assert not spell_dir.exists()
    assert "ACCIO" not in store.spell_counts


def test_delete_spell_returns_false_for_nonexistent_spell(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    assert store.delete_spell("NOSUCHSPELL") is False


def test_delete_spell_returns_false_for_blank_name(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    assert store.delete_spell("   ") is False


def test_delete_spell_returns_false_for_system_spell(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    (dataset / "STAND BY").mkdir(parents=True)

    store = DataStore(dataset_dir=str(dataset))

    assert store.delete_spell("STAND BY") is False
    assert (dataset / "STAND BY").exists()


def test_standby_auto_recreates_when_missing_on_refresh(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    store = DataStore(dataset_dir=str(dataset))

    standby_dir = dataset / "STAND BY"
    assert standby_dir.exists()
    os.rmdir(standby_dir)
    assert not standby_dir.exists()

    store.refresh_database(force=True)

    assert standby_dir.exists()
    assert store.spell_counts.get("STAND BY") == 0


def test_migration_creates_backup_snapshot_when_legacy_meta_exists(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    legacy_dir = dataset / "ACCIO"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "sample_legacy.meta.json").write_text('{"tag":"old"}', encoding="utf-8")

    _ = DataStore(dataset_dir=str(dataset))

    backup_root = tmp_path / "_migration_backups"
    backups = [p for p in backup_root.iterdir() if p.is_dir()]
    assert backups
    manifest = backups[0] / "backup_manifest.json"
    assert manifest.exists()


def test_prediction_compat_with_legacy_model_after_standby_bootstrap(qapp, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    model_path = tmp_path / "legacy_model.tflite"
    model_path.write_bytes(b"legacy")

    store = DataStore(dataset_dir=str(dataset))
    store.save_settings({"model_path": str(model_path)})
    store.update_prediction("LEGACY_GESTURE", 0.81)

    label, confidence = store.get_prediction_state()
    assert label == "LEGACY_GESTURE"
    assert confidence == pytest.approx(0.81)
    assert store.get_settings_snapshot()["model_path"] == str(model_path)


# ── Settings reload ─────────────────────────────────────────────────────────────


def test_reload_settings_returns_current_snapshot(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    store.save_settings({"window_size": "20"})

    reloaded = store.reload_settings()

    assert reloaded["window_size"] == 20

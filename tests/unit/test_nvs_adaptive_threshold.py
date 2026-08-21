"""Unit tests for NVSBuildWorker adaptive per-class threshold calculation."""

from pathlib import Path
import numpy as np
import pytest

from logic.handler import NVSBuildWorker
import logic.handler as handler_mod


class _MockRecognizer:
    def __init__(self, emb_map: dict[str, np.ndarray]) -> None:
        self.emb_map = emb_map

    def _embed_batch(self, batch: np.ndarray) -> np.ndarray:
        first_val = float(batch[0, 0, 0])
        for key, base_emb in self.emb_map.items():
            if abs(first_val - float(key)) < 0.01:
                embs = np.repeat(base_emb[np.newaxis, :], len(batch), axis=0)
                return embs.astype(np.float32)
        return np.ones((len(batch), 16), dtype=np.float32)


def _write_mock_csv(file_path: Path, value: float, num_rows: int = 70) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["ax,ay,az,gx,gy,gz"]
    for _ in range(num_rows):
        lines.append(f"{value},{value},{value},0.0,0.0,0.0")
    file_path.write_text("\n".join(lines), encoding="utf-8")


def test_nvs_adaptive_threshold_well_separated_and_overlapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test adaptive thresholds on well-separated vs overlapping synthetic gestures."""
    captured: dict[str, list] = {}

    def mock_build_config_bin(gesture_names, centroids, is_spell_flags, thresholds, colors, out_path):
        captured["gesture_names"] = list(gesture_names)
        captured["centroids"] = list(centroids)
        captured["thresholds"] = list(thresholds)

    monkeypatch.setattr(handler_mod, "build_config_bin", mock_build_config_bin)

    dataset_dir = tmp_path / "dataset"
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Well-separated gestures (orthogonal unit vectors)
    # Spell A: [1, 0, 0, ...] -> identifier value 1.0
    # Spell B: [0, 1, 0, ...] -> identifier value 2.0
    emb1 = np.zeros(16, dtype=np.float32); emb1[0] = 1.0
    emb2 = np.zeros(16, dtype=np.float32); emb2[1] = 1.0

    _write_mock_csv(dataset_dir / "spells" / "SPELL_A" / "sample1.csv", value=1.0)
    _write_mock_csv(dataset_dir / "spells" / "SPELL_B" / "sample1.csv", value=2.0)

    recognizer_sep = _MockRecognizer({"1.0": emb1, "2.0": emb2})

    worker = NVSBuildWorker(
        spell_names=["SPELL_A", "SPELL_B"],
        dataset_dir=str(dataset_dir),
        spell_recognizer=recognizer_sep,
        app_data_dir=str(app_data_dir),
    )
    worker.run()

    assert "gesture_names" in captured, "build_config_bin was not called"
    name_to_thresh = dict(zip(captured["gesture_names"], captured["thresholds"]))
    assert "SPELL_A" in name_to_thresh
    assert "SPELL_B" in name_to_thresh
    thresh_a = name_to_thresh["SPELL_A"]
    thresh_b = name_to_thresh["SPELL_B"]

    # Assert both resolved thresholds land in [0.55, 0.70]
    assert 0.55 <= thresh_a <= 0.70
    assert 0.55 <= thresh_b <= 0.70
    # For orthogonal classes (max_other ≈ 0.0), threshold should be at base clamp 0.55
    assert pytest.approx(0.55, abs=0.01) == thresh_a
    assert pytest.approx(0.55, abs=0.01) == thresh_b

    # 2. Overlapping gestures (near-identical unit vectors: cos_sim > 0.95)
    # SPIRAL: [1, 0, 0, ...] -> identifier value 3.0
    # ROLL_WAND: [0.99, 0.141, 0, ...] (norm=1) -> identifier value 4.0
    emb_c = np.zeros(16, dtype=np.float32); emb_c[0] = 1.0
    emb_d = np.zeros(16, dtype=np.float32); emb_d[0] = 0.99; emb_d[1] = float(np.sqrt(1.0 - 0.99**2))

    dataset_overlap_dir = tmp_path / "dataset_overlap"
    _write_mock_csv(dataset_overlap_dir / "primitives" / "SPIRAL" / "sample1.csv", value=3.0)
    _write_mock_csv(dataset_overlap_dir / "primitives" / "ROLL_WAND" / "sample1.csv", value=4.0)

    recognizer_overlap = _MockRecognizer({"3.0": emb_c, "4.0": emb_d})

    worker_overlap = NVSBuildWorker(
        spell_names=[],
        dataset_dir=str(dataset_overlap_dir),
        spell_recognizer=recognizer_overlap,
        app_data_dir=str(app_data_dir),
    )
    worker_overlap.run()

    overlap_name_to_thresh = dict(zip(captured["gesture_names"], captured["thresholds"]))
    thresh_spiral = overlap_name_to_thresh["SPIRAL"]
    thresh_roll = overlap_name_to_thresh["ROLL_WAND"]

    # Threshold must be pushed toward high end (>= 0.65) due to overlap margin logic
    assert thresh_spiral >= 0.65
    assert thresh_roll >= 0.65
    assert thresh_spiral <= 0.70
    assert thresh_roll <= 0.70


def test_nvs_empty_sample_gesture_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A gesture with zero samples gets 0.70 threshold with zero centroid."""
    captured: dict[str, list] = {}

    def mock_build_config_bin(gesture_names, centroids, is_spell_flags, thresholds, colors, out_path):
        captured["gesture_names"] = list(gesture_names)
        captured["centroids"] = list(centroids)
        captured["thresholds"] = list(thresholds)

    monkeypatch.setattr(handler_mod, "build_config_bin", mock_build_config_bin)

    dataset_dir = tmp_path / "empty_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir(parents=True, exist_ok=True)

    worker = NVSBuildWorker(
        spell_names=["EMPTY_SPELL"],
        dataset_dir=str(dataset_dir),
        spell_recognizer=_MockRecognizer({}),
        app_data_dir=str(app_data_dir),
    )
    worker.run()

    assert "gesture_names" in captured, "build_config_bin was not called"
    name_to_thresh = dict(zip(captured["gesture_names"], captured["thresholds"]))
    assert name_to_thresh["EMPTY_SPELL"] == 0.70

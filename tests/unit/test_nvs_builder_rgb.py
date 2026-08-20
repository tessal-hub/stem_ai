"""Unit tests cho NVS builder với phần mở rộng RGB LED."""

import csv
from pathlib import Path
import struct
import pytest

from logic.tensorflow.nvs_builder import build_config_bin
import logic.tensorflow.nvs_builder as nvs_builder_mod


def test_nvs_builder_packs_rgb_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NVS builder phải đóng gói 3 bytes RGB vào cuối mỗi binary blob và thêm key version=2."""
    recorded_blobs: dict[str, bytes] = {}
    recorded_csv_rows: list[list[str]] = []

    def mock_call_api(csv_path: str, out_path: str, partition_size: str = "0x10000") -> None:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                recorded_csv_rows.append(row)
                if len(row) >= 4 and row[1] == "file" and row[2] == "binary":
                    bin_path = row[3]
                    with open(bin_path, "rb") as bf:
                        recorded_blobs[row[0]] = bf.read()
        Path(out_path).write_bytes(b"mock_nvs_bin")

    monkeypatch.setattr(nvs_builder_mod, "_call_nvs_gen_api", mock_call_api)

    gesture_names = ["LUMOS", "FIREBALL"]
    centroids = [[0.1] * 16, [0.2] * 16]
    is_spell_flags = [True, True]
    thresholds = [0.85, 0.90]
    colors = {
        "LUMOS": (255, 255, 200),
        "FIREBALL": (255, 50, 0),
    }

    out_file = tmp_path / "labels.bin"
    build_config_bin(
        gesture_names=gesture_names,
        centroids=centroids,
        is_spell_flags=is_spell_flags,
        thresholds=thresholds,
        colors=colors,
        out_path=str(out_file),
    )

    assert out_file.exists()

    # Kiểm tra version=2 trong CSV rows
    version_row = next((r for r in recorded_csv_rows if len(r) >= 4 and r[0] == "version"), None)
    assert version_row is not None
    assert version_row[3] == "2"

    # Kiểm tra blob size = 16*4 + 4 + 1 + 3 = 72 bytes
    lumos_blob = recorded_blobs.get("g0_cen")
    assert lumos_blob is not None
    assert len(lumos_blob) == 72

    # Unpack tail
    *_, is_spell, r, g, b = struct.unpack("<16ffBBBB", lumos_blob)
    assert is_spell == 1
    assert (r, g, b) == (255, 255, 200)

    fireball_blob = recorded_blobs.get("g1_cen")
    assert fireball_blob is not None
    assert len(fireball_blob) == 72
    *_, is_spell, r, g, b = struct.unpack("<16ffBBBB", fireball_blob)
    assert (r, g, b) == (255, 50, 0)


def test_nvs_builder_defaults_to_white_when_no_color_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NVS builder mặc định màu trắng (255, 255, 255) nếu không truyền màu."""
    recorded_blobs: dict[str, bytes] = {}

    def mock_call_api(csv_path: str, out_path: str, partition_size: str = "0x10000") -> None:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4 and row[1] == "file" and row[2] == "binary":
                    with open(row[3], "rb") as bf:
                        recorded_blobs[row[0]] = bf.read()
        Path(out_path).write_bytes(b"bin")

    monkeypatch.setattr(nvs_builder_mod, "_call_nvs_gen_api", mock_call_api)

    build_config_bin(
        gesture_names=["DEFAULT_SPELL"],
        centroids=[[0.0] * 16],
        is_spell_flags=[True],
        thresholds=[0.8],
        colors=None,
        out_path=str(tmp_path / "labels.bin"),
    )

    blob = recorded_blobs.get("g0_cen")
    assert blob is not None
    assert len(blob) == 72
    *_, is_spell, r, g, b = struct.unpack("<16ffBBBB", blob)
    assert (r, g, b) == (255, 255, 255)

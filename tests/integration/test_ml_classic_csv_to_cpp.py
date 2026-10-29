from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig


def _write_motion_csv(path: Path, class_index: int, file_index: int) -> None:
    phase = file_index * 0.17
    t = np.arange(64, dtype=np.float64)
    if class_index == 0:
        channels = (3000 * np.sin(t / 6 + phase), 400 * np.cos(t / 7), 16384 + 1800 * np.sin(t / 10),
                    5000 * np.sin(t / 5 + phase), 300 * np.cos(t / 8), 250 * np.sin(t / 11))
    else:
        channels = (400 * np.cos(t / 7), 3000 * np.sin(t / 6 + phase), 16384 + 1800 * np.sin(t / 10),
                    300 * np.cos(t / 8), 5000 * np.sin(t / 5 + phase), 250 * np.sin(t / 11))
    raw = np.column_stack(channels).astype(np.int16)
    scaled = raw.astype(np.float64)
    scaled[:, :3] /= 16384.0
    scaled[:, 3:] /= 131.0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ax", "ay", "az", "gx", "gy", "gz"))
        writer.writerows(scaled)


def test_csv_training_exports_matching_esp32_model(tmp_path):
    pytest.importorskip("sklearn")
    compiler = shutil.which("g++")
    if not compiler:
        pytest.skip("g++ required for host-side ESP32 model contract check")

    from ml_lab.core.hyperparam_schema import DecisionTreeConfig
    from ml_lab.core.pipeline import train_classic_model

    dataset = tmp_path / "spells"
    for class_index, class_name in enumerate(("TEST_ALPHA", "TEST_BETA")):
        class_dir = dataset / class_name
        class_dir.mkdir(parents=True)
        for file_index in range(4):
            _write_motion_csv(class_dir / f"sample_{file_index}.csv", class_index, file_index)

    train_samples, val_samples, class_names = split_user_dataset_file_level(
        dataset, val_fraction=0.25, window_size=64, step_size=16, seed=11
    )
    config = FeatureGroupConfig(include_magnitudes=False)
    extractor = ClassicFeatureExtractor(config)
    X_train, y_train = extractor.extract_from_samples(train_samples)
    X_val, y_val = extractor.extract_from_samples(val_samples)
    result = train_classic_model(
        X_train,
        y_train,
        X_val,
        y_val,
        class_names=class_names,
        feature_names=extractor.feature_names,
        algo="tree",
        config=DecisionTreeConfig(max_depth=3),
        feature_config=config,
        standby_thresholds=(0.12, 20.0),
    )

    firmware_dir = tmp_path / "firmware"
    firmware_dir.mkdir()
    header_path = firmware_dir / "model_classic.h"
    source_path = firmware_dir / "model_classic.cc"
    header_path.write_text(CCodeExporter().generate_header_string(result), encoding="utf-8")
    source_path.write_text(CCodeExporter().generate_source_string(result), encoding="utf-8")
    firmware_header = Path(__file__).resolve().parents[2] / "esp32_classic_ml" / "main" / "classic_features.h"
    (firmware_dir / "classic_features.h").write_text(firmware_header.read_text(encoding="utf-8"), encoding="utf-8")

    window = val_samples[0][0]
    scales = np.array([16384.0] * 3 + [131.0] * 3, dtype=np.float32)
    raw = np.rint(window * scales).astype(np.int16)
    expected_features = extractor.extract_from_window(window)
    raw_values = ", ".join(str(int(value)) for value in raw.ravel())
    runner = firmware_dir / "integration.cpp"
    runner.write_text(
        "#include \"model_classic.h\"\n#include \"classic_features.h\"\n"
        "#include <iomanip>\n#include <iostream>\n"
        "int main() {\n"
        f"  const int16_t raw[] = {{{raw_values}}};\n"
        "  float features[CLASSIC_NUM_FEATURES] = {};\n"
        "  int count = extract_classic_features(raw, 64, features);\n"
        "  float confidence = 0.0f; int prediction = classic_predict(features, &confidence);\n"
        "  std::cout << count << ' ' << prediction << ' ' << std::setprecision(9) << confidence;\n"
        "  for (int i = 0; i < count; ++i) std::cout << ' ' << std::setprecision(9) << features[i];\n"
        "}\n",
        encoding="utf-8",
    )
    executable = firmware_dir / "integration.exe"
    subprocess.run(
        [compiler, "-std=c++11", str(runner), str(source_path), "-o", str(executable), "-lm"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout
    values = np.fromstring(output, sep=" ")

    assert int(values[0]) == len(result.feature_names) == 63
    assert int(values[1]) == int(result.model.predict(expected_features[None, :])[0])
    np.testing.assert_allclose(values[3:], expected_features, rtol=2e-4, atol=2e-4)

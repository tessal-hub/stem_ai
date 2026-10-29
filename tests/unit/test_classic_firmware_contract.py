from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig


def test_exported_feature_profile_matches_esp32_extractor(tmp_path):
    compiler = shutil.which("g++")
    if not compiler:
        pytest.skip("g++ required for host-side ESP32 feature contract check")

    firmware_header = Path(__file__).resolve().parents[2] / "esp32_classic_ml" / "main" / "classic_features.h"
    profiles = (
        FeatureGroupConfig(),
        FeatureGroupConfig(include_magnitudes=False),
    )
    raw = np.column_stack(
        (
            2500 * np.sin(np.arange(64) / 7),
            1800 * np.cos(np.arange(64) / 9),
            16384 + 2200 * np.sin(np.arange(64) / 11),
            4300 * np.sin(np.arange(64) / 5),
            3100 * np.cos(np.arange(64) / 8),
            1900 * np.sin(np.arange(64) / 13),
        )
    ).astype(np.int16)
    normalized = raw.astype(np.float32)
    normalized[:, :3] /= 16384.0
    normalized[:, 3:] /= 131.0

    for index, config in enumerate(profiles):
        extractor = ClassicFeatureExtractor(config)
        result = SimpleNamespace(
            algo="tree",
            algo_name="Decision Tree",
            val_accuracy=1.0,
            cv_mean=1.0,
            class_names=["LUMOS", "NOX"],
            feature_names=extractor.feature_names,
            feature_config=config,
            standby_thresholds=(0.12, 20.0),
        )
        model_header = tmp_path / "model_classic.h"
        model_header.write_text(CCodeExporter().generate_header_string(result), encoding="utf-8")
        (tmp_path / "classic_features.h").write_text(firmware_header.read_text(encoding="utf-8"), encoding="utf-8")

        raw_values = ", ".join(str(int(value)) for value in raw.ravel())
        runner = tmp_path / "feature_contract.cpp"
        runner.write_text(
            "#include \"model_classic.h\"\n"
            "#include \"classic_features.h\"\n"
            "#include <iomanip>\n#include <iostream>\n"
            "int main() {\n"
            f"  const int16_t raw[] = {{{raw_values}}};\n"
            "  float features[CLASSIC_NUM_FEATURES] = {};\n"
            "  int count = extract_classic_features(raw, 64, features);\n"
            "  std::cout << count;\n"
            "  for (int i = 0; i < count; ++i) std::cout << ' ' << std::setprecision(9) << features[i];\n"
            "}\n",
            encoding="utf-8",
        )
        executable = tmp_path / f"feature_contract_{index}.exe"
        subprocess.run(
            [compiler, "-std=c++11", str(runner), "-o", str(executable), "-lm"],
            check=True,
            capture_output=True,
            text=True,
        )
        output = subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout
        values = np.fromstring(output, sep=" ")
        expected = extractor.extract_from_window(normalized)

        assert int(values[0]) == len(expected) == len(extractor.feature_names)
        np.testing.assert_allclose(values[1:], expected, rtol=2e-4, atol=2e-4)

"""
Test that file_level_split ensures ZERO data leakage across train and val windows.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pytest

from ml_lab.data.dataset_split import split_user_dataset_file_level


def test_classic_ml_split_no_leakage():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)

        # Create two classes with multiple files
        for spell in ["ACCIO", "LUMOS"]:
            s_dir = root / spell
            s_dir.mkdir(parents=True)
            for i in range(10):
                # Write 100 rows per file
                rows = ["ax,ay,az,gx,gy,gz"]
                # Give each file a distinct base offset so we can trace its windows
                offset = (100 if spell == "ACCIO" else 200) + i
                for _ in range(100):
                    rows.append(f"{offset},{offset},{offset},0,0,0")
                (s_dir / f"file_{i:02d}.csv").write_text("\n".join(rows), encoding="utf-8")

        train_windows, val_windows, class_names = split_user_dataset_file_level(
            root, val_fraction=0.3, window_size=64, step_size=16, seed=42
        )

        assert len(class_names) == 2
        assert len(train_windows) > 0
        assert len(val_windows) > 0

        # Check that unique offsets in train never overlap with offsets in val
        train_offsets = {round(float(w[0, 0]), 1) for w, _ in train_windows}
        val_offsets = {round(float(w[0, 0]), 1) for w, _ in val_windows}

        # Assert zero intersection (no leakage)
        intersection = train_offsets.intersection(val_offsets)
        assert len(intersection) == 0, f"Data leakage detected! Overlapping file offsets: {intersection}"

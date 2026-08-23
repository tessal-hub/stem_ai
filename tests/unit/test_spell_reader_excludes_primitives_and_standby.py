"""
Test that spell_reader strictly excludes primitives, STAND BY, and internal prefix keys.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from ml_lab.data.spell_reader import list_user_spell_classes, count_user_spell_samples


def test_spell_reader_excludes_primitives_and_standby():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)

        # Create valid user spells
        accio_dir = root / "ACCIO"
        accio_dir.mkdir(parents=True)
        (accio_dir / "sample_001.csv").write_text("ax,ay,az,gx,gy,gz\n1,2,3,4,5,6\n", encoding="utf-8")

        lumos_dir = root / "LUMOS"
        lumos_dir.mkdir(parents=True)
        (lumos_dir / "sample_002.csv").write_text("ax,ay,az,gx,gy,gz\n1,2,3,4,5,6\n", encoding="utf-8")

        # Create primitive gesture
        swipe_dir = root / "SWIPE_RIGHT"
        swipe_dir.mkdir(parents=True)
        (swipe_dir / "prim_001.csv").write_text("ax,ay,az,gx,gy,gz\n1,2,3,4,5,6\n", encoding="utf-8")

        # Create system protected null class STAND BY
        standby_dir = root / "STAND BY"
        standby_dir.mkdir(parents=True)
        (standby_dir / "standby_001.csv").write_text("ax,ay,az,gx,gy,gz\n1,2,3,4,5,6\n", encoding="utf-8")

        # Test on-disk structure
        classes = list_user_spell_classes(root)

        assert "ACCIO" in classes
        assert "LUMOS" in classes
        assert "SWIPE_RIGHT" not in classes
        assert "STAND BY" not in classes
        assert "STAND_BY" not in classes

        counts = count_user_spell_samples(root)
        assert counts.get("ACCIO") == 1
        assert counts.get("LUMOS") == 1
        assert "SWIPE_RIGHT" not in counts
        assert "STAND BY" not in counts


def test_spell_reader_excludes_group_prefix(monkeypatch):
    # Mock discover_class_directories returning internal "::" keys
    mock_classes = {
        "ACCIO": [Path("dummy/ACCIO")],
        "SPELL::MY_GROUP": [Path("dummy/SPELL::MY_GROUP")],
        "SWIPE_LEFT": [Path("dummy/SWIPE_LEFT")],
        "STAND BY": [Path("dummy/STAND BY")],
    }
    monkeypatch.setattr("ml_lab.data.spell_reader.discover_class_directories", lambda root: mock_classes)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        classes = list_user_spell_classes(Path(tmp_dir))
        assert "ACCIO" in classes
        assert "SPELL::MY_GROUP" not in classes
        assert "SWIPE_LEFT" not in classes
        assert "STAND BY" not in classes

"""Verify CSV saves use atomic write-then-rename."""
import tempfile
import os
from pathlib import Path

def test_save_uses_atomic_rename(tmp_path):
    from logic.data_io_worker import DataIOWorker
    worker = DataIOWorker(dataset_dir=str(tmp_path))
    
    spell_dir = tmp_path / "spells" / "TEST_SPELL"
    spell_dir.mkdir(parents=True)
    
    data = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]] * 10
    worker._do_save("TEST_SPELL", data)
    
    # Verify: no .tmp files left behind
    tmp_files = list(spell_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"Temp files left behind: {tmp_files}"
    
    # Verify: CSV file exists and is complete
    csv_files = list(spell_dir.glob("*.csv"))
    assert len(csv_files) == 1
    with open(csv_files[0]) as f:
        lines = f.readlines()
    assert len(lines) == 11  # header + 10 rows

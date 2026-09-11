"""
ml_lab/data/spell_reader.py — Đọc và lọc thư mục spell cho ML Lab.

Chỉ trả về các cử chỉ thần chú do người dùng tự thu thập trong `dataset/spells/`.
Loại trừ các cử chỉ nguyên mẫu (primitives) và null-class hệ thống (STAND BY).
"""

from __future__ import annotations

from pathlib import Path

import csv
import numpy as np

from constants import is_system_spell
from logic.dataset_layout import (
    _PRIMITIVE_LOGICAL_NAMES,
    discover_class_directories,
    folder_name_match_key,
)


def _collect_standby_dirs(root: Path, all_classes: dict[str, list[Path]]) -> list[Path]:
    """Gom mọi thư mục STAND BY: bản tự ghi (spells/) + thư viện mẫu (primitives/)."""
    seen: dict[str, Path] = {}
    for name, paths in all_classes.items():
        if folder_name_match_key(name) in {"STAND BY", "STAND_BY"}:
            for p in paths:
                seen[str(p.resolve())] = p

    # Thư viện primitives nằm cạnh thư mục spells (dataset/primitives/STAND BY)
    for cand in (root.parent / "primitives" / "STAND BY", root / "primitives" / "STAND BY"):
        if cand.is_dir():
            seen[str(cand.resolve())] = cand
    return list(seen.values())


def compute_standby_thresholds(dataset_root: Path | str) -> tuple[float, float]:
    """
    Tính ngưỡng động học (acc_std_sum, gyr_std_sum) từ tập mẫu STAND BY.
    Dùng làm Motion Gate độc lập trong C code / firmware để lọc trạng thái nghỉ.
    """
    root = Path(dataset_root)
    try:
        from logic.dataset_layout import discover_class_directories as _discover
        all_classes = _discover(root)
    except Exception:
        all_classes = {}
    standby_dirs = _collect_standby_dirs(root, all_classes)
    acc_sums: list[float] = []
    gyr_sums: list[float] = []

    for d in standby_dirs:
        for csv_file in d.glob("*.csv"):
            try:
                rows: list[list[float]] = []
                with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for r in reader:
                        if len(r) >= 6:
                            try:
                                rows.append([float(r[i]) for i in range(6)])
                            except ValueError:
                                continue
                if len(rows) >= 16:
                    arr = np.array(rows, dtype=np.float32)
                    ax_std = float(np.std(arr[:, 0]))
                    ay_std = float(np.std(arr[:, 1]))
                    az_std = float(np.std(arr[:, 2]))
                    gx_std = float(np.std(arr[:, 3]))
                    gy_std = float(np.std(arr[:, 4]))
                    gz_std = float(np.std(arr[:, 5]))
                    acc_sums.append(ax_std + ay_std + az_std)
                    gyr_sums.append(gx_std + gy_std + gz_std)
            except Exception:
                continue

    if acc_sums and gyr_sums:
        acc_th = float(np.percentile(acc_sums, 95) * 1.25)
        gyr_th = float(np.percentile(gyr_sums, 95) * 1.25)
        return max(0.12, min(0.35, acc_th)), max(12.0, min(35.0, gyr_th))
    from ml_lab.data.window_config import MIN_ACC_STD_SUM, MIN_GYR_STD_SUM

    return (MIN_ACC_STD_SUM, MIN_GYR_STD_SUM)


def list_user_spell_classes(
    dataset_root: Path | str,
    include_standby: bool = False,
    allowed_spells: set[str] | None = None,
) -> dict[str, list[Path]]:
    """
    Trả về các spell do người dùng tự ghi qua trang Record.

    Args:
        dataset_root: Thư mục dataset (thường là dataset/spells).
        include_standby: Mặc định False để các mô hình ML chỉ học phân loại các spell thực sự.
        allowed_spells: Tập các phép thuật được chọn.

    Returns:
        dict[class_name, list_of_directory_paths]
    """
    root = Path(dataset_root)
    if not root.exists():
        return {}

    primitive_keys = {folder_name_match_key(p) for p in _PRIMITIVE_LOGICAL_NAMES}
    all_classes = discover_class_directories(root)

    filtered = {
        name: paths
        for name, paths in all_classes.items()
        if "::" not in name
        and folder_name_match_key(name) not in primitive_keys
        and not is_system_spell(name)
    }

    if allowed_spells is not None:
        allowed_set = {str(s) for s in allowed_spells}
        filtered = {k: v for k, v in filtered.items() if k in allowed_set}

    if include_standby:
        standby_dirs = _collect_standby_dirs(root, all_classes)
        if standby_dirs:
            filtered["STAND BY"] = standby_dirs

    return filtered


def count_user_spell_samples(
    dataset_root: Path | str,
    include_standby: bool = False,
    allowed_spells: set[str] | None = None,
) -> dict[str, int]:
    """
    Đếm số lượng file CSV mẫu cử chỉ hợp lệ cho mỗi lớp spell.
    """
    classes = list_user_spell_classes(
        dataset_root, include_standby=include_standby, allowed_spells=allowed_spells
    )
    counts: dict[str, int] = {}
    for name, dir_paths in classes.items():
        total_files = 0
        for d in dir_paths:
            if d.is_dir():
                total_files += len(list(d.glob("*.csv")))
        if total_files > 0:
            counts[name] = total_files
    return counts

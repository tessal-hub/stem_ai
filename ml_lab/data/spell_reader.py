"""
ml_lab/data/spell_reader.py — Đọc và lọc thư mục spell cho ML Lab.

Chỉ trả về các cử chỉ thần chú do người dùng tự thu thập trong `dataset/spells/`.
Loại trừ các cử chỉ nguyên mẫu (primitives) và null-class hệ thống (STAND BY).
"""

from __future__ import annotations

from pathlib import Path

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


def list_user_spell_classes(
    dataset_root: Path | str, include_standby: bool = False
) -> dict[str, list[Path]]:
    """
    Trả về các spell do người dùng tự ghi qua trang Record.

    Mặc định loại trừ:
    - 23 primitive gesture (SWIPE_RIGHT, CIRCLE_CW, ... dùng để train encoder few-shot)
    - STAND BY / STAND_BY (null-class hệ thống, được bảo vệ, không phải cử chỉ thật)
    - group-prefix key nội bộ dạng "SPELL::group_name" (DataStore tự sinh để đếm theo prefix)

    Args:
        dataset_root: Thư mục dataset (thường là dataset/spells).
        include_standby: Bật để thêm lớp STAND BY ("không vung gì cả") — gộp cả
            thư viện mẫu primitives/STAND BY và bản tự ghi của người dùng.

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

    if include_standby:
        standby_dirs = _collect_standby_dirs(root, all_classes)
        if standby_dirs:
            filtered["STAND BY"] = standby_dirs

    return filtered


def count_user_spell_samples(
    dataset_root: Path | str, include_standby: bool = False
) -> dict[str, int]:
    """
    Đếm số lượng file CSV mẫu cử chỉ hợp lệ cho mỗi lớp spell.
    """
    classes = list_user_spell_classes(dataset_root, include_standby=include_standby)
    counts: dict[str, int] = {}
    for name, dir_paths in classes.items():
        total_files = 0
        for d in dir_paths:
            if d.is_dir():
                total_files += len(list(d.glob("*.csv")))
        if total_files > 0:
            counts[name] = total_files
    return counts

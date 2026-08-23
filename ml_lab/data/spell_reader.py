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


def list_user_spell_classes(dataset_root: Path | str) -> dict[str, list[Path]]:
    """
    Trả về CHỈ các spell do người dùng tự ghi qua trang Record.

    Loại trừ:
    - 23 primitive gesture (SWIPE_RIGHT, CIRCLE_CW, ... dùng để train encoder few-shot)
    - STAND BY / STAND_BY (null-class hệ thống, được bảo vệ, không phải cử chỉ thật)
    - group-prefix key nội bộ dạng "SPELL::group_name" (DataStore tự sinh để đếm theo prefix)

    Returns:
        dict[class_name, list_of_directory_paths]
    """
    root = Path(dataset_root)
    if not root.exists():
        return {}

    primitive_keys = {folder_name_match_key(p) for p in _PRIMITIVE_LOGICAL_NAMES}
    all_classes = discover_class_directories(root)

    return {
        name: paths
        for name, paths in all_classes.items()
        if "::" not in name
        and folder_name_match_key(name) not in primitive_keys
        and not is_system_spell(name)
    }


def count_user_spell_samples(dataset_root: Path | str) -> dict[str, int]:
    """
    Đếm số lượng file CSV mẫu cử chỉ hợp lệ cho mỗi lớp spell.
    """
    classes = list_user_spell_classes(dataset_root)
    counts: dict[str, int] = {}
    for name, dir_paths in classes.items():
        total_files = 0
        for d in dir_paths:
            if d.is_dir():
                total_files += len(list(d.glob("*.csv")))
        if total_files > 0:
            counts[name] = total_files
    return counts

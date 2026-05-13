"""
logic/dataset_layout.py — Quy ước thư mục dataset (spells/primitives + legacy flat).

Dùng chung cho train, audit, và ghi/đọc file CSV để luôn trùng với cấu trúc
dataset/ ở gốc workspace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from constants import canonical_system_spell, normalize_spell_name

# Khớp logic `DataStore.save_cropped_data` + tên thư mục thực tế "STAND BY".
_PRIMITIVE_LOGICAL_NAMES = frozenset(
    {
        "SWIPE_RIGHT",
        "SWIPE_UP",
        "THRUST",
        "CIRCLE_CW",
        "CIRCLE_CCW",
        "WRIST_FLICK",
        "ZIGZAG",
        "STAND_BY",
    }
)


def folder_name_match_key(name: str) -> str:
    """Khóa so sánh tên thư mục lớp (underscore / khoảng trắng)."""
    return name.replace("_", " ").strip().upper()


def _routes_to_primitives(canonical_folder: str) -> bool:
    if canonical_folder in _PRIMITIVE_LOGICAL_NAMES:
        return True
    return canonical_folder == "STAND BY"


def filter_selected_class_names(
    class_names: Sequence[str],
    selected_spells: set[str] | None,
) -> list[str]:
    """Lọc tên lớp theo danh sách spell chọn (không phân biệt underscore / khoảng trắng)."""
    if not selected_spells:
        return sorted(class_names)
    sel = {s.strip() for s in selected_spells if s.strip()}
    if not sel:
        return sorted(class_names)
    sel_keys = {folder_name_match_key(s) for s in sel}
    return sorted(
        n
        for n in class_names
        if n.strip() in sel or folder_name_match_key(n) in sel_keys
    )


def discover_class_directories(dataset_root: Path) -> dict[str, list[Path]]:
    """Liệt kê thư mục lớp (spell/primitive), gộp cả layout lồng và flat legacy.

    Layout lồng: ``dataset/spells/<Tên>``, ``dataset/primitives/<Tên>``.
    Legacy: ``dataset/<Tên>`` (bỏ qua thư mục tên ``spells`` / ``primitives``).

    Một tên lớp có thể có nhiều đường dẫn (ví dụ migration từ flat sang lồng).

    Args:
        dataset_root: Thư mục gốc dataset (thường là ``config.DATASET_DIR``).

    Returns:
        Map ``tên_thư_mục_trên_đĩa`` -> danh sách thư mục chứa CSV.
    """
    out: dict[str, list[Path]] = {}
    if not dataset_root.exists():
        return out

    for branch_name in ("spells", "primitives"):
        branch = dataset_root / branch_name
        if not branch.is_dir():
            continue
        for child in sorted(branch.iterdir()):
            if not child.is_dir():
                continue
            name = child.name.strip()
            if name:
                out.setdefault(name, []).append(child)

    skip = {"spells", "primitives"}
    for child in sorted(dataset_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.lower() in skip:
            continue
        name = child.name.strip()
        if name:
            out.setdefault(name, []).append(child)

    return out


def spell_write_dir(dataset_root: Path, spell_label: str) -> Path:
    """Thư mục ghi CSV mới cho một spell/primitive (khớp DataStore.save_cropped_data).

    Args:
        dataset_root: Thư mục gốc dataset.
        spell_label: Tên spell từ UI hoặc recorder.

    Returns:
        Đường dẫn thư mục lớp (đã suy ra spells vs primitives).
    """
    normalized_name = normalize_spell_name(spell_label)
    folder_name = canonical_system_spell(normalized_name)
    spells_root = dataset_root / "spells"
    prim_root = dataset_root / "primitives"
    if spells_root.is_dir() or prim_root.is_dir():
        base = prim_root if _routes_to_primitives(folder_name) else spells_root
        disk_folder = "STAND BY" if _routes_to_primitives(folder_name) and folder_name_match_key(
            folder_name
        ) in {"STAND BY", "STAND_BY"} else folder_name
        return base / disk_folder
    return dataset_root / folder_name


def storage_dirs_for_spell(dataset_root: Path, spell_name: str) -> list[Path]:
    """Mọi thư mục lưu trữ hiện có cho một spell (phục vụ xóa / quản lý).

    Args:
        dataset_root: Thư mục gốc dataset.
        spell_name: Tên spell cần tìm.

    Returns:
        Danh sách thư mục (không trùng), có thể rỗng.
    """
    mapping = discover_class_directories(dataset_root)
    want = folder_name_match_key(canonical_system_spell(normalize_spell_name(spell_name)))
    seen: dict[str, Path] = {}
    for key, paths in mapping.items():
        if folder_name_match_key(key) != want:
            continue
        for p in paths:
            seen[str(p.resolve())] = p
    return list(seen.values())

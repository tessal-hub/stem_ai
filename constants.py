"""
Hằng số và hàm tiện ích dùng chung cho toàn bộ dự án.

Quản lý danh sách spell hệ thống (protected) và cung cấp các hàm
chuẩn hóa tên spell để đảm bảo so sánh nhất quán.
"""

from __future__ import annotations

SYSTEM_SPELL_NAMES = {"STAND BY"}


def normalize_spell_name(name: str) -> str:
    """Chuẩn hóa tên spell thành chữ hoa, loại bỏ khoảng trắng thừa.

    Args:
        name: Tên spell cần chuẩn hóa.

    Returns:
        Tên spell đã chuẩn hóa (uppercase, single-space).
    """
    return " ".join(str(name).strip().split()).upper()


SYSTEM_SPELL_NAMES_NORMALIZED = {normalize_spell_name(name) for name in SYSTEM_SPELL_NAMES}


def is_system_spell(name: str) -> bool:
    """Kiểm tra xem spell có phải là spell hệ thống (protected) không.

    Args:
        name: Tên spell cần kiểm tra.

    Returns:
        True nếu spell thuộc danh sách hệ thống.
    """
    return normalize_spell_name(name) in SYSTEM_SPELL_NAMES_NORMALIZED


def canonical_system_spell(name: str) -> str:
    """Trả về tên chính tắc của spell hệ thống, hoặc tên đã chuẩn hóa.

    Args:
        name: Tên spell cần tra cứu.

    Returns:
        Tên chính tắc nếu là system spell, ngược lại trả về tên đã chuẩn hóa.
    """
    normalized = normalize_spell_name(name)
    for candidate in SYSTEM_SPELL_NAMES:
        if normalize_spell_name(candidate) == normalized:
            return candidate
    return normalized

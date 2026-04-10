"""Shared project constants and helpers."""

from __future__ import annotations

SYSTEM_SPELL_NAMES = {"STAND BY"}


def normalize_spell_name(name: str) -> str:
    """Return uppercase spell name with collapsed internal whitespace."""
    return " ".join(str(name).strip().split()).upper()


SYSTEM_SPELL_NAMES_NORMALIZED = {normalize_spell_name(name) for name in SYSTEM_SPELL_NAMES}


def is_system_spell(name: str) -> bool:
    """Return True when the provided spell name is protected/system-managed."""
    return normalize_spell_name(name) in SYSTEM_SPELL_NAMES_NORMALIZED


def canonical_system_spell(name: str) -> str:
    """Return canonical spelling for a known system spell, otherwise normalized name."""
    normalized = normalize_spell_name(name)
    for candidate in SYSTEM_SPELL_NAMES:
        if normalize_spell_name(candidate) == normalized:
            return candidate
    return normalized

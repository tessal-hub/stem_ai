"""Unit tests for ml_lab serial port coordinator (no Qt needed)."""

from __future__ import annotations

import pytest

from ml_lab.core.serial_coordinator import (
    acquire,
    owner_of,
    register_owner,
    release,
    unregister_owner,
)


@pytest.fixture(autouse=True)
def _clean():
    for owner in ("t_a", "t_b"):
        try:
            release(owner)
        except Exception:
            pass
        try:
            unregister_owner(owner)
        except Exception:
            pass
    yield
    for owner in ("t_a", "t_b"):
        try:
            release(owner)
        except Exception:
            pass
        try:
            unregister_owner(owner)
        except Exception:
            pass


def test_first_claim_wins_port():
    assert acquire("t_a", "COM3") is True
    assert owner_of("COM3") == "t_a"


def test_second_owner_steals_and_auto_releases_first():
    released: list[str] = []
    register_owner("t_a", lambda: released.append("t_a"))
    register_owner("t_b", lambda: released.append("t_b"))
    assert acquire("t_a", "COM3") is True
    assert acquire("t_b", "COM3") is True
    assert released == ["t_a"]
    assert owner_of("COM3") == "t_b"


def test_port_match_case_insensitive():
    register_owner("t_a", lambda: None)
    assert acquire("t_a", "COM3") is True
    assert owner_of("com3") == "t_a"


def test_release_frees_port():
    register_owner("t_a", lambda: None)
    acquire("t_a", "COM7")
    release("t_a", "COM7")
    assert owner_of("COM7") is None


def test_empty_port_rejected():
    assert acquire("t_a", "") is False
    assert acquire("t_a", "   ") is False

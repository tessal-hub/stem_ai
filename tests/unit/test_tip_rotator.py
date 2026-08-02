"""Unit tests for TipRotator."""
from __future__ import annotations

from logic.tip_rotator import TipRotator


def test_no_immediate_repeat_across_draws() -> None:
    """next_tip() never returns same string twice in a row for pool >= 2."""
    rotator = TipRotator(["A", "B", "C", "D"])
    previous = rotator.next_tip()
    for _ in range(50):
        current = rotator.next_tip()
        assert current != previous, f"Immediate repeat detected: {current}"
        previous = current


def test_reload_pool_reflects_new_content() -> None:
    """reload_pool() with new pool immediately reflects new content."""
    rotator = TipRotator(["old_A", "old_B"])
    rotator.next_tip()

    rotator.reload_pool(["new_X", "new_Y", "new_Z"])
    tip = rotator.next_tip()
    assert tip.startswith("new_"), f"Expected new pool content, got: {tip}"


def test_empty_pool_returns_empty_string() -> None:
    """Empty pool returns '' without raising."""
    rotator = TipRotator([])
    assert rotator.next_tip() == ""


def test_single_item_pool_always_returns_that_item() -> None:
    """Single-item pool always returns that item."""
    rotator = TipRotator(["ONLY"])
    for _ in range(10):
        assert rotator.next_tip() == "ONLY"

"""Unit tests for confidence-based quote selection in home_tips_i18n and PageHome."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from logic.home_tips_i18n import get_tip_pool
from logic.locale_manager import locale_manager
from ui.page_home import PageHome


def test_get_tip_pool_by_confidence_level_vi() -> None:
    """Verify VI tip pools vary by confidence level."""
    high_pool = get_tip_pool("vi", "high")
    mod_pool = get_tip_pool("vi", "moderate")
    low_pool = get_tip_pool("vi", "low")
    full_pool = get_tip_pool("vi", None)

    assert any("hình mẫu" in t for t in high_pool)
    assert any("Vẫy run tay" in t for t in mod_pool)
    assert any("STAND BY" in t for t in low_pool)

    # Full pool contains all
    assert len(full_pool) == len(high_pool) + len(mod_pool) + len(low_pool)


def test_get_tip_pool_by_confidence_level_en() -> None:
    """Verify EN tip pools vary by confidence level."""
    high_pool = get_tip_pool("en", "high")
    mod_pool = get_tip_pool("en", "moderate")
    low_pool = get_tip_pool("en", "low")

    assert any("reference shape" in t for t in high_pool)
    assert any("shaky wave" in t for t in mod_pool)
    assert any("STAND BY" in t for t in low_pool)


def test_page_home_confidence_quote_rotation(qapp) -> None:
    """Verify PageHome updates confidence level and updates quote on timer tick."""
    store = MagicMock()
    store.is_connected = True
    store.spell_history = []
    store.spell_counts = {}

    page = PageHome(store)
    initial_quote = page.lbl_tip.text()

    # Moderate confidence recognized spell
    page.show_recognized_spell("Lumos", 0.75)
    assert page._last_confidence_level == "moderate"
    # Immediate quote should NOT change (timeout preserved)
    assert page.lbl_tip.text() == initial_quote

    # Trigger timer tick
    page._on_tip_timer_tick()
    new_quote = page.lbl_tip.text()
    lang = page._tip_rotator._pool  # or get_tip_pool(locale_manager.current_language, "moderate")
    mod_pool = get_tip_pool(locale_manager.current_language, "moderate")
    assert new_quote in mod_pool

    # High confidence recognized spell
    page.show_recognized_spell("Nox", 0.95)
    assert page._last_confidence_level == "high"

    # Trigger timer tick
    page._on_tip_timer_tick()
    high_quote = page.lbl_tip.text()
    high_pool = get_tip_pool(locale_manager.current_language, "high")
    assert high_quote in high_pool

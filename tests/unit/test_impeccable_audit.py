"""Unit test for Impeccable design system & technical quality audit."""
from pathlib import Path
from scripts.audit_impeccable import (
    audit_palettes,
    audit_absolute_bans,
    audit_hardcoded_colors,
)


def test_impeccable_palette_contrast():
    """All palette colors must pass WCAG 2.1 AA (>= 4.5:1)."""
    failures = audit_palettes()
    assert not failures, f"Contrast failures detected: {failures}"


def test_impeccable_zero_absolute_bans():
    """Zero side-stripes, gradient text, glassmorphism defaults, or eyebrows."""
    findings = audit_absolute_bans()
    assert not findings, f"Absolute ban violations found: {findings}"


def test_impeccable_token_discipline():
    """UI pages must not contain raw untokenized hex colors in inline setStyleSheet."""
    hits = audit_hardcoded_colors()
    assert not hits, f"Untokenized hardcoded colors found: {hits}"

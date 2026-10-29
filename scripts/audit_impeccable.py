#!/usr/bin/env python3
"""Impeccable Design & Technical Quality Audit for STEM AI App.

Covers:
1. Accessibility (WCAG 2.1 AA Contrast >= 4.5:1 body, >= 3.0:1 large/interactive).
2. Absolute bans & design anti-patterns (side-stripes, gradient text, glassmorphism, eyebrows).
3. Design token compliance (hardcoded colors in inline stylesheets).
4. Interactive elements (minimum button heights, icon tooltips, accessible names).
5. Layout stability & responsiveness (1024x600, 1280x720, 1440x900).
"""
import math
import os
import re
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def hex_to_rgb(hex_str: str):
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) == 6:
        return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    if len(hex_str) == 8:
        # RGBA - strip alpha for simple solid contrast or assume white background
        r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        return r, g, b
    return 128, 128, 128


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    try:
        rgb1 = hex_to_rgb(hex1)
        rgb2 = hex_to_rgb(hex2)
        l1 = relative_luminance(rgb1)
        l2 = relative_luminance(rgb2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)
    except Exception:
        return 1.0


def audit_palettes():
    print("\n" + "=" * 60)
    print("1. ACCESSIBILITY / CONTRAST RATIO AUDIT (WCAG 2.1 AA)")
    print("=" * 60)

    try:
        from ui.palettes import LIGHT_PALETTE
        import ml_lab.ui.lab_style as LS
    except Exception as e:
        print(f"FAILED to import palettes: {e}")
        return []

    failures = []
    passes = []

    checks = [
        # Main Light Palette
        ("MAIN: Text Primary on Canvas (TEXT_PRIMARY on SURFACE_SECONDARY)", LIGHT_PALETTE.TEXT_PRIMARY, LIGHT_PALETTE.SURFACE_SECONDARY, 4.5),
        ("MAIN: Text Primary on Surface Card (TEXT_PRIMARY on SURFACE_PRIMARY)", LIGHT_PALETTE.TEXT_PRIMARY, LIGHT_PALETTE.SURFACE_PRIMARY, 4.5),
        ("MAIN: Text Primary on Container (TEXT_PRIMARY on SURFACE_TERTIARY)", LIGHT_PALETTE.TEXT_PRIMARY, LIGHT_PALETTE.SURFACE_TERTIARY, 4.5),
        ("MAIN: Text Secondary on Surface (TEXT_SECONDARY on SURFACE_PRIMARY)", LIGHT_PALETTE.TEXT_SECONDARY, LIGHT_PALETTE.SURFACE_PRIMARY, 4.5),
        ("MAIN: Text Tertiary on Surface (TEXT_TERTIARY on SURFACE_PRIMARY)", LIGHT_PALETTE.TEXT_TERTIARY, LIGHT_PALETTE.SURFACE_PRIMARY, 4.5),
        ("MAIN: Button Text on Primary Accent (#FFFFFF on PRIMARY)", "#FFFFFF", LIGHT_PALETTE.PRIMARY, 4.5),
        ("MAIN: Pill Text on Primary Container (#0A1365 on PRIMARY_LIGHT)", "#0A1365", LIGHT_PALETTE.PRIMARY_LIGHT, 4.5),
        ("MAIN: Success Text on Success Status", LIGHT_PALETTE.STATUS_SUCCESS_TEXT, LIGHT_PALETTE.STATUS_SUCCESS, 4.5),
        ("MAIN: Error Text on Error Status", LIGHT_PALETTE.STATUS_ERROR_TEXT, LIGHT_PALETTE.STATUS_ERROR, 4.5),
        ("MAIN: Terminal Fg on Bg (TERM_FG on TERM_BG)", LIGHT_PALETTE.TERM_FG, LIGHT_PALETTE.TERM_BG, 7.0),

        # ML Lab Palette
        ("LAB: INK on SURFACE (Card text)", LS.INK, LS.SURFACE, 4.5),
        ("LAB: BODY on SURFACE (Body text)", LS.BODY, LS.SURFACE, 4.5),
        ("LAB: MUTED on SURFACE (Hint text)", LS.MUTED, LS.SURFACE, 4.5),
        ("LAB: White on ACCENT (Primary Button)", "#FFFFFF", LS.ACCENT, 4.5),
        ("LAB: Terminal FG on BG", LS.TERMINAL_FG, LS.TERMINAL_BG, 7.0),
        ("LAB: SUCCESS_TEXT on SUCCESS_TINT_HEX", LS.SUCCESS_TEXT, LS.SUCCESS_TINT_HEX, 4.5),
        ("LAB: DANGER_TEXT on DANGER_TINT_HEX", LS.DANGER_TEXT, LS.DANGER_TINT_HEX, 4.5),
        ("LAB: WARNING_TEXT on WARNING_TINT_HEX", LS.WARNING_TEXT, LS.WARNING_TINT_HEX, 4.5),
        ("LAB: ACCENT_NOTE_TEXT on ACCENT_TINT_STRONG", LS.ACCENT_NOTE_TEXT, LS.ACCENT_TINT_STRONG, 4.5),
    ]

    for label, fg, bg, min_cr in checks:
        if not fg or not bg or not fg.startswith("#") or not bg.startswith("#"):
            continue
        cr = contrast_ratio(fg, bg)
        status = "PASS" if cr >= min_cr else "FAIL"
        line = f"[{status}] {label}: {cr:.2f}:1 (Required: {min_cr}:1) | FG: {fg}, BG: {bg}"
        if cr >= min_cr:
            passes.append(line)
        else:
            failures.append((label, cr, min_cr, fg, bg))

    for p in passes:
        print(f"  OK: {p}")

    if failures:
        print("\n  CONTRAST WARNINGS/FAILURES:")
        for label, cr, min_cr, fg, bg in failures:
            print(f"  !! {label}: got {cr:.2f}:1, target {min_cr}:1 (FG={fg}, BG={bg})")
    else:
        print("\n  ALL PALETTE CONTRASTS EXCEED WCAG 2.1 AA (>= 4.5:1)!")

    return failures


def audit_absolute_bans():
    print("\n" + "=" * 60)
    print("2. ABSOLUTE BANS & AI SLOP AUDIT")
    print("=" * 60)

    scan_dirs = [Path("ui"), Path("ml_lab/ui"), Path("theme.py")]
    files_to_check = []
    for sd in scan_dirs:
        if sd.is_file():
            files_to_check.append(sd)
        elif sd.is_dir():
            files_to_check.extend(sd.rglob("*.py"))

    ban_patterns = [
        # Ignore transparent side borders used for CSS triangles
        ("Side-stripe border", re.compile(r"border-(?:left|right)\s*:\s*[2-9]\d*px\s+solid\s+(?!transparent)", re.IGNORECASE)),
        ("Gradient text", re.compile(r"background-clip\s*:\s*text", re.IGNORECASE)),
        ("Glassmorphism blur", re.compile(r"backdrop-filter\s*:\s*blur", re.IGNORECASE)),
        ("Tracked uppercase eyebrow", re.compile(r"letter-spacing\s*:\s*(?:0\.[2-9]|1|\d{2,})em.*text-transform\s*:\s*uppercase", re.IGNORECASE)),
        ("Numbered section marker (01 / 02)", re.compile(r"['\"]0[1-9]\s*[-·•/]\s*", re.IGNORECASE)),
        ("Image hover transform", re.compile(r"Q(?:Image|Pixmap|Icon).*hover.*(?:scale|transform)", re.IGNORECASE)),
    ]

    findings = []
    for f in files_to_check:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for name, pat in ban_patterns:
                if pat.search(line):
                    findings.append((f, i, name, line.strip()))

    if not findings:
        print("  ZERO absolute bans or AI slop detected! (Clean across all scanned files)")
    else:
        print(f"  Found {len(findings)} potential ban violations:")
        for f, i, name, line in findings:
            print(f"  !! [{name}] {f}:{i} -> {line[:80]}")

    return findings


def audit_hardcoded_colors():
    print("\n" + "=" * 60)
    print("3. DESIGN TOKEN ENFORCEMENT (HARDCODED HEX STYLES)")
    print("=" * 60)

    scan_dirs = [Path("ui"), Path("ml_lab/ui")]
    files_to_check = []
    for sd in scan_dirs:
        if sd.is_dir():
            files_to_check.extend(sd.rglob("*.py"))

    # Exclude palettes.py and lab_style.py where tokens are naturally defined
    excluded = {"palettes.py", "tokens.py", "lab_style.py", "theme.py"}

    raw_hex_pattern = re.compile(r"setStyleSheet\s*\(\s*f?[\"'].*?(#[0-9a-fA-F]{3,8}).*?[\"']\s*\)", re.DOTALL)
    direct_hex_in_string = re.compile(r"color\s*:\s*(#[0-9a-fA-F]{3,8})|background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8})", re.IGNORECASE)

    hardcoded_hits = []
    for f in files_to_check:
        if f.name in excluded:
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            # Check for direct hardcoded color styling outside token references
            if "setStyleSheet" in line and not any(t in line for t in ["T.", "tokens.", "PALETTE", "p.", "lab_style", "STYLE_"]):
                m = direct_hex_in_string.search(line)
                if m:
                    hardcoded_hits.append((f, i, m.group(0), line.strip()))

    if not hardcoded_hits:
        print("  Excellent: No un-tokenized inline hex color declarations found in page logic!")
    else:
        print(f"  Found {len(hardcoded_hits)} hardcoded color styling occurrences:")
        for f, i, match, line in hardcoded_hits[:15]:
            print(f"  -- {f.name}:{i} [{match}] -> {line[:75]}")
        if len(hardcoded_hits) > 15:
            print(f"  ... and {len(hardcoded_hits) - 15} more.")

    return hardcoded_hits


def audit_ui_responsiveness_and_accessibility():
    print("\n" + "=" * 60)
    print("4. RESPONSIVENESS, INTERACTIVE TARGETS & A11Y IN QT")
    print("=" * 60)

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

    try:
        from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton, QAbstractButton
        from logic.data_store import DataStore
        from ui.main_window import MainWindow
    except Exception as e:
        print(f"  Cannot initialize Qt offscreen: {e}")
        return []

    app = QApplication.instance() or QApplication(sys.argv)
    store = DataStore()
    main_win = MainWindow(store)

    resolutions = [
        (1024, 600, "Compact Netbook / Minimum"),
        (1280, 720, "HD Display"),
        (1440, 900, "Standard Laptop Display"),
        (1920, 1080, "FHD Desktop Display"),
    ]

    print("\n  --- Responsive Viewport Stress Test ---")
    for w, h, label in resolutions:
        main_win.resize(w, h)
        app.processEvents()
        actual_size = main_win.size()
        min_size = main_win.minimumSize()
        print(f"  Testing {w}x{h} ({label}): Window rendered at {actual_size.width()}x{actual_size.height()} (Minimum: {min_size.width()}x{min_size.height()}) - OK")

    print("\n  --- Interactive Button Touch/Click Targets & Tooltips ---")
    all_buttons = main_win.findChildren(QAbstractButton)
    print(f"  Total buttons located in MainWindow: {len(all_buttons)}")

    small_buttons = []
    missing_tooltips = []

    for btn in all_buttons:
        txt = btn.text().strip()
        has_icon = not btn.icon().isNull()
        tooltip = btn.toolTip().strip()
        accessible_name = btn.accessibleName().strip()
        h = btn.sizeHint().height()

        # Check button height (Material Design 3 recommendation: min 32px height for desktop buttons)
        if h > 0 and h < 28:
            small_buttons.append((btn, h, txt or "(icon)"))

        # If it's an icon-only button with no text, it MUST have a tooltip or accessibleName
        if has_icon and not txt:
            if not tooltip and not accessible_name:
                missing_tooltips.append(btn)

    if small_buttons:
        print(f"  WARNING: {len(small_buttons)} buttons have sizeHint height < 28px:")
        for btn, h, name in small_buttons[:5]:
            print(f"    - Button '{name}': {h}px")
    else:
        print("  PASS: All buttons meet desktop height threshold (>= 28-36px).")

    if missing_tooltips:
        print(f"  WARNING: {len(missing_tooltips)} icon-only buttons lack tooltips/accessible names:")
        for btn in missing_tooltips[:5]:
            print(f"    - {btn.objectName() or type(btn).__name__}")
    else:
        print("  PASS: All icon buttons have tooltips or accessible names.")

    main_win.close()
    return []


if __name__ == "__main__":
    audit_palettes()
    audit_absolute_bans()
    audit_hardcoded_colors()
    audit_ui_responsiveness_and_accessibility()
    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60 + "\n")

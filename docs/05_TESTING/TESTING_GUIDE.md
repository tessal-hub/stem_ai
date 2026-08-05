# Testing Guide

Status: Active
Language: English
Owner: QA and Core Team
Last Updated: 2026-08-05

## Test Commands

- `.\.venv\Scripts\pytest.exe tests/`
- `.\.venv\Scripts\pytest.exe tests/unit -v`
- `.\.venv\Scripts\pytest.exe tests/integration -v`
- `.\.venv\Scripts\pytest.exe tests/perf -v`

## Status & Coverage

- **Suite Status**: 100% PASS (164/164 tests passing).
- **Unit Layer**: Protocol parsing, data store, rarity, recorder, tips, security guards.
- **Integration Layer**: Handler guards, mode transitions, signal routing.
- **Performance Layer**: End-to-end latency (50Hz), packet drop, UI block time (<50ms), plot FPS.

## Standalone Executable Packaging

- **Build Command**: `.\.venv\Scripts\pyinstaller.exe STEMSpellBook.spec --noconfirm`
- **Output Artifact**: `dist/STEMSpellBook.exe` (~499 MB standalone executable with bundled Python runtime, PyQt6, TensorFlow, C++ DLLs, and resources).
- **Portability**: 100% self-contained for Windows 10/11 offline environments.

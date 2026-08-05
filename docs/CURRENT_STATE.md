# STEM AI — Current System State & Release Summary

Status: Active (Production-Ready)
Language: English / Vietnamese
Owner: Core Maintainers
Last Updated: 2026-08-05

## 1. System Overview

STEM Spell Book is a high-performance desktop application for hardware IMU telemetry collection, TinyML model training, gesture dataset management, and serial/UDP firmware flashing for ESP32 magic wands.

- **UI Framework**: PyQt6 (Native Windows/macOS design system with Vanguard/Apple layering).
- **Inference Engine**: TensorFlow / TFLite Micro (INT8 quantized gesture encoder).
- **Hardware Protocols**: Serial (UART frame protocol) and UDP Telemetry (port 5555).

---

## 2. Recent Key Enhancements (2026-08-05)

### A. UI & Layout Modernization
- **PageSetting 2-Column Dashboard**:
  - **Left Column**: System Appearance & Language (fully vertically stacked inputs), IMU Hardware configuration, Hardware & TinyML Metrics, Primitive Dataset Quality Scanner.
  - **Right Column**: Firmware Flasher & Terminal Console Widget.
  - **Control Bar**: Sticky bottom bar with Revert, Save, and real-time status messages.
- **MacShell Sidebar**: Cleaned navigation sidebar by removing obsolete hint text (`_swipe_hint`).

### B. High-Performance Zero-Lag UI Optimizations
- **TerminalWidget Bulk Line Trimming**: Replaced O(N) Python iteration with C++ 1-shot block selection (`movePosition(NextBlock, KeepAnchor, overflow)`).
- **Batch Text Updates**: Wrapped terminal document modifications with `setUpdatesEnabled(False/True)` to eliminate UI main thread layout recalculation freezes.
- **Smart Timer Lifecycle Management**: Overrode `showEvent` / `hideEvent` and bounded deque buffers to suspend background UI renders when tabs/pages are hidden.

### C. Standalone Executable Packaging
- **PyInstaller Specification**: `STEMSpellBook.spec` produces a self-contained single `.exe` file (`dist/STEMSpellBook.exe`).
- **Dependencies Bundled**: Python 3.12, PyQt6, TensorFlow/Keras, SciPy, PyQtGraph, ESPTool, VC++ runtimes.
- **Portability**: 100% offline portable without requiring external Python environments.

---

## 3. Verification & Quality Assurance

- **Total Test Suite**: 164 tests across unit, integration, and performance modules.
- **Pass Rate**: 100% (164/164 passed).
- **Latency / Performance**:
  - UI Event Loop Block Spike: < 50 ms
  - End-to-End Latency (50Hz): Passed
  - Signal Roundtrip: Passed
  - Plot FPS: Passed

---

## 4. Key Files & Artifacts

- **Executable Output**: `dist/STEMSpellBook.exe`
- **Spec File**: `STEMSpellBook.spec`
- **Main Entry Point**: `main.py`
- **Settings Page**: `ui/page_setting.py`
- **Terminal Widget**: `ui/terminal_widget.py`
- **Navigation Shell**: `ui/mac_shell.py`

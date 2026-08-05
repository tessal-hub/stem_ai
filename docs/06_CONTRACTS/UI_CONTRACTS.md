# UI Contracts

Status: Active
Language: English
Owner: UI and Handler Maintainers
Last Updated: 2026-08-05

This document is the frozen contract between UI pages and orchestration logic.
Signal and method names in this file are compatibility boundaries.

## Pages Covered

- PageHome
- PageRecord
- PagePrimitiveCollect
- PageWand
- PageSetting

## Contract Rules

1. Do not rename public signals or inbound methods without updating this file and all handlers.
2. Keep payload shapes stable.
3. Preserve backward-compat attributes required by handler wiring.
4. Use deprecation path instead of silent contract breakage.

## Compatibility Notes

- `combo_serial_ports` remains a required compatibility attribute for existing handler logic.
- Worker to UI signal paths remain handler-mediated and must not bypass orchestration.
- `PageHome` inbound compatibility contract methods:
  - `set_connection_status(connected: bool)`
  - `set_mode(mode: str)`
  - `apply_ui_language()`
  - `refresh_styles()`
  - `show_recognized_spell(action: str, confidence: float)`
  - `update_spell_history(history: list[dict])`
  - `update_loaded_spells(spells: set[str])`
- `PageSetting` single-page 2-column layout:
  - Left column: Appearance & Language (vertical form items), IMU Sensor Config, Hardware Metrics, Dataset Quality Scan.
  - Right column: Firmware Flasher & Terminal Console.
  - Sticky bottom action bar: Revert, Save, Status message.
- `MacShell`: Nav hint label (`_swipe_hint`) removed from sidebar while preserving touch/mouse swipe gestures.
- `TerminalWidget`: Optimized bulk block removal (`movePosition` with `QTextCursor.MoveOperation.NextBlock`) and batch updates with `setUpdatesEnabled(False/True)` for zero-lag high-throughput logging.
- `Wand3DWidget`: Retired from runtime data path (no longer embedded on PageHome or updated via serial/sensor signals).

# UI Contracts

Status: Active
Language: English
Owner: UI and Handler Maintainers
Last Updated: 2026-04-21

This document is the frozen contract between UI pages and orchestration logic.
Signal and method names in this file are compatibility boundaries.

## Pages Covered

- PageHome
- PageRecord
- PageStatistics
- PageWand
- PageSetting
- Wand3DWidget

## Contract Rules

1. Do not rename public signals or inbound methods without updating this file and all handlers.
2. Keep payload shapes stable.
3. Preserve backward-compat attributes required by handler wiring.
4. Use deprecation path instead of silent contract breakage.

## Compatibility Notes

- combo_serial_ports remains a required compatibility attribute for existing handler logic.
- Worker to UI signal paths remain handler-mediated and must not bypass orchestration.

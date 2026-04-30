# Architecture Overview

Status: Active
Language: English
Owner: Core Team
Last Updated: 2026-04-21

## System Shape

The application is a PyQt desktop system with a UI layer, handler orchestration, background workers, and data/model services.

## Core Runtime Boundaries

- UI pages emit user actions as Qt signals.
- Handler maps UI actions to worker operations and datastore updates.
- Workers run in dedicated threads for serial, feature extraction, flashing, and I/O.
- DataStore is the state hub for samples, spell counts, and runtime statistics.

## Canonical References

- DATA_FLOW.md: event and data movement through the app.
- WORKER_THREADING.md: worker responsibilities and thread safety rules.
- ../06_CONTRACTS/UI_CONTRACTS.md: frozen method and signal contracts.

## Change Guardrails

1. Avoid direct UI to worker coupling.
2. Keep thread boundaries explicit.
3. Keep public signal and method names backward-compatible unless contract is updated.

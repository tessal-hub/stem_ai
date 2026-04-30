# Testing Guide

Status: Active
Language: English
Owner: QA and Core Team
Last Updated: 2026-04-21

## Test Commands

- pytest
- pytest tests/unit -v
- pytest tests/integration -v
- pytest tests/perf -v

## Test Layers

- Unit: protocol parsing, datastore, rarity, recorder, helpers.
- Integration: handler guards, signal routing, mode transitions.
- Performance: latency, UI blocking, packet stability, plot responsiveness.

## Required Checks

1. Malformed frame rejection.
2. Mode and connection guard enforcement.
3. Protected system spell behavior.
4. Dataset save/delete/export reliability.
5. Thread-safe signal flow in live pipeline.

## Coverage Targets

Prioritize high coverage on core runtime modules in logic.

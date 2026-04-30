# AI Agent Guide

Status: Active
Language: English
Owner: Core Maintainers
Last Updated: 2026-04-21

## Purpose

This guide defines mandatory architecture rules for AI agents modifying the project.

## Hard Constraints

1. Keep UI and logic layers separated.
2. Route UI actions through handler orchestration.
3. Use queued cross-thread signals for worker-to-UI flow.
4. Avoid main-thread blocking operations.
5. Keep contracts stable unless explicitly migrated.

## Architecture Anchors

- Handler is the runtime coordinator.
- DataStore is the shared state authority.
- Worker classes own I/O and heavy processing.
- UI pages are signal emitters and renderers.

## Change Discipline

1. Define data flow before coding.
2. Apply logic changes before UI wiring changes.
3. Update canonical docs when contracts or flow change.
4. Add or update tests for guards and regressions.

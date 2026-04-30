# Design System

Status: Active
Language: English
Owner: UI Maintainers
Last Updated: 2026-04-21

## Source of Truth

All visual constants are defined in centralized token/style modules.
Do not hardcode colors, spacing, or component metrics in page files.

## Core Modules

- ui/tokens.py
- ui/modern_layout.py
- ui/component_factory.py
- theme.py

## Design Principles

1. Token-first styling.
2. Consistent spacing scale.
3. Consistent card and control patterns.
4. Accessible text contrast and state feedback.

## Component Coverage

- Navigation shell and page layouts.
- Buttons and action states.
- Inputs and forms.
- Cards, lists, progress, terminal widgets.
- Rarity badges and telemetry surfaces.

## Change Process

1. Add or update tokens in shared modules.
2. Apply tokenized style in component/page.
3. Document new token usage in DESIGN_TOKENS.md.
4. Avoid introducing one-off visual constants.

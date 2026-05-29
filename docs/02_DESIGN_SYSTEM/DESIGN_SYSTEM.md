# Design System

Status: Active
Language: English
Owner: UI Maintainers
Last Updated: 2026-04-21

## Source of Truth

All visual constants are defined in centralized token/style modules (`ui/tokens.py`).
**Do not hardcode colors, spacing, or component metrics in page files.**
**Do not use `setStyleSheet` in Python classes.** All styling must be applied via global QSS in `theme.py` (or a `.qss` file) using object names (`setObjectName()`) and dynamic properties.

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

1. Add or update tokens in shared modules (`tokens.py`).
2. Add QSS rules to `theme.py` targeting specific Object Names (`#MyWidget`) or custom properties (`[state="active"]`).
3. Apply styling in components by calling `self.setObjectName("MyWidget")` and updating dynamic properties.
4. Document new token usage in `DESIGN_TOKENS.md`.
5. Strictly avoid introducing one-off visual constants or inline `setStyleSheet` calls.

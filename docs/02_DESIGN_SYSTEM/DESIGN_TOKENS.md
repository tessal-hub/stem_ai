# Design Tokens

Status: Active
Language: English
Owner: UI Maintainers
Last Updated: 2026-04-21

All colors, dimensions, and style strings must come from ui/tokens.py and related centralized UI style modules.
Do not hardcode visual constants directly in page files.

## Token Source of Truth

- ui/tokens.py
- ui/modern_layout.py
- ui/component_factory.py

## Token Categories

- Color palette: primary, secondary, surface, text, status, rarity.
- Spacing and sizing: margins, paddings, fixed heights, panel widths.
- QSS style presets: buttons, cards, inputs, progress bars, lists, terminal widgets.

## Usage Rules

1. Reuse existing token names where possible.
2. Add new tokens in centralized modules only.
3. When introducing a new component style, document the token and intended usage in this file and DESIGN_SYSTEM.md.

## Legacy Mapping

The historical theme references were archived and merged into this token guide:

- ../ARCHIVE/2026-04/MODERN_THEME_IMPLEMENTATION_2026-04.md
- ../ARCHIVE/2026-04/MODERN_THEME_COLOR_REFERENCE_2026-04.md

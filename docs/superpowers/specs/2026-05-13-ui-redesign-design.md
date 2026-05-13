# STEM AI UI Redesign Design

Status: Proposed (Approved in chat)  
Owner: UI Maintainers  
Last Updated: 2026-05-13

## 1. Problem Statement

The current UI is functional but visually inconsistent across pages and does not present a unified, high-clarity workflow for hardware status, recording, model workflows, and telemetry-heavy surfaces.  
The project needs a UI that better fits its product identity: a modern, minimal lab-console style, light-first with dark fallback, while preserving runtime stability.

## 2. Goals

1. Deliver a coherent visual system across navigation shell and all pages.
2. Improve scanability of status, actions, telemetry, and progress states.
3. Keep existing Handler/UI contracts stable (signals, public methods, payload shapes).
4. Support light-first theme with token-driven dark fallback.
5. Introduce minor UX flow improvements without changing core behavior.

## 3. Non-Goals

1. No architectural change to worker orchestration.
2. No direct UI-to-worker coupling.
3. No renaming/removal of contract-bound signals or methods.
4. No large feature additions unrelated to UI/UX fit.

## 4. Constraints (Canonical Docs)

1. Token-first styling: no one-off visual constants in page files.
2. UI contracts are frozen unless explicitly updated with compatibility path.
3. UI remains view layer; Handler and DataStore own orchestration/state authority.
4. Existing compatibility attributes used by Handler must be preserved.

## 5. Design Approach

Chosen approach: **Layout + token redesign**.

Why this approach:

1. It provides meaningful UX gains (hierarchy, clarity, consistency).
2. It keeps risk lower than a full component-system rewrite.
3. It aligns with current codebase conventions and docs guardrails.

## 6. Visual Direction

### 6.1 Brand and Atmosphere

- Style: modern lab-console minimal.
- Default mode: light-first.
- Alternate mode: dark fallback via shared tokens.
- Emphasis: precise, calm, technical; not playful or neon-heavy.

### 6.2 Visual Hierarchy

All pages use a shared structure:

1. **Status strip** (current mode/connection/critical state).
2. **Primary action band** (the next most likely user action).
3. **Main workspace** (plots/viewer/terminal/forms).
4. **Secondary rail** (lists, metadata, auxiliary controls).

### 6.3 Token Strategy

- Centralize colors, spacing, radii, state colors, and typography in `ui/tokens.py`.
- Keep spacing scale from `ui/modern_layout.py` and use it consistently.
- Avoid inline style strings in page files except template assembly already used by token constants.

## 7. Information Architecture by Surface

### 7.1 Navigation Shell (`MacShell`)

1. Keep current page routing and swipe behavior.
2. Improve active nav state visibility (clear active rail + icon/text contrast).
3. Make toolbar context stronger: page title + concise operational subtitle.
4. Keep sidebar width and interaction density ergonomic for telemetry workflows.

### 7.2 Home

1. Keep 3D orientation viewer as hero card.
2. Right rail reorganized into:
   - Mode card
   - Device/manager health card
   - Spellbook quick-access card
3. Improve status semantics (connected/disconnected/mode states) with consistent color mapping.

### 7.3 Record

1. Reframe as guided workflow:
   - Spell selection and record controls at top
   - Dual telemetry plots in center
   - Sample management rail on side
2. Keep record/stop/snip behavior and signals unchanged.
3. Clarify frozen/live state transitions visually.

### 7.4 Statistics

1. Promote live features and model build status into prominent cards.
2. Keep mastery distribution and spell drill-down but unify card style and typography.
3. Improve progress/error/success readability in model workflow surfaces.

### 7.5 Primitives

1. Keep collection start/stop/capture flow.
2. Strengthen capture readiness visibility and empty-state guidance.
3. Align controls and quality cues with shared card/action patterns.

### 7.6 Wand

1. Keep split tooling layout (connection, flash/build, terminal, stats, payload).
2. Normalize panel hierarchy and button priority levels.
3. Improve terminal framing and warning/error emphasis consistency.

### 7.7 Setting

1. Keep two-column form structure and firmware section.
2. Standardize section headers, input states, validation cues, and danger-zone treatment.
3. Keep settings save semantics and emitted payload unchanged.

## 8. Minor UX Flow Improvements (Allowed Scope)

1. Deterministic control enable/disable patterns based on mode/connection/recording state.
2. Consistent status copy style for progress, warnings, and errors.
3. More explicit empty states and recovery hints in list/graph/terminal-adjacent areas.
4. Consistent destructive-action confirmation affordances.

## 9. Data Flow and Contract Safety

1. No change to core flow: `UI signals -> Handler -> workers/DataStore -> UI updates`.
2. Preserve all contract-sensitive public methods/signals and compatibility attributes.
3. Any new UI helper methods remain internal/private to page components.

## 10. Accessibility and Interaction Quality

1. Keep and extend accessible names for newly emphasized controls.
2. Preserve keyboard navigation order where practical; update tab order in redesigned areas.
3. Maintain clear contrast and state differentiation in both light and dark modes.

## 11. Verification Strategy

1. Update/add integration tests where UI state wiring is affected.
2. Keep existing handler guard and contract tests green.
3. Validate visual consistency manually across all pages in both theme modes.
4. Confirm no regressions in critical actions (connect, record, snip, build, flash, save settings).

## 12. Implementation Impact (Expected Files)

Primary expected touchpoints:

- `ui/tokens.py`
- `ui/mac_shell.py`
- `ui/page_home.py`
- `ui/page_record.py`
- `ui/page_statistics.py`
- `ui/page_primitive_collect.py`
- `ui/page_wand.py`
- `ui/page_setting.py`
- Supporting UI component/style helpers as needed (`ui/component_factory.py`, `ui/modern_layout.py`, etc.)

No contract changes are planned in `logic/handler.py` for this UI redesign scope.

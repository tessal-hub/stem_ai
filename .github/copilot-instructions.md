# Copilot instructions for STEM AI

## Project shape

- This is a PyQt6 desktop app for real-time wand/gesture control, dataset recording, and TinyML/ESP32 firmware workflows.
- `main.py` bootstraps `DataStore`, `MainWindow`, and `Handler`, applies the theme, and starts the Qt event loop.
- Keep the architecture boundary intact:
  - `ui/` is view-only.
  - `logic/` owns workers, parsing, orchestration, and state.
  - `DataStore` is the shared runtime state hub.
  - `Handler` is the orchestration boundary between UI and workers.
- Background work lives in QThreads/workers; never block the Qt main thread.

## Commands

- Install dependencies: `python -m pip install -r requirements.txt`
- Run the app: `python main.py`
- Run all tests: `pytest`
- Run unit tests: `pytest tests/unit -v`
- Run one unit test file: `pytest tests/unit/test_frame_protocol.py -v`
- Run integration tests: `pytest tests/integration -v`
- Run performance tests: `pytest tests/perf -v`

## Key conventions

- Read `docs/README.md`, `docs/01_ARCHITECTURE/OVERVIEW.md`, `docs/06_CONTRACTS/UI_CONTRACTS.md`, and `docs/05_TESTING/TESTING_GUIDE.md` before changing flows or contracts.
- Treat docs under `docs/` as canonical; archive files are historical, and worktree snapshots are not source of truth.
- UI pages should use centralized tokens and QSS in `theme.py` / `ui/tokens.py`; avoid inline `setStyleSheet` and one-off visual constants.
- Do not rename public UI signals or inbound methods without updating the UI contracts.
- In `logic/`, avoid `QtWidgets` imports; logic modules should stay pure Python/QtCore-level.
- Use queued cross-thread signal connections for worker-to-UI updates.
- Preserve port ownership rules: serial, flash, and upload actions are mutually exclusive.
- Protected system spells are defined in `constants.SYSTEM_SPELL_NAMES`; use the normalization helpers before comparing spell names.
- `DataIOWorker` uses a tuple-based job queue; `DataRecorder` writes CSV samples on a worker thread; both are designed to keep I/O off the UI thread.
- Docstrings/comments in the codebase are commonly written in Vietnamese; match the surrounding file when editing existing modules.

Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.

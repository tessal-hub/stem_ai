# STEM AI Current State

Status: Active; CI configured; hardware commissioning pending
Language: English / Vietnamese
Last updated: 2026-09-30

## Application

### UI refinement — 2026-09-30

- Training and flashing are separate actions. Model Lab disables flashing after input changes and checks CSV metadata before opening the flash dialog.
- Settings and Wand panels scroll/reflow at small desktop sizes; ML Lab panels preserve control sizes with native scroll areas.
- Legacy dark settings resolve to the supported light theme. Algorithm editors and settings fields have accessible labels.
- Data Studio shows loading/error/retry instructions and clears stale analysis. Home instructions follow connection and loaded spell state.
- Closing ML Lab requests worker interruption and keeps the event loop active until all tracked threads stop. Main-window shutdown waits for ML Lab; an in-progress library fit must finish before closing.
- Verification: 44 focused tests passed; 33 offscreen renders generated, key small-window screens visually inspected. Real model training remains unverified here because this Python environment lacks scikit-learn; hardware and screen-reader checks remain pending.

STEM Spell Book is a Windows-first desktop app for recording wand IMU data, managing gesture datasets, and running live recognition. The main app uses a TensorFlow few-shot encoder. ML Lab is a separate scikit-learn workflow for classic models, model inspection, C++ export, and ESP32 flashing.

The default classic feature profile emits 75 features. ML Lab can disable feature groups; exported model headers pass that profile to the firmware extractor and fail compilation when feature counts disagree.

## Verification

### Audit recheck fixes — 2026-09-30

- Cropped saves keep the raw CSV until the replacement is committed with `os.replace`. Queue-full and write failures show retry feedback; concurrent UI saves cannot overwrite pending save context. Accepted saves drain before DataIO shutdown and retain the dataset path captured when queued.
- ML Lab uses `DataStore.dataset_dir`, including custom and legacy layouts. Changing the dataset replaces the Lab window only after its workers stop; closing the main app cancels reopening.
- Serial disconnect retains its worker and port claim until `finished`, without waiting on the UI thread. Both apps and flash dialogs honor failed acquisition and ask the user to retry after release.
- Verification: 61 focused tests passed across separate runs (21 Handler guards, 29 worker/persistence/coordinator checks, 7 UI regressions, 4 new audit regressions). Record error and Serial disconnect screens were rendered and visually inspected at small desktop sizes. This is not a full-suite, real-training, or hardware validation result.

### Main app audit fixes — 2026-09-30

- Record plots update when the 500-sample rolling buffer changes without growing.
- Recording UI follows the recorder's file-open/state signals. Rejected starts and file errors appear on Record; disconnected Stop no longer reports readiness.
- Main shutdown requests worker interruption, keeps the event loop active, and delays closing until Handler and UDP threads finish. Finite library/build work may still need time to complete.
- Record and Primitive pages scroll at 920×640, with primary controls first. Settings/encoder action labels switch between Vietnamese and English.
- Verification: 47 focused recorder, Handler, shutdown and UI regression tests passed. Isolated probes showed updated chart values and shutdown request time of approximately 0.1 ms (formerly approximately 302 ms); this measures UI blocking, not total task completion time. Small-window screenshots include top and bottom scroll positions. Physical recording/flashing remains pending.

- CI runs `python -m pytest tests -q` on Python 3.12 for Windows and Ubuntu.
- Host C++ contract tests compare Python and ESP32 feature vectors for default and reduced profiles. Integration test covers CSV split, training, C++ export, feature extraction, and prediction. `g++` is required for these checks.
- CI configuration is present; report pass status from the latest workflow run, not this document.
- ESP-IDF build, physical flashing, sensor calibration, and real-wand behavior require the ESP-IDF toolchain and hardware.

## Packaging

`STEMSpellBook.spec` builds an onedir package. Executable path: `dist/STEMSpellBook/STEMSpellBook.exe`. Run the manual `Windows package smoke` workflow or build with `python -m PyInstaller STEMSpellBook.spec --noconfirm` after installing `requirements-build.txt`.

The package does not include the ESP-IDF project. Place `esp32_classic_ml/` beside the executable and install/activate ESP-IDF before using ML Lab flashing.

# Testing Guide

Python support target: 3.12. Install test dependencies with `python -m pip install -r requirements-dev.txt`.

## Test Commands

- Full suite: `python -m pytest tests -q`
- Unit tests: `python -m pytest tests/unit -q`
- Integration tests: `python -m pytest tests/integration -q`
- Performance tests: `python -m pytest tests/perf -q`

GitHub Actions runs the full suite on Windows and Ubuntu. The C++ contract tests need `g++`; without it, pytest marks those tests skipped. The CSV-to-C++ integration test also needs scikit-learn, installed through `requirements-dev.txt`.

Performance tests use short local profiles by default. Set `PERF_STRICT=1` when running on a stable benchmark machine; strict mode is not part of ordinary CI.

## Windows Package Smoke

Install the optional training and build dependencies, then build the onedir app:

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller STEMSpellBook.spec --noconfirm
```

Expected executable: `dist/STEMSpellBook/STEMSpellBook.exe`. The manual `Windows package smoke` GitHub Actions workflow checks this output and uploads the package artifact.

ESP-IDF firmware compilation and physical flash tests remain separate hardware checks. The package needs an `esp32_classic_ml/` folder beside its executable. Build current ML Lab sources with `idf.py build` in that project before flashing; the app rejects missing or stale binaries.

## UI refinement regression

Run `python -m pytest tests/unit/test_ui_refinement.py tests/unit/test_window_ml_lab.py -q`.
Checks cover stale-model flashing, CSV changes, analysis errors, legacy theme settings, Home guidance, and main-window shutdown while ML Lab work is running.
Manually inspect Settings/Wand at 920×640 and all ML Lab tabs at 960×600; scroll to reach lower controls. Confirm keyboard focus and screen-reader labels on Windows.

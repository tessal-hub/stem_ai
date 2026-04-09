from __future__ import annotations

from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent


def _detect_workspace_file() -> Path:
    candidates = sorted(WORKSPACE_ROOT.glob("*.code-workspace"))
    if candidates:
        return candidates[0]
    return WORKSPACE_ROOT / f"{WORKSPACE_ROOT.name}.code-workspace"


APP_DATA_DIR = WORKSPACE_ROOT / "app_data"
DATASET_DIR = APP_DATA_DIR / "dataset"
DEFAULT_MODEL_PATH = APP_DATA_DIR / "model.tflite"
VSCODE_WORKSPACE_FILE = _detect_workspace_file()
GESTURE_MODEL_CC_OUTPUT = APP_DATA_DIR / "gesture_model.cc"


def ensure_data_dir() -> Path:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR

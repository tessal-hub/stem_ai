"""
Cấu hình đường dẫn và thư mục làm việc của dự án.

Module này cung cấp các hằng số đường dẫn chính (workspace root,
thư mục dataset, model output) và hàm đảm bảo cấu trúc thư mục
tồn tại trước khi ứng dụng chạy I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path

import os

if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).resolve().parent
    # Kiểm tra quyền ghi — fallback về %APPDATA% nếu thư mục là read-only (e.g. Program Files)
    _test_file = _exe_dir / ".write_test"
    try:
        _test_file.touch()
        _test_file.unlink()
        WORKSPACE_ROOT = _exe_dir
    except (PermissionError, OSError):
        WORKSPACE_ROOT = Path(os.environ.get("APPDATA", Path.home())) / "STEMSpellBook"
else:
    WORKSPACE_ROOT = Path(__file__).resolve().parent

# Ensure packages from local .venv (e.g. esptool, esp_idf_nvs_partition_gen) are importable as fallback
_venv_site = WORKSPACE_ROOT / ".venv" / "Lib" / "site-packages"
if _venv_site.is_dir() and str(_venv_site) not in sys.path:
    sys.path.append(str(_venv_site))

APP_DATA_DIR = WORKSPACE_ROOT / "app_data"
USER_DATA_DIR = WORKSPACE_ROOT / "user_data"
DATASET_DIR = WORKSPACE_ROOT / "dataset"
SPELL_DIR = DATASET_DIR / "spells"
PRIMITIVE_DIR = DATASET_DIR / "primitives"

if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
    _bundled_sounds = Path(sys._MEIPASS) / "assets" / "sounds"
    SOUNDS_PRESET_DIR = _bundled_sounds if _bundled_sounds.is_dir() else (WORKSPACE_ROOT / "assets" / "sounds")
else:
    SOUNDS_PRESET_DIR = WORKSPACE_ROOT / "assets" / "sounds"

SOUNDS_USER_DIR = USER_DATA_DIR / "sounds"
FIRMWARE_PROJECT_ROOT = WORKSPACE_ROOT / "mpu6050"
FIRMWARE_BIN_DIR = WORKSPACE_ROOT / "firmware"
DEFAULT_MODEL_PATH = APP_DATA_DIR / "model.tflite"
GESTURE_MODEL_CC_OUTPUT = APP_DATA_DIR / "gesture_model.cc"


def ensure_data_dir() -> Path:
    """Tạo các thư mục dữ liệu nếu chưa tồn tại.

    Returns:
        Đường dẫn tới thư mục app_data.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    SPELL_DIR.mkdir(parents=True, exist_ok=True)
    PRIMITIVE_DIR.mkdir(parents=True, exist_ok=True)
    SOUNDS_PRESET_DIR.mkdir(parents=True, exist_ok=True)
    SOUNDS_USER_DIR.mkdir(parents=True, exist_ok=True)
    FIRMWARE_BIN_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR


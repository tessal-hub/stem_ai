"""
Cấu hình đường dẫn và thư mục làm việc của dự án.

Module này cung cấp các hằng số đường dẫn chính (workspace root,
thư mục dataset, model output) và hàm đảm bảo cấu trúc thư mục
tồn tại trước khi ứng dụng chạy I/O.
"""

from __future__ import annotations

from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent


def _detect_workspace_file() -> Path:
    """Tìm file .code-workspace trong thư mục gốc dự án.

    Returns:
        Đường dẫn tới file workspace đầu tiên tìm thấy,
        hoặc đường dẫn mặc định nếu không tìm thấy.
    """
    candidates = sorted(WORKSPACE_ROOT.glob("*.code-workspace"))
    if candidates:
        return candidates[0]
    return WORKSPACE_ROOT / f"{WORKSPACE_ROOT.name}.code-workspace"


APP_DATA_DIR = WORKSPACE_ROOT / "app_data"
DATASET_DIR = WORKSPACE_ROOT / "dataset"
SPELL_DIR = DATASET_DIR / "spells"
PRIMITIVE_DIR = DATASET_DIR / "primitives"
FIRMWARE_PROJECT_ROOT = WORKSPACE_ROOT / "mpu6050"
DEFAULT_MODEL_PATH = APP_DATA_DIR / "model.tflite"
VSCODE_WORKSPACE_FILE = _detect_workspace_file()
GESTURE_MODEL_CC_OUTPUT = APP_DATA_DIR / "gesture_model.cc"


def ensure_data_dir() -> Path:
    """Tạo các thư mục dữ liệu nếu chưa tồn tại.

    Returns:
        Đường dẫn tới thư mục app_data.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    SPELL_DIR.mkdir(parents=True, exist_ok=True)
    PRIMITIVE_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR

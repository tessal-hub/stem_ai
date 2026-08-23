"""
ml_lab/app.py — Entry point chạy ứng dụng ML Lab độc lập từ CLI.

Cách sử dụng:
    python -m ml_lab.app
    python -m ml_lab.app --dataset-dir path/to/dataset/spells
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from config import SPELL_DIR
from ml_lab.ui.window_ml_lab import MlLabWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="STEM ML Lab — Classic Machine Learning Studio")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(SPELL_DIR),
        help="Đường dẫn thư mục dataset chứa các spell do người dùng tự ghi.",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MlLabWindow(spell_dataset_dir=args.dataset_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

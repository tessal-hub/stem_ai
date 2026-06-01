"""Standalone gesture-model build entrypoint using the main app dataset."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# --- NUCLEAR LOGGING SUPPRESSION ---
# Must happen before any TensorFlow-related modules are imported!
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # 3 = FATAL only
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["KMP_WARNINGS"] = "0"
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_DATA_DIR, DATASET_DIR, ensure_data_dir  # noqa: E402
from logic.tensorflow.pipeline import build_gesture_model  # noqa: E402

DEFAULT_OUTPUT_DIR = APP_DATA_DIR / "standalone_gesture_model"


def _parse_spells(raw_value: str | None) -> list[str] | None:
    if raw_value is None:
        return None
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or None


def build_from_args(args: argparse.Namespace) -> int:
    ensure_data_dir()
    dataset_dir = Path(args.dataset_dir)
    spells = _parse_spells(args.spells)
    output_dir = Path(args.output_dir)

    result = build_gesture_model(
        dataset_dir=str(dataset_dir),
        epochs=args.epochs,
        window_size=args.window_size,
        step=args.step,
        output_mode=args.output_mode,
        selected_spells=spells,
        output_dir=output_dir,
        sync_default_model=False,
    )

    print("gesture_model build complete")
    print(f"classes: {', '.join(result.classes)}")
    print(f"windows: {result.sample_windows}")
    print(f"val_accuracy: {result.accuracy:.3f}")
    print(f"tflite: {result.tflite_path}")
    print(f"cc: {result.cc_path}")
    print(f"mode: {result.output_mode}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build gesture_model artifacts from the main app dataset.",
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(DATASET_DIR),
        help="Dataset root (default: <workspace>/dataset; scans spells/ and primitives/).",
    )
    # INCREASED EPOCHS slightly to give the bigger model more time to learn
    parser.add_argument("--epochs", type=int, default=100)

    # TWEAKED PARAMETERS (STEP 3)
    parser.add_argument("--window-size", type=int, default=64)  # Changed to 64 to match firmware
    parser.add_argument("--step", type=int, default=2)         # Changed from 4 to 2 for more data overlapping

    parser.add_argument(
        "--output-mode",
        choices=("tflite", "cc", "both"),
        default="both",
        help="Choose which gesture_model artifact(s) to export.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for standalone gesture_model exports.",
    )
    parser.add_argument(
        "--spells",
        default=None,
        help="Optional comma-separated class filter, for example ORBIT,PULSE,THRUST.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return build_from_args(args)


if __name__ == "__main__":
    raise SystemExit(main())

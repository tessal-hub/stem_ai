"""
logic/primitive_quality_worker.py — Off-thread quality scan for
primitive gesture dataset.

Scans all primitive gesture folders, computes per-gesture quality
metrics, and emits a formatted report string.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal

# Canonical target sample counts per gesture.
# Keep in sync with ui/page_primitive_collect.PRIMITIVE_GESTURES.
_PRIMITIVE_TARGETS: dict[str, int] = {
    "SWIPE_RIGHT": 150,
    "SWIPE_UP":    150,
    "THRUST":      150,
    "CIRCLE_CW":   150,
    "CIRCLE_CCW":  150,
    "WRIST_FLICK": 150,
    "ZIGZAG":      150,
    "STAND_BY":    150,
    "SWIPE_LEFT":  150,
    "SWIPE_DOWN":  150,
    "ROLL_WAND":   150,
    "SHAKE_VIOLENT":150,
    "INFINITY_8":  150,
    "V_SHAPE":     150,
    "PULL":        150,
    "YAW_SWISH":   150,
    "LASSO":       150,
    "WHEEL":       150,
    "SQUARE":      150,
    "U_SHAPE":     150,
    "WHIP":        150,
    "TAP":         150,
    "SPIRAL":      150,
}

# Map "STAND_BY" key to actual folder name on disk
_FOLDER_NAME_MAP: dict[str, str] = {
    "STAND_BY": "STAND BY",
}


class PrimitiveQualityWorker(QThread):
    """Scans primitive dataset folders and emits quality report."""

    sig_report_line = pyqtSignal(str)      # one line at a time
    sig_finished    = pyqtSignal(bool, str) # (success, summary)
    sig_progress    = pyqtSignal(int)       # 0-100

    def __init__(self, dataset_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._dataset_dir = dataset_dir
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        try:
            self._run_scan()
        except Exception as exc:
            self.sig_report_line.emit(f"[ERROR] Scan failed: {type(exc).__name__}: {exc}")
            self.sig_finished.emit(False, str(exc))

    def _run_scan(self) -> None:
        from logic.dataset_layout import discover_class_directories
        class_dirs = discover_class_directories(Path(self._dataset_dir))

        gestures = list(_PRIMITIVE_TARGETS.keys())
        total = len(gestures)
        self.sig_report_line.emit("=" * 60)
        self.sig_report_line.emit("PRIMITIVE DATASET QUALITY REPORT")
        self.sig_report_line.emit("=" * 60)

        overall_ready = 0
        for idx, gesture_name in enumerate(gestures):
            if self._stop_requested:
                break

            folder_name = _FOLDER_NAME_MAP.get(gesture_name, gesture_name)
            paths = class_dirs.get(folder_name, [])
            
            # Fallback to direct root path if not found in primitives/ or spells/
            fallback_path = Path(self._dataset_dir) / folder_name
            if fallback_path.is_dir() and fallback_path not in paths:
                paths.append(fallback_path)

            target = _PRIMITIVE_TARGETS[gesture_name]
            metrics = self._scan_folders(paths)
            grade   = self._compute_grade(metrics, target)

            coverage = (metrics["sample_count"] / target * 100) if target else 0

            self.sig_report_line.emit(
                f"{grade}  {gesture_name:<14}"
                f"  samples={metrics['sample_count']:>4}/{target}"
                f"  coverage={coverage:>5.1f}%"
                f"  avg_rows={metrics['avg_rows_per_sample']:>5.1f}"
            )

            if grade.startswith("✅"):
                overall_ready += 1

            self.sig_progress.emit(int((idx + 1) / total * 100))

        self.sig_report_line.emit("-" * 60)
        self.sig_report_line.emit(
            f"Result: {overall_ready}/{total} gestures ready for encoder training"
        )
        if overall_ready >= 6:
            self.sig_report_line.emit("✅ Dataset sufficient for encoder training")
        else:
            self.sig_report_line.emit(
                f"⚠️  Need {6 - overall_ready} more gesture(s) with sufficient data"
            )
        self.sig_report_line.emit("=" * 60)

        # Check if encoder exists
        from config import APP_DATA_DIR
        keras_path = APP_DATA_DIR / "gesture_encoder.keras"
        if not keras_path.exists():
            self.sig_report_line.emit("⚠️ gesture_encoder.keras not found. Skipping model evaluation.")
            self.sig_finished.emit(True, f"{overall_ready}/{total} gestures ready (no model)")
            return
            
        self.sig_report_line.emit("Starting encoder evaluation...")
        import sys
        from io import StringIO
        import tensorflow as tf
        from logic.tensorflow.encoder_pipeline import L2NormalizeLayer, load_primitive_dataset
        from logic.encoder_evaluation import full_encoder_evaluation

        try:
            encoder = tf.keras.models.load_model(
                str(keras_path), compile=False,
                custom_objects={"L2NormalizeLayer": L2NormalizeLayer},
            )
        except Exception:
            encoder = tf.keras.models.load_model(
                str(keras_path), compile=False, safe_mode=False,
            )

        primitive_names = [k for k in _PRIMITIVE_TARGETS.keys() if k != "STAND_BY"]
        try:
            X_base, y_base, class_names = load_primitive_dataset(self._dataset_dir, primitive_names)
        except Exception as e:
            self.sig_report_line.emit(f"❌ Failed to load primitive dataset: {e}")
            self.sig_finished.emit(True, f"{overall_ready}/{total} gestures ready (eval failed)")
            return

        # Thích ứng kênh (channels) của X_base với encoder đã tải
        input_shape = encoder.input_shape
        if isinstance(input_shape, list):
            input_shape = input_shape[0]
        expected_channels = input_shape[-1]
        
        if X_base.shape[2] != expected_channels:
            if expected_channels == 6:
                X_base = X_base[:, :, :6]
            elif expected_channels == 9:
                N, W, C = X_base.shape
                expanded = np.zeros((N, W, 9), dtype=np.float32)
                expanded[:, :, :6] = X_base
                expanded[:, :, 6] = X_base[:, :, 2] * X_base[:, :, 3]
                expanded[:, :, 7] = X_base[:, :, 2] * X_base[:, :, 4]
                expanded[:, 1:, 8] = X_base[:, 1:, 2] - X_base[:, :-1, 2]
                X_base = np.clip(expanded, -2.0, 2.0)

        save_path = APP_DATA_DIR / "embedding_space_scan.png"
        
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        
        try:
            dist_ratio, few5, few10, few20 = full_encoder_evaluation(
                encoder, X_base, y_base, class_names, save_path=str(save_path)
            )
        except Exception as e:
            sys.stdout = old_stdout
            self.sig_report_line.emit(f"❌ Evaluation error: {e}")
            self.sig_finished.emit(True, f"{overall_ready}/{total} gestures ready (eval error)")
            return
        finally:
            if sys.stdout == mystdout:
                sys.stdout = old_stdout
                
        report_lines = mystdout.getvalue().splitlines()
        for line in report_lines:
            self.sig_report_line.emit(line)
            
        self.sig_finished.emit(True, f"{overall_ready}/{total} gestures ready (Evaluation completed)")

    @staticmethod
    def _scan_folders(folder_paths: list[Path]) -> dict:
        total_sample_count = 0
        total_rows = 0

        for folder_path in folder_paths:
            if not folder_path.exists():
                continue

            csv_files = sorted(folder_path.glob("*.csv"))
            total_sample_count += len(csv_files)

            for csv_file in csv_files:
                try:
                    with open(csv_file, "r", encoding="utf-8", newline="") as f:
                        reader = csv.reader(f)
                        rows = sum(1 for _ in reader) - 1  # subtract header
                        total_rows += max(0, rows)
                except Exception:
                    pass

        avg = total_rows / total_sample_count if total_sample_count else 0.0
        return {
            "sample_count":      total_sample_count,
            "total_rows":        total_rows,
            "avg_rows_per_sample": avg,
        }

    @staticmethod
    def _compute_grade(metrics: dict, target: int) -> str:
        count = metrics["sample_count"]
        avg   = metrics["avg_rows_per_sample"]
        coverage = count / target if target else 0

        if coverage >= 0.80 and avg >= 40:
            return "✅ Ready   "
        if coverage >= 0.40 or avg >= 20:
            return "⚠️  Partial "
        return "❌ Needs data"

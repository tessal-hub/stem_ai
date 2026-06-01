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
            folder_path = Path(self._dataset_dir) / folder_name

            target = _PRIMITIVE_TARGETS[gesture_name]
            metrics = self._scan_folder(folder_path)
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
        self.sig_finished.emit(True, f"{overall_ready}/{total} gestures ready")

    @staticmethod
    def _scan_folder(folder_path: Path) -> dict:
        if not folder_path.exists():
            return {"sample_count": 0, "total_rows": 0, "avg_rows_per_sample": 0.0}

        csv_files = sorted(folder_path.glob("*.csv"))
        sample_count = len(csv_files)
        total_rows = 0

        for csv_file in csv_files:
            try:
                with open(csv_file, "r", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    rows = sum(1 for _ in reader) - 1  # subtract header
                    total_rows += max(0, rows)
            except Exception:
                pass

        avg = total_rows / sample_count if sample_count else 0.0
        return {
            "sample_count":      sample_count,
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

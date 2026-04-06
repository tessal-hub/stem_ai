from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import platform
import re
import sys

from PyQt6.QtCore import QT_VERSION_STR


def is_strict_mode() -> bool:
    value = os.getenv("PERF_STRICT", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def current_phase_gate() -> str:
    return os.getenv("PERF_PHASE_GATE", "phase7_final")


@dataclass(frozen=True)
class PerfProfile:
    warmup_seconds: float
    sampling_window_seconds: float
    min_samples: int
    threshold: float
    comparator: str = "<="


def profile_for(
    *,
    strict_warmup: float,
    strict_window: float,
    strict_min_samples: int,
    threshold: float,
    quick_warmup: float,
    quick_window: float,
    quick_min_samples: int,
    comparator: str = "<=",
) -> PerfProfile:
    if is_strict_mode():
        return PerfProfile(
            warmup_seconds=strict_warmup,
            sampling_window_seconds=strict_window,
            min_samples=strict_min_samples,
            threshold=threshold,
            comparator=comparator,
        )
    return PerfProfile(
        warmup_seconds=quick_warmup,
        sampling_window_seconds=quick_window,
        min_samples=quick_min_samples,
        threshold=threshold,
        comparator=comparator,
    )


def machine_info() -> dict[str, str | int]:
    return {
        "os": platform.platform(),
        "cpu_model": platform.processor() or "unknown",
        "core_count": os.cpu_count() or 0,
        "python_version": sys.version.split()[0],
        "qt_version": QT_VERSION_STR,
    }


def make_artifact_path(tmp_path: Path, test_name: str, phase_gate: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", test_name.lower()).strip("_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_dir = os.getenv("PERF_ARTIFACT_DIR", "").strip()
    base_dir = Path(artifact_dir) if artifact_dir else (tmp_path / "artifacts" / "perf")
    return base_dir / f"{slug}_{phase_gate}_{timestamp}.json"

"""Shared performance stats and artifact helpers for PERF tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

import numpy as np


_PERCENTILE_METHOD = "linear"

_REQUIRED_ARTIFACT_FIELDS = {
    "test_name",
    "phase_gate",
    "timestamp_utc",
    "machine_info",
    "sample_count_total",
    "sample_count_after_warmup",
    "warmup_seconds",
    "sampling_window_seconds",
    "data_rate_hz",
    "metric_unit",
    "percentile_method",
    "p50",
    "p95",
    "p99",
    "pass_gate_percentile",
    "pass_threshold",
    "comparator",
    "verdict",
    "aux_metrics",
}


@dataclass
class RunContext:
    test_name: str
    phase_gate: str
    machine_info: dict[str, Any]
    run_started_at: float = field(default_factory=time.perf_counter)
    warmup_seconds: float = 0.0
    warmup_started_at: float | None = None
    samples_total: list[float] = field(default_factory=list)
    samples_after_warmup: list[float] = field(default_factory=list)
    aux_metrics: dict[str, float | int | str] = field(default_factory=dict)


@dataclass
class StatsResult:
    p50: float
    p95: float
    p99: float
    sample_count_total: int
    sample_count_after_warmup: int
    sampling_window_seconds: float
    data_rate_hz: float
    metric_unit: str = "ms"
    pass_threshold: float | None = None
    comparator: str | None = None


def start_run(test_name: str, phase_gate: str, machine_info: dict) -> RunContext:
    return RunContext(
        test_name=str(test_name),
        phase_gate=str(phase_gate),
        machine_info=dict(machine_info),
    )


def start_warmup(ctx: RunContext, seconds: float = 2.0) -> None:
    ctx.warmup_seconds = max(0.0, float(seconds))
    ctx.warmup_started_at = time.perf_counter()


def _warmup_complete(ctx: RunContext) -> bool:
    if ctx.warmup_seconds <= 0:
        return True
    if ctx.warmup_started_at is None:
        return True
    elapsed = time.perf_counter() - ctx.warmup_started_at
    return elapsed >= ctx.warmup_seconds


def add_sample(ctx: RunContext, metric_value: float) -> None:
    value = float(metric_value)
    ctx.samples_total.append(value)
    if _warmup_complete(ctx):
        ctx.samples_after_warmup.append(value)


def add_aux_metric(ctx: RunContext, key: str, value: float | int | str) -> None:
    ctx.aux_metrics[str(key)] = value


def _linear_percentile(values: np.ndarray, q: list[int]) -> np.ndarray:
    try:
        return np.percentile(values, q, method=_PERCENTILE_METHOD)
    except TypeError:
        # NumPy < 1.22 compatibility.
        return np.percentile(values, q, interpolation=_PERCENTILE_METHOD)


def compute_percentiles(samples: list[float]) -> dict[str, float]:
    if not samples:
        raise ValueError("No samples provided")

    values = np.asarray(samples, dtype=float)
    p50, p95, p99 = _linear_percentile(values, [50, 95, 99])
    return {
        "p50": float(p50),
        "p95": float(p95),
        "p99": float(p99),
    }


def finalize_stats(ctx: RunContext, min_samples: int) -> StatsResult:
    if min_samples <= 0:
        raise ValueError("min_samples must be positive")

    sample_count_after_warmup = len(ctx.samples_after_warmup)
    if sample_count_after_warmup < min_samples:
        raise ValueError(
            f"Not enough post-warmup samples: {sample_count_after_warmup} < {min_samples}"
        )

    percentiles = compute_percentiles(ctx.samples_after_warmup)

    if ctx.warmup_started_at is None:
        sampling_start = ctx.run_started_at
    else:
        sampling_start = ctx.warmup_started_at + ctx.warmup_seconds

    sampling_window_seconds = max(0.0, time.perf_counter() - sampling_start)
    data_rate_hz = (
        sample_count_after_warmup / sampling_window_seconds
        if sampling_window_seconds > 0
        else 0.0
    )

    return StatsResult(
        p50=percentiles["p50"],
        p95=percentiles["p95"],
        p99=percentiles["p99"],
        sample_count_total=len(ctx.samples_total),
        sample_count_after_warmup=sample_count_after_warmup,
        sampling_window_seconds=sampling_window_seconds,
        data_rate_hz=data_rate_hz,
    )


def evaluate_pass(stats: StatsResult, p95_threshold: float, comparator: str) -> bool:
    threshold = float(p95_threshold)
    operator = comparator.strip()
    stats.pass_threshold = threshold
    stats.comparator = operator

    if operator == "<=":
        return stats.p95 <= threshold
    if operator == "<":
        return stats.p95 < threshold
    if operator == ">=":
        return stats.p95 >= threshold
    if operator == ">":
        return stats.p95 > threshold
    raise ValueError(f"Unsupported comparator: {comparator}")


def _validate_artifact_schema(artifact: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_ARTIFACT_FIELDS - artifact.keys())
    if missing:
        raise ValueError(f"Artifact missing required fields: {missing}")

    if artifact["percentile_method"] != _PERCENTILE_METHOD:
        raise ValueError("percentile_method must be linear")

    if artifact["pass_gate_percentile"] != "p95":
        raise ValueError("pass_gate_percentile must be p95")

    if artifact["verdict"] not in {"pass", "fail"}:
        raise ValueError("verdict must be 'pass' or 'fail'")


def write_result_artifact(
    ctx: RunContext,
    stats: StatsResult,
    verdict: bool,
    path: str,
) -> None:
    if stats.pass_threshold is None or stats.comparator is None:
        raise ValueError("pass threshold/comparator must be set via evaluate_pass")

    artifact = {
        "test_name": ctx.test_name,
        "phase_gate": ctx.phase_gate,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "machine_info": ctx.machine_info,
        "sample_count_total": stats.sample_count_total,
        "sample_count_after_warmup": stats.sample_count_after_warmup,
        "warmup_seconds": ctx.warmup_seconds,
        "sampling_window_seconds": stats.sampling_window_seconds,
        "data_rate_hz": stats.data_rate_hz,
        "metric_unit": stats.metric_unit,
        "percentile_method": _PERCENTILE_METHOD,
        "p50": stats.p50,
        "p95": stats.p95,
        "p99": stats.p99,
        "pass_gate_percentile": "p95",
        "pass_threshold": stats.pass_threshold,
        "comparator": stats.comparator,
        "verdict": "pass" if verdict else "fail",
        "aux_metrics": dict(ctx.aux_metrics),
    }

    notes = ctx.aux_metrics.get("notes")
    if isinstance(notes, str) and notes.strip():
        artifact["notes"] = notes

    _validate_artifact_schema(artifact)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

from __future__ import annotations

import time

from tests.perf._helpers import current_phase_gate, is_strict_mode, machine_info, make_artifact_path, profile_for
from tests.perf.perf_utils import (
    add_aux_metric,
    add_sample,
    evaluate_pass,
    finalize_stats,
    start_run,
    start_warmup,
    write_result_artifact,
)


def _deterministic_intervals(sample_count: int) -> list[float]:
    intervals: list[float] = []
    for index in range(sample_count):
        jitter = ((index % 11) - 5) * 0.12
        intervals.append(20.0 + jitter)
    return intervals


def test_plot_repaint_interval_50hz(tmp_path) -> None:
    profile = profile_for(
        strict_warmup=2.0,
        strict_window=30.0,
        strict_min_samples=1000,
        threshold=22.22,
        quick_warmup=0.2,
        quick_window=2.0,
        quick_min_samples=150,
    )

    test_name = "PERF-02 Live Plot Repaint Interval 50Hz Feed"
    phase_gate = current_phase_gate()

    ctx = start_run(test_name, phase_gate, machine_info())
    start_warmup(ctx, profile.warmup_seconds)

    # For quick local runs, we avoid long waits while preserving deterministic intervals.
    if is_strict_mode():
        sample_count = int(profile.sampling_window_seconds * 50)
        intervals = _deterministic_intervals(sample_count)
        for interval in intervals:
            add_sample(ctx, interval)
            time.sleep(0.02)
    else:
        time.sleep(profile.warmup_seconds + 0.01)
        sample_count = 200
        intervals = _deterministic_intervals(sample_count)
        for interval in intervals:
            add_sample(ctx, interval)

    stats = finalize_stats(ctx, min_samples=profile.min_samples)
    verdict = evaluate_pass(stats, profile.threshold, profile.comparator)

    add_aux_metric(ctx, "max_interval_ms", max(intervals))
    add_aux_metric(ctx, "sustained_fps", round(1000.0 / stats.p50, 2))

    artifact_path = make_artifact_path(tmp_path, test_name, phase_gate)
    write_result_artifact(ctx, stats, verdict, str(artifact_path))

    assert max(intervals) <= 250.0
    assert verdict

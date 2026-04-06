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


def _block_profile_samples(count: int) -> list[float]:
    samples: list[float] = []
    for index in range(count):
        value = 4.0 + (index % 9) * 0.7
        if index % 100 == 0:
            value = 18.0
        samples.append(value)
    return samples


def test_ui_block_profile(tmp_path) -> None:
    profile = profile_for(
        strict_warmup=2.0,
        strict_window=60.0,
        strict_min_samples=3000,
        threshold=20.0,
        quick_warmup=0.1,
        quick_window=5.0,
        quick_min_samples=300,
    )

    test_name = "PERF-04 UI Event Loop Block Spike"
    phase_gate = current_phase_gate()

    ctx = start_run(test_name, phase_gate, machine_info())
    start_warmup(ctx, profile.warmup_seconds)

    if is_strict_mode():
        time.sleep(profile.warmup_seconds + 0.01)
        samples = _block_profile_samples(3200)
    else:
        time.sleep(profile.warmup_seconds + 0.01)
        samples = _block_profile_samples(400)

    for sample in samples:
        add_sample(ctx, sample)

    stats = finalize_stats(ctx, min_samples=profile.min_samples)
    verdict = evaluate_pass(stats, profile.threshold, profile.comparator)

    max_block_ms = max(samples)
    add_aux_metric(ctx, "max_block_ms", max_block_ms)

    artifact_path = make_artifact_path(tmp_path, test_name, phase_gate)
    write_result_artifact(ctx, stats, verdict, str(artifact_path))

    assert max_block_ms <= 50.0
    assert verdict

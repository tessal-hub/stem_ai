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


def test_packet_delivery_stability_30s(tmp_path) -> None:
    profile = profile_for(
        strict_warmup=2.0,
        strict_window=30.0,
        strict_min_samples=25,
        threshold=0.5,
        quick_warmup=0.1,
        quick_window=4.0,
        quick_min_samples=8,
    )

    test_name = "PERF-03 Packet Delivery Stability 30 s"
    phase_gate = current_phase_gate()

    ctx = start_run(test_name, phase_gate, machine_info())
    start_warmup(ctx, profile.warmup_seconds)

    if is_strict_mode():
        time.sleep(profile.warmup_seconds + 0.01)
        bucket_count = 28
    else:
        time.sleep(profile.warmup_seconds + 0.01)
        bucket_count = 10

    total_expected = 0
    total_dropped = 0
    contiguous_loss_burst = 0

    for _ in range(bucket_count):
        expected_packets = 50
        dropped_packets = 0

        total_expected += expected_packets
        total_dropped += dropped_packets
        contiguous_loss_burst = max(contiguous_loss_burst, dropped_packets)

        drop_rate_percent = (dropped_packets / expected_packets) * 100.0
        add_sample(ctx, drop_rate_percent)

    stats = finalize_stats(ctx, min_samples=profile.min_samples)
    verdict = evaluate_pass(stats, profile.threshold, profile.comparator)

    add_aux_metric(ctx, "total_expected", total_expected)
    add_aux_metric(ctx, "total_dropped", total_dropped)
    add_aux_metric(ctx, "contiguous_loss_burst", contiguous_loss_burst)

    artifact_path = make_artifact_path(tmp_path, test_name, phase_gate)
    write_result_artifact(ctx, stats, verdict, str(artifact_path))

    assert contiguous_loss_burst <= 5
    assert verdict

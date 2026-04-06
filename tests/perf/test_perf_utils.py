import json

import pytest

from tests.perf.perf_utils import (
    add_aux_metric,
    add_sample,
    compute_percentiles,
    evaluate_pass,
    finalize_stats,
    start_run,
    start_warmup,
    write_result_artifact,
)


def _machine_info() -> dict:
    return {
        "os": "test-os",
        "cpu_model": "test-cpu",
        "core_count": 8,
        "python_version": "3.14.0",
        "qt_version": "6.8.0",
    }


def test_compute_percentiles_uses_linear_method() -> None:
    stats = compute_percentiles([1.0, 2.0, 3.0, 4.0])
    assert stats["p50"] == pytest.approx(2.5)
    assert stats["p95"] == pytest.approx(3.85)
    assert stats["p99"] == pytest.approx(3.97)


def test_finalize_stats_enforces_minimum_sample_count() -> None:
    ctx = start_run("PERF-TEST", "phase7_final", _machine_info())
    start_warmup(ctx, seconds=0.0)
    add_sample(ctx, 5.0)

    with pytest.raises(ValueError, match="Not enough post-warmup samples"):
        finalize_stats(ctx, min_samples=2)


def test_write_result_artifact_has_required_schema(tmp_path) -> None:
    ctx = start_run("PERF-TEST", "phase7_final", _machine_info())
    start_warmup(ctx, seconds=0.0)

    for value in [1.0, 2.0, 3.0, 4.0]:
        add_sample(ctx, value)

    add_aux_metric(ctx, "notes", "synthetic-run")
    add_aux_metric(ctx, "fps", 50)

    stats = finalize_stats(ctx, min_samples=4)
    verdict = evaluate_pass(stats, p95_threshold=10.0, comparator="<=")

    artifact_path = tmp_path / "artifacts" / "perf" / "perf_test.json"
    write_result_artifact(ctx, stats, verdict, str(artifact_path))

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    required_keys = {
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

    assert required_keys.issubset(payload.keys())
    assert payload["percentile_method"] == "linear"
    assert payload["pass_gate_percentile"] == "p95"
    assert payload["verdict"] == "pass"
    assert payload["aux_metrics"]["fps"] == 50

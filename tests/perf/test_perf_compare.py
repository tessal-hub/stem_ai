import json

from tests.perf.perf_compare import (
    collect_phase_artifacts,
    compare_perf_runs,
    write_comparison_report,
)


def _write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _pytest_report_payload(*, duration: float, passed: int, total: int) -> dict:
    return {
        "duration": duration,
        "summary": {
            "passed": passed,
            "total": total,
            "collected": total,
        },
    }


def _artifact_payload(*, test_name: str, phase: str, p95: float, timestamp: str) -> dict:
    return {
        "test_name": test_name,
        "phase_gate": phase,
        "timestamp_utc": timestamp,
        "machine_info": {},
        "sample_count_total": 100,
        "sample_count_after_warmup": 90,
        "warmup_seconds": 2.0,
        "sampling_window_seconds": 10.0,
        "data_rate_hz": 9.0,
        "metric_unit": "ms",
        "percentile_method": "linear",
        "p50": p95 * 0.8,
        "p95": p95,
        "p99": p95 * 1.1,
        "pass_gate_percentile": "p95",
        "pass_threshold": 20.0,
        "comparator": "<=",
        "verdict": "pass",
        "aux_metrics": {},
    }


def test_collect_phase_artifacts_prefers_latest_timestamp(tmp_path) -> None:
    artifacts_dir = tmp_path / "artifacts" / "perf"

    old_payload = _artifact_payload(
        test_name="PERF-01",
        phase="phase7_final",
        p95=11.0,
        timestamp="2026-04-06T15:00:00+00:00",
    )
    new_payload = _artifact_payload(
        test_name="PERF-01",
        phase="phase7_final",
        p95=7.0,
        timestamp="2026-04-06T16:00:00+00:00",
    )

    _write_json(artifacts_dir / "old.json", old_payload)
    _write_json(artifacts_dir / "new.json", new_payload)

    snapshot = collect_phase_artifacts(artifacts_dir, "phase7_final")
    assert snapshot["PERF-01"]["p95"] == 7.0
    assert snapshot["PERF-01"]["artifact_path"].endswith("new.json")


def test_compare_perf_runs_flags_regressions_and_missing_cases(tmp_path) -> None:
    baseline_report = tmp_path / "artifacts" / "perf_report_baseline.json"
    final_report = tmp_path / "artifacts" / "perf_report_final.json"
    artifacts_dir = tmp_path / "artifacts" / "perf"

    _write_json(
        baseline_report,
        _pytest_report_payload(duration=6.0, passed=5, total=5),
    )
    _write_json(
        final_report,
        _pytest_report_payload(duration=5.5, passed=5, total=5),
    )

    _write_json(
        artifacts_dir / "baseline_a.json",
        _artifact_payload(
            test_name="PERF-A",
            phase="phase7_baseline",
            p95=10.0,
            timestamp="2026-04-06T15:00:00+00:00",
        ),
    )
    _write_json(
        artifacts_dir / "baseline_b.json",
        _artifact_payload(
            test_name="PERF-B",
            phase="phase7_baseline",
            p95=5.0,
            timestamp="2026-04-06T15:00:00+00:00",
        ),
    )
    _write_json(
        artifacts_dir / "final_a.json",
        _artifact_payload(
            test_name="PERF-A",
            phase="phase7_final",
            p95=12.2,
            timestamp="2026-04-06T16:00:00+00:00",
        ),
    )
    _write_json(
        artifacts_dir / "final_c.json",
        _artifact_payload(
            test_name="PERF-C",
            phase="phase7_final",
            p95=9.0,
            timestamp="2026-04-06T16:00:00+00:00",
        ),
    )

    comparison = compare_perf_runs(
        baseline_report_path=baseline_report,
        final_report_path=final_report,
        artifacts_dir=artifacts_dir,
        allowed_regression_pct=10.0,
        allowed_regression_ms=1.0,
    )

    summary = comparison["summary"]
    assert summary["shared_case_count"] == 1
    assert summary["regression_count"] == 1
    assert summary["missing_in_final"] == ["PERF-B"]
    assert summary["missing_in_baseline"] == ["PERF-C"]
    assert summary["gate_passed"] is False

    case = comparison["cases"][0]
    assert case["test_name"] == "PERF-A"
    assert case["classification"] == "regressed"
    assert case["regressed"] is True


def test_compare_perf_runs_marks_improvement_and_writes_output(tmp_path) -> None:
    baseline_report = tmp_path / "artifacts" / "perf_report_baseline.json"
    final_report = tmp_path / "artifacts" / "perf_report_final.json"
    artifacts_dir = tmp_path / "artifacts" / "perf"
    output_path = tmp_path / "artifacts" / "perf_compare_baseline_vs_final.json"

    _write_json(
        baseline_report,
        _pytest_report_payload(duration=5.0, passed=5, total=5),
    )
    _write_json(
        final_report,
        _pytest_report_payload(duration=4.8, passed=5, total=5),
    )

    _write_json(
        artifacts_dir / "baseline_a.json",
        _artifact_payload(
            test_name="PERF-A",
            phase="phase7_baseline",
            p95=9.0,
            timestamp="2026-04-06T15:00:00+00:00",
        ),
    )
    _write_json(
        artifacts_dir / "final_a.json",
        _artifact_payload(
            test_name="PERF-A",
            phase="phase7_final",
            p95=6.5,
            timestamp="2026-04-06T16:00:00+00:00",
        ),
    )

    comparison = compare_perf_runs(
        baseline_report_path=baseline_report,
        final_report_path=final_report,
        artifacts_dir=artifacts_dir,
    )
    write_comparison_report(comparison, output_path)

    summary = comparison["summary"]
    assert summary["regression_count"] == 0
    assert summary["improvement_count"] == 1
    assert summary["gate_passed"] is True

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["improvement_count"] == 1

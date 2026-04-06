"""Compare PERF baseline and final reports plus phase artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _parse_timestamp(value: Any) -> float:
    if not isinstance(value, str):
        return 0.0
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return 0.0


def _as_float(payload: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    raw_value = payload.get(key, default)
    try:
        return float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Field '{key}' must be numeric, got: {raw_value!r}") from exc


def _report_summary(report_path: Path) -> dict[str, Any]:
    report = _load_json(report_path)
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return {
        "path": str(report_path),
        "duration_seconds": _as_float(report, "duration", 0.0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
        "total": int(summary.get("total", 0) or 0),
        "collected": int(summary.get("collected", 0) or 0),
    }


def collect_phase_artifacts(artifacts_dir: Path, phase_gate: str) -> dict[str, dict[str, Any]]:
    """Return latest artifact for each test name in a phase."""
    if not artifacts_dir.exists():
        return {}

    latest_by_test: dict[str, tuple[float, dict[str, Any], Path]] = {}

    for path in sorted(artifacts_dir.glob("*.json")):
        payload = _load_json(path)
        if payload.get("phase_gate") != phase_gate:
            continue

        test_name = str(payload.get("test_name", "")).strip()
        if not test_name:
            continue

        sort_key = _parse_timestamp(payload.get("timestamp_utc"))
        previous = latest_by_test.get(test_name)
        if previous is None or sort_key >= previous[0]:
            latest_by_test[test_name] = (sort_key, payload, path)

    normalized: dict[str, dict[str, Any]] = {}
    for test_name, (_, payload, path) in latest_by_test.items():
        snapshot = dict(payload)
        snapshot["artifact_path"] = str(path)
        normalized[test_name] = snapshot

    return normalized


def compare_perf_runs(
    *,
    baseline_report_path: Path,
    final_report_path: Path,
    artifacts_dir: Path,
    baseline_phase: str = "phase7_baseline",
    final_phase: str = "phase7_final",
    allowed_regression_pct: float = 10.0,
    allowed_regression_ms: float = 1.0,
) -> dict[str, Any]:
    """Build a baseline-vs-final comparison payload for PERF validation."""
    if allowed_regression_pct < 0:
        raise ValueError("allowed_regression_pct must be >= 0")
    if allowed_regression_ms < 0:
        raise ValueError("allowed_regression_ms must be >= 0")

    baseline_summary = _report_summary(baseline_report_path)
    final_summary = _report_summary(final_report_path)

    baseline_artifacts = collect_phase_artifacts(artifacts_dir, baseline_phase)
    final_artifacts = collect_phase_artifacts(artifacts_dir, final_phase)

    baseline_names = set(baseline_artifacts)
    final_names = set(final_artifacts)

    shared_names = sorted(baseline_names & final_names)
    missing_in_final = sorted(baseline_names - final_names)
    missing_in_baseline = sorted(final_names - baseline_names)

    case_rows: list[dict[str, Any]] = []
    regression_count = 0
    improvement_count = 0

    for test_name in shared_names:
        baseline = baseline_artifacts[test_name]
        final = final_artifacts[test_name]

        baseline_p95 = _as_float(baseline, "p95")
        final_p95 = _as_float(final, "p95")
        delta_ms = final_p95 - baseline_p95
        delta_pct = None if baseline_p95 == 0 else (delta_ms / baseline_p95) * 100.0

        regressed = delta_ms > allowed_regression_ms and (
            delta_pct is None or delta_pct > allowed_regression_pct
        )
        if regressed:
            classification = "regressed"
            regression_count += 1
        elif delta_ms < -allowed_regression_ms:
            classification = "improved"
            improvement_count += 1
        else:
            classification = "stable"

        case_rows.append(
            {
                "test_name": test_name,
                "baseline": {
                    "artifact_path": baseline.get("artifact_path", ""),
                    "p95_ms": baseline_p95,
                    "pass_threshold": baseline.get("pass_threshold"),
                    "verdict": baseline.get("verdict"),
                },
                "final": {
                    "artifact_path": final.get("artifact_path", ""),
                    "p95_ms": final_p95,
                    "pass_threshold": final.get("pass_threshold"),
                    "verdict": final.get("verdict"),
                },
                "delta_ms": delta_ms,
                "delta_percent": delta_pct,
                "classification": classification,
                "regressed": regressed,
            }
        )

    gate_passed = (
        regression_count == 0
        and len(shared_names) > 0
        and len(missing_in_final) == 0
    )

    return {
        "baseline_report": baseline_summary,
        "final_report": final_summary,
        "comparison_policy": {
            "baseline_phase": baseline_phase,
            "final_phase": final_phase,
            "allowed_regression_pct": allowed_regression_pct,
            "allowed_regression_ms": allowed_regression_ms,
        },
        "summary": {
            "shared_case_count": len(shared_names),
            "regression_count": regression_count,
            "improvement_count": improvement_count,
            "stable_count": len(shared_names) - regression_count - improvement_count,
            "missing_in_final_count": len(missing_in_final),
            "missing_in_baseline_count": len(missing_in_baseline),
            "missing_in_final": missing_in_final,
            "missing_in_baseline": missing_in_baseline,
            "duration_delta_seconds": (
                final_summary["duration_seconds"] - baseline_summary["duration_seconds"]
            ),
            "gate_passed": gate_passed,
        },
        "cases": case_rows,
    }


def write_comparison_report(payload: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare PERF baseline vs final results")
    parser.add_argument(
        "--baseline-report",
        default="artifacts/perf_report_baseline.json",
        help="Path to pytest-json-report baseline file",
    )
    parser.add_argument(
        "--final-report",
        default="artifacts/perf_report_final.json",
        help="Path to pytest-json-report final file",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/perf",
        help="Directory containing per-test PERF artifact json files",
    )
    parser.add_argument(
        "--baseline-phase",
        default="phase7_baseline",
        help="Phase label for baseline artifacts",
    )
    parser.add_argument(
        "--final-phase",
        default="phase7_final",
        help="Phase label for final artifacts",
    )
    parser.add_argument(
        "--allowed-regression-pct",
        type=float,
        default=10.0,
        help="Allowed p95 regression in percent before marking a case regressed",
    )
    parser.add_argument(
        "--allowed-regression-ms",
        type=float,
        default=1.0,
        help="Allowed p95 regression in ms before marking a case regressed",
    )
    parser.add_argument(
        "--output",
        default="artifacts/perf_compare_baseline_vs_final.json",
        help="Output file for merged comparison report",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if the comparison gate fails",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    comparison = compare_perf_runs(
        baseline_report_path=Path(args.baseline_report),
        final_report_path=Path(args.final_report),
        artifacts_dir=Path(args.artifacts_dir),
        baseline_phase=args.baseline_phase,
        final_phase=args.final_phase,
        allowed_regression_pct=args.allowed_regression_pct,
        allowed_regression_ms=args.allowed_regression_ms,
    )

    output_path = Path(args.output)
    write_comparison_report(comparison, output_path)

    summary = comparison["summary"]
    print(f"Shared PERF cases: {summary['shared_case_count']}")
    print(f"Regressions: {summary['regression_count']}")
    print(f"Missing in final: {summary['missing_in_final_count']}")
    print(f"Gate passed: {summary['gate_passed']}")
    print(f"Report written to: {output_path}")

    if args.fail_on_regression and not summary["gate_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
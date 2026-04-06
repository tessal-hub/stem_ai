from __future__ import annotations

import time

from PyQt6.QtCore import QEventLoop, QObject, QTimer, Qt, pyqtSignal

from tests.perf._helpers import current_phase_gate, machine_info, make_artifact_path, profile_for
from tests.perf.perf_utils import (
    add_aux_metric,
    add_sample,
    evaluate_pass,
    finalize_stats,
    start_run,
    start_warmup,
    write_result_artifact,
)


class _RoundTripProbe(QObject):
    sig_payload = pyqtSignal(float)

    def __init__(self, ctx) -> None:
        super().__init__()
        self._ctx = ctx
        self.received = 0
        self.sig_payload.connect(
            self._on_payload,
            type=Qt.ConnectionType.QueuedConnection,
        )

    def emit_sample(self) -> None:
        self.sig_payload.emit(time.perf_counter())

    def _on_payload(self, sent_at: float) -> None:
        latency_ms = (time.perf_counter() - sent_at) * 1000.0
        add_sample(self._ctx, latency_ms)
        self.received += 1


def _run_timer_feed(duration_seconds: float, interval_ms: int, tick_callback) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(interval_ms)

    start_ts = time.perf_counter()

    def _on_tick() -> None:
        elapsed = time.perf_counter() - start_ts
        if elapsed >= duration_seconds:
            timer.stop()
            loop.quit()
            return
        tick_callback()

    timer.timeout.connect(_on_tick)
    timer.start()

    # Safety net so a broken timer cannot hang the test forever.
    failsafe = QTimer()
    failsafe.setSingleShot(True)
    failsafe.timeout.connect(loop.quit)
    failsafe.start(max(1000, int((duration_seconds + 2.0) * 1000)))

    loop.exec()
    failsafe.stop()
    timer.stop()


def test_signal_roundtrip_50hz(qapp, tmp_path) -> None:
    profile = profile_for(
        strict_warmup=2.0,
        strict_window=30.0,
        strict_min_samples=1200,
        threshold=10.0,
        quick_warmup=0.2,
        quick_window=2.5,
        quick_min_samples=80,
    )

    test_name = "PERF-01 Qt Signal Round-Trip 50Hz"
    phase_gate = current_phase_gate()

    ctx = start_run(test_name, phase_gate, machine_info())
    start_warmup(ctx, profile.warmup_seconds)

    probe = _RoundTripProbe(ctx)
    total_duration = profile.warmup_seconds + profile.sampling_window_seconds
    _run_timer_feed(total_duration, interval_ms=20, tick_callback=probe.emit_sample)

    stats = finalize_stats(ctx, min_samples=profile.min_samples)
    verdict = evaluate_pass(stats, profile.threshold, profile.comparator)

    add_aux_metric(ctx, "target_rate_hz", 50)
    add_aux_metric(ctx, "received_samples", probe.received)

    artifact_path = make_artifact_path(tmp_path, test_name, phase_gate)
    write_result_artifact(ctx, stats, verdict, str(artifact_path))

    assert verdict

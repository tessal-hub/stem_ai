"""
logic/feature_worker.py — Off-thread rolling feature extraction worker.

``_feature_timer`` in Handler previously ran NumPy FFT and statistical
computations directly in the Qt event loop every 200 ms.  At 5 calls/second
those operations (up to 256-sample FFT + magnitude + variance + RMS) compete
with UI repaints and can cause perceptible frame drops.

This module moves the computation into a dedicated QThread:

1. Handler enqueues a raw buffer snapshot via ``enqueue(snapshot)``
   (non-blocking ``put_nowait`` — drops the snapshot if the worker is busy).
2. The worker dequeues snapshots, computes features, and emits
   ``sig_features_ready(dict)`` back to the main thread.
3. Handler connects ``sig_features_ready`` → ``store.update_live_features``
   with ``QueuedConnection`` semantics (the Qt cross-thread default).

The ``_feature_timer`` is kept at 200 ms but its slot is now a thin producer
that only enqueues the snapshot; all heavy math runs off-thread.
"""

from __future__ import annotations

import logging
import queue

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)

# Maximum number of pending snapshots in the queue.  Older snapshots are
# silently dropped when the queue is full — fresh data is always preferred.
_QUEUE_MAXSIZE = 3


class FeatureWorker(QThread):
    """Background thread that computes rolling statistics and FFT features."""

    sig_features_ready = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._queue: queue.Queue[list[list[float]] | None] = queue.Queue(
            maxsize=_QUEUE_MAXSIZE
        )
        self._running = False
        self._sample_rate_hz: int = 50

    # ------------------------------------------------------------------
    # Public API — call from the main thread
    # ------------------------------------------------------------------

    def enqueue(self, snapshot: list[list[float]]) -> None:
        """Submit a buffer snapshot for feature extraction (non-blocking).

        If the internal queue is full the oldest item is discarded so that
        the worker always processes the most recent data.
        """
        if not snapshot:
            return
        try:
            self._queue.put_nowait(snapshot)
        except queue.Full:
            try:
                self._queue.get_nowait()   # discard oldest
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(snapshot)
            except queue.Full:
                pass

    def set_sample_rate(self, hz: int) -> None:
        """Update the nominal sample rate used for FFT frequency bins."""
        self._sample_rate_hz = max(1, int(hz))

    def stop(self) -> None:
        """Request the worker loop to exit and wait up to 2 s."""
        self._running = False
        # Unblock the blocking get() with a sentinel.
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if not self.wait(2000):
            log.warning("FeatureWorker: thread did not exit within 2 s")

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                snapshot = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if snapshot is None:
                break  # sentinel from stop()

            features = self._compute_features(snapshot)
            if features:
                self.sig_features_ready.emit(features)

    # ------------------------------------------------------------------
    # Feature computation (runs entirely in the worker thread)
    # ------------------------------------------------------------------

    def _compute_features(self, snapshot: list[list[float]]) -> dict:
        try:
            if len(snapshot) < 16:
                return {}

            arr = np.asarray(snapshot, dtype=float)
            if arr.ndim != 2 or arr.shape[1] != 6:
                return {}

            window = 256 if len(arr) >= 256 else len(arr)
            accel = arr[-window:, 0:3]
            gyro  = arr[-window:, 3:6]
            accel_mag = np.linalg.norm(accel, axis=1)
            gyro_mag  = np.linalg.norm(gyro,  axis=1)

            features: dict = {
                "accel_mean": float(np.mean(accel_mag)),
                "accel_var":  float(np.var(accel_mag)),
                "accel_rms":  float(np.sqrt(np.mean(accel_mag ** 2))),
                "gyro_mean":  float(np.mean(gyro_mag)),
                "gyro_var":   float(np.var(gyro_mag)),
                "gyro_rms":   float(np.sqrt(np.mean(gyro_mag ** 2))),
                "sample_count": int(window),
            }

            sample_rate_hz = self._sample_rate_hz
            fft_values = np.fft.rfft(accel_mag * np.hanning(len(accel_mag)))
            fft_mags   = np.abs(fft_values)
            fft_freqs  = np.fft.rfftfreq(len(accel_mag), d=1.0 / sample_rate_hz)

            max_bins = 128
            if len(fft_mags) > max_bins:
                fft_mags  = fft_mags[:max_bins]
                fft_freqs = fft_freqs[:max_bins]

            features.update(
                {
                    "fft_freqs": fft_freqs.tolist(),
                    "fft_mags":  fft_mags.tolist(),
                    "fft_sample_rate_hz": sample_rate_hz,
                }
            )
            return features
        except Exception:
            log.exception("FeatureWorker: feature computation failed")
            return {}

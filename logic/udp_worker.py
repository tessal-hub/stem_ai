"""
logic/udp_worker.py — Background network listener for ESP32 telemetry.

Architecture:
-------------
* Runs completely independent of the main GUI thread.
* Uses standard Python `socket` for robust blocking `recvfrom`.
* Emits strictly-typed PyQt Signals to transfer data across thread boundaries safely.
"""

import json
import logging
import socket
import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

_UDP_BUFFER_SIZE = 4096
_SOCKET_TIMEOUT_S = 1.0
_HEALTH_EMIT_INTERVAL_S = 0.2
_IDLE_HEALTH_THRESHOLD_S = 2.0
_STOP_WAIT_TIMEOUT_MS = 2000


class UdpWorker(QThread):
    """Listens for incoming UDP packets and emits parsed data safely to the GUI."""

    # Outbound signals (Cross-thread safe)
    sig_data_received = pyqtSignal(dict)  # Emits parsed JSON payload
    sig_status_change = pyqtSignal(bool)  # Emits True when receiving, False if timeout/disconnected
    sig_error = pyqtSignal(str)
    sig_health_update = pyqtSignal(dict)
    sig_finished = pyqtSignal(bool, str)

    def __init__(self, host: str = "0.0.0.0", port: int = 5555, parent=None) -> None:
        super().__init__(parent)
        self.host = host
        self.port = port
        self._is_running = False
        self._sock: socket.socket | None = None
        self._packet_count = 0
        self._dropped_count = 0
        self._last_seq: int | None = None
        self._last_rx_time: float | None = None
        self._last_health_emit = 0.0
        self._ema_rate_hz: float | None = None
        self._ema_jitter_ms: float | None = None
        self._health_emit_interval = _HEALTH_EMIT_INTERVAL_S

    def run(self) -> None:
        """Main thread loop. Blocks on recvfrom() but does not block the UI."""
        self._is_running = True
        run_success = True
        run_message = "UDP worker stopped"

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(_SOCKET_TIMEOUT_S)
            self._sock.bind((self.host, self.port))

            while self._is_running:
                try:
                    data, _addr = self._sock.recvfrom(_UDP_BUFFER_SIZE)
                    self.sig_status_change.emit(True)

                    payload_str = data.decode("utf-8").strip()
                    payload_dict = json.loads(payload_str)
                    self._update_health_metrics(payload_dict)
                    self.sig_data_received.emit(payload_dict)
                except socket.timeout:
                    self._emit_idle_health_if_needed()
                except json.JSONDecodeError:
                    self.sig_error.emit("Received malformed JSON from ESP32.")
                except Exception as exc:
                    if self._is_running:
                        raise RuntimeError(f"UDP runtime error: {exc}") from exc
                    else:
                        break
        except Exception as exc:
            run_success = False
            run_message = str(exc)
            self.sig_error.emit(run_message)
        finally:
            self._is_running = False
            if self._sock:
                self._sock.close()
                self._sock = None
            self.sig_finished.emit(run_success, run_message)

    def stop(self) -> None:
        """Gracefully asks the thread to terminate."""
        self._is_running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

        import time
        start_time = time.perf_counter()
        while self.isRunning() and (time.perf_counter() - start_time < 2.0):
            time.sleep(0.01)

        if self.isRunning():
            logging.getLogger(__name__).warning(
                "UdpWorker: thread did not exit within 2 s after stop()"
            )

    def _update_health_metrics(self, payload: dict[str, Any]) -> None:
        """Cập nhật thống kê tốc độ/jitter/loss từ một gói UDP mới nhận.

        Args:
            payload: Payload JSON đã parse từ ESP32.
        """
        now = time.perf_counter()
        self._packet_count += 1

        if self._last_rx_time is not None:
            delta = max(1e-6, now - self._last_rx_time)
            rate_hz = 1.0 / delta
            interval_ms = delta * 1000.0
            if self._ema_rate_hz is None:
                self._ema_rate_hz = rate_hz
            else:
                self._ema_rate_hz = (self._ema_rate_hz * 0.9) + (rate_hz * 0.1)
            if self._ema_jitter_ms is None:
                self._ema_jitter_ms = interval_ms
            else:
                self._ema_jitter_ms = (self._ema_jitter_ms * 0.9) + (interval_ms * 0.1)

        seq = self._extract_sequence(payload)
        if seq is not None:
            if self._last_seq is not None and seq > self._last_seq + 1:
                self._dropped_count += seq - (self._last_seq + 1)
            self._last_seq = seq

        self._last_rx_time = now
        self._emit_health_snapshot(now)

    def _emit_health_snapshot(self, now: float) -> None:
        """Phát snapshot health định kỳ để UI hiển thị chất lượng kết nối.

        Args:
            now: Mốc thời gian hiện tại từ ``time.perf_counter``.
        """
        if now - self._last_health_emit < self._health_emit_interval:
            return
        self._last_health_emit = now
        total_seen = self._packet_count + self._dropped_count
        loss_pct = (self._dropped_count / total_seen) * 100.0 if total_seen else 0.0
        self.sig_health_update.emit(
            {
                "udp_rate_hz": round(self._ema_rate_hz or 0.0, 2),
                "udp_jitter_ms": round(self._ema_jitter_ms or 0.0, 2),
                "udp_received": self._packet_count,
                "udp_dropped": self._dropped_count,
                "udp_loss_pct": round(loss_pct, 2),
                "udp_last_seq": self._last_seq,
            }
        )

    def _emit_idle_health_if_needed(self) -> None:
        if self._last_rx_time is None:
            return
        now = time.perf_counter()
        if now - self._last_rx_time >= _IDLE_HEALTH_THRESHOLD_S:
            self.sig_status_change.emit(False)
            self._emit_health_snapshot(now)

    @staticmethod
    def _extract_sequence(payload: dict[str, Any]) -> int | None:
        for key in ("seq", "sequence", "packet_id"):
            if key in payload:
                try:
                    return int(payload[key])
                except (TypeError, ValueError):
                    return None
        return None

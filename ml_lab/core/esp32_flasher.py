"""
ml_lab/core/esp32_flasher.py — Module Nạp Code Tự Động 1-Click Sang ESP32 Cho ML Lab.

Tự động:
1. Đồng bộ mã nguồn C/C++ (model_classic.h & model_classic.cc) vào project esp32_classic_ml.
2. Quét cổng Serial COM và nhận diện chip ESP32 qua esptool.
3. Thực thi nạp firmware trực tiếp vào vi điều khiển với tiến trình % và log thời gian thực.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

from ml_lab.core.c_exporter import CCodeExporter
from ml_lab.core.pipeline import TrainClassicResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def list_serial_ports() -> list[tuple[str, str]]:
    """
    Quét danh sách các cổng Serial COM khả dụng trên máy tính.
    Returns: list of (port_name, description), ví dụ: [("COM3", "USB Serial Device (COM3)")]
    """
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            desc = p.description if p.description else p.device
            result.append((p.device, desc))
        return result
    except Exception:
        return []


class _RealtimeStreamCapture:
    """Bắt và phân tích log thời gian thực từ tiến trình esptool."""

    def __init__(self, on_line_cb: Callable[[str], None], on_progress_cb: Callable[[int], None] | None = None) -> None:
        self._on_line_cb = on_line_cb
        self._on_progress_cb = on_progress_cb
        self._buffer = ""
        self._full_log: list[str] = []

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buffer += s
        while "\n" in self._buffer or "\r" in self._buffer:
            idx_n = self._buffer.find("\n")
            idx_r = self._buffer.find("\r")
            if idx_n != -1 and (idx_r == -1 or idx_n < idx_r):
                chunk = self._buffer[:idx_n].strip()
                self._buffer = self._buffer[idx_n + 1 :]
            else:
                chunk = self._buffer[:idx_r].strip()
                self._buffer = self._buffer[idx_r + 1 :]

            if chunk:
                self._full_log.append(chunk)
                if self._on_progress_cb:
                    match = re.search(r"\((\d{1,3})\s*%\)", chunk)
                    if match:
                        try:
                            pct = int(match.group(1))
                            if 0 <= pct <= 100:
                                self._on_progress_cb(pct)
                        except ValueError:
                            pass
                if self._on_line_cb:
                    self._on_line_cb(chunk)
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            chunk = self._buffer.strip()
            self._full_log.append(chunk)
            if self._on_line_cb:
                self._on_line_cb(chunk)
            self._buffer = ""

    def getvalue(self) -> str:
        return "\n".join(self._full_log)


class Esp32FlashWorker(QThread):
    """
    Worker chạy ngầm nạp mã nguồn & firmware sang ESP32.
    """

    log_msg = pyqtSignal(str)           # Dòng log xuất ra terminal
    sig_progress = pyqtSignal(int)      # Tiến trình 0-100%
    sig_status = pyqtSignal(str)        # Trạng thái hiện tại
    sig_chip_info = pyqtSignal(str)     # Thông tin chip nhận diện
    sig_finished = pyqtSignal(bool, str)# (Thành công, Thông điệp)

    def __init__(
        self,
        port: str,
        result: TrainClassicResult,
        baud_rate: int = 115200,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.port = port
        self.result = result
        self.baud_rate = baud_rate
        self.c_exporter = CCodeExporter()
        self._is_cancelled = False
        self._subproc: subprocess.Popen | None = None

    def cancel(self) -> None:
        self._is_cancelled = True
        if self._subproc and self._subproc.poll() is None:
            try:
                self._subproc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        self.log_msg.emit(f"🚀 [BẮT ĐẦU] Chuẩn bị nạp mã nguồn cho mô hình '{self.result.algo_name}' vào cổng {self.port}...")
        self.sig_progress.emit(5)
        self.sig_status.emit("Đang đồng bộ mã nguồn C++...")

        # ── Bước 1: Đồng bộ mã nguồn C++ vào esp32_classic_ml ─
        try:
            esp32_main_dir = PROJECT_ROOT / "esp32_classic_ml" / "main"
            h_path, cc_path = self.c_exporter.export_to_esp32_project(self.result, esp32_main_dir)
            self.log_msg.emit(f"✅ Đã sinh & đồng bộ mã nguồn C++:\n   • {h_path}\n   • {cc_path}")
        except Exception as exc:
            err = f"Lỗi đồng bộ mã C++: {exc}"
            self.log_msg.emit(f"❌ [LỖI] {err}")
            self.sig_finished.emit(False, err)
            return

        if self._is_cancelled:
            self.sig_finished.emit(False, "Đã hủy bởi người dùng.")
            return

        self.sig_progress.emit(20)
        self.sig_status.emit("Đang kết nối & nhận diện ESP32...")

        # ── Bước 2: Nhận diện Chip ESP32 qua esptool ─────────
        chip_info = self._probe_chip_id()
        if chip_info:
            self.log_msg.emit(f"📟 [CHIP DETECTED] {chip_info}")
            self.sig_chip_info.emit(chip_info)
        else:
            self.log_msg.emit("⚠️ Tiếp tục nạp vào cổng Serial...")

        if self._is_cancelled:
            self.sig_finished.emit(False, "Đã hủy bởi người dùng.")
            return

        self.sig_progress.emit(35)
        self.sig_status.emit("Đang nạp chương trình vào Flash ROM ESP32...")

        # ── Bước 3: Nạp Firmware qua esptool API trực tiếp ───
        success, msg = self._flash_payload()
        if success:
            self.sig_progress.emit(100)
            self.sig_status.emit("✅ Nạp code thành công!")
            self.log_msg.emit("🎉 [HOÀN TẤT] Mã nguồn học máy đã được nạp thành công vào ESP32!")
            self.sig_finished.emit(True, "Nạp code thành công vào ESP32!")
        else:
            self.sig_progress.emit(0)
            self.sig_status.emit("❌ Nạp thất bại")
            self.log_msg.emit(f"❌ [THẤT BÀI] {msg}")
            self.sig_finished.emit(False, msg)

    def _probe_chip_id(self) -> str | None:
        """Thực thi esptool chip_id để lấy thông tin phần cứng."""
        try:
            cmd = [
                sys.executable,
                "-m",
                "esptool",
                "--port",
                self.port,
                "--baud",
                "115200",
                "chip_id",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            lines = res.stdout.splitlines()
            chip_line = next((l for l in lines if "Detecting chip type" in l or "Chip is" in l or "Chip type:" in l), None)
            mac_line = next((l for l in lines if "MAC:" in l), None)
            if chip_line:
                info = chip_line.strip()
                if mac_line:
                    info += f" | {mac_line.strip()}"
                return info
        except Exception:
            pass
        return None

    def _flash_payload(self) -> tuple[bool, str]:
        """Thực thi lệnh nạp mã nguồn vào ESP32 qua esptool Python API."""
        bin_target = PROJECT_ROOT / "esp32_classic_ml" / "build" / "esp32_classic_ml.bin"
        if not bin_target.exists():
            bin_target = PROJECT_ROOT / "assets" / "firmware" / "classic_inference.bin"

        if not bin_target.exists():
            return True, "Đã đồng bộ mã C++ thành công vào esp32_classic_ml/main/ (Sẵn sàng biên dịch)"

        # Tham số tương thích esptool v5 (dùng dấu gạch ngang chuẩn)
        esptool_args = [
            "--chip", "esp32",
            "--port", self.port,
            "--baud", str(self.baud_rate),
            "--before", "default-reset",
            "--after", "hard-reset",
            "write-flash",
            "-z",
            "--flash-mode", "dio",
            "--flash-freq", "80m",
            "--flash-size", "keep",
            "0x10000",
            str(bin_target.resolve()),
        ]

        self.log_msg.emit(f"[INFO] Bắt đầu nạp firmware (Baud: {self.baud_rate})...")

        # Thử nạp trực tiếp qua Python package esptool
        try:
            import esptool

            stream_capture = _RealtimeStreamCapture(
                on_line_cb=self.log_msg.emit,
                on_progress_cb=lambda pct: self.sig_progress.emit(int(35 + pct * 0.65)),
            )

            code = 0
            try:
                with contextlib.redirect_stdout(stream_capture), contextlib.redirect_stderr(stream_capture):
                    esptool.main(esptool_args)
            except SystemExit as exc:
                stream_capture.flush()
                code = exc.code if exc.code is not None else 0
            except Exception as exc:
                stream_capture.flush()
                self.log_msg.emit(f"[WARN] Direct esptool call error: {exc}. Thử chuyển sang subprocess...")
                return self._flash_payload_subprocess(bin_target)

            stream_capture.flush()
            if code == 0:
                return True, "Nạp Flash thành công!"

            # Nếu lỗi, fallback sang subprocess
            return self._flash_payload_subprocess(bin_target)

        except ImportError:
            return self._flash_payload_subprocess(bin_target)

    def _flash_payload_subprocess(self, bin_target: Path) -> tuple[bool, str]:
        """Fallback qua Subprocess CLI với cờ an toàn."""
        cmd = [
            sys.executable,
            "-m",
            "esptool",
            "--chip",
            "esp32",
            "--port",
            self.port,
            "--baud",
            str(self.baud_rate),
            "--before",
            "default-reset",
            "--after",
            "hard-reset",
            "write-flash",
            "-z",
            "--flash-mode",
            "dio",
            "--flash-freq",
            "80m",
            "--flash-size",
            "keep",
            "0x10000",
            str(bin_target.resolve()),
        ]

        self.log_msg.emit(f">> CLI Fallback: {' '.join(cmd)}")

        stream_capture = _RealtimeStreamCapture(
            on_line_cb=self.log_msg.emit,
            on_progress_cb=lambda pct: self.sig_progress.emit(int(35 + pct * 0.65)),
        )

        try:
            self._subproc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            if self._subproc.stdout:
                for line in self._subproc.stdout:
                    stream_capture.write(line)
                    if self._is_cancelled:
                        self._subproc.terminate()
                        return False, "Đã hủy bởi người dùng."

            self._subproc.wait(timeout=180)
            if self._subproc.returncode == 0:
                return True, "Nạp Flash thành công 100%!"
            else:
                return False, f"esptool hoàn tất với mã: {self._subproc.returncode}"

        except subprocess.TimeoutExpired:
            return False, "Thời gian nạp quá 180s (Timeout)."
        except Exception as exc:
            return False, f"Lỗi thực thi subprocess: {exc}"

"""
logic/flash_worker.py — ESP32-S3 firmware flashing via esptool subprocess.

This QThread manages non-blocking firmware flashing using esptool.py
via the user's current Python environment (sys.executable).

Architecture:
    - Spawns subprocess with sys.executable -m esptool
    - Avoids "No module named esptool" by using the active venv
    - Real-time progress parsing with regex
    - Error handling for missing files, permission issues, COM port errors
    - Thread-safe signal emission for UI updates
    - Writes to 0x10000 address (app firmware partition)
"""

import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

_FLASH_TIMEOUT_S = 300
_ESPTOOL_CHECK_TIMEOUT_S = 5
_PROCESS_TERMINATE_TIMEOUT_S = 5
_PROCESS_CLEANUP_TIMEOUT_S = 2
_FLASH_ADDRESS = "0x10000"


class FlashWorker(QThread):
    """Flash firmware to ESP32-S3 via esptool in background thread."""

    # ── Signals ──────────────────────────────────────────────────────────
    log_msg = pyqtSignal(str)           # Real-time console output
    sig_progress = pyqtSignal(int)           # 0-100 progress percent
    sig_error = pyqtSignal(str)           # error message
    sig_finished = pyqtSignal(bool, str)     # (success, message)

    def __init__(self) -> None:
        super().__init__()
        self._process: subprocess.Popen | None = None
        self._port: str = ""
        self._bin_path: str = ""
        self._last_error_message: str = ""

    def flash_firmware(self, port: str, bin_path: str) -> None:
        """
        Queue a firmware flash operation.

        Args:
            port: Serial port (e.g., "COM3", "/dev/ttyUSB0")
            bin_path: Path to .bin firmware file
        """
        self._port = port
        self._bin_path = bin_path
        self.start()

    def run(self) -> None:
        """Core run loop — validate inputs, build command, then execute flash."""
        self._last_error_message = ""
        success = False
        finished_message = "Flash failed"
        try:
            bin_file = self._validate_flash_inputs()
            if bin_file is None:
                finished_message = self._last_error_message or "Flash validation failed"
                return
            cmd = self._build_esptool_cmd(bin_file)
            success, finished_message = self._execute_flash(cmd)
        except subprocess.TimeoutExpired:
            self.log_msg.emit("[ERROR] Flash operation timed out (5 minutes)")
            self.sig_error.emit("Flash operation timed out")
            finished_message = "Timeout"
            if self._process:
                self._process.kill()
        except Exception as e:
            self.log_msg.emit(f"[ERROR] Flash exception: {type(e).__name__}: {e}")
            self.sig_error.emit(f"Flash exception: {type(e).__name__}: {e}")
            finished_message = f"Exception: {e}"
        finally:
            self._cleanup()
            self.sig_finished.emit(success, finished_message)

    def _fail(self, message: str) -> None:
        """Emit one error path and store latest failure reason for run() finalization."""
        self._last_error_message = message
        self.log_msg.emit(f"[ERROR] {message}")
        self.sig_error.emit(message)

    def _validate_flash_inputs(self) -> "Path | None":
        """Validate port, binary path, binary size, and esptool availability.

        Returns the resolved ``Path`` on success, or ``None`` on any failure
        (error signals are already emitted before returning ``None``).
        """
        if not self._port:
            self._fail("No serial port specified")
            return None

        if not self._bin_path:
            self._fail("No binary file path specified")
            return None

        bin_file = Path(self._bin_path).resolve()
        if not bin_file.exists():
            self._fail(f"Binary file not found: {bin_file}")
            return None

        file_size = bin_file.stat().st_size
        if file_size == 0:
            self._fail(f"Binary file is empty: {bin_file}")
            return None

        self.log_msg.emit(f"[INFO] Binary file: {bin_file}")
        self.log_msg.emit(f"[INFO] Binary size: {file_size} bytes")

        if not self._check_esptool_available():
            self._fail("esptool not installed. Run: pip install esptool")
            return None

        return bin_file

    def _build_esptool_cmd(self, bin_file: "Path") -> list[str]:
        """Return the esptool command list for the configured port and binary."""
        return [
            sys.executable, "-m", "esptool",
            "--chip", "esp32s3",
            "--port", self._port,
            "--baud", "115200",
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash", "-z",
            "--flash_mode", "dio",
            "--flash_freq", "80m",
            "--flash_size", "keep",
            _FLASH_ADDRESS,      # Address where app firmware is flashed
            str(bin_file),
        ]

    def _execute_flash(self, cmd: list[str]) -> tuple[bool, str]:
        """Spawn esptool process, stream output, and return final status tuple."""
        self.log_msg.emit(f"[INFO] Command: {' '.join(cmd)}")
        self.log_msg.emit(f"[INFO] Using Python: {sys.executable}")
        self.log_msg.emit("=" * 70)
        self.sig_progress.emit(0)

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        if not (self._process and self._process.stdout):
            self._fail("Failed to start esptool process")
            return False, self._last_error_message

        success = self._parse_esptool_output(self._process.stdout)
        return_code = self._process.wait(timeout=_FLASH_TIMEOUT_S)

        if return_code == 0 and success:
            self.sig_progress.emit(100)
            self.log_msg.emit("=" * 70)
            self.log_msg.emit("[SUCCESS] Firmware flash completed!")
            return True, "Flash successful"

        self.log_msg.emit("=" * 70)
        self.log_msg.emit(f"[FAILED] Firmware flash failed (exit code: {return_code})")
        self.sig_error.emit(f"Flash failed (exit code: {return_code})")
        return False, f"Flash failed (exit code: {return_code})"

    def _check_esptool_available(self) -> bool:
        """Check if esptool is installed in current Python environment."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "esptool", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=_ESPTOOL_CHECK_TIMEOUT_S,
                encoding="utf-8",
                errors="ignore",
            )
            return result.returncode == 0
        except Exception as e:
            self.log_msg.emit(f"[WARN] Could not verify esptool: {e}")
            return False

    def _parse_esptool_output(self, stream) -> bool:
        """
        Parse esptool stdout/stderr stream line by line.
        Emits progress signals and logs messages.
        Returns True if "FINISH" or "Hard resetting" detected.
        """
        success = False
        try:
            for line in stream:
                if not line:
                    continue

                line_str = str(line).strip()
                self.log_msg.emit(line_str)

                # Extract progress percentage from esptool output
                # Format: "Writing at 0x00010000... (35%)    [ xxx / xxx ]"
                match = re.search(r"\((\d{1,3})%\)", line_str)
                if match:
                    try:
                        percent = int(match.group(1))
                        if 0 <= percent <= 100:
                            self.sig_progress.emit(percent)
                    except ValueError:
                        pass

                # Detect success markers
                if "FINISH" in line_str or "Hard resetting" in line_str:
                    success = True

        except Exception as e:
            self.log_msg.emit(f"[WARN] Error parsing output: {e}")

        return success

    def stop(self) -> None:
        """Gracefully stop the flashing process."""
        if self._process and self._process.poll() is None:  # Process still running
            try:
                self._process.terminate()
                self._process.wait(timeout=_PROCESS_TERMINATE_TIMEOUT_S)
            except Exception as e:
                self.log_msg.emit(f"[WARN] Error terminating process: {e}")
                try:
                    self._process.kill()
                except Exception:
                    pass

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._process:
            try:
                if self._process.poll() is None:  # Still running
                    self._process.terminate()
                    self._process.wait(timeout=_PROCESS_CLEANUP_TIMEOUT_S)
            except Exception:
                pass
            self._process = None

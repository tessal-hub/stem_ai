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

import os
import re
import sys
import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class FlashWorker(QThread):
    """Flash firmware to ESP32-S3 via esptool in background thread."""

    # ── Signals ──────────────────────────────────────────────────────────
    progress = pyqtSignal(int)          # 0-100 progress percent
    log_msg = pyqtSignal(str)           # Real-time console output
    finished = pyqtSignal(bool, str)    # (success, message)

    def __init__(self) -> None:
        super().__init__()
        self._process: subprocess.Popen | None = None
        self._port: str = ""
        self._bin_path: str = ""

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
        """Core run loop — execute esptool flash command."""
        try:
            # ── Step 1: Validate inputs ───────────────────────────────
            if not self._port:
                self.log_msg.emit("[ERROR] No serial port specified")
                self.finished.emit(False, "No serial port specified")
                return

            if not self._bin_path:
                self.log_msg.emit("[ERROR] No binary file path specified")
                self.finished.emit(False, "No binary file path specified")
                return

            # ── Step 2: Resolve file path (absolute) ──────────────────
            bin_file = Path(self._bin_path).resolve()
            if not bin_file.exists():
                self.log_msg.emit(f"[ERROR] Binary file not found: {bin_file}")
                self.finished.emit(False, f"Binary file not found: {bin_file}")
                return

            file_size = bin_file.stat().st_size
            if file_size == 0:
                self.log_msg.emit(f"[ERROR] Binary file is empty: {bin_file}")
                self.finished.emit(False, f"Binary file is empty: {bin_file}")
                return

            self.log_msg.emit(f"[INFO] Binary file: {bin_file}")
            self.log_msg.emit(f"[INFO] Binary size: {file_size} bytes")

            # ── Step 3: Check esptool availability ────────────────────
            if not self._check_esptool_available():
                self.log_msg.emit("[ERROR] esptool not installed. Run: pip install esptool")
                self.finished.emit(False, "esptool not installed")
                return

            # ── Step 4: Build esptool command ────────────────────────
            # Using sys.executable to ensure venv compatibility
            cmd = [
                sys.executable,
                "-m",
                "esptool",
                "--chip", "esp32s3",
                "--port", self._port,
                "--baud", "115200",
                "--before", "default_reset",
                "--after", "hard_reset",
                "write_flash",
                "-z",
                "--flash_mode", "dio",
                "--flash_freq", "80m",
                "--flash_size", "keep",
                "0x10000",           # Address where app firmware is flashed
                str(bin_file),
            ]

            self.log_msg.emit(f"[INFO] Command: {' '.join(cmd)}")
            self.log_msg.emit(f"[INFO] Using Python: {sys.executable}")
            self.log_msg.emit("=" * 70)
            self.progress.emit(0)

            # ── Step 5: Execute flash command ────────────────────────
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            # ── Step 6: Stream output and parse progress ─────────────
            if self._process and self._process.stdout:
                success = self._parse_esptool_output(self._process.stdout)

                # Wait for process to finish
                return_code = self._process.wait(timeout=300)

                if return_code == 0 and success:
                    self.progress.emit(100)
                    self.log_msg.emit("=" * 70)
                    self.log_msg.emit("[SUCCESS] Firmware flash completed!")
                    self.finished.emit(True, "Flash successful")
                else:
                    self.log_msg.emit("=" * 70)
                    self.log_msg.emit(f"[FAILED] Firmware flash failed (exit code: {return_code})")
                    self.finished.emit(False, "Flash failed")
            else:
                self.log_msg.emit("[ERROR] Failed to start esptool process")
                self.finished.emit(False, "Process failed")

        except subprocess.TimeoutExpired:
            self.log_msg.emit("[ERROR] Flash operation timed out (5 minutes)")
            self.finished.emit(False, "Timeout")
            if self._process:
                self._process.kill()

        except Exception as e:
            self.log_msg.emit(f"[ERROR] Flash exception: {type(e).__name__}: {e}")
            self.finished.emit(False, f"Exception: {e}")

        finally:
            self._cleanup()

    def _check_esptool_available(self) -> bool:
        """Check if esptool is installed in current Python environment."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "esptool", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
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
                            self.progress.emit(percent)
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
                self._process.wait(timeout=5)
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
                    self._process.wait(timeout=2)
            except Exception:
                pass
            self._process = None

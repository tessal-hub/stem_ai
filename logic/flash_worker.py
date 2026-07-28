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
        self._cancel_requested = False
        self._port: str = ""
        self._flash_parts: dict[str, str] = {}
        self._last_error_message: str = ""

    def flash_firmware(self, port: str, bin_path: str = "", flash_parts: dict[str, str] = None) -> None:
        """
        Queue a firmware flash operation.

        Args:
            port: Serial port (e.g., "COM3", "/dev/ttyUSB0")
            bin_path: Path to .bin firmware file (flashed to 0x10000 by default)
            flash_parts: Dictionary mapping address strings to file paths
        """
        self._port = port
        self._flash_parts = flash_parts or {}
        if bin_path:
            self._flash_parts[_FLASH_ADDRESS] = bin_path
        self.start()

    def run(self) -> None:
        """Core run loop — validate inputs, build command, then execute flash."""
        self._last_error_message = ""
        success = False
        finished_message = "Flash failed"

        if self._cancel_requested:
            self.sig_finished.emit(False, "Flash cancelled before start")
            return

        try:
            valid_parts = self._validate_flash_inputs()
            if not valid_parts:
                finished_message = self._last_error_message or "Flash validation failed"
                return
            cmd = self._build_esptool_cmd(valid_parts)
            success, finished_message = self._execute_flash(cmd)
        except subprocess.TimeoutExpired:
            self.log_msg.emit("[ERROR] Flash operation timed out (5 minutes)")
            self.sig_error.emit("Flash operation timed out")
            finished_message = "Timeout"
        except FileNotFoundError as e:
            self.log_msg.emit(f"[ERROR] Executable or binary not found: {e}")
            self.sig_error.emit("Tool or binary not found")
            finished_message = "FileNotFound"
        except PermissionError as e:
            self.log_msg.emit(f"[ERROR] Permission denied: {e}")
            self.sig_error.emit("Permission denied executing esptool")
            finished_message = "PermissionError"
        except subprocess.SubprocessError as e:
            self.log_msg.emit(f"[ERROR] Subprocess error during flash: {e}")
            self.sig_error.emit("Subprocess execution failed")
            finished_message = "SubprocessError"
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

    def _validate_flash_inputs(self) -> dict[str, "Path"]:
        """Validate port, binary paths, binary sizes, and esptool availability.

        Returns a dict mapping addresses to validated ``Path`` objects, or empty dict on failure.
        """
        if not self._port:
            self._fail("No serial port specified")
            return {}

        if not self._flash_parts:
            self._fail("No binaries specified for flashing")
            return {}

        valid_parts = {}
        for addr, path_str in self._flash_parts.items():
            bin_file = Path(path_str).resolve()
            
            import sys
            from config import FIRMWARE_BIN_DIR, APP_DATA_DIR, WORKSPACE_ROOT
            allowed_roots = [
                FIRMWARE_BIN_DIR.resolve(),
                APP_DATA_DIR.resolve(),
                (WORKSPACE_ROOT / "assets").resolve(),
            ]
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                allowed_roots.append(Path(sys._MEIPASS).resolve())

            is_valid = any(
                bin_file == root or bin_file.is_relative_to(root)
                for root in allowed_roots
            )
            if not is_valid:
                self._fail(f"Path traversal detected: {bin_file}")
                return {}

            if not bin_file.exists():
                self._fail(f"Binary file not found: {bin_file}")
                return {}

            file_size = bin_file.stat().st_size
            if file_size == 0:
                self._fail(f"Binary file is empty: {bin_file}")
                return {}

            self.log_msg.emit(f"[INFO] File: {bin_file} -> {addr} ({file_size} bytes)")
            valid_parts[addr] = bin_file

        if not self._check_esptool_available():
            self._fail("esptool not installed. Run: pip install esptool")
            return {}

        return valid_parts

    def _build_esptool_cmd(self, valid_parts: dict[str, "Path"]) -> list[str]:
        """Return the esptool argument list for the configured port and binaries."""
        args = [
            "--chip", "esp32",
            "--port", self._port,
            "--baud", "115200",
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash", "-z",
            "--flash_mode", "dio",
            "--flash_freq", "80m",
            "--flash_size", "keep",
        ]
        for addr, path in valid_parts.items():
            args.extend([addr, str(path)])
        return args

    def _execute_flash(self, args: list[str]) -> tuple[bool, str]:
        """Call esptool Python API directly (works in both frozen and normal mode).

        If stub files are missing (common in packaged .exe), automatically
        retries with --no-stub to avoid the 'Flasher stub data is missing' error.
        """
        self.log_msg.emit(f"[INFO] esptool args: {' '.join(args)}")
        self.log_msg.emit("=" * 70)
        self.sig_progress.emit(0)
        try:
            import esptool
            import io
            import contextlib

            return self._run_esptool(esptool, args)
        except ImportError:
            self.log_msg.emit("[ERROR] esptool Python package not found. Run: pip install esptool")
            return False, "esptool not installed"
        except Exception as exc:
            self.log_msg.emit(f"[ERROR] esptool exception: {exc}")
            return False, str(exc)

    def _run_esptool(self, esptool, args: list[str], _retry_no_stub: bool = False) -> tuple[bool, str]:
        """Run esptool.main() with output capture. Retries with --no-stub on stub error."""
        import io
        import contextlib

        log_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(log_buf), contextlib.redirect_stderr(log_buf):
                esptool.main(args)
        except SystemExit as exc:
            output = log_buf.getvalue()
            # Flush captured output before processing result
            for line in output.splitlines():
                self.log_msg.emit(line)
            code = exc.code if exc.code is not None else -1
            if code == 0:
                self.sig_progress.emit(100)
                self.log_msg.emit("[SUCCESS] Firmware flash completed!")
                return True, "Flash successful"
            self.log_msg.emit(f"[FAIL] esptool exited with code {code}")
            return False, f"Flash failed (exit code: {code})"
        except Exception as exc:
            output = log_buf.getvalue()
            for line in output.splitlines():
                self.log_msg.emit(line)
            raise

        output = log_buf.getvalue()

        # Check for stub-missing error BEFORE emitting lines — retry with --no-stub
        _STUB_MISSING = "stub data is missing" in output.lower() or "stub files" in output.lower()
        if _STUB_MISSING and not _retry_no_stub:
            self.log_msg.emit("[WARN] Stub files missing — retrying with --no-stub (slower but compatible)...")
            no_stub_args = ["--no-stub"] + args
            return self._run_esptool(esptool, no_stub_args, _retry_no_stub=True)

        success = False
        for line in output.splitlines():
            self.log_msg.emit(line)
            if "FINISH" in line or "Hard resetting" in line:
                success = True
            match = re.search(r"\((\d{1,3})%\)", line)
            if match:
                try:
                    percent = int(match.group(1))
                    if 0 <= percent <= 100:
                        self.sig_progress.emit(percent)
                except ValueError:
                    pass

        if success:
            self.sig_progress.emit(100)
            self.log_msg.emit("=" * 70)
            self.log_msg.emit("[SUCCESS] Firmware flash completed!")
            return True, "Flash successful"
        self.log_msg.emit("=" * 70)
        self.log_msg.emit("[FAIL] Firmware flash FAILED: " + ("Flasher stub data is missing for ESP32.\n"
            "This means the esptool installation is incomplete or broken - "
            "stub JSON files were removed or a third-party distribution package didn't ship them. "
            "It is\nunlikely to be a defect in esptool itself.\n\n"
            "Try reinstalling esptool or restoring the stub files from the upstream source tree. "
            "As a workaround, you can pass --no-stub (slower operation, fewer\nfeatures)."
            if _STUB_MISSING else "no completion marker detected"))
        return False, "Flash failed (stub missing)" if _STUB_MISSING else "Flash failed (no completion marker)"


    def _check_esptool_available(self) -> bool:
        """Check if esptool is importable as a Python module."""
        try:
            import esptool  # noqa: F401
            return True
        except ImportError:
            self.log_msg.emit("[WARN] esptool Python module not found: pip install esptool")
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
        self._cancel_requested = True

    def _cleanup(self) -> None:
        """Clean up resources."""
        pass

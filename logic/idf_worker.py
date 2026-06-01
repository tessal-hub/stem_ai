"""
logic/idf_worker.py — Background worker for ESP-IDF build operations.
"""

import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class IDFBuildWorker(QThread):
    """Executes idf.py build in a separate thread."""
    sig_log = pyqtSignal(str)
    sig_finished = pyqtSignal(bool, str)
    sig_progress = pyqtSignal(int)

    def __init__(self, project_dir: Path):
        super().__init__()
        self.project_dir = project_dir

    def run(self):
        try:
            self.sig_log.emit(f"[BUILD] Starting ESP-IDF build in {self.project_dir}...")

            # Check if idf.py exists in path
            # On Windows, idf.py usually runs via idf.py.exe or python idf.py
            # We assume the user has run the export script or has it in PATH
            cmd = ["idf.py", "build"]

            process = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                bufsize=1
            )

            if process.stdout:
                for line in process.stdout:
                    self.sig_log.emit(line.strip())

            process.wait()

            if process.returncode == 0:
                bin_path = self.project_dir / "build" / "mpu6050.bin"
                self.sig_finished.emit(True, str(bin_path))
            else:
                self.sig_finished.emit(False, f"Build failed with exit code {process.returncode}")

        except Exception as e:
            self.sig_finished.emit(False, str(e))

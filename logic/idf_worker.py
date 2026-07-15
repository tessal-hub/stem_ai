"""
logic/idf_worker.py — Background worker for ESP-IDF build operations.
"""

import shutil
import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class IDFBuildWorker(QThread):
    """Executes idf.py build in a separate thread."""
    sig_log = pyqtSignal(str)
    sig_finished = pyqtSignal(bool, str)
    sig_progress = pyqtSignal(int)

    def __init__(self, project_dir: Path, port: str = None):
        super().__init__()
        self.project_dir = project_dir
        self.port = port

    def run(self):
        # Kiểm tra idf.py có trong PATH không — khi frozen exe thừa hưởng PATH tối thiểu
        if not shutil.which("idf.py"):
            self.sig_finished.emit(
                False,
                "ESP-IDF không tìm thấy trong PATH. "
                "Hãy cài đặt và kích hoạt ESP-IDF trước (chạy 'idf_cmd_init.bat' hoặc 'export.bat').",
            )
            return

        try:
            cmd_str = "build"
            if self.port:
                cmd_str = f"flash -p {self.port}"
                self.sig_log.emit(f"[BUILD] Starting ESP-IDF build & flash to {self.port}...")
            else:
                self.sig_log.emit(f"[BUILD] Starting ESP-IDF build in {self.project_dir}...")

            cmd = ["idf.py", "build"]
            if self.port:
                cmd = ["idf.py", "build", "flash", "-p", self.port]

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


"""
logic/data_io_worker.py — Off-thread file I/O worker for dataset operations.

All file-system heavy-lifting (CSV save, spell delete, CSV export, and the
directory-scan ``refresh_database``) is routed through this worker so that
the Qt event loop — and therefore the UI — is never stalled by disk I/O.

Job protocol
------------
Jobs are pushed onto an internal ``queue.Queue`` as plain tuples:

    ("save",   spell_name: str, data: list[list[float]], tag: str)
    ("delete", spell_name: str)
    ("export", buf: list[list[float]], path: str)
    ("refresh",)                   # trigger a database rescan only

Results are signalled back to the main thread via Qt signals that the
caller connects with ``QueuedConnection`` semantics (the default when
connecting cross-thread).
"""

from __future__ import annotations

import csv
import glob as glob_module
import json
import logging
import os
import queue
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class DataIOWorker(QThread):
    """Background thread that handles all dataset file operations."""

    # ── Result signals (emitted in the worker thread, delivered to the main
    #    thread via Qt's automatic QueuedConnection cross-thread dispatch) ──
    sig_save_done    = pyqtSignal(bool, str)   # (success, message)
    sig_delete_done  = pyqtSignal(bool, str)   # (success, message)
    sig_export_done  = pyqtSignal(bool, str)   # (success, message)
    # Emitted after any operation that changes the dataset directory layout.
    sig_db_refreshed = pyqtSignal(dict)        # spell_counts: {name: int}

    def __init__(self, dataset_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._dataset_dir = dataset_dir
        self._job_queue: queue.Queue[tuple] = queue.Queue()
        self._running = False

    # ------------------------------------------------------------------
    # Public API — call from the main thread
    # ------------------------------------------------------------------

    def enqueue_save(
        self,
        spell_name: str,
        data: list[list[float]],
        tag: str = "",
    ) -> None:
        """Schedule a cropped sample write (non-blocking)."""
        self._job_queue.put_nowait(("save", spell_name, data, tag))

    def enqueue_delete(self, spell_name: str) -> None:
        """Schedule a spell deletion (non-blocking)."""
        self._job_queue.put_nowait(("delete", spell_name))

    def enqueue_export(self, buf: list[list[float]], path: str) -> None:
        """Schedule a buffer CSV export (non-blocking)."""
        self._job_queue.put_nowait(("export", buf, path))

    def enqueue_refresh(self) -> None:
        """Schedule a database directory rescan (non-blocking)."""
        self._job_queue.put_nowait(("refresh",))

    def stop(self) -> None:
        """Request the worker loop to exit and wait up to 2 s."""
        self._running = False
        # Unblock the blocking get() with a sentinel.
        self._job_queue.put_nowait(("_stop",))
        if not self.wait(2000):
            log.warning("DataIOWorker: thread did not exit within 2 s")

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                job = self._job_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            kind = job[0]
            if kind == "_stop":
                break
            elif kind == "save":
                _, spell_name, data, tag = job
                self._do_save(spell_name, data, tag)
            elif kind == "delete":
                _, spell_name = job
                self._do_delete(spell_name)
            elif kind == "export":
                _, buf, path = job
                self._do_export(buf, path)
            elif kind == "refresh":
                self._do_refresh()
            else:
                log.warning("DataIOWorker: unknown job kind %r", kind)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _do_save(self, spell_name: str, data: list[list[float]], tag: str) -> None:
        try:
            folder = os.path.join(self._dataset_dir, spell_name.strip().upper())
            os.makedirs(folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(folder, f"sample_{timestamp}.csv")
            meta_path = os.path.join(folder, f"sample_{timestamp}.meta.json")

            with open(file_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["aX", "aY", "aZ", "gX", "gY", "gZ"])
                writer.writerows(data)

            if tag:
                with open(meta_path, mode="w", encoding="utf-8") as meta_file:
                    json.dump(
                        {
                            "tag": tag,
                            "timestamp": timestamp,
                            "sample_count": len(data),
                        },
                        meta_file,
                        ensure_ascii=True,
                        indent=2,
                    )

            counts = self._scan_database()
            self.sig_db_refreshed.emit(counts)
            self.sig_save_done.emit(True, f"Saved {len(data)} samples → {spell_name}")
        except Exception as exc:
            msg = f"Save failed: {type(exc).__name__}: {exc}"
            log.exception("DataIOWorker._do_save")
            self.sig_save_done.emit(False, msg)

    def _do_delete(self, spell_name: str) -> None:
        try:
            spell_path = os.path.join(self._dataset_dir, spell_name.strip().upper())
            if not os.path.exists(spell_path):
                self.sig_delete_done.emit(False, f"Spell not found: {spell_name}")
                return

            for filename in os.listdir(spell_path):
                file_path = os.path.join(spell_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(spell_path)

            counts = self._scan_database()
            self.sig_db_refreshed.emit(counts)
            self.sig_delete_done.emit(True, f"Deleted spell: {spell_name}")
        except Exception as exc:
            msg = f"Delete failed: {type(exc).__name__}: {exc}"
            log.exception("DataIOWorker._do_delete")
            self.sig_delete_done.emit(False, msg)

    def _do_export(self, buf: list[list[float]], path: str) -> None:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
                writer.writerows(buf)
            self.sig_export_done.emit(True, f"Exported {len(buf)} samples → {path}")
        except Exception as exc:
            msg = f"Export failed: {type(exc).__name__}: {exc}"
            log.exception("DataIOWorker._do_export")
            self.sig_export_done.emit(False, msg)

    def _do_refresh(self) -> None:
        counts = self._scan_database()
        self.sig_db_refreshed.emit(counts)

    def _scan_database(self) -> dict[str, int]:
        """Return {spell_name: csv_file_count} for the dataset directory."""
        counts: dict[str, int] = {}
        if not os.path.exists(self._dataset_dir):
            return counts
        for item in os.listdir(self._dataset_dir):
            spell_path = os.path.join(self._dataset_dir, item)
            if os.path.isdir(spell_path):
                csv_files = glob_module.glob(os.path.join(spell_path, "*.csv"))
                counts[item] = len(csv_files)
        return counts

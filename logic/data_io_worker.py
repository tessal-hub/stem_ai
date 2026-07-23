"""
logic/data_io_worker.py — Off-thread file I/O worker for dataset operations.

All file-system heavy-lifting (CSV save, spell delete, CSV export, and the
directory-scan ``refresh_database``) is routed through this worker so that
the Qt event loop — and therefore the UI — is never stalled by disk I/O.

Job protocol
------------
Jobs are pushed onto an internal ``queue.Queue`` as plain tuples:

    ("save",   spell_name: str, data: list[list[float]])
    ("delete", spell_name: str)
    ("delete_latest_sample", spell_name: str)
    ("export", buf: list[list[float]], path: str)
    ("refresh",)                   # trigger a database rescan only

Results are signalled back to the main thread via Qt signals that the
caller connects with ``QueuedConnection`` semantics (the default when
connecting cross-thread).
"""

from __future__ import annotations

import csv
import logging
import os
import queue
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from constants import is_system_spell

from .dataset_layout import (discover_class_directories, spell_write_dir,
                             storage_dirs_for_spell)

log = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 50
_QUEUE_WARN_THRESHOLD = 40


class DataIOWorker(QThread):
    """Background thread that handles all dataset file operations."""

    # ── Result signals (emitted in the worker thread, delivered to the main
    #    thread via Qt's automatic QueuedConnection cross-thread dispatch) ──
    sig_save_done = pyqtSignal(bool, str)   # (success, message)
    sig_delete_done = pyqtSignal(bool, str)   # (success, message)
    sig_delete_sample_done = pyqtSignal(bool, str)  # (success, message)
    sig_export_done = pyqtSignal(bool, str)   # (success, message)
    sig_queue_warning = pyqtSignal(str)        # queue drop/backpressure warnings
    # Emitted after any operation that changes the dataset directory layout.
    sig_db_refreshed = pyqtSignal(dict)        # spell_counts: {name: int}

    def __init__(self, dataset_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._dataset_dir = dataset_dir
        self._job_queue: queue.Queue[tuple] = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        self._running = False

    @property
    def dataset_dir(self) -> str:
        return self._dataset_dir

    @dataset_dir.setter
    def dataset_dir(self, value: str) -> None:
        self._dataset_dir = value

    def _warn_if_queue_pressure(self) -> None:
        qsize = self._job_queue.qsize()
        if qsize >= _QUEUE_WARN_THRESHOLD:
            log.warning(
                "DataIOWorker: queue depth high (%d/%d)",
                qsize,
                _QUEUE_MAXSIZE,
            )

    # ------------------------------------------------------------------
    # Public API — call from the main thread
    # ------------------------------------------------------------------

    def enqueue_save(
        self,
        spell_name: str,
        data: list[list[float]],
        prefix: str = "",
    ) -> None:
        """Schedule a cropped sample write (non-blocking)."""
        try:
            self._job_queue.put_nowait(("save", spell_name, data, prefix))
            self._warn_if_queue_pressure()
        except queue.Full:
            msg = f"DataIOWorker queue full: save job dropped for spell '{spell_name}'"
            log.warning(msg)
            self.sig_queue_warning.emit(msg)

    def enqueue_delete(self, spell_name: str) -> None:
        """Schedule a spell deletion (non-blocking)."""
        try:
            self._job_queue.put_nowait(("delete", spell_name))
            self._warn_if_queue_pressure()
        except queue.Full:
            msg = f"DataIOWorker queue full: delete job dropped for spell '{spell_name}'"
            log.warning(msg)
            self.sig_queue_warning.emit(msg)

    def enqueue_delete_latest_sample(self, spell_name: str) -> None:
        """Schedule deletion of the newest CSV sample for a spell."""
        try:
            self._job_queue.put_nowait(("delete_latest_sample", spell_name))
            self._warn_if_queue_pressure()
        except queue.Full:
            msg = (
                "DataIOWorker queue full: latest-sample delete job dropped "
                f"for spell '{spell_name}'"
            )
            log.warning(msg)
            self.sig_queue_warning.emit(msg)

    def enqueue_export(self, buf: list[list[float]], path: str) -> None:
        """Schedule a buffer CSV export (non-blocking)."""
        try:
            self._job_queue.put_nowait(("export", buf, path))
            self._warn_if_queue_pressure()
        except queue.Full:
            msg = "DataIOWorker queue full: export job dropped"
            log.warning(msg)
            self.sig_queue_warning.emit(msg)

    def enqueue_refresh(self) -> None:
        """Schedule a database directory rescan (non-blocking)."""
        try:
            self._job_queue.put_nowait(("refresh",))
            self._warn_if_queue_pressure()
        except queue.Full:
            msg = "DataIOWorker queue full: refresh job dropped"
            log.warning(msg)
            self.sig_queue_warning.emit(msg)

    def stop(self) -> None:
        """Cooperatively ask the worker to exit (non-blocking)."""
        self._running = False
        try:
            self._job_queue.put_nowait(("_stop",))
        except queue.Full:
            pass

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
                if len(job) == 4:
                    _, spell_name, data, prefix = job
                else:
                    _, spell_name, data = job
                    prefix = ""
                self._do_save(spell_name, data, prefix)
            elif kind == "delete":
                _, spell_name = job
                self._do_delete(spell_name)
            elif kind == "delete_latest_sample":
                _, spell_name = job
                self._do_delete_latest_sample(spell_name)
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

    def _do_save(self, spell_name: str, data: list[list[float]], prefix: str = "") -> None:
        try:
            folder = spell_write_dir(Path(self._dataset_dir), spell_name)
            folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_sample_{timestamp}.csv" if prefix else f"sample_{timestamp}.csv"
            file_path = folder / filename

            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
                writer.writerows(data)

            counts = self._scan_database()
            self.sig_db_refreshed.emit(counts)
            self.sig_save_done.emit(True, f"Saved {len(data)} samples → {spell_name}")
        except Exception as exc:
            msg = f"Save failed: {type(exc).__name__}: {exc}"
            log.exception("DataIOWorker._do_save")
            self.sig_save_done.emit(False, msg)

    def _do_delete(self, spell_name: str) -> None:
        try:
            if is_system_spell(spell_name):
                self.sig_delete_done.emit(False, f"Protected system spell cannot be deleted: {spell_name}")
                return

            dirs = storage_dirs_for_spell(Path(self._dataset_dir), spell_name)
            if not dirs:
                self.sig_delete_done.emit(False, f"Spell not found: {spell_name}")
                return

            for spell_path in dirs:
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

    def _do_delete_latest_sample(self, spell_name: str) -> None:
        """Delete the most recently named sample CSV under one spell folder."""
        try:
            dirs = storage_dirs_for_spell(Path(self._dataset_dir), spell_name)
            if not dirs:
                self.sig_delete_sample_done.emit(False, f"Spell not found: {spell_name}")
                return

            csv_files: list[Path] = []
            for d in dirs:
                csv_files.extend(d.glob("*.csv"))
            csv_files = sorted(csv_files, key=lambda p: p.name)
            if not csv_files:
                self.sig_delete_sample_done.emit(False, f"No samples found for {spell_name}")
                return

            latest_file = csv_files[-1]
            latest_file.unlink(missing_ok=False)

            counts = self._scan_database()
            self.sig_db_refreshed.emit(counts)
            self.sig_delete_sample_done.emit(
                True,
                f"Deleted latest sample: {latest_file.parent.name}/{latest_file.name}",
            )
        except Exception as exc:
            msg = f"Delete latest sample failed: {type(exc).__name__}: {exc}"
            log.exception("DataIOWorker._do_delete_latest_sample")
            self.sig_delete_sample_done.emit(False, msg)

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
        root = Path(self._dataset_dir)
        if not root.exists():
            return counts
        class_map = discover_class_directories(root)
        for name, paths in class_map.items():
            total = 0
            for p in paths:
                total += len(list(p.glob("*.csv")))
            counts[name] = total
        return counts

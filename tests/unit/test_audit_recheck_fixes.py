"""Regression checks for crop persistence, dataset routing and serial handoff."""
import time
from types import SimpleNamespace

from PyQt6.QtCore import QThread, QTimer


def test_crop_failure_retry_and_dataset_snapshot(qapp, tmp_path, monkeypatch):
    from logic.data_io_worker import DataIOWorker
    from logic.handler import Handler

    root = tmp_path / "original"
    raw = root / "raw.csv"
    root.mkdir()
    (root / "spells").mkdir()
    raw.write_text("original sample", encoding="utf-8")
    worker = DataIOWorker(str(root))
    messages = []
    handler = SimpleNamespace(
        _pending_save_context="", _pending_save_spell="", _recording_raw_file=str(raw),
        data_io_worker=worker,
        ui_record=SimpleNamespace(show_recording_error=messages.append, set_save_status=messages.append),
        on_spell_selected=lambda _: None, _run_consistency_analysis=lambda _: None,
    )
    handler._on_io_save_done = lambda ok, msg: Handler._on_io_save_done(handler, ok, msg)
    worker.sig_save_done.connect(handler._on_io_save_done)
    while not worker._job_queue.full():
        worker._job_queue.put_nowait(("refresh",))
    Handler.on_data_cropped(handler, [[1] * 6], "LUMOS")
    assert raw.read_text() == "original sample"
    assert not handler._pending_save_context and messages
    while not worker._job_queue.empty():
        worker._job_queue.get_nowait()

    Handler.on_data_cropped(handler, [[1] * 6], "LUMOS")
    Handler.on_data_cropped(handler, [[2] * 6], "OTHER")
    assert worker._job_queue.qsize() == 1
    assert handler._pending_save_spell == "LUMOS"
    job = worker._job_queue.get_nowait()
    with monkeypatch.context() as patch:
        def fail_replace(*args):
            raise OSError("disk unavailable")
        patch.setattr("logic.data_io_worker.os.replace", fail_replace)
        worker._do_save(*job[1:])
    assert raw.exists() and not handler._pending_save_context
    assert not list(root.rglob("*.tmp"))

    Handler.on_data_cropped(handler, [[3] * 6], "LUMOS")
    job = worker._job_queue.get_nowait()
    worker.dataset_dir = str(tmp_path / "new-dataset")
    worker._do_save(*job[1:])
    assert not raw.exists()
    assert handler._recording_raw_file is None
    assert len(list((root / "spells" / "LUMOS").glob("*.csv"))) == 1
    assert not (tmp_path / "new-dataset").exists()


def test_lab_uses_custom_dataset_and_replaces_after_worker_stops(qapp, tmp_path, monkeypatch):
    from logic.data_store import DataStore
    from logic.udp_worker import UdpWorker
    from ui.main_window import MainWindow
    from ml_lab.ui.tabs.tab_serial_monitor import TabSerialMonitor

    monkeypatch.setattr(UdpWorker, "start", lambda self: None)
    monkeypatch.setattr(MainWindow, "_preload_one", lambda *args: None)
    monkeypatch.setattr(MainWindow, "_check_first_run_guide", lambda *args: None)
    monkeypatch.setattr(TabSerialMonitor, "refresh_ports", lambda self: None)
    store = DataStore(dataset_dir=str(tmp_path / "first"))
    main = MainWindow(store)
    main._open_ml_lab()
    old = main._ml_lab_window
    assert old.spell_dataset_dir == (tmp_path / "first").resolve()

    class Worker(QThread):
        def run(self):
            self.msleep(150)

    worker = Worker()
    old.tab_model._current_worker = worker
    worker.start()
    try:
        store.dataset_dir = str(tmp_path / "second")
        main._open_ml_lab()
        assert main._ml_lab_window is old
        deadline = time.monotonic() + 3
        while main._ml_lab_window is old and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        lab = main._ml_lab_window
        assert lab is not old
        assert lab.spell_dataset_dir == (tmp_path / "second").resolve()
        assert lab.tab_model.dataset_dir == lab.spell_dataset_dir
        assert lab.tab_data.dataset_dir == lab.spell_dataset_dir
    finally:
        worker.wait()
        main.close()
        qapp.processEvents()


def test_stop_drains_accepted_saves(tmp_path):
    from logic.data_io_worker import DataIOWorker

    worker = DataIOWorker(str(tmp_path))
    assert worker.enqueue_save("LUMOS", [[1] * 6])
    assert worker.enqueue_save("ACCIO", [[2] * 6])
    worker.stop()
    worker.run()
    assert len(list(tmp_path.rglob("*.csv"))) == 2


def test_serial_disconnect_retains_worker_and_port_without_blocking(qapp, monkeypatch):
    from ml_lab.ui.tabs.tab_serial_monitor import TabSerialMonitor
    from ml_lab.core.serial_coordinator import acquire, owner_of, release, unregister_owner, ML_LAB_SERIAL

    monkeypatch.setattr(TabSerialMonitor, "refresh_ports", lambda self: None)
    tab = TabSerialMonitor()

    class Worker(QThread):
        def run(self):
            self.msleep(250)

        def stop(self):
            self.requestInterruption()

    worker = Worker()
    tab._worker = worker
    tab._claimed_port = "AUDIT_PORT"
    worker.finished.connect(tab._finish_disconnect)
    assert acquire(ML_LAB_SERIAL, "AUDIT_PORT")
    worker.start()
    ticks = []
    QTimer.singleShot(10, lambda: ticks.append(worker.isRunning()))
    try:
        start = time.monotonic()
        tab.disconnect_serial()
        assert time.monotonic() - start < 0.1
        assert tab._worker is worker and not tab.btn_connect.isEnabled()
        assert not acquire("audit_next", "AUDIT_PORT")
        assert owner_of("AUDIT_PORT") == ML_LAB_SERIAL
        deadline = time.monotonic() + 2
        while tab._worker is not None and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert ticks == [True]
        assert tab._worker is None and tab.btn_connect.isEnabled()
        assert acquire("audit_next", "AUDIT_PORT")
    finally:
        worker.wait()
        tab.close()
        release("audit_next")
        unregister_owner(ML_LAB_SERIAL)

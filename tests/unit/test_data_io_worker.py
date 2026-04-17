import logging

from logic.data_io_worker import DataIOWorker


def test_data_io_worker_queue_is_bounded(tmp_path) -> None:
    worker = DataIOWorker(dataset_dir=str(tmp_path / "dataset"))
    assert worker._job_queue.maxsize == 50


def test_enqueue_save_drops_when_queue_full(tmp_path, caplog) -> None:
    worker = DataIOWorker(dataset_dir=str(tmp_path / "dataset"))
    caplog.set_level(logging.WARNING)
    warnings: list[str] = []
    worker.sig_queue_warning.connect(warnings.append)

    for _ in range(worker._job_queue.maxsize):
        worker._job_queue.put_nowait(("refresh",))

    worker.enqueue_save("ACCIO", [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]])

    assert worker._job_queue.qsize() == worker._job_queue.maxsize
    assert "save job dropped" in caplog.text
    assert warnings
    assert "save job dropped" in warnings[-1]


def test_enqueue_warns_when_queue_depth_is_high(tmp_path, caplog) -> None:
    worker = DataIOWorker(dataset_dir=str(tmp_path / "dataset"))
    caplog.set_level(logging.WARNING)

    for _ in range(40):
        worker._job_queue.put_nowait(("refresh",))

    worker.enqueue_refresh()

    assert "queue depth high" in caplog.text

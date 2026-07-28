"""Verify FlashWorker supports pre-flight cancellation."""
from logic.flash_worker import FlashWorker

def test_flash_worker_cancel_requested_flag():
    worker = FlashWorker()
    assert hasattr(worker, '_cancel_requested')
    worker.stop()
    assert worker._cancel_requested is True

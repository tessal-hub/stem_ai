"""Verify the app can import and initialize without tensorflow installed."""
import importlib
import sys

def test_core_modules_import_without_tensorflow(monkeypatch):
    """Core modules must not fail if tensorflow is absent."""
    # Block tensorflow from importing
    monkeypatch.setitem(sys.modules, 'tensorflow', None)
    
    # These must succeed without tensorflow
    for mod_name in [
        'config', 'constants',
        'logic.data_store', 'logic.serial_worker',
        'logic.udp_worker', 'logic.frame_protocol',
        'logic.recorder', 'logic.data_io_worker',
        'logic.feature_worker', 'logic.flash_worker',
        'logic.model_uploader', 'logic.dataset_layout',
        'logic.prototypical_recognizer',
    ]:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"{mod_name} failed to import"

"""Verify the app can import and initialize without tensorflow installed."""
import importlib
import sys
from unittest.mock import patch

def test_core_modules_import_without_tensorflow():
    """Core modules must not fail if tensorflow is absent."""
    with patch.dict(sys.modules, {'tensorflow': None}):
        for mod_name in [
            'config', 'constants',
            'logic.data_store', 'logic.serial_worker',
            'logic.udp_worker', 'logic.frame_protocol',
            'logic.recorder', 'logic.data_io_worker',
            'logic.feature_worker', 'logic.flash_worker',
            'logic.model_uploader', 'logic.dataset_layout',
            'logic.prototypical_recognizer',
        ]:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"{mod_name} failed to import"


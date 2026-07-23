"""Verify encoder loading doesn't block the main thread."""
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import importlib

def test_encoder_pipeline_defers_tf_import():
    """encoder_pipeline module must not import tensorflow at module level."""
    for key in list(sys.modules.keys()):
        if 'logic.tensorflow.encoder_pipeline' in key:
            del sys.modules[key]
    
    with patch.dict(sys.modules, {'tensorflow': None}):
        try:
            importlib.import_module('logic.tensorflow.encoder_pipeline')
            imported_ok = True
        except (ImportError, AttributeError):
            imported_ok = False
    
    assert imported_ok, "encoder_pipeline imports tensorflow at module level"

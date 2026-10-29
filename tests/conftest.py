import os

import pytest
from PyQt6.QtWidgets import QApplication


# Ensure Qt widgets can initialize in headless CI and local terminal runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_APP = QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return _APP

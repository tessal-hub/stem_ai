# -*- coding: utf-8 -*-
import os
import sys
import time
import traceback

sys.path.insert(0, ".")
os.environ["QT_QPA_PLATFORM"] = "windows"

import warnings

warnings.filterwarnings("ignore")

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QTabWidget  # noqa: E402

app = QApplication(sys.argv)

from ml_lab.ui.window_ml_lab import MlLabWindow  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_shots")
win = MlLabWindow(spell_dataset_dir="dataset/spells")
win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
win.resize(1024, 700)
win.show()


def slot(fn):
    def safe(*a, **kw):
        try:
            fn(*a, **kw)
        except Exception:
            traceback.print_exc()
            app.quit()
    return safe


@slot
def phase() -> None:
    deadline = time.time() + 30
    while time.time() < deadline and not win.tab_data._analysis_done:
        app.processEvents()
        time.sleep(0.02)

    win.tabs.setCurrentIndex(1)
    win.tab_model.start_training()
    QTimer.singleShot(400, poll)


@slot
def poll() -> None:
    if win.tab_model._last_result is None:
        QTimer.singleShot(400, poll)
        return
    print("trained", flush=True)

    par = win.tab_model.misclass_widget.parent()
    tabs = None
    while par is not None:
        if isinstance(par, QTabWidget):
            tabs = par
            break
        par = par.parent()

    for i in range(tabs.count()):
        if tabs.tabText(i).startswith("Lớp nào"):
            print("switching to subtab", i, flush=True)
            tabs.setCurrentIndex(i)
            print("switched", flush=True)
            break

    def step_list() -> None:
        lw = win.tab_model.misclass_widget.list_errors
        print("errors:", lw.count(), flush=True)
        if lw.count() > 0:
            lw.setCurrentRow(0)
            print("row 0 selected", flush=True)

        def step_grab() -> None:
            app.processEvents()
            print("grabbing", flush=True)
            win.grab().save(os.path.join(OUT, "adapt_inspector.png"))
            print("saved adapt_inspector", flush=True)
            win.close()
            app.quit()

        QTimer.singleShot(300, step_grab)

    QTimer.singleShot(300, step_list)


QTimer.singleShot(500, phase)
sys.exit(app.exec())

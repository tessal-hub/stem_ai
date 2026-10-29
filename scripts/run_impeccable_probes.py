"""Impeccable Audit Runner for 2026-10-29.
Performs full automated probing, widget tree inspection, and report generation.
"""
from pathlib import Path
import json
import os
import sys
import time
from types import SimpleNamespace
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".impeccable" / "audit" / "2026-10-29"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
runtime = OUT / f"runtime_{time.time_ns()}"
for name, subdir in (("APP_DATA_DIR", "app_data"), ("USER_DATA_DIR", "user_data"),
                     ("DATASET_DIR", "dataset"), ("SPELL_DIR", "dataset/spells"),
                     ("PRIMITIVE_DIR", "dataset/primitives"), ("SOUNDS_USER_DIR", "sounds")):
    path = runtime / subdir
    path.mkdir(parents=True, exist_ok=True)
    setattr(config, name, path)
config.ensure_data_dir = lambda: config.APP_DATA_DIR

from PyQt6.QtCore import QSettings, QPoint, QTimer, QThread
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QAbstractButton, QAbstractSpinBox,
    QComboBox, QLineEdit, QScrollArea
)
from logic.data_store import DataStore, SettingsStore
from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from logic.udp_worker import UdpWorker
from ml_lab.core.experiment_store import ExperimentStore
from ml_lab.core.spell_selection_store import SpellSelectionStore

def settings_init(self):
    self._settings = QSettings(str(runtime / "settings.ini"), QSettings.Format.IniFormat)
    self._settings.clear()
SettingsStore.__init__ = settings_init

for cls in (ExperimentStore, SpellSelectionStore):
    original = cls.__init__
    def isolated_init(self, root_dir=None, _original=original):
        _original(self, root_dir or runtime / "lab")
    cls.__init__ = isolated_init
UdpWorker.start = lambda self: None

from theme import apply_modern_theme
from ui.main_window import MainWindow
from ml_lab.ui.window_ml_lab import MlLabWindow

MainWindow._preload_one = lambda *args: None
MainWindow._check_first_run_guide = lambda *args: None

app = QApplication.instance() or QApplication([])
for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "segoeuii.ttf", "consola.ttf", "seguiemj.ttf"):
    font_path = Path("C:/Windows/Fonts") / filename
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont("Segoe UI", 10))
locale_manager.current_language = "vi"
apply_modern_theme(app, "light")

def settle(seconds=0.08):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)

main_records = []
lab_records = []

def capture_widget_info(window, records_list, name, size):
    window.resize(*size)
    window.show()
    settle()
    window.grab().save(str(OUT / f"{name}.png"))
    entry = {"name": name, "requested": size, "actual": [window.width(), window.height()], "fields": [], "clipped_labels": []}
    labels = window.findChildren(QLabel)
    for widget in window.findChildren(QWidget):
        if not widget.isVisible() or not isinstance(widget, (QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit)):
            continue
        if isinstance(widget, QLineEdit) and isinstance(widget.parentWidget(), (QAbstractSpinBox, QComboBox)):
            continue
        point = widget.mapTo(window, QPoint(0, 0))
        entry["fields"].append({
            "type": type(widget).__name__,
            "text": widget.text() if hasattr(widget, "text") else "",
            "accessible": widget.accessibleName(),
            "tooltip": widget.toolTip(),
            "buddies": [x.text() for x in labels if x.buddy() is widget],
            "geometry": [point.x(), point.y(), widget.width(), widget.height()],
            "focus": widget.focusPolicy().name
        })
    for label in labels:
        if label.isVisible() and label.text() and not label.wordWrap() and "<" not in label.text() and label.fontMetrics().horizontalAdvance(label.text()) > label.contentsRect().width() + 4:
            entry["clipped_labels"].append({"text": label.text(), "width": label.contentsRect().width(), "needed": label.fontMetrics().horizontalAdvance(label.text())})
    records_list.append(entry)

print("--- 1. Probing Main Window ---")
store = DataStore(dataset_dir=str(config.DATASET_DIR))
store.save_settings({"has_seen_beginner_guide": True, "advanced_mode": True, "ui_language": "vi"})
main = MainWindow(store)
main_pages = ["home", "primitive", "record", "wand", "settings"]
for index, name in enumerate(main_pages):
    main._set_page(index)
    capture_widget_info(main, main_records, f"main_{name}_wide", (1366, 900))
    capture_widget_info(main, main_records, f"main_{name}_small", (920, 640))
    if index in (1, 2):
        panel = main.page_primitive_collect if index == 1 else main.page_record
        scrolls = panel.findChildren(QScrollArea)
        if scrolls:
            area = scrolls[0]
            area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
            capture_widget_info(main, main_records, f"main_{name}_small_bottom", (920, 640))
            area.verticalScrollBar().setValue(0)

theme_manager.current_theme = "dark"
main.page_setting.load_settings({"theme": "dark"})
apply_modern_theme(app, "dark")
capture_widget_info(main, main_records, "main_settings_dark", (1366, 900))
main._set_page(0)
capture_widget_info(main, main_records, "main_home_dark", (1366, 900))
main.close()
theme_manager.current_theme = "light"
apply_modern_theme(app, "light")

# Main Probes
from logic.handler import Handler
main_probes = {}
main2 = MainWindow(store)
main2.show()
main2._set_page(2)
page = main2.page_record
if not hasattr(page, "curve_ax"):
    page._setup_plots()
page.is_live = True
store.live_buffer.clear()
for _ in range(500): store.add_live_sample([1.0]*6)
page._render_plots(force=True)
before = page.curve_ax.getData()[1].copy()
for _ in range(500): store.add_live_sample([2.0]*6)
page._render_plots()
after = page.curve_ax.getData()[1].copy()
main_probes['record_plot'] = {
    'buffer_latest': float(store.get_live_buffer_numpy()[-1,0]),
    'plotted_latest': float(after[-1]),
    'unchanged': bool(np.array_equal(before, after))
}
page.combo_spell.addItem('AUDIT_SPELL')
page.combo_spell.setCurrentText('AUDIT_SPELL')
rejections = []
fake_handler = SimpleNamespace(store=store, ui_record=page, ui_wand=SimpleNamespace(append_terminal_text=rejections.append))
page.sig_start_record.connect(lambda spell: Handler.on_record_start(fake_handler, spell))
page.set_recording_state(False)
page._on_btn_start_clicked()
main_probes['rejected_recording'] = {
    'connected': store.get_connection_state()[0],
    'ui_is_live': page.is_live,
    'timer_active': page._recording_timer.isActive(),
    'stop_enabled': page.btn_stop.isEnabled(),
    'handler_message': rejections
}
page._on_btn_stop_clicked()
main_probes['stopped_disconnected_status'] = page.lbl_wand_status.text()
page.is_live = False

class SlowWorker(QThread):
    def run(self): self.msleep(400)
worker = SlowWorker()
worker.start()
fake_h = SimpleNamespace(_encoder_worker=worker)
fake_h.running_workers = lambda: Handler.running_workers(fake_h)
ticks = []
QTimer.singleShot(10, lambda: ticks.append(True))
t = time.perf_counter()
Handler.shutdown(fake_h)
main_probes['main_shutdown'] = {
    'elapsed_ms': round((time.perf_counter()-t)*1000, 1),
    'worker_running': worker.isRunning(),
    'timer_processed': bool(ticks)
}
settle(0.08)
main_probes["main_shutdown"]["timer_during_worker"] = bool(ticks)
worker.wait()
main2.close()

(OUT / "main-probes.json").write_text(json.dumps(main_probes, ensure_ascii=False, indent=2), encoding="utf8")
(OUT / "main-widgets.json").write_text(json.dumps(main_records, ensure_ascii=False, indent=2), encoding="utf8")
print("Main probes complete:", main_probes)

print("--- 2. Probing ML Lab ---")
lab = MlLabWindow(config.SPELL_DIR)
for index in range(lab.tabs.count()):
    lab.tabs.setCurrentIndex(index)
    capture_widget_info(lab, lab_records, f"lab_{index}_wide_empty", (1260, 880))
    capture_widget_info(lab, lab_records, f"lab_{index}_small_empty", (960, 600))

for label, offset in (("LUMOS", 0.0), ("WINGARDIUM_LEVIOSA", 0.4)):
    folder = config.SPELL_DIR / label
    folder.mkdir(parents=True, exist_ok=True)
    for sample in range(3):
        rows = ["timestamp,ax,ay,az,gx,gy,gz"]
        rows += [f"{i/50:.3f},{offset+i/1000},0.5,1.0,0.1,0.2,0.3" for i in range(70)]
        (folder / f"sample_{sample}.csv").write_text("\n".join(rows), encoding="utf-8")
lab.refresh_dataset_info(force_rescan=True)
lab.filter_bar.btn_all.click()
lab.refresh_dataset_info()
settle(0.5)

for index in (0, 1, 2):
    lab.tabs.setCurrentIndex(index)
    capture_widget_info(lab, lab_records, f"lab_{index}_populated", (1260, 880))

lab_probes = {}
lab.tabs.setCurrentIndex(2)
lab.tab_model.chk_beginner.setChecked(False)
capture_widget_info(lab, lab_records, "lab_2_advanced", (1260, 880))

unnamed = []
for index in range(lab.tab_model.combo_algo.count()):
    lab.tab_model.combo_algo.setCurrentIndex(index)
    layout = lab.tab_model.param_container_layout
    for row_index in range(layout.count()):
        item = layout.itemAt(row_index)
        row = item.layout() if item is not None else None
        widget = row.itemAt(1).widget() if row is not None and row.count() > 1 else None
        if isinstance(widget, (QAbstractSpinBox, QComboBox)) and not widget.accessibleName():
            buddies = [label.text() for label in lab.tab_model.box_param.findChildren(QLabel) if label.buddy() is widget]
            if not buddies:
                unnamed.append({"algo": lab.tab_model.combo_algo.currentData(), "type": type(widget).__name__, "tooltip": widget.toolTip()})
lab_probes["unnamed_algorithm_fields"] = unnamed

model = lab.tab_model
model.combo_algo.setCurrentIndex(model.combo_algo.findData("knn"))
model._last_result = SimpleNamespace(algo="knn", algo_name="KNN")
model._set_cta_mode("flash")
model.combo_algo.setCurrentIndex(model.combo_algo.findData("tree"))
actions = []
model._open_flash_dialog = lambda: actions.append("flash_previous_model")
model.start_training = lambda: actions.append("train_current_config")
model._on_primary_cta()
lab_probes["cta_after_algorithm_change"] = {
    "selected_algo": model.combo_algo.currentData(),
    "result_algo": model._last_result.algo,
    "button": model.btn_train.text(),
    "action": actions
}

lab.tabs.setCurrentIndex(7)
capture_widget_info(lab, lab_records, "lab_7_small_verified", (960, 600))
lab_probes["serial_small_heights"] = {
    name: getattr(lab.tab_serial, name).height()
    for name in ("lbl_spell_name", "lbl_conf_text", "lbl_live_model", "chk_live_predict")
}

class SlowAuditWorker(QThread):
    def __init__(self, delay_ms):
        super().__init__()
        self.delay_ms = delay_ms
    def run(self): self.msleep(self.delay_ms)

if lab.tab_data._analysis_worker:
    lab.tab_data._analysis_worker.wait(1000)
data_worker = SlowAuditWorker(300)
model_worker = SlowAuditWorker(600)
lab.tab_data._analysis_worker = data_worker
lab.tab_model._current_worker = model_worker
data_worker.start()
model_worker.start()

timer_fired = []
QTimer.singleShot(20, lambda: timer_fired.append(True))
start = time.perf_counter()
lab.close()
lab_probes["close_ms"] = round((time.perf_counter() - start) * 1000, 1)
settle(0.08)
lab_probes["timer_processed_while_closing"] = bool(timer_fired)
lab_probes["close_deferred"] = lab.isVisible()
lab_probes["model_worker_running_after_close"] = model_worker.isRunning()
settle(0.8)
lab_probes["closed_after_workers_finished"] = not lab.isVisible()
data_worker.wait()
model_worker.wait()

(OUT / "lab-probes.json").write_text(json.dumps(lab_probes, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "lab-widgets.json").write_text(json.dumps(lab_records, ensure_ascii=False, indent=2), encoding="utf-8")
print("Lab probes complete:", lab_probes)

print("--- 3. Probing Extra / Regression Items ---")
from logic.data_io_worker import DataIOWorker
io = DataIOWorker(dataset_dir=str(runtime/'queue-dataset'))
while not io._job_queue.full():
    io._job_queue.put_nowait(('noop',))
raw = runtime / 'raw.csv'
raw.write_text('ax,ay,az,gx,gy,gz\n1,2,3,4,5,6', encoding='utf8')
warnings = []
io.sig_queue_warning.connect(warnings.append)
fake_crop = SimpleNamespace(
    _recording_raw_file=str(raw),
    data_io_worker=io,
    ui_record=SimpleNamespace(show_recording_error=lambda m: None, set_save_status=lambda m: None),
    _pending_save_context="",
    _pending_save_spell="",
    _on_io_save_done=lambda ok, msg: None
)
Handler.on_data_cropped(fake_crop, [[1,2,3,4,5,6]], 'AUDIT')
extra = {
    'crop_full_queue': {
        'raw_exists': raw.exists(),
        'queue_full': io._job_queue.full()
    }
}

import ml_lab.ui.window_ml_lab as lm
original_lab_cls = lm.MlLabWindow
paths = []
def fake_lab_cls(spell_dataset_dir):
    paths.append(spell_dataset_dir)
    return SimpleNamespace(show=lambda: None, raise_=lambda: None, activateWindow=lambda: None, spell_dataset_dir=Path(spell_dataset_dir), setWindowTitle=lambda t: None)
lm.MlLabWindow = fake_lab_cls
custom = str(runtime / 'custom-dataset')
try:
    fake_main = SimpleNamespace(_ml_lab_window=None, data_store=SimpleNamespace(dataset_dir=custom), setWindowTitle=lambda t: None)
    MainWindow._open_ml_lab(fake_main)
finally:
    lm.MlLabWindow = original_lab_cls
extra['dataset_routing'] = {'configured': custom, 'opened': paths}

from ml_lab.ui.tabs.tab_serial_monitor import TabSerialMonitor
serial_tab = TabSerialMonitor()
class SlowSerial(QThread):
    def stop(self): self.requestInterruption()
    def run(self): self.msleep(800)
w = SlowSerial()
serial_tab._worker = w
w.start()
ticks = []
QTimer.singleShot(10, lambda: ticks.append(True))
start = time.perf_counter()
serial_tab.disconnect_serial()
extra['disconnect_serial'] = {
    'elapsed_ms': round((time.perf_counter()-start)*1000, 1),
    'worker_running': w.isRunning(),
    'worker_retained': serial_tab._worker is w,
    'timer_processed': bool(ticks)
}
w.wait()
if serial_tab._port_scan_worker:
    serial_tab._port_scan_worker.wait()
serial_tab.close()

(OUT / "extra-probes.json").write_text(json.dumps(extra, ensure_ascii=False, indent=2), encoding='utf8')
print("Extra probes complete:", extra)
print("ALL AUDIT PROBES COMPLETE!")

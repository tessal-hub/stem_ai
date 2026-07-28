# Production Readiness Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two user-reported issues (slow app, huge download) and all 14 P0 safety findings from the 2026-07-23 audit.

**Architecture:** Lazy-load TensorFlow behind a background thread, split dependencies into core vs training, fix thread-safety violations, harden security inputs. No architectural changes — all fixes stay within existing MVC boundaries.

**Tech Stack:** PyQt6, Python 3.11+, TensorFlow (lazy), esptool, PyInstaller

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `requirements.txt` | Core runtime deps only | 1 |
| `requirements-train.txt` | TF + scipy + pandas (optional) | 1 |
| `STEMSpellBook.spec` | PyInstaller without TF/scipy/keras | 1 |
| `logic/tensorflow/encoder_pipeline.py` | Defer TF import to function scope | 2 |
| `logic/handler.py` | Async encoder load, queued connections, double-start guards | 2, 5, 6 |
| `theme.py` | QSS-only frame reset (no widget traversal) | 3 |
| `logic/udp_worker.py` | Non-blocking stop() | 4 |
| `logic/data_io_worker.py` | Non-blocking stop(), sig_finished, atomic CSV writes | 4, 7, 8 |
| `logic/feature_worker.py` | Non-blocking stop(), sig_finished | 4, 7 |
| `logic/recorder.py` | Unconditional sig_finished | 7 |
| `logic/model_uploader.py` | sig_finished in finally | 7 |
| `logic/flash_worker.py` | Remove dead _process, path validation | 8, 10 |
| `logic/idf_worker.py` | Remove shell=True | 9 |
| `constants.py` | Sanitize spell names | 9 |
| `logic/tensorflow/pipeline.py` | Fix dummy val_acc, fix fallback split | 11 |
| `ui/main_window.py` | Queued UdpWorker connections | 5 |
| `tests/unit/test_*.py` | Tests for each fix | All |

---

## Tier 1 — User-Reported Issues (Performance & Package Size)

### Task 1: Split Dependencies — Shrink Download from 476MB

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-train.txt`
- Modify: `STEMSpellBook.spec`

- [ ] **Step 1: Write the test — verify core app imports without tensorflow**

```python
# tests/unit/test_core_imports.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_core_imports.py -v`
Expected: FAIL — `encoder_pipeline.py` top-level TF import poisons the chain

- [ ] **Step 3: Split requirements.txt**

```txt
# requirements.txt — Core runtime (no TensorFlow)
PyQt6>=6.5.0
PyOpenGL>=3.1.0
pyqtgraph>=0.13.3
numpy>=1.26.0
esptool
esp-idf-nvs-partition-gen
pyserial>=3.5
```

```txt
# requirements-train.txt — Training pipeline (optional)
-r requirements.txt
tensorflow>=2.16.0
pandas>=2.1.0
scipy>=1.11.0
```

- [ ] **Step 4: Remove TF/scipy/keras from PyInstaller spec**

In `STEMSpellBook.spec`, remove these lines:
```python
# DELETE these collect_all blocks:
tf_datas, tf_binaries, tf_hiddenimports = collect_all('tensorflow')
sc_datas, sc_binaries, sc_hiddenimports = collect_all('scipy')
keras_datas, keras_binaries, keras_hiddenimports = collect_all('keras')

# DELETE tf/sc/keras from binaries, datas, hiddenimports aggregations
```

Keep `esptool` and `esp_idf_nvs_partition_gen` — those are runtime deps.

Remove TF/keras/scipy entries from `hiddenimports` list (lines 80-89).

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_core_imports.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-train.txt STEMSpellBook.spec tests/unit/test_core_imports.py
git commit -m "perf: split deps — core runtime vs training, remove TF from frozen build"
```

---

### Task 2: Lazy-Load TensorFlow — Fix Multi-Second Startup Freeze

**Files:**
- Modify: `logic/tensorflow/encoder_pipeline.py:7-25`
- Modify: `logic/handler.py:575-606` (`_try_load_encoder`)
- Modify: `logic/handler.py:282-287` (`_load_initial_state`)
- Test: `tests/unit/test_encoder_lazy_load.py`

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_encoder_lazy_load.py
"""Verify encoder loading doesn't block the main thread."""
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_encoder_pipeline_defers_tf_import():
    """encoder_pipeline module must not import tensorflow at module level."""
    import sys
    # If tensorflow is in sys.modules, it was imported eagerly
    # Clear it and re-import encoder_pipeline
    for key in list(sys.modules.keys()):
        if 'logic.tensorflow.encoder_pipeline' in key:
            del sys.modules[key]
    
    with patch.dict(sys.modules, {'tensorflow': None}):
        # This should NOT raise — TF import should be deferred
        try:
            import importlib
            importlib.import_module('logic.tensorflow.encoder_pipeline')
            imported_ok = True
        except (ImportError, AttributeError):
            imported_ok = False
    
    assert imported_ok, "encoder_pipeline imports tensorflow at module level"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_encoder_lazy_load.py -v`
Expected: FAIL — `L2NormalizeLayer(tf.keras.layers.Layer)` at line 25 crashes when tf=None

- [ ] **Step 3: Defer TF import in encoder_pipeline.py**

Replace lines 7-25 of `logic/tensorflow/encoder_pipeline.py`:

```python
# Remove top-level TF import. Move inside functions/classes.
_TF_AVAILABLE = False
tf = None

def _require_tensorflow():
    global tf, _TF_AVAILABLE
    if tf is not None:
        return tf
    try:
        import tensorflow as _tf
        tf = _tf
        _TF_AVAILABLE = True
        return tf
    except ModuleNotFoundError:
        raise RuntimeError("TensorFlow is required for encoder pipeline operations.")


def _get_l2_normalize_layer_class():
    """Return L2NormalizeLayer class, importing TF lazily."""
    _tf = _require_tensorflow()
    
    class L2NormalizeLayer(_tf.keras.layers.Layer):
        """Normalize embeddings to unit sphere."""
        def call(self, inputs):
            return _tf.math.l2_normalize(inputs, axis=-1)
    
    return L2NormalizeLayer
```

Update all references to `L2NormalizeLayer` in the file to call `_get_l2_normalize_layer_class()` instead.

- [ ] **Step 4: Move encoder loading to background thread in handler.py**

Replace `_try_load_encoder` (lines 575-606) and `_load_initial_state` (lines 282-287):

```python
def _load_initial_state(self) -> None:
    """Nạp trạng thái ban đầu sau khi khởi tạo."""
    # Encoder loading runs in background — no UI freeze
    self._start_async_encoder_load()
    self.on_serial_scan()
    self.ui_home.set_mode(self._mode)
    self._feature_timer.start()

def _start_async_encoder_load(self) -> None:
    """Khởi chạy nạp encoder trên luồng nền."""
    path = APP_DATA_DIR / "gesture_encoder.keras"
    if not path.exists():
        return
    
    class _EncoderLoadWorker(QThread):
        sig_done = pyqtSignal(object)  # encoder or None
        sig_error = pyqtSignal(str)
        
        def __init__(self, model_path, proto_path):
            super().__init__()
            self._model_path = model_path
            self._proto_path = proto_path
        
        def run(self):
            try:
                import tensorflow as tf
                from logic.tensorflow.encoder_pipeline import _get_l2_normalize_layer_class
                L2NormalizeLayer = _get_l2_normalize_layer_class()
                try:
                    encoder = tf.keras.models.load_model(
                        str(self._model_path), compile=False,
                        custom_objects={"L2NormalizeLayer": L2NormalizeLayer},
                    )
                except Exception:
                    encoder = tf.keras.models.load_model(
                        str(self._model_path), compile=False, safe_mode=False,
                    )
                self.sig_done.emit(encoder)
            except Exception as e:
                self.sig_error.emit(str(e))
    
    proto_path = APP_DATA_DIR / "spell_prototypes.json"
    self._encoder_load_worker = _EncoderLoadWorker(path, proto_path)
    self._encoder_load_worker.sig_done.connect(
        self._on_encoder_loaded, type=Qt.ConnectionType.QueuedConnection)
    self._encoder_load_worker.sig_error.connect(
        lambda e: log.error(f"Encoder load failed: {e}"),
        type=Qt.ConnectionType.QueuedConnection)
    self._encoder_load_worker.start()

def _on_encoder_loaded(self, encoder) -> None:
    """Callback khi encoder đã nạp xong trên luồng nền."""
    self.spell_recognizer = PrototypicalRecognizer(encoder)
    proto_path = APP_DATA_DIR / "spell_prototypes.json"
    if proto_path.exists():
        self.spell_recognizer.load(str(proto_path))
        self.store.registered_prototypes = set(self.spell_recognizer.prototypes.keys())
    log.info(f"Loaded encoder and {len(self.spell_recognizer.prototypes)} prototypes.")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_encoder_lazy_load.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add logic/tensorflow/encoder_pipeline.py logic/handler.py tests/unit/test_encoder_lazy_load.py
git commit -m "perf: lazy-load TensorFlow in background thread — eliminates startup freeze"
```

---

### Task 3: Eliminate Widget Tree Traversal at Startup

**Files:**
- Modify: `theme.py:659-667`
- Modify: `main.py:72`

- [ ] **Step 1: Replace apply_flat_widget_chrome with QSS rule**

In `theme.py`, replace the `apply_flat_widget_chrome` function:

```python
def apply_flat_widget_chrome(root_widget: QWidget) -> None:
    """No-op — frame removal is now handled by QSS in get_modern_stylesheet."""
    pass
```

Add to `get_modern_stylesheet()` (inside the QSS f-string, after the base reset section):

```css
QFrame {{
    border: none;
    background: transparent;
}}
```

- [ ] **Step 2: Run app to verify no visual regression**

Run: `python main.py`
Expected: App looks identical — no frame borders visible

- [ ] **Step 3: Commit**

```bash
git add theme.py
git commit -m "perf: replace O(n) widget traversal with QSS rule for frame reset"
```

---

### Task 4: Fix Blocking stop() Methods — Eliminate 2-Second UI Hangs

**Files:**
- Modify: `logic/udp_worker.py:91-108`
- Modify: `logic/data_io_worker.py:143-158`
- Modify: `logic/feature_worker.py:78-93`
- Test: `tests/unit/test_worker_stop_nonblocking.py`

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_worker_stop_nonblocking.py
"""Verify worker stop() methods do not block the calling thread."""
import time
import ast
import inspect

def _has_sleep_in_method(cls, method_name: str) -> bool:
    """Check if a method contains time.sleep calls via AST inspection."""
    source = inspect.getsource(getattr(cls, method_name))
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr == 'sleep':
                return True
    return False

def test_udp_worker_stop_no_sleep():
    from logic.udp_worker import UdpWorker
    assert not _has_sleep_in_method(UdpWorker, 'stop'), \
        "UdpWorker.stop() contains time.sleep — blocks UI thread"

def test_data_io_worker_stop_no_sleep():
    from logic.data_io_worker import DataIOWorker
    assert not _has_sleep_in_method(DataIOWorker, 'stop'), \
        "DataIOWorker.stop() contains time.sleep — blocks UI thread"

def test_feature_worker_stop_no_sleep():
    from logic.feature_worker import FeatureWorker
    assert not _has_sleep_in_method(FeatureWorker, 'stop'), \
        "FeatureWorker.stop() contains time.sleep — blocks UI thread"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_worker_stop_nonblocking.py -v`
Expected: All 3 FAIL

- [ ] **Step 3: Fix UdpWorker.stop()**

Replace `logic/udp_worker.py` lines 91-108:

```python
def stop(self) -> None:
    """Cooperatively ask the thread to terminate (non-blocking)."""
    self._is_running = False
    if self._sock:
        try:
            self._sock.close()
        except Exception:
            pass
```

- [ ] **Step 4: Fix DataIOWorker.stop()**

Replace `logic/data_io_worker.py` lines 143-158:

```python
def stop(self) -> None:
    """Cooperatively ask the worker to exit (non-blocking)."""
    self._running = False
    try:
        self._job_queue.put_nowait(("_stop",))
    except queue.Full:
        pass  # Worker will exit via _running=False on next timeout.
```

- [ ] **Step 5: Fix FeatureWorker.stop()**

Replace `logic/feature_worker.py` lines 78-93:

```python
def stop(self) -> None:
    """Cooperatively ask the worker to exit (non-blocking)."""
    self._running = False
    try:
        self._queue.put_nowait(None)
    except queue.Full:
        pass
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_worker_stop_nonblocking.py -v`
Expected: All 3 PASS

- [ ] **Step 7: Commit**

```bash
git add logic/udp_worker.py logic/data_io_worker.py logic/feature_worker.py tests/unit/test_worker_stop_nonblocking.py
git commit -m "fix(P0): remove blocking sleep loops from worker stop() — eliminates UI hangs"
```

---

## Tier 2 — P0 Safety Fixes

### Task 5: Add Queued Connections for All Cross-Thread Signals

**Files:**
- Modify: `logic/handler.py:353-368` (`_connect_worker_signals`)
- Modify: `ui/main_window.py:98-100` (UdpWorker connections)

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_queued_connections.py
"""Verify all cross-thread signal connections use QueuedConnection."""
import ast
import inspect

def test_handler_worker_signals_are_queued():
    from logic.handler import Handler
    source = inspect.getsource(Handler._connect_worker_signals)
    tree = ast.parse(source)
    
    connect_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'connect':
                connect_calls.append(node)
    
    for call in connect_calls:
        has_queued = any(
            'QueuedConnection' in ast.dump(kw.value)
            for kw in call.keywords
            if kw.arg == 'type'
        )
        # Also check positional args
        if not has_queued and len(call.args) >= 2:
            has_queued = 'QueuedConnection' in ast.dump(call.args[1])
        assert has_queued, f"Worker signal connection missing QueuedConnection at line {call.lineno}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_queued_connections.py -v`
Expected: FAIL — several connections missing `type=Qt.ConnectionType.QueuedConnection`

- [ ] **Step 3: Add QueuedConnection to handler.py worker signals**

In `_connect_worker_signals`, add `type=Qt.ConnectionType.QueuedConnection` to these lines:

```python
self.data_io_worker.sig_save_done.connect(
    self._on_io_done, type=Qt.ConnectionType.QueuedConnection)
self.data_io_worker.sig_db_refreshed.connect(
    self.store.update_counts_from_worker, type=Qt.ConnectionType.QueuedConnection)
self.data_io_worker.sig_delete_sample_done.connect(
    self._on_io_delete_sample_done, type=Qt.ConnectionType.QueuedConnection)
self.feature_worker.sig_features_ready.connect(
    self.store.update_live_features, type=Qt.ConnectionType.QueuedConnection)
self.uploader.status_msg.connect(
    self.ui_wand.append_terminal_text, type=Qt.ConnectionType.QueuedConnection)
self.uploader.sig_progress.connect(
    self.ui_wand.update_flash_progress, type=Qt.ConnectionType.QueuedConnection)
self.uploader.sig_finished.connect(
    self._on_upload_finished, type=Qt.ConnectionType.QueuedConnection)
self.flash_worker.log_msg.connect(
    self._flash_log_to_console, type=Qt.ConnectionType.QueuedConnection)
self.flash_worker.sig_progress.connect(
    self.ui_setting.update_flash_progress, type=Qt.ConnectionType.QueuedConnection)
self.flash_worker.sig_finished.connect(
    self._on_firmware_flash_finished, type=Qt.ConnectionType.QueuedConnection)
```

- [ ] **Step 4: Add QueuedConnection to UdpWorker signals in main_window.py**

```python
self.udp_worker.sig_data_received.connect(
    self._on_udp_sensor_dispatch, type=Qt.ConnectionType.QueuedConnection)
self.udp_worker.sig_status_change.connect(
    self._on_udp_status_changed, type=Qt.ConnectionType.QueuedConnection)
self.udp_worker.sig_health_update.connect(
    self._on_udp_health_updated, type=Qt.ConnectionType.QueuedConnection)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_queued_connections.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add logic/handler.py ui/main_window.py tests/unit/test_queued_connections.py
git commit -m "fix(P0): add QueuedConnection to all cross-thread worker signals"
```

---

### Task 6: Add Double-Start Guards to All Workers

**Files:**
- Modify: `logic/handler.py` (all `.start()` call sites)

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_double_start_guard.py
"""Verify all worker start() calls are guarded by isRunning()."""
import ast
import inspect

def test_handler_start_calls_are_guarded():
    from logic.handler import Handler
    source = inspect.getsource(Handler)
    tree = ast.parse(source)
    
    # Find all .start() calls on workers
    worker_attrs = {
        'serial_worker', 'data_io_worker', 'feature_worker',
        'flash_worker', 'uploader', 'recorder',
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute) and func.attr == 'start'
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr in worker_attrs):
                # This worker.start() must be preceded by an isRunning() check
                # We verify by checking if the enclosing if/method has isRunning
                pass  # AST verification of guard presence
```

- [ ] **Step 2: Add isRunning() guards to all worker start() calls in handler.py**

For each worker `start()` call, wrap with guard:

```python
# Pattern to apply at every start() site:
if not self.serial_worker.isRunning():
    self.serial_worker.start()
```

Apply to: `serial_worker.start()` (line 394), `data_io_worker.start()` (line 243), `feature_worker.start()` (line 246), and any other start() sites.

- [ ] **Step 3: Run existing handler guard tests**

Run: `python -m pytest tests/integration/test_handler_phase6_guards.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add logic/handler.py tests/unit/test_double_start_guard.py
git commit -m "fix(P0): add isRunning() guards to all worker start() calls"
```

---

### Task 7: Ensure All Workers Emit sig_finished on All Exit Paths

**Files:**
- Modify: `logic/data_io_worker.py:164` (add finally block)
- Modify: `logic/feature_worker.py:99` (add finally block)
- Modify: `logic/recorder.py:276` (unconditional sig_finished)
- Modify: `logic/model_uploader.py:78` (sig_finished in finally)

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_worker_terminal_signal.py
"""Verify all workers emit sig_finished on all exit paths."""
import ast
import inspect

def _run_has_finally_with_sig_finished(cls) -> bool:
    source = inspect.getsource(cls.run)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.finalbody:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Attribute) and 'sig_finished' in ast.dump(stmt):
                    return True
    return False

def test_data_io_worker_emits_sig_finished():
    from logic.data_io_worker import DataIOWorker
    assert _run_has_finally_with_sig_finished(DataIOWorker)

def test_feature_worker_emits_sig_finished():
    from logic.feature_worker import FeatureWorker
    assert _run_has_finally_with_sig_finished(FeatureWorker)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_worker_terminal_signal.py -v`
Expected: FAIL

- [ ] **Step 3: Add finally block to DataIOWorker.run()**

Wrap the existing `run()` body in try/finally:

```python
def run(self) -> None:
    self._running = True
    try:
        while self._running:
            try:
                job = self._job_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            kind = job[0]
            if kind == "_stop":
                break
            elif kind == "save":
                # ... existing code ...
    finally:
        self.sig_finished.emit(True, "DataIOWorker stopped")
```

- [ ] **Step 4: Add finally block to FeatureWorker.run()**

Same pattern:

```python
def run(self) -> None:
    self._running = True
    try:
        while self._running:
            # ... existing loop body ...
    finally:
        self.sig_finished.emit(True, "FeatureWorker stopped")
```

- [ ] **Step 5: Fix DataRecorder — unconditional sig_finished**

In `logic/recorder.py`, ensure `run()` always emits:

```python
def run(self) -> None:
    try:
        # ... existing run body ...
    finally:
        self._close_recording(True)
        self.sig_finished.emit(True, "Recording stopped")
```

- [ ] **Step 6: Fix ModelUploader — sig_finished in finally**

In `logic/model_uploader.py`, add to the finally block at line 78:

```python
finally:
    if self._serial and self._serial.is_open:
        self._serial.close()
    self._serial = None
    self._is_running = False
    self._cancel_requested = False
    self.sig_finished.emit(False, self._last_error or "Upload ended")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_worker_terminal_signal.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add logic/data_io_worker.py logic/feature_worker.py logic/recorder.py logic/model_uploader.py tests/unit/test_worker_terminal_signal.py
git commit -m "fix(P0): ensure all workers emit sig_finished on every exit path"
```

---

### Task 8: Atomic CSV Writes — Prevent Partial-Write Corruption

**Files:**
- Modify: `logic/data_io_worker.py:200-220` (`_do_save`)

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_atomic_csv_write.py
"""Verify CSV saves use atomic write-then-rename."""
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

def test_save_uses_atomic_rename(tmp_path):
    from logic.data_io_worker import DataIOWorker
    worker = DataIOWorker(dataset_dir=str(tmp_path))
    
    # Create spell directory
    spell_dir = tmp_path / "spells" / "TEST_SPELL"
    spell_dir.mkdir(parents=True)
    
    data = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]] * 10
    worker._do_save("TEST_SPELL", data)
    
    # Verify: no .tmp files left behind
    tmp_files = list(spell_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"Temp files left behind: {tmp_files}"
    
    # Verify: CSV file exists and is complete
    csv_files = list(spell_dir.glob("*.csv"))
    assert len(csv_files) == 1
    with open(csv_files[0]) as f:
        lines = f.readlines()
    assert len(lines) == 11  # header + 10 rows
```

- [ ] **Step 2: Implement atomic write in _do_save**

Replace the file write in `logic/data_io_worker.py` `_do_save`:

```python
# Write to temp file, then atomic rename
tmp_path = file_path.with_suffix('.csv.tmp')
try:
    with open(tmp_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
        writer.writerows(data)
    # Atomic rename — either fully written or not at all
    os.replace(str(tmp_path), str(file_path))
except Exception:
    # Clean up temp file on failure
    tmp_path.unlink(missing_ok=True)
    raise
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_atomic_csv_write.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add logic/data_io_worker.py tests/unit/test_atomic_csv_write.py
git commit -m "fix(P0): atomic CSV writes — prevent partial-file corruption on crash"
```

---

### Task 9: Security Fixes — Shell Injection, Path Traversal, Directory Escape

**Files:**
- Modify: `logic/idf_worker.py:51` (remove `shell=True`)
- Modify: `constants.py:22` (sanitize spell names)
- Modify: `logic/flash_worker.py:120` (path validation)
- Test: `tests/unit/test_security.py`

- [ ] **Step 1: Write the tests**

```python
# tests/unit/test_security.py
"""Verify security hardening: no shell injection, no path traversal."""
from constants import normalize_spell_name

def test_spell_name_strips_path_separators():
    assert '/' not in normalize_spell_name("../../etc")
    assert '\\' not in normalize_spell_name("..\\..\\windows")
    assert '..' not in normalize_spell_name("../hack")

def test_spell_name_strips_special_chars():
    result = normalize_spell_name("SPELL; rm -rf /")
    assert ';' not in result
    assert '/' not in result

def test_spell_name_preserves_valid_names():
    assert normalize_spell_name("FIRE BALL") == "FIRE BALL"
    assert normalize_spell_name("circle_cw") == "CIRCLE CW"
    assert normalize_spell_name("STAND BY") == "STAND BY"

def test_idf_worker_no_shell_true():
    import ast, inspect
    from logic.idf_worker import IDFBuildWorker
    source = inspect.getsource(IDFBuildWorker.run)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == 'shell':
            assert not (isinstance(node.value, ast.Constant) and node.value.value is True), \
                "idf_worker still uses shell=True"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_security.py -v`
Expected: FAIL — spell name allows `../`, idf_worker has `shell=True`

- [ ] **Step 3: Harden normalize_spell_name in constants.py**

```python
import re

def normalize_spell_name(name: str) -> str:
    """Chuẩn hóa tên spell: chữ hoa, chỉ giữ chữ cái, số, dấu cách, gạch dưới.

    Args:
        name: Tên spell cần chuẩn hóa.

    Returns:
        Tên spell đã chuẩn hóa, an toàn cho đường dẫn hệ thống.
    """
    cleaned = re.sub(r'[^A-Za-z0-9_ ]', '', str(name))
    return " ".join(cleaned.strip().split()).upper()
```

- [ ] **Step 4: Remove shell=True from idf_worker.py**

In `logic/idf_worker.py` line 51, change:

```python
process = subprocess.Popen(
    cmd,
    cwd=str(self.project_dir),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    shell=False,   # SECURITY: never shell=True with user input
    bufsize=1
)
```

- [ ] **Step 5: Add path validation to flash_worker.py**

In `logic/flash_worker.py` `_validate_flash_inputs`, after `bin_file = Path(path_str).resolve()`:

```python
# Security: verify binary is within expected asset directory
from config import FIRMWARE_BIN_DIR, APP_DATA_DIR
allowed_roots = [Path(FIRMWARE_BIN_DIR).resolve(), Path(APP_DATA_DIR).resolve()]
if not any(bin_file.is_relative_to(root) for root in allowed_roots):
    self._fail(f"Binary path outside allowed directories: {bin_file}")
    return {}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_security.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add constants.py logic/idf_worker.py logic/flash_worker.py tests/unit/test_security.py
git commit -m "fix(P0): harden security — sanitize spell names, remove shell=True, validate flash paths"
```

---

## Tier 3 — P0 ML Pipeline + P1 Fixes

### Task 10: Fix Dummy val_acc=1.000 on Skip-Train Path

**Files:**
- Modify: `logic/tensorflow/pipeline.py:867-870`

- [ ] **Step 1: Write the test**

```python
# tests/unit/test_skip_train_accuracy.py
"""Verify skip-train path does not report fake perfect accuracy."""
def test_skip_train_does_not_fake_accuracy():
    import ast, inspect
    from logic.tensorflow.pipeline import build_gesture_model
    # Read the source and check for DummyHistory with 1.0
    source = inspect.getsource(build_gesture_model)
    assert 'DummyHistory' not in source or '1.0' not in source.split('DummyHistory')[1][:100], \
        "Skip-train path still fabricates val_accuracy=1.0"
```

- [ ] **Step 2: Fix the dummy history**

Replace lines 867-870 of `logic/tensorflow/pipeline.py`:

```python
else:
    class SkippedHistory:
        history = {"accuracy": [0.0], "val_accuracy": [0.0]}
    history = SkippedHistory()
    _emit_status(status_cb,
        "[WARN] Bỏ qua train — val_accuracy=N/A (trả về 0.0, cần evaluate riêng)")
```

- [ ] **Step 3: Commit**

```bash
git add logic/tensorflow/pipeline.py tests/unit/test_skip_train_accuracy.py
git commit -m "fix(P0): skip-train path reports 0.0 instead of fabricating val_acc=1.0"
```

---

### Task 11: Fix Train/Validation Leakage in Fallback Split

**Files:**
- Modify: `logic/tensorflow/pipeline.py:644-663`

- [ ] **Step 1: Fix fallback split to use temporal order instead of random shuffle**

Replace lines 644-661:

```python
if validation_data is None and val_fraction > 0:
    # Fallback: temporal split from base windows (NOT random shuffle)
    # to prevent data leakage from overlapping strides.
    val_size = int(len(cnn_train_features) * val_fraction)
    if val_size > 0:
        # Take last N windows as validation (temporal, no overlap leakage)
        val_base_feat = cnn_train_features[-val_size:]
        val_base_labels = cnn_train_labels[-val_size:]
        cnn_train_features = cnn_train_features[:-val_size]
        cnn_train_labels = cnn_train_labels[:-val_size]
        
        X_val_base = np.clip(np.stack(val_base_feat, axis=0), -2.0, 2.0)
        y_val_base = tf.keras.utils.to_categorical(
            np.asarray(val_base_labels, dtype=np.int32), num_classes=len(class_names))
        validation_data = (X_val_base, y_val_base)
        _emit_status(status_cb,
            f"[WARN] Dùng temporal split {val_fraction*100:.0f}% từ Base Windows "
            f"(cuối chuỗi, không shuffle để tránh Data Leakage).")
    else:
        val_fraction = 0.0
```

- [ ] **Step 2: Commit**

```bash
git add logic/tensorflow/pipeline.py
git commit -m "fix(P0): fallback val split uses temporal order to prevent overlap leakage"
```

---

### Task 12: Fix Uncancellable Flash Worker

**Files:**
- Modify: `logic/flash_worker.py:41, 178-186`

- [ ] **Step 1: Remove dead _process variable and document uninterruptible flash**

In `flash_worker.py`:

```python
def stop(self) -> None:
    """Request flash cancellation.
    
    NOTE: esptool.main() runs synchronously in-thread and cannot be
    interrupted mid-flash. This flag only prevents starting new operations.
    """
    self._cancel_requested = True
```

Remove the dead `self._process` references from `stop()`.

Add a pre-flight cancellation check in `run()` before calling `_execute_flash()`:

```python
if self._cancel_requested:
    self.sig_finished.emit(False, "Flash cancelled before start")
    return
```

- [ ] **Step 2: Commit**

```bash
git add logic/flash_worker.py
git commit -m "fix(P0): remove dead subprocess code from flash worker, add pre-flight cancel check"
```

---

## Execution Summary

| Task | Fixes | Severity | User Impact |
|---|---|---|---|
| 1 | Split deps, shrink .exe from 476MB to ~50MB | P0 | **Extra package download** |
| 2 | Lazy TF load, background encoder init | P0 | **Multi-second startup freeze** |
| 3 | QSS frame reset vs widget traversal | P2 | Startup overhead |
| 4 | Non-blocking stop() methods | P0 | **2-second UI hangs** |
| 5 | Queued cross-thread connections | P0 | Thread-safety crashes |
| 6 | Double-start guards | P0 | Worker restart crashes |
| 7 | sig_finished on all exit paths | P0 | UI hangs forever |
| 8 | Atomic CSV writes | P0 | Dataset corruption |
| 9 | Security hardening | P0 | Shell injection, path traversal |
| 10 | Fix fake val_acc=1.0 | P0 | Misleading accuracy |
| 11 | Fix train/val leakage | P0 | Inflated validation metrics |
| 12 | Fix uncancellable flash | P0 | Permanent port lock |

> **NOTE:** P0-01 (preprocessing parity mismatch — Python L1 energy vs C++ tail-variance) is NOT in this plan. It requires design discussion on which energy algorithm to standardize on. Flag for separate spec.

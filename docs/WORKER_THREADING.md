# 🧵 Worker & Threading Architecture

Mọi quy tắc về threading trong project STEM Spell Book.

---

## 1. Nguyên tắc nền tảng

> **Không bao giờ block main thread (Qt event loop).**

Main thread chỉ được phép:
- Xử lý UI events và signal dispatch
- Đọc dữ liệu đã được chuẩn bị sẵn từ DataStore (snapshot)
- Chạy QTimer callbacks nhẹ (< 1ms)

---

## 2. Danh sách workers

| Worker class | Module | Loại | Mục đích |
|---|---|---|---|
| `SerialWorker` | `logic/serial_worker.py` | `QThread` | UART read/write loop |
| `UdpWorker` | `logic/udp_worker.py` | `QThread` | UDP socket listener |
| `DataIOWorker` | `logic/data_io_worker.py` | `QThread` | File I/O (save/delete/export) |
| `FeatureWorker` | `logic/feature_worker.py` | `QThread` | FFT + statistics |
| `FlashWorker` | `logic/flash_worker.py` | `QThread` | esptool firmware flash |
| `ModelUploader` | `logic/model_uploader.py` | `QThread` | .tflite chunked upload |
| `GestureModelBuildWorker` | `logic/tensorflow/pipeline.py` | `QThread` | Keras train + TFLite build |

---

## 3. Anti-freeze pattern cho serial stop

**Tình huống:** Cần stop SerialWorker trước khi flash/upload.

❌ **Cấm:**
```python
serial_worker.stop()
serial_worker.wait()   # BLOCKS main thread → UI freeze
do_flash()
```

✅ **Đúng cách (deferred callback):**
```python
def handle_firmware_flash(self, bin_type):
    if self.serial_worker.isRunning():
        self._pending_flash_bin_type = bin_type
        self.serial_worker.finished.connect(
            self._deferred_start_flash,
            type=Qt.ConnectionType.SingleShotConnection,
        )
        self.serial_worker.stop()
        return   # Return ngay — flash sẽ trigger qua finished signal
    self._do_flash_firmware()

def _deferred_start_flash(self):
    self._do_flash_firmware()
```

Pattern tương tự cho model upload (`_deferred_start_upload`).

---

## 4. Cross-thread signal connections

Mọi signal từ worker thread → UI hoặc Handler **phải** dùng `QueuedConnection`:

```python
# Trong Handler._connect_worker_output_signals():
self._connect_queued(worker.sig_data_received, self._on_data_received)
# Tương đương:
worker.sig_data_received.connect(
    self._on_data_received,
    type=Qt.ConnectionType.QueuedConnection
)
```

Helper method trong Handler:
```python
def _connect_queued(self, signal, slot) -> None:
    signal.connect(slot, type=Qt.ConnectionType.QueuedConnection)

def _connect_many_queued(self, bindings: list[tuple]) -> None:
    for signal, slot in bindings:
        self._connect_queued(signal, slot)
```

> **Lưu ý:** `QueuedConnection` là default khi connect cross-thread tự động.  
> Tuy nhiên, explicit declaration tốt hơn để tránh nhầm lẫn.

---

## 5. DataIOWorker — Job queue pattern

```python
# Enqueue từ main thread (non-blocking)
data_io_worker.enqueue_save(spell_name, data)
data_io_worker.enqueue_delete(spell_name)
data_io_worker.enqueue_export(buf, output_path)
data_io_worker.enqueue_refresh()

# Worker thread xử lý và emit signals:
sig_save_done(bool, str)
sig_delete_done(bool, str)
sig_export_done(bool, str)
sig_db_refreshed(dict)  # spell_counts
```

Khởi động trong Handler init:
```python
self.data_io_worker = DataIOWorker(dataset_dir=...)
self.data_io_worker.start()   # Chạy suốt vòng đời app
```

---

## 6. FeatureWorker — Bounded queue, drop oldest

```python
# Enqueue từ Handler QTimer slot (200ms) — non-blocking
feature_worker.enqueue(snapshot)  # Drops oldest if queue full (maxsize=3)

# Worker thread emit:
sig_features_ready(dict)
```

Bounded queue đảm bảo feature computation không tích luỹ lag khi UI busy.

Khởi động trong Handler init:
```python
self.feature_worker = FeatureWorker()
self.feature_worker.start()   # Chạy suốt vòng đời app
```

---

## 7. SerialWorker — Outbound command queue

```python
# Send command từ main thread:
serial_worker.send_command("CMD:MODE=RECORD")
# Returns True/False, non-blocking (puts to internal queue)

# Worker run() loop:
#   readline() from serial
#   check outbound queue → write to serial
#   emit sig_data_received / sig_prediction_received / sig_raw_line_received
```

Dừng worker:
```python
serial_worker.stop()   # sets _running = False, closes serial
# Worker sẽ exit run() loop tự nhiên và emit sig_finished
```

---

## 8. FlashWorker — Subprocess pattern

```python
flash_worker.set_target(port, bin_path)
flash_worker.start()

# run() trong worker thread:
#   subprocess.Popen(["python", "-m", "esptool", ..., "write_flash", "0x10000", bin_path])
#   Parse stdout cho % progress
#   sig_flash_progress(int, str)
#   sig_flash_finished(bool, str)
```

---

## 9. Port ownership mutex

```python
handler._port_owner: str | None   # "serial" | "flash" | "upload" | None

def _can_use_port(self, requester: str) -> bool:
    return self._port_owner is None or self._port_owner == requester

def _set_port_owner(self, owner: str | None) -> None:
    self._port_owner = owner
```

Workflow:
1. Trước khi flash/upload: gọi `_can_use_port("flash")` hoặc `("upload")`.
2. Nếu serial đang chạy: stop nó, trong callback deferred mới `_set_port_owner`.
3. Sau khi flash/upload xong: `_set_port_owner(None)`.
4. SerialWorker set `_port_owner = "serial"` khi connect, clear khi disconnect.

---

## 10. GestureModelBuildWorker

```python
worker = GestureModelBuildWorker(
    dataset_dir=...,
    output_mode="both",          # "tflite" | "cc" | "both"
    selected_spells=[...],       # empty = dùng tất cả
    window_size=...,
    window_overlap=...,
)
worker.sig_status.connect(...)
worker.sig_progress.connect(...)
worker.sig_finished.connect(...)
worker.start()
```

Fallback khi thiếu TensorFlow:
- Nếu model.tflite đã tồn tại → dùng lại, chỉ generate .cc nếu cần.
- Nếu không có TF và không có model → emit `sig_finished(False, "TensorFlow not available")`.

---

## 11. UdpWorker — secondary data source

Chạy trong `MainWindow`, không phải Handler:

```python
# main_window.py
self.udp_worker = UdpWorker(port=5555)
self.udp_worker.sig_data_received.connect(self._on_udp_data)
self.udp_worker.sig_health_update.connect(self._on_udp_health_update)
self.udp_worker.start()

def closeEvent(self, event):
    self.udp_worker.stop()
    super().closeEvent(event)
```

---

## 12. Threading lifecycle summary

```
App start:
  DataIOWorker.start()          ← lifespan = app lifetime
  FeatureWorker.start()         ← lifespan = app lifetime
  UdpWorker.start()             ← lifespan = app lifetime
  _feature_timer.start(200ms)   ← lifespan = app lifetime

On serial connect:
  SerialWorker.start()          ← lifespan = connection session

On serial disconnect or before flash:
  SerialWorker.stop()           ← non-blocking
  [finished signal] → deferred callback

On flash/upload:
  FlashWorker.start()  OR  ModelUploader.start()  ← lifespan = operation

On train:
  GestureModelBuildWorker.start()                 ← lifespan = training session

App close:
  UdpWorker.stop()
  (SerialWorker.stop() nếu đang chạy)
  DataIOWorker / FeatureWorker: Qt sẽ clean up
```

---

## 13. Debug tips

### Kiểm tra thread safety
- Nếu thấy `QObject: Cannot create children for a parent that is in a different thread` → signal connection dùng sai `ConnectionType`.
- Nếu thấy `QPixmap: It is not safe to use pixmaps outside the GUI thread` → có code UI trong worker.

### Performance indicators
- Plot FPS target: 30 FPS (33ms QTimer).
- Feature worker interval: 200ms.
- Terminal flush interval: 100ms.
- Signal roundtrip target: < 5ms p99.

### Test workers
```bash
pytest tests/perf/test_perf_signal_roundtrip.py -v
pytest tests/perf/test_perf_end_to_end_latency.py -v
pytest tests/perf/test_perf_ui_block.py -v
```

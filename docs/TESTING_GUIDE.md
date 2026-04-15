# 🧪 Testing Guide — STEM Spell Book

---

## 1. Chạy tests

```bash
# Chạy tất cả tests
pytest

# Chỉ unit tests
pytest tests/unit/ -v

# Chỉ integration tests
pytest tests/integration/ -v

# Performance tests (chậm hơn)
pytest tests/perf/ -v

# Một file cụ thể
pytest tests/unit/test_data_store.py -v

# Một test cụ thể
pytest tests/unit/test_data_store.py::test_add_live_sample_validates_shape_and_updates_buffer -v

# Kèm coverage
pytest --cov=logic --cov=ui --cov-report=term-missing
```

---

## 2. Cấu trúc test

```
tests/
├── __init__.py
├── conftest.py                     # qapp fixture, tmp_path reuse
├── unit/
│   ├── test_data_store.py          # DataStore, SettingsStore
│   ├── test_frame_protocol.py      # Parsing, validation, normalisation
│   ├── test_recorder.py            # DataRecorder, sanitize_label
│   ├── test_rarity_utils.py        # RarityTier, resolve_rarity
│   ├── test_firmware_main_generator.py   # sync_firmware_sources
│   └── test_pipeline_build_flow.py # Keras/TFLite build flow (mocked)
├── integration/
│   └── test_handler_phase6_guards.py  # Handler mode guards, signal flows
└── perf/
    ├── perf_utils.py               # RunContext, StatsResult helpers
    ├── _helpers.py                 # PerfProfile
    ├── perf_compare.py             # Artifact comparison logic
    ├── test_perf_utils.py          # perf_utils unit tests
    ├── test_perf_compare.py        # compare artifacts tests
    ├── test_perf_ui_block.py       # UI thread blocking measurement
    ├── test_perf_signal_roundtrip.py  # Signal latency
    ├── test_perf_packet_drop.py    # Packet delivery stability
    ├── test_perf_plot_fps.py       # Plot FPS
    └── test_perf_end_to_end_latency.py  # Full latency serial→UI
```

---

## 3. Fixtures (conftest.py)

### `qapp`

```python
@pytest.fixture(scope="session")
def qapp():
    """Reuse a single QApplication instance for the entire test session."""
    app = QApplication.instance() or QApplication([])
    yield app
```

Dùng cho bất kỳ test nào cần QObject, QSettings, hoặc signals.

### `tmp_path`

Built-in pytest fixture cung cấp temporary directory riêng cho mỗi test.

---

## 4. Unit test patterns

### Test DataStore

```python
def test_add_live_sample_validates_shape(qapp, tmp_path) -> None:
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    # Valid
    store.add_live_sample([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert len(store.get_live_buffer_snapshot()) == 1
    # Invalid shape — should be rejected
    store.add_live_sample([1.0, 2.0])
    assert len(store.get_live_buffer_snapshot()) == 1  # unchanged
```

### Test frame_protocol

```python
from logic.frame_protocol import parse_sensor_csv_frame, DEFAULT_SCALE_PROFILE

def test_parse_sensor_csv_frame_normalizes():
    frame = "16384,0,0,131,0,0"
    result = parse_sensor_csv_frame(frame, DEFAULT_SCALE_PROFILE)
    assert result is not None
    assert abs(result[0] - 1.0) < 0.001  # accel X = 1g
    assert abs(result[3] - 1.0) < 0.001  # gyro X = 1 dps
```

### Test rarity_utils

```python
from logic.rarity_utils import resolve_rarity

def test_resolve_rarity_returns_epic():
    tier = resolve_rarity(100)
    assert tier.label == "EPIC"
```

---

## 5. Integration test pattern

Tests trong `tests/integration/test_handler_phase6_guards.py` dùng stub classes để simulate UI pages:

```python
class RecordStub(QObject):
    sig_start_record   = pyqtSignal(str)
    sig_stop_record    = pyqtSignal()
    sig_data_cropped   = pyqtSignal(list, str)
    sig_spell_deleted  = pyqtSignal(str)
    sig_clear_buffer   = pyqtSignal()
    sig_export_csv     = pyqtSignal()
    # ... + inbound methods as no-ops

class HandlerHarness:
    def __init__(self, tmp_path):
        self.store   = DataStore(dataset_dir=str(tmp_path / "dataset"))
        self.wand    = WandStub()
        self.record  = RecordStub()
        self.home    = HomeStub()
        self.setting = SettingStub()
        self.handler = Handler(
            self.wand, self.record, self.home,
            self.store, self.setting
        )
```

Ví dụ guard test:
```python
def test_record_start_requires_active_connection(handler_harness):
    harness = handler_harness
    # Not connected → should block
    harness.record.sig_start_record.emit("FIREBALL")
    assert harness.handler._mode != "RECORD"
```

---

## 6. Perf test pattern

```python
from tests.perf.perf_utils import RunContext, finalize_stats

def test_signal_roundtrip_50hz(qapp, tmp_path):
    latencies = []
    
    with RunContext(duration_s=5.0, target_hz=50) as ctx:
        while not ctx.done():
            t0 = time.perf_counter()
            # emit signal and process events
            QApplication.processEvents()
            latencies.append((time.perf_counter() - t0) * 1000)
    
    stats = finalize_stats(latencies, min_samples=10)
    assert stats.p99_ms < 5.0, f"p99 latency {stats.p99_ms:.1f}ms > 5ms"
```

---

## 7. Mocking TensorFlow

`test_pipeline_build_flow.py` mock TF để test không cần install TensorFlow:

```python
class _FakeTF:
    """Minimal tensorflow mock."""
    class lite:
        class TFLiteConverter:
            @classmethod
            def from_keras_model(cls, model):
                return _FakeLiteConverter()
        class Optimize:
            DEFAULT = "default"

monkeypatch.setattr("logic.tensorflow.pipeline.tf", _FakeTF())
```

---

## 8. Kiểm tra cấu trúc dataset trong tests

```python
def test_save_cropped_data_creates_csv(qapp, tmp_path):
    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    data = [[float(i)] * 6 for i in range(10)]
    store.save_cropped_data(data, "FIREBALL")
    
    spell_dir = tmp_path / "dataset" / "FIREBALL"
    csv_files = list(spell_dir.glob("*.csv"))
    assert len(csv_files) == 1
    
    with csv_files[0].open() as f:
        rows = list(csv.reader(f))
    assert len(rows) == 11  # 1 header + 10 data rows
```

---

## 9. Các test cases quan trọng

### Must-have tests

- [ ] Frame validation reject malformed CSV (wrong length, non-numeric, NaN)
- [ ] Frame validation reject malformed PREDICT (non-finite confidence)
- [ ] DataStore buffer maxlen enforcement (500 samples)
- [ ] System spell STAND BY cannot be deleted
- [ ] Handler blocks record start when not connected
- [ ] Handler blocks flash when recording
- [ ] Handler blocks UPDATE mode transition from RECORD
- [ ] Rarity tiers at all boundary values (0, 10, 20, 50, 100)
- [ ] firmware_main_generator creates backup of existing main.cpp
- [ ] DataStore migration detects legacy meta.json

### Performance thresholds

| Test | Threshold |
|------|-----------|
| Signal roundtrip p99 | < 5ms |
| End-to-end latency p99 | < 10ms |
| UI block during I/O | < 16ms |
| Plot repaint interval | < 40ms (>25 FPS) |
| Packet delivery stability 30s | > 95% delivery |

---

## 10. Coverage expectations

| Module | Target coverage |
|--------|----------------|
| `logic/frame_protocol.py` | 90%+ |
| `logic/data_store.py` | 80%+ |
| `logic/rarity_utils.py` | 100% |
| `logic/recorder.py` | 85%+ |
| `logic/firmware_main_generator.py` | 80%+ |

---

## 11. CI / pre-push checklist

```bash
# 1. Unit + integration
pytest tests/unit tests/integration -v

# 2. Kiểm tra không có import lỗi
python -c "import logic.handler; import ui.page_record; print('OK')"

# 3. Kiểm tra DataStore STAND BY tự tạo
python -c "
from logic.data_store import DataStore
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    store = DataStore(dataset_dir=os.path.join(tmp, 'dataset'))
    store.refresh_database(force=True)
    spells = store.get_spell_list()
    assert 'STAND BY' in spells, f'STAND BY missing from {spells}'
    print('STAND BY check: OK')
"
```

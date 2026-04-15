# 🤖 AI Agent Guide — STEM Spell Book

Tài liệu này là cẩm nang cho AI agent khi làm việc với project **STEM Spell Book** (stem_ai).  
Đọc kỹ trước khi chỉnh sửa bất kỳ file nào.

---

## 1. Mục tiêu sản phẩm

Desktop app (PyQt6) để:

1. Kết nối ESP32 qua Serial UART 115 200 baud hoặc nhận UDP telemetry cổng 5555.  
2. Hiển thị 3D wand realtime và timeline plot 6-axis IMU (aX/aY/aZ/gX/gY/gZ).  
3. Thu thập dataset CSV → train/build mô hình TinyML → flash firmware lên ESP32.  
4. Quản lý "spell library" (nhãn hành động cảm biến) với rarity system.

---

## 2. Cấu trúc thư mục

```
stem_ai/
├── main.py                         # Entry point
├── config.py                       # APP_DATA_DIR, DATASET_DIR, DEFAULT_MODEL_PATH
├── constants.py                    # SYSTEM_SPELL_NAMES, helpers
├── theme.py                        # apply_modern_theme(app)
├── logic/
│   ├── handler.py                  # 🧠 Controller trung tâm (MVC)
│   ├── data_store.py               # 📦 Single source of truth + signals
│   ├── serial_worker.py            # 🔌 UART QThread
│   ├── udp_worker.py               # 📡 UDP QThread
│   ├── recorder.py                 # 🎙️ DataRecorder
│   ├── data_io_worker.py           # 💾 File I/O QThread
│   ├── feature_worker.py           # 📊 FFT/stats QThread
│   ├── flash_worker.py             # ⚡ esptool flash QThread
│   ├── model_uploader.py           # 📤 .tflite upload QThread
│   ├── frame_protocol.py           # ✅ Validation & normalisation
│   ├── firmware_main_generator.py  # 🔧 ESP-IDF main.cpp generator
│   ├── rarity_utils.py             # 🏆 Rarity tier logic
│   └── tensorflow/
│       └── pipeline.py             # 🤖 Keras training + TFLite export
├── ui/
│   ├── main_window.py              # QMainWindow + UdpWorker
│   ├── mac_shell.py                # macOS-style sidebar nav
│   ├── page_home.py                # Home/Dashboard
│   ├── page_record.py              # Record/Plot/Snip
│   ├── page_statistics.py          # Stats/Train
│   ├── page_wand.py                # Hardware/Connection
│   ├── page_setting.py             # Settings/Firmware
│   ├── wand_3d_widget.py           # OpenGL 3D visualizer
│   ├── wand_panels/                # Decomposed PageWand sub-panels
│   │   ├── connection_panel.py
│   │   ├── flash_panel.py
│   │   ├── terminal_panel.py
│   │   ├── stats_panel.py
│   │   ├── spell_payload_panel.py
│   │   └── connection_presenter.py
│   ├── component_factory.py        # Centralised widget factories
│   ├── layout_utils.py             # clear_layout helper
│   ├── confirm_dialog.py           # 2-button destructive confirm
│   ├── terminal_widget.py          # Reusable terminal QTextEdit
│   ├── modern_layout.py            # MARGIN_*, SPACING_* constants
│   ├── mac_material.py             # apply_soft_shadow
│   └── tokens.py                   # 🎨 Design tokens (colours, sizes, QSS)
├── assets/
│   ├── icon/                       # SVG icons
│   └── firmware/                   # collect.bin, inference.bin
├── app_data/                       # Runtime data (gitignored)
│   ├── dataset/                    # <SPELL_NAME>/<sample>.csv
│   ├── model.tflite
│   └── gesture_model.cc
├── docs/                           # Technical documentation
└── tests/
    ├── unit/
    ├── integration/
    └── perf/
```

---

## 3. Nguyên tắc kiến trúc BẮT BUỘC

### 3.1 Phân tách UI ↔ Logic

| Layer | Phép | Cấm |
|-------|------|-----|
| `ui/` | PyQt6 widgets, signals, styles | Import logic, gọi trực tiếp worker |
| `logic/` | Python thuần, QThread, QObject | Import `QtWidgets` |
| `logic/handler.py` | Connect signals giữa UI và workers | Trực tiếp update UI state |

> **Quy tắc vàng:** UI *emit signal* → Handler slot xử lý → Worker hoặc DataStore → signal ngược về UI.

### 3.2 Anti-freeze rules

- **Không bao giờ** gọi `serial_worker.wait()` trên main thread.
- Mọi I/O nặng (save CSV, delete, export, scan dataset) → `DataIOWorker`.
- Mọi tính toán numpy/FFT → `FeatureWorker`.
- Khi cần stop SerialWorker trước khi flash/upload: dùng `serial_worker.finished` callback, **không** `wait()`.

### 3.3 Signal connection rules

- Worker → UI connections phải dùng `QueuedConnection` (cross-thread safe).
- Handler dùng `_connect_queued(signal, slot)` và `_connect_many_queued(bindings)`.

---

## 4. Startup sequence

```python
# main.py
app = QApplication(sys.argv)
apply_modern_theme(app)          # Load QSS toàn app
ensure_data_dir()                # Tạo app_data/ và app_data/dataset/
data_store = DataStore(...)      # Khởi DataStore + QSettings
_remove_legacy_demo_spell_folders(data_store)   # Cleanup 1 lần
window = MainWindow(data_store)  # Tạo UI + UdpWorker
handler = Handler(               # Wiring tất cả signals
    ui_page_wand=..., ui_page_record=..., ui_page_home=...,
    ui_page_statistics=..., ui_page_setting=...,
    data_store=data_store
)
window.showMaximized()
sys.exit(app.exec())
```

---

## 5. State machine (Mode)

Handler có 4 mode, lưu trong `DataStore` và `SettingsStore`:

```
IDLE  ←→  INFER
 ↑↓         ↑↓
RECORD    UPDATE
```

**Transition map:**
```python
IDLE   → {IDLE, INFER, RECORD, UPDATE}
INFER  → {IDLE, INFER, RECORD, UPDATE}
RECORD → {IDLE, INFER, RECORD}        # Không vào UPDATE khi đang record
UPDATE → {IDLE, INFER, UPDATE}        # Không vào RECORD khi đang update
```

Dùng `handler._transition_mode(target, reason=..., push_to_device=...)`.

---

## 6. Port ownership

Chỉ một subsystem được dùng COM port tại 1 thời điểm:

```python
handler._port_owner: str | None
# Values: None | "serial" | "flash" | "upload"
```

Guard `_can_use_port(requester)` kiểm tra trước mọi thao tác serial.

---

## 7. Rarity system

Spell "mastery" dựa vào số lượng CSV samples:

| Threshold | Label | Color token |
|-----------|-------|-------------|
| 0 | UNLEARNED | `RARITY_NONE` |
| 10 | COMMON | `RARITY_COM` |
| 20 | UNCOMMON | `RARITY_UNC` |
| 50 | RARE | `RARITY_RARE` |
| 100 | EPIC | `RARITY_EPIC` |

Module: `logic/rarity_utils.py` — `RarityTier`, `RARITY_TIERS`, `resolve_rarity(count)`.

---

## 8. System spell protection

`"STAND BY"` là spell hệ thống, luôn tồn tại và không được xóa.

```python
# constants.py
SYSTEM_SPELL_NAMES = {"STAND BY"}
is_system_spell(name)         # → bool
canonical_system_spell(name)  # → "STAND BY"
```

`DataStore` tự tái tạo thư mục `STAND BY` khi không thấy trong dataset.

---

## 9. Quy ước đặt tên

- Signals: tiền tố `sig_` (vd: `sig_data_received`)
- Private methods: tiền tố `_` (vd: `_on_data_received`)
- Public slots: tiền tố `on_` (vd: `on_record_start`)
- Worker threads: hậu tố `Worker` (vd: `SerialWorker`)
- UI pages: tiền tố `Page` (vd: `PageRecord`)

---

## 10. Khi thêm feature mới

1. **Định nghĩa data flow** trước khi code.
2. **Logic trước** — implement ở `/logic`.
3. **UI sau** — tạo widget/signal ở `/ui`.
4. **Wiring** — connect trong `Handler._connect_signals`.
5. **Test** — thêm unit test ở `tests/unit/`, integration test nếu cần.

---

## 11. Danh sách kiểm tra khi review

- [ ] Không có `time.sleep` hay blocking loop trên main thread.
- [ ] Signal cross-thread dùng `QueuedConnection`.
- [ ] Không import `QtWidgets` trong `/logic`.
- [ ] Không hardcode màu sắc hoặc kích thước (dùng `tokens.py`).
- [ ] File path dùng `pathlib.Path`, không dùng string concatenation.
- [ ] System spell `"STAND BY"` không bị xóa.
- [ ] Guard `_can_use_port` được gọi trước mọi flash/upload.
- [ ] DataIOWorker và FeatureWorker nhận job qua queue, không gọi trực tiếp.

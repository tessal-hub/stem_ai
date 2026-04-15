# 📁 Dataset & File Conventions

---

## 1. Cấu trúc thư mục runtime

```
app_data/                        ← APP_DATA_DIR (config.py)
├── dataset/                     ← DATASET_DIR
│   ├── STAND BY/                ← System spell (auto-created, protected)
│   │   ├── sample_20240115_143022_001.csv
│   │   └── sample_20240115_143045_002.csv
│   ├── FIREBALL/
│   │   ├── sample_20240115_150312_001.csv
│   │   └── ...
│   └── <SPELL_NAME>/
│       └── sample_<timestamp>.csv
├── model.tflite                 ← DEFAULT_MODEL_PATH
└── gesture_model.cc             ← GESTURE_MODEL_CC_OUTPUT
```

> **Lưu ý:** `app_data/` thường được gitignore, chỉ tồn tại khi chạy app.

---

## 2. Tên spell

| Rule | Chi tiết |
|------|---------|
| Uppercase | Tự động convert bằng `normalize_spell_name()` |
| Whitespace | Collapse nhiều space thành 1 |
| Filesystem safe | Dùng làm tên thư mục trực tiếp |
| Protected | `"STAND BY"` không thể xóa |

```python
# constants.py
normalize_spell_name("  fire  ball  ")  # → "FIRE BALL"
normalize_spell_name("STAND BY")        # → "STAND BY"
is_system_spell("stand by")             # → True
canonical_system_spell("stand by")      # → "STAND BY"
```

---

## 3. Sample CSV format

Mỗi sample là một file CSV với header:

```csv
accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z
0.0874,-0.1123,0.9561,0.0107,-0.0229,0.0015
0.0891,-0.1148,0.9512,0.0112,-0.0223,0.0019
...
```

- **6 columns** bắt buộc: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`
- Giá trị đã được **normalized** (float, không phải raw int16)
- Accel đơn vị: g (gia tốc, 1.0 = 9.8 m/s²)
- Gyro đơn vị: deg/s (angular velocity)

---

## 4. File naming convention

```
sample_<YYYYMMDD>_<HHMMSS>_<seq>.csv

Ví dụ:
  sample_20240115_143022_001.csv
  sample_20240115_143045_002.csv
```

Tạo bởi `DataIOWorker._do_save()`:
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
seq = len(existing_files) + 1
filename = f"sample_{timestamp}_{seq:03d}.csv"
```

---

## 5. DataStore — Database management

### `refresh_database(force=False)`

Scan DATASET_DIR, đếm CSV files per spell:
```python
spell_counts = {
    "STAND BY": 12,
    "FIREBALL": 45,
    "ICE LANCE": 8,
}
```

- **Debounce:** Nếu `force=False`, skip nếu < 2 giây từ lần scan trước.
- Auto tạo lại thư mục `STAND BY` nếu bị mất.
- Emit `sig_db_updated(spell_counts)` sau mỗi scan.

### `get_spell_list() → list[str]`

Trả về danh sách spell names (sorted, bao gồm system spells).

### `get_samples_for_spell(spell_name) → list[str]`

Trả về sorted list of CSV filenames cho một spell:
```python
["sample_20240115_143022_001.csv", "sample_20240115_143045_002.csv"]
```

---

## 6. DataStore — Save/delete flow

### Save (qua DataIOWorker)

```python
# Từ Handler:
self.data_io_worker.enqueue_save(spell_name, cropped_6d_data)
# cropped_6d_data: list[list[6 floats]]

# DataIOWorker thread:
# 1. normalize spell name
# 2. tạo thư mục nếu chưa có
# 3. generate filename
# 4. write CSV header + rows
# 5. emit sig_save_done(True, filename)
# 6. enqueue_refresh() → scan + emit sig_db_refreshed
```

### Delete (qua DataIOWorker)

```python
# Từ Handler:
self.data_io_worker.enqueue_delete(spell_name)

# DataIOWorker thread:
# 1. kiểm tra không phải system spell
# 2. shutil.rmtree(spell_dir)
# 3. emit sig_delete_done(True, message)
# 4. enqueue_refresh()
```

---

## 7. Export CSV

```python
# Từ Handler:
self.data_io_worker.enqueue_export(live_buffer_snapshot, output_path)
# output_path: str từ QFileDialog

# DataIOWorker thread:
# write CSV với header, mỗi row là 1 frame 6D
# emit sig_export_done(True, output_path)
```

---

## 8. Migration (legacy meta.json)

Nếu DataStore phát hiện `*.meta.json` cũ trong dataset folder:

```python
# Trong DataStore._run_migrations():
# 1. Tìm tất cả *.meta.json
# 2. Backup toàn bộ dataset vào app_data/_migration_backups/<timestamp>/
# 3. Xóa meta.json files
# 4. Log cảnh báo
```

Backup path: `app_data/_migration_backups/<YYYYMMDD_HHMMSS>/`

---

## 9. Settings persistence (QSettings)

```python
# SettingsStore._ORG_NAME = "STEMSpellBook"
# SettingsStore._APP_NAME = "Reboot"
# Platform: Windows → Registry, macOS → plist, Linux → INI file
```

Default values:
```python
{
    "sample_rate":              "50 Hz",
    "accel_scale":              "±2g",
    "gyro_scale":               "±250 dps",
    "window_size":              10,       # frames per window
    "window_overlap":           0,        # overlap percentage
    "ml_pipeline":              "Random Forest (Edge)",
    "project_name":             "",
    "auto_save":                False,
    "selected_port":            "",
    "baud_rate":                "115200",
    "model_path":               str(DEFAULT_MODEL_PATH),
    "firmware_mode":            "data",   # "data" | "inference"
    "idf_main_dir":             "",
    "demo_spell_cleanup_done":  False,    # one-time cleanup flag
}
```

---

## 10. ESP-IDF firmware sync

Sau khi build model thành công, `firmware_main_generator.sync_firmware_sources` làm:

```
idf_main_dir/
    gesture_model.cc         ← copy từ app_data/gesture_model.cc
    main.cpp                 ← generate từ template với spell class names
    main.cpp.backup_<ts>     ← backup main.cpp cũ nếu có
```

Template `main.cpp` chứa:
- `enum class GestureClass { <spell1>, <spell2>, ..., UNKNOWN }`
- Dispatch map từ class index → handler function
- IDLE index cho `STAND BY`

---

## 11. Firmware binaries

```
assets/firmware/
    collect.bin     ← ESP32 firmware cho Record mode (stream CSV)
    inference.bin   ← ESP32 firmware cho Inference mode (predict)
```

- Flash bằng esptool: `write_flash 0x10000 <bin>`
- Guard: `Path(bin_path).stat().st_size > 0` trước khi flash.

---

## 12. Model files

| File | Path | Format |
|------|------|--------|
| TFLite model | `app_data/model.tflite` | TensorFlow Lite FlatBuffer |
| C source | `app_data/gesture_model.cc` | C array: `const unsigned char gesture_model[] = {...}` |

Upload protocol (ModelUploader):
1. Send `CMD:UPLOAD_MODEL:<size_bytes>\n`
2. Wait `ACK:READY`
3. Send chunks (4096 bytes) → wait `ACK:CHUNK_RECEIVED` per chunk
4. Wait `ACK:UPLOAD_COMPLETE`

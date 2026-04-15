# 📋 UI Signal & Method Contract

Tài liệu này định nghĩa contract giữa các UI page và Handler.  
**Frozen** — không đổi tên signal/method mà không cập nhật tài liệu này.

---

## 1. PageHome (ui/page_home.py)

### Signals (outbound → Handler)

| Signal | Payload | Ý nghĩa |
|--------|---------|---------|
| `sig_simulation_replay_requested` | — | Replay last input frames |
| `sig_simulation_stop_requested` | — | Stop simulation |
| `sig_calibrate_requested` | — | Calibrate wand (send command) |
| `sig_quick_test_requested` | — | Quick test mode |

### Methods (inbound ← Handler / DataStore)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `set_connection_status(connected, port)` | `bool, str` | Cập nhật status bar |
| `set_mode(mode)` | `str` | Cập nhật mode label (IDLE/INFER/RECORD/UPDATE) |
| `update_prediction(label, confidence)` | `str, float` | Kết quả inference |
| `wand_3d.update_orientation(ax,ay,az,gx,gy,gz)` | 6× `float` | Update 3D model |
| `update_spell_list(spells)` | `list[str]` | Refresh spell preview |

---

## 2. PageRecord (ui/page_record.py)

### Signals (outbound → Handler)

| Signal | Payload | Ý nghĩa |
|--------|---------|---------|
| `sig_start_record` | `str` spell_name | Bắt đầu ghi dữ liệu |
| `sig_stop_record` | — | Dừng ghi |
| `sig_snip_record` | — | (internal, sau khi emit data_cropped) |
| `sig_data_cropped` | `list, str` (6D data, spell_name) | Gửi crop để save |
| `sig_spell_selected` | `str` spell_name | User chọn spell |
| `sig_spell_deleted` | `str` spell_name | User xóa spell |
| `sig_clear_buffer` | — | Xóa live buffer |
| `sig_export_csv` | — | Export buffer ra CSV |
| `sig_sample_opened` | `str` filename | Mở sample cụ thể |

### Methods (inbound ← Handler / DataStore)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `update_plot_data(buffer_snapshot)` | `list[list[6]]` | Nhận snapshot buffer mới |
| `set_wand_ready(is_ready)` | `bool` | Trạng thái wand ready/not ready |
| `set_recording_state(recording)` | `bool` | Toggle START/STOP enable |
| `set_save_status(spell_name)` | `str` | Feedback sau khi save thành công |
| `load_spell_list(spells)` | `list[str]` | Cập nhật spell combo + spell library |
| `load_samples_for_spell(spell_name, samples)` | `str, list[str]` | Mở sample list page |
| `update_record_count(count)` | `int` | Cập nhật count label |

### Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | START recording |
| `Ctrl+T` | STOP recording |
| `Ctrl+X` | SNIP selected region |

---

## 3. PageStatistics (ui/page_statistics.py)

### Signals (outbound → Handler)

| Signal | Payload | Ý nghĩa |
|--------|---------|---------|
| `sig_train_build_requested` | — | Train + build full pipeline |
| `sig_sample_opened` | `str` filename | Open sample for review |
| `sig_spell_selected` | `str` spell_name | (internal, auto-wired) |

### Methods (inbound ← Handler / DataStore)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `update_spell_counts(spell_counts)` | `dict[str, int]` | Cập nhật spell mastery cards |
| `update_live_features(features)` | `dict` | Cập nhật live feature labels + FFT |
| `set_training_state(running)` | `bool` | Toggle train button |
| `update_training_status(text)` | `str` | Update `[TRAIN]`/`[BUILD]`/`[DONE]` status |
| `update_training_progress(value)` | `int` 0–100 | Update progress bar |
| `set_training_finished(success, summary)` | `bool, str` | Hoàn thành train/build |

---

## 4. PageWand (ui/page_wand.py)

### Signals (outbound → Handler)

| Signal | Payload | Ý nghĩa |
|--------|---------|---------|
| `sig_serial_scan` | — | Scan COM ports |
| `sig_serial_connect` | `str` port | Kết nối serial |
| `sig_serial_disconnect` | — | Ngắt kết nối serial |
| `sig_bt_scan` | — | Scan Bluetooth devices |
| `sig_bt_connect` | `str` device | Kết nối Bluetooth |
| `sig_bt_disconnect` | — | Ngắt kết nối Bluetooth |
| `sig_flash_compile` | `list[str]` spells | Compile (legacy) |
| `sig_flash_upload` | — | Upload model |
| `sig_term_clear` | — | Clear terminal |
| `sig_train_build_tflite_requested` | — | Build .tflite only |
| `sig_train_build_cc_requested` | — | Build .cc only |
| `sig_train_build_requested` | — | Build cả hai |

### Methods (inbound ← Handler / DataStore)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `append_terminal_text(text)` | `str` | Thêm dòng vào terminal |
| `update_flash_progress(percentage, status_text)` | `int, str` | Cập nhật flash progress |
| `set_serial_status(connected, port_name)` | `bool, str` | Cập nhật serial status label |
| `update_serial_port_list(ports)` | `list[str]` | Populate port dropdown |
| `set_bluetooth_status(connected, device_name)` | `bool, str` | Cập nhật BT status |
| `update_bt_device_list(devices)` | `list[str]` | Populate BT dropdown |
| `update_esp_stats(stats)` | `dict[str, str]` | Cập nhật ESP telemetry labels + chart |
| `load_spell_payload_list(spell_counts)` | `dict[str, int]` | Cập nhật spell payload panel |

### Legacy attributes (backward-compat)

| Attribute | Type | Lý do giữ |
|-----------|------|----------|
| `combo_serial_ports` | `QComboBox` | Handler đọc `currentText()` |

---

## 5. PageSetting (ui/page_setting.py)

### Signals (outbound → Handler)

| Signal | Payload | Ý nghĩa |
|--------|---------|---------|
| `sig_settings_saved` | `dict` config | User click SAVE SETTINGS |
| `sig_clear_database` | — | User confirm erase all data |
| `sig_flash_data_firmware` | — | Flash collect.bin |
| `sig_flash_inference_firmware` | — | Flash inference.bin |

### Methods (inbound ← Handler / DataStore)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `load_settings(config)` | `dict` | Populate form fields |
| `set_flash_buttons_enabled(enabled)` | `bool` | Enable/disable flash buttons |
| `update_flash_progress(percentage, status_text)` | `int, str` | Cập nhật progress bar |
| `append_console_text(text)` | `str` | Thêm log vào console |

### Config dict keys (sig_settings_saved payload)

```python
{
    "sample_rate":    str,   # "50 Hz"
    "accel_scale":    str,   # "±2g"
    "gyro_scale":     str,   # "±250 dps"
    "window_size":    int,
    "window_overlap": int,
    "ml_pipeline":    str,
    "project_name":   str,
    "auto_save":      bool,
    "idf_main_dir":   str,   # path to ESP-IDF 'main' directory
}
```

---

## 6. Wand3DWidget (ui/wand_3d_widget.py)

### Methods (inbound ← Handler)

| Method | Args | Ý nghĩa |
|--------|------|---------|
| `update_orientation(ax,ay,az,gx,gy,gz)` | 6× `float` | Cập nhật 3D rotation |
| `reset_camera()` | — | Đặt lại góc nhìn về HOME |

Complementary filter parameters:
- `_GYRO_WEIGHT = 0.96` (96% gyro integration)
- `_ACCEL_WEIGHT = 0.04` (4% accel correction)
- `_DT = 1/50` (50 Hz nominal)

---

## 7. Sub-panels trong PageWand

### WandConnectionPanel

Signals: `sig_serial_scan/connect/disconnect`, `sig_bt_scan/connect/disconnect`

Methods:
- `set_serial_status(connected, port_name)`
- `update_serial_port_list(ports)`
- `set_bluetooth_status(connected, device_name)`
- `update_bt_device_list(devices)`

### WandFlashPanel

Signals: `sig_build_tflite_clicked`, `sig_build_cc_clicked`, `sig_upload_clicked`

Methods:
- `update_flash_progress(percentage, status_text)`

### WandTerminalPanel

Signals: `sig_clear_requested`

Methods:
- `append_terminal_text(text)` — buffered 100ms flush

### WandStatsPanel

Methods:
- `update_esp_stats(stats: dict[str, str])`
- `update_spell_chart(spell_counts: dict[str, int])`

### WandSpellPayloadPanel

Methods:
- `load_spell_list(spell_counts: dict[str, int])`
- `get_checked_spells() → list[str]`
- `get_available_spell_names() → list[str]`

---

## 8. MacShell (ui/mac_shell.py)

```python
shell.nav_requested.connect(main_window._set_page)  # int index 0–4
shell.set_active_index(index)                        # highlight nav button
```

Nav indices:
- 0 → Home
- 1 → Record
- 2 → Statistics
- 3 → Wand
- 4 → Setting

---

## 9. ConfirmDialog (ui/confirm_dialog.py)

```python
from ui.confirm_dialog import confirm_destructive

result: bool = confirm_destructive(
    parent_widget,
    title="...",
    message="...",
    confirm_text="Delete",
    cancel_text="Cancel",
)
```

Dùng cho mọi destructive action (xóa spell, erase database, clear buffer).

---

## 10. TerminalWidget (ui/terminal_widget.py)

```python
from ui.terminal_widget import TerminalWidget

t = TerminalWidget(max_lines=1000, read_only=True)
t.append_line("text")  # auto-scroll, line-capped at max_lines
```

Dùng trong `WandTerminalPanel` và `PageSetting.console_log`.

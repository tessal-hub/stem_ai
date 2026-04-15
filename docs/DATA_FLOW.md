# 🔁 Data Flow — STEM Spell Book

Chi tiết mọi luồng dữ liệu trong ứng dụng từ phần cứng đến UI.

---

## 1. Serial UART (ESP32 → PC)

```
ESP32 (UART 115200)
    │
    ▼
SerialWorker.run()              [QThread — KHÔNG phải main thread]
    │   Parse line (readline)
    │   frame_protocol.parse_sensor_csv_frame()    → 6 float normalised
    │   frame_protocol.parse_prediction_frame()   → (label, confidence)
    │
    ├── sig_data_received(list[6])
    │       └─► Handler._on_data_received(values)
    │               ├─► Wand3DWidget.update_orientation(ax,ay,az,gx,gy,gz)
    │               ├─► DataStore.update_sensor_data(dict)
    │               │       └─► sig_stats_updated(dict) ──► PageWand.update_esp_stats
    │               ├─► [if RECORD mode] DataRecorder.add_row(values)
    │               │                   DataStore.add_live_sample(values)
    │               │                       └─► sig_live_buffer_updated(list)
    │               │                               └─► PageRecord.update_plot_data
    │               └─► FeatureWorker.enqueue(snapshot)  [non-blocking]
    │
    ├── sig_prediction_received(str, float)
    │       └─► Handler._on_prediction_received(label, conf)
    │               └─► DataStore.update_prediction(label, conf)
    │                       └─► sig_prediction_updated(str,float) ──► PageHome
    │
    ├── sig_raw_line_received(str)
    │       └─► Handler slot ──► PageWand.append_terminal_text
    │
    └── sig_connection_status(bool, str)
            └─► Handler._on_connection_status_changed
                    ├─► DataStore.set_connection_status(connected, port)
                    │       └─► sig_connection_state_updated ──► PageHome
                    └─► PageWand.set_serial_status
                        PageRecord.set_wand_ready
```

---

## 2. UDP Telemetry (ESP32 WiFi → PC)

```
ESP32 (UDP JSON → 0.0.0.0:5555)
    │
    ▼
UdpWorker.run()                 [QThread — chạy trong MainWindow]
    │   socket.recvfrom(4096)
    │   json.loads(payload)
    │   _update_health_metrics() [EMA rate/jitter/loss]
    │
    ├── sig_data_received(dict)
    │       └─► MainWindow._on_udp_data(payload)
    │               │   Extract: accel_x/y/z, gyro_x/y/z
    │               ├─► DataStore.update_sensor_data(dict)
    │               └─► [if live buffer active] DataStore.add_live_sample(values)
    │
    ├── sig_health_update(dict)     [throttled: max 5 Hz]
    │       └─► MainWindow._on_udp_health_update
    │               └─► DataStore.update_udp_health(stats)
    │                       └─► sig_stats_updated ──► PageWand (UDP Rate/Jitter/Loss)
    │
    └── sig_status_change(bool)
            └─► MainWindow._on_udp_status_change
                    └─► PageHome connection indicator
```

UDP health dict keys:
```
udp_rate_hz    float  — EMA packets/sec
udp_jitter_ms  float  — EMA inter-packet interval
udp_received   int    — total packets since start
udp_dropped    int    — estimated dropped (from seq gaps)
udp_loss_pct   float  — loss percentage
udp_last_seq   int|None
```

---

## 3. Feature extraction (FFT / statistics)

```
Handler._feature_timer          [QTimer, 200ms interval]
    │
    ▼
Handler._emit_live_features()
    │   snapshot = DataStore.get_live_buffer_snapshot()
    │
    ▼
FeatureWorker.enqueue(snapshot)  [non-blocking, drop oldest if full]
    │
    ▼
FeatureWorker.run()              [QThread]
    │   accel_mean, accel_var, accel_rms per axis
    │   gyro_mean, gyro_var, gyro_rms per axis
    │   FFT (numpy.fft.rfft) on accel magnitude
    │   dominant_freq, fft_magnitudes
    │
    ▼
sig_features_ready(dict)
    └─► Handler slot (QueuedConnection)
            └─► DataStore.update_live_features(features)
                    └─► sig_live_features_updated(dict)
                            └─► PageStatistics.update_live_features
                                PageStatistics FFT plot
```

Feature dict keys:
```
accel_mean_x/y/z, accel_var_x/y/z, accel_rms
gyro_mean_x/y/z, gyro_var_x/y/z, gyro_rms
dominant_freq (Hz), fft_magnitudes (list)
```

---

## 4. Recording & snipping pipeline

```
User: SELECT spell → click START
    │
    ▼
PageRecord.sig_start_record(spell_name)
    └─► Handler.on_record_start(spell_name)
            │   Guard: serial connected, not recording, not UPDATE mode
            │   _transition_mode("RECORD")
            │   DataRecorder.start_recording(spell_name)
            │   DataStore.clear_live_buffer()
            └─► PageRecord.set_recording_state(True)

During recording:
    SerialWorker → sig_data_received → DataStore.add_live_sample
                                           → sig_live_buffer_updated
                                               → PageRecord.update_plot_data
    PageRecord._render_plots() [QTimer 33ms ≈ 30 FPS]
        reads DataStore.get_live_buffer_snapshot()
        → curve_ax/ay/az/gx/gy/gz.setData(arr)

User: click STOP
    │
    ▼
PageRecord.sig_stop_record()
    └─► Handler.on_record_stop()
            │   DataRecorder.stop()
            │   PageRecord.is_live = False  (freeze buffer for crop)
            │   crop_region.show()          (drag handles visible)
            └─► _transition_mode("INFER" if serial running else "IDLE")

User: drag crop region → click SNIP
    │
    ▼
PageRecord._on_snip()
    │   Crop buffer[min_x:max_x]
    └─► sig_data_cropped(cropped_6d, spell_name)
            └─► Handler.on_data_cropped(data, spell_name)
                    └─► DataIOWorker.enqueue_save(spell_name, data)
                                │
                    DataIOWorker runs in thread:
                        write app_data/dataset/<SPELL>/sample_<ts>.csv
                        sig_save_done(bool, message)
                        sig_db_refreshed(spell_counts)
                                │
                    Handler._on_save_done → PageRecord.set_save_status
                    Handler._on_db_updated → PageRecord/PageStatistics/PageWand refresh lists
```

---

## 5. Firmware flashing pipeline

```
User: click INSTALL DATA FIRMWARE / INSTALL AI ENGINE (PageSetting)
    │
    ▼
PageSetting.sig_flash_data_firmware  OR  sig_flash_inference_firmware
    └─► Handler.handle_firmware_flash("data" | "inference")
            │   Guards:
            │     • selected port not empty
            │     • not currently recording
            │     • flash_worker not running
            │     • firmware .bin exists and not empty
            │     • _can_use_port("flash")
            │
            ├─► If serial_worker running:
            │       serial_worker.stop()
            │       serial_worker.finished → _deferred_start_flash()
            │
            └─► _do_flash_firmware()
                    _set_port_owner("flash")
                    PageSetting.set_flash_buttons_enabled(False)
                    FlashWorker.set_target(port, bin_path)
                    FlashWorker.start()

FlashWorker.run()                [QThread]
    esptool subprocess: write_flash 0x10000 <bin>
    Parse stdout for percentage
    sig_flash_progress(int, str)
    sig_flash_finished(bool, str)

Handler slots:
    _on_flash_progress → PageSetting.update_flash_progress / append_console_text
    _on_flash_finished → _set_port_owner(None)
                         PageSetting.set_flash_buttons_enabled(True)
                         _transition_mode("IDLE")
```

---

## 6. Model upload (.tflite) pipeline

```
User: click sig_flash_upload (PageWand)
    │
    ▼
Handler.on_flash_upload()
    │   Guards:
    │     • model .tflite exists + not empty
    │     • selected port not empty
    │     • _can_use_port("upload")
    │     • not recording
    │
    ├─► If serial_worker running:
    │       serial_worker.stop()
    │       serial_worker.finished → _deferred_start_upload()
    │
    └─► _do_model_upload()
            _set_port_owner("upload")
            ModelUploader.start()

ModelUploader.run()              [QThread]
    Protocol:
        send "CMD:UPLOAD_MODEL:<size>\n"
        wait "ACK:READY"
        loop: send 4096-byte chunk → wait "ACK:CHUNK_RECEIVED"
        wait "ACK:UPLOAD_COMPLETE"
    sig_progress(int)
    sig_status_msg(str)
    sig_error(str)
    sig_finished(bool, str)

Handler slots:
    _on_upload_progress → PageWand.update_flash_progress
    _on_upload_status   → PageWand.append_terminal_text
    _on_upload_finished → _set_port_owner(None), _transition_mode("IDLE")
```

---

## 7. Model training & build pipeline

```
User: click TRAIN+BUILD (PageStatistics or PageWand)
    │
    ▼
Handler.on_train_build_model_requested()
    │   Guard: not already training
    │   selected_spells = PageWand.spell_payload_panel.get_checked_spells()
    │   output_mode = "both" | "tflite" | "cc"
    │
    ▼
GestureModelBuildWorker.start()  [QThread]
    │
    build_gesture_model(dataset_dir, output_mode, selected_spells)
        │   Scan spell folders, read CSVs
        │   Windowize time-series (window_size, step)
        │   Build Keras Conv1D model
        │   Fit with EarlyStopping + ReduceLROnPlateau
        │   Convert → .tflite
        │   Write C-array → gesture_model.cc
        │
        sig_status(str)    → Handler → PageStatistics.update_training_status
        sig_progress(int)  → Handler → PageStatistics.update_training_progress
        sig_finished(bool, str)
            │
            └─► Handler._on_model_build_finished(success, summary)
                    │   If success:
                    │     DataStore.save_settings({"model_path": tflite_path})
                    │     sync_firmware_sources(idf_main_dir, cc_path, class_names)
                    │       ← copy gesture_model.cc, generate main.cpp with enum
                    └─► PageStatistics.set_training_finished(success, summary)
```

---

## 8. DataStore signals summary

| Signal | Payload | Consumers |
|--------|---------|-----------|
| `sig_db_updated` | `dict[str, int]` spell counts | PageRecord, PageStatistics, PageWand |
| `sig_stats_updated` | `dict[str, str]` ESP stats | PageWand.update_esp_stats |
| `sig_prediction_updated` | `(str, float)` | PageHome |
| `sig_live_buffer_updated` | `list[list[6]]` | PageRecord.update_plot_data |
| `sig_live_features_updated` | `dict` features | PageStatistics |
| `sig_recording_state_updated` | `bool` | PageRecord |
| `sig_mode_updated` | `str` | PageHome.set_mode |
| `sig_connection_state_updated` | `(bool, str)` | PageHome |
| `sig_udp_health_updated` | `dict` | PageWand (via stats_updated) |

---

## 9. Buffer sizes (DataStore)

| Buffer | Type | maxlen |
|--------|------|--------|
| `_sensor_data[axis]` | `deque[float]` | 100 |
| `_sensor_frame_history` | `deque[list[6]]` | 500 |
| `_live_buffer` | `deque[list[6]]` | 500 |

---

## 10. Normalisation rules

Accel raw int → g:
```python
float(raw) / accel_lsb_per_g
# Default: 16384.0 (±2 g range MPU-6050)
```

Gyro raw int → dps:
```python
float(raw) / gyro_lsb_per_dps
# Default: 131.0 (±250 dps range MPU-6050)
```

Scale profiles configured via Settings page, stored in `QSettings`, applied to
`SerialWorker` via `Handler._configure_serial_scale_profile()`.

ESP32 CSV line format:
```
<aX>,<aY>,<aZ>,<gX>,<gY>,<gZ>\n
# values are raw int16 from MPU-6050 register reads
```

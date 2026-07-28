# Audit Report — 2026-07-23

## Summary
- Total findings: P0=**14** P1=**10** P2=**3**
- Go/No-Go recommendation: **NO-GO**
- 14 P0 findings span threading safety (4), ML pipeline correctness (3), security (3), error resilience (2), and architectural integrity (2). The preprocessing parity mismatch alone (Python L1 energy vs C++ tail-variance) guarantees silent misclassification on-device. Combined with shell injection in `idf_worker.py`, unbounded directory traversal via unsanitized spell names, and multiple workers that can permanently hang the UI, this codebase is not safe to hand to a real user.

---

## P0 Findings

### [P0-01] Preprocessing Parity Mismatch — Training vs Firmware Energy Calculation
- File: `logic/tensorflow/pipeline.py:151` vs `assets/firmware/main.cpp.template:407`
- Evidence:
  ```python
  # Python (Training) — full-window L1 sum over 6 channels
  energy = sum(
      abs(row[0]) + abs(row[1]) + abs(row[2]) +
      abs(row[3]) + abs(row[4]) + abs(row[5])
      for row in w
  )
  ```
  ```cpp
  // C++ (Inference) — tail-15-sample variance
  var_accel += (dx * dx + dy * dy + dz * dz);
  float motion_energy = var_accel + (var_gyro / 10000.0f);
  ```
- Why this is P0: Peak/energy windowing logic is completely mismatched. Training selects the "best window" using L1 norm across the entire window; firmware uses variance over a 15-sample tail. The model was trained on windows selected by a different criterion than what the device uses at inference time. This causes silent accuracy collapse — the exact pattern that produced the historical BOOST→CIRCLE_CW misclassification bug.
- Suggested direction: Standardize on a single energy/motion calculation algorithm and apply it identically in both Python window extraction and C++ streaming.

### [P0-02] Train/Validation Leakage via Overlapping Window Split
- File: `logic/tensorflow/pipeline.py:646`
- Evidence:
  ```python
  val_size = int(len(cnn_train_features) * val_fraction)
  if val_size > 0:
      perm_base = np.random.default_rng(random_seed).permutation(len(cnn_train_features))
      cnn_train_features = [cnn_train_features[i] for i in perm_base]
      val_base_feat = cnn_train_features[-val_size:]
  ```
- Why this is P0: The fallback split (when file-level split fails) slices from `cnn_train_features`, which was built by windowizing with overlapping strides (`step=effective_step`). Randomly splitting overlapping windows guarantees data leakage — validation accuracy will be inflated, hiding model quality issues from the user.
- Suggested direction: Ensure file-level split always works, or if window-level fallback is needed, split temporally (not randomly) to avoid overlapping windows crossing the boundary.

### [P0-03] Dummy val_acc=1.000 on Skip-Train Path
- File: `logic/tensorflow/pipeline.py:868`
- Evidence:
  ```python
  else:
      class DummyHistory:
          history = {"accuracy": [1.0], "val_accuracy": [1.0]}
      history = DummyHistory()
  ```
- Why this is P0: When weights are loaded (`skip_train=True`) and no validation data is present, the pipeline silently fabricates perfect 1.000 accuracy. This misleads the user into trusting an unevaluated model.
- Suggested direction: Report `N/A` or `0.0` for skipped validations and log an explicit warning.

### [P0-04] Missing Queued Semantics on QThread Signals (handler.py)
- File: `logic/handler.py:353-368`
- Evidence:
  ```python
  self.data_io_worker.sig_save_done.connect(self._on_io_done)
  self.data_io_worker.sig_db_refreshed.connect(self.store.update_counts_from_worker)
  self.feature_worker.sig_features_ready.connect(self.store.update_live_features)
  self.uploader.status_msg.connect(self.ui_wand.append_terminal_text)
  self.flash_worker.log_msg.connect(self._flash_log_to_console)
  ```
- Why this is P0: Signals crossing from `QThread` workers to the main UI thread lack `type=Qt.ConnectionType.QueuedConnection`. Rapid emissions from background threads will cause thread-safety violations and UI state corruption. This is a regression of BUG #1 (documented in `docs/ARCHIVE/2026-04/ARCHITECTURE_AUDIT_REPORT_2026-04-03.md`).
- Suggested direction: Add `type=Qt.ConnectionType.QueuedConnection` to all cross-thread signal connections.

### [P0-05] Missing Queued Semantics on UdpWorker Signals (main_window.py)
- File: `ui/main_window.py:98-100`
- Evidence:
  ```python
  self.udp_worker.sig_data_received.connect(self._on_udp_sensor_dispatch)
  self.udp_worker.sig_status_change.connect(self._on_udp_status_changed)
  self.udp_worker.sig_health_update.connect(self._on_udp_health_updated)
  ```
- Why this is P0: `UdpWorker` runs in a background `QThread`. Without explicit `QueuedConnection`, signals emitted at 50Hz from the worker thread risk Qt event loop corruption.
- Suggested direction: Add `type=Qt.ConnectionType.QueuedConnection` to UdpWorker signals.

### [P0-06] Missing Double-Start Guards on Multiple Workers
- File: `logic/handler.py:382` (serial_worker), and similar for UdpWorker, FlashWorker, DataIOWorker, FeatureWorker
- Evidence:
  ```python
  def on_serial_connect(self, port: str) -> None:
      ...
      self.serial_worker.start()
  ```
- Why this is P0: Calling `start()` on a `QThread` that has already run and finished without recreating the instance causes undefined behavior / crash. No `isRunning()` guard is present for most workers.
- Suggested direction: Add `if not self.<worker>.isRunning():` guard before every `start()` call, or recreate worker instances.

### [P0-07] stop() Blocks UI Thread with Sleep Loop
- File: `logic/udp_worker.py:102`, `logic/data_io_worker.py:154`, `logic/feature_worker.py:89`
- Evidence:
  ```python
  import time
  start_time = time.perf_counter()
  while self.isRunning() and (time.perf_counter() - start_time < 2.0):
      time.sleep(0.01)
  ```
- Why this is P0: `stop()` is called from the UI thread. The `while` + `time.sleep()` loop blocks the UI event loop for up to 2 seconds, causing the application to visibly hang during shutdown/stop operations.
- Suggested direction: Remove blocking wait loop; use cooperative exit with optional bounded `QThread.wait()`, or dispatch stop from a non-UI context.

### [P0-08] Missing Terminal Signal Emission in DataIOWorker and FeatureWorker
- File: `logic/data_io_worker.py:164`, `logic/feature_worker.py:99`
- Evidence:
  ```python
  def run(self) -> None:
      self._running = True
      while self._running:
          # ... loop body ...
      # No finally block emitting sig_finished
  ```
- Why this is P0: These workers exit their `run()` method without emitting `sig_finished`. If the handler or UI waits for them to finish (during mode transitions or shutdown), the application hangs indefinitely in a "still running" state.
- Suggested direction: Add `finally:` block in `run()` that always emits `sig_finished(success, message)`.

### [P0-09] Conditional Terminal Signal Emission in DataRecorder
- File: `logic/recorder.py:276`
- Evidence:
  ```python
  def _close_recording(self, success: bool, error_message: str = "") -> None:
      if not self._is_recording and self._file is None and self._writer is None:
          return  # <-- early return, sig_finished never emitted
  ```
- Why this is P0: If the worker thread stops without having actually recorded (e.g. connection dropped before first sample), `_close_recording` returns early and `sig_finished` is never emitted. UI hangs in "recording" state forever.
- Suggested direction: Always emit `sig_finished` in the `finally:` block of `run()`, regardless of recording state.

### [P0-10] Partial-Write CSV Data Corruption
- File: `logic/data_io_worker.py:209`
- Evidence:
  ```python
  with open(file_path, mode="w", newline="", encoding="utf-8") as f:
      writer = csv.writer(f)
      writer.writerow(["ax", "ay", "az", "gx", "gy", "gz"])
      writer.writerows(data)
  ```
- Why this is P0: Writes directly to the target `.csv` file. If the process crashes or power is lost during `writerows()`, a corrupted partial CSV is left in the dataset directory, permanently breaking downstream training.
- Suggested direction: Write to a `.tmp` file first, then `os.replace()` atomically on success.

### [P0-11] Uncancellable Flash Worker / Serial Port Lock
- File: `logic/flash_worker.py:186` and `logic/flash_worker.py:41`
- Evidence:
  ```python
  # esptool called in-thread, not as subprocess
  with contextlib.redirect_stdout(log_buf), contextlib.redirect_stderr(log_buf):
      esptool.main(args)
  # ...
  def stop(self) -> None:
      if self._process and self._process.poll() is None:  # _process always None
          self._process.terminate()
  ```
- Why this is P0: `esptool.main()` is called synchronously inside the thread (not as a subprocess). `self._process` is always `None`, making `stop()` a complete no-op. If flashing hangs (e.g. cable disconnect mid-flash), the thread blocks forever, permanently locking the serial port for the rest of the session.
- Suggested direction: Run esptool as a `subprocess.Popen` and store the handle in `self._process`, or document it as uninterruptible and add a timeout.

### [P0-12] Shell Injection in IDF Worker
- File: `logic/idf_worker.py:45-53`
- Evidence:
  ```python
  process = subprocess.Popen(
      cmd,
      cwd=str(self.project_dir),
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      shell=True,   # <-- shell=True with user-controlled port
      bufsize=1
  )
  ```
- Why this is P0: `self.port` is a user-controlled string passed in `cmd` (line 43: `cmd = ["idf.py", "build", "flash", "-p", self.port]`). With `shell=True`, a port value like `COM3 & calc` executes arbitrary commands on Windows.
- Suggested direction: Remove `shell=True` or rigorously validate `self.port` against a COM-port regex.

### [P0-13] Flash Worker Path Traversal
- File: `logic/flash_worker.py:120`
- Evidence:
  ```python
  for addr, path_str in self._flash_parts.items():
      bin_file = Path(path_str).resolve()
  ```
- Why this is P0: `bin_file` is resolved without verifying it belongs to an expected asset directory. A malicious config or crafted `_flash_parts` could flash arbitrary local files to the ESP32, leaking data or bricking the device.
- Suggested direction: Validate that `bin_file.is_relative_to(FIRMWARE_BIN_DIR)` before proceeding.

### [P0-14] Dataset Directory Escape via Unsanitized Spell Names
- File: `logic/dataset_layout.py:126-136` and `constants.py:22`
- Evidence:
  ```python
  # constants.py:22
  def normalize_spell_name(name: str) -> str:
      return " ".join(str(name).strip().split()).upper()
  # dataset_layout.py — uses normalized name as folder path component
  return base / disk_folder
  ```
- Why this is P0: `normalize_spell_name` only strips whitespace and uppercases. It does not remove `.`, `/`, or `\`. A spell name like `"../../WINDOWS"` escapes the dataset root directory, enabling arbitrary directory writes/deletions.
- Suggested direction: Enforce `re.sub(r'[^A-Z0-9_ ]', '', name)` during spell name normalization, or validate the resolved path stays within `DATASET_DIR`.

---

## P1 Findings

### [P1-01] Direct Worker Ownership from UI
- File: `ui/main_window.py:130-145`
- Evidence:
  ```python
  self.udp_worker.start()
  # ...
  if self.udp_worker.isRunning():
      self.udp_worker.stop()
  ```
- Why this is P1: Contract violation. UI pages own and directly invoke `UdpWorker` lifecycle methods. All worker orchestration should route through `Handler`.
- Suggested direction: Move `UdpWorker` ownership and control to `logic/handler.py`.

### [P1-02] UI Mutating DataStore Directly
- File: `ui/main_window.py:220-237`, `ui/page_record.py:826`
- Evidence:
  ```python
  self.data_store.update_udp_health(health)
  self.data_store.save_settings(config)
  self.store.refresh_database(force=True)
  ```
- Why this is P1: UI is directly mutating shared state in `DataStore` instead of routing through `Handler`, violating the documented MVC boundary.
- Suggested direction: Expose action methods in `Handler` to execute these state changes.

### [P1-03] UI Reading DataStore Directly
- File: `ui/page_record.py:424` (and multiple other UI files)
- Evidence:
  ```python
  buf = self.store.get_live_buffer_snapshot()
  samples = self.store.get_samples_for_spell(spell)
  ```
- Why this is P1: UI classes fetch data directly from `DataStore` bypassing `Handler` orchestration. While reads are less dangerous than writes, this creates coupling the architecture explicitly prohibits.
- Suggested direction: Pass read-only data through Qt signals, or explicitly document read-only DataStore access as permitted.

### [P1-04] Incomplete Terminal Signal Emission in ModelUploader
- File: `logic/model_uploader.py:78`
- Evidence:
  ```python
  finally:
      if self._serial and self._serial.is_open:
          self._serial.close()
      self._serial = None
      self._is_running = False
      self._cancel_requested = False
      # No sig_finished.emit() here
  ```
- Why this is P1: The `finally` block handles cleanup but doesn't emit `sig_finished` on all exit paths. A `BaseException` or cancellation can leave the UI without a terminal signal.
- Suggested direction: Move `sig_finished.emit` to the `finally` block.

### [P1-05] Unbounded Augmentation Ratio (Up to 1000×)
- File: `logic/tensorflow/encoder_pipeline.py:222`, `logic/tensorflow/pipeline.py:696`
- Evidence:
  ```python
  shortfall = target_count - count
  for _ in range(shortfall):
      base_idx = int(aug_rng.integers(0, count))
      aug_sample = _augment_window(base_samples[base_idx], aug_rng)
  ```
- Why this is P1: If a class has 1 sample, augmentation reaches 1000× without ceiling or warning. Augmented data massively dominates over real signal diversity, leading to overfitting.
- Suggested direction: Introduce `MAX_AUGMENT_RATIO` (e.g. 50×) and warn when exceeded.

### [P1-06] Per-Class Validation Coverage Gaps Not Warned
- File: `logic/tensorflow/pipeline.py:326`
- Evidence:
  ```python
  if n_train == 0:
      for rows in shuffled:
          train_file_rows.append((class_index, rows))
  if not val_file_rows:
      return train_file_rows, None
  ```
- Why this is P1: If Class A has 5 files and Class B has 1 file, `val_file_rows` is non-empty (has Class A data), so the fallback is bypassed. Class B is silently omitted from validation entirely — no warning is logged.
- Suggested direction: Check coverage per-class after splitting and log warnings for classes missing from validation.

### [P1-07] Window Size Hardcoded in 3 Disjoint Locations
- File: `logic/data_store.py:45`, `logic/tensorflow/pipeline.py:485`, `assets/firmware/main.cpp.template:112`
- Evidence:
  ```
  data_store.py:      "window_size": 10
  pipeline.py:        window_size: int = 64
  main.cpp.template:  #define WINDOW_SIZE 64
  ```
- Why this is P1: These defaults are hardcoded in disjoint layers. Changing one without the others causes silent shape mismatches — near-zero recall despite good training accuracy, the exact symptom documented in project history.
- Suggested direction: Auto-generate or import `WINDOW_SIZE` from a single source of truth.

### [P1-08] Hardware Disconnect Hangs Recording State
- File: `logic/recorder.py:202`
- Evidence:
  ```python
  def _drain_rows_once(self) -> None:
      if not self._is_recording or self._writer is None:
          return
      try:
          row = self._row_queue.get_nowait()
  ```
- Why this is P1: If hardware disconnects mid-recording, no new rows arrive. The worker stays stuck in `_is_recording = True` with the file open indefinitely. `PageRecord` doesn't listen to `sig_connection_state_updated` to auto-stop the recorder.
- Suggested direction: Connect connection-lost signals to `DataRecorder.stop_recording()` to finalize the file and revert UI state.

### [P1-09] Missing PageStatistics Contract
- File: `docs/06_CONTRACTS/UI_CONTRACTS.md:15`
- Evidence:
  ```markdown
  ## Pages Covered
  - PageStatistics
  ```
- Why this is P1: Contract lists `PageStatistics`, but `ui/page_statistics.py` does not exist in the codebase. Contract drift confuses future maintainers.
- Suggested direction: Remove `PageStatistics` from the contract or restore the missing file.

### [P1-10] Missing Accessibility Implementation in Wand3DWidget
- File: `ui/wand_3d_widget.py:194`
- Evidence:
  ```python
  self.btn_reset = QPushButton("⌂ HOME")
  self.btn_reset.setFixedSize(70, 24)
  self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
  ```
- Why this is P1: Coding standard requires `_configure_accessibility` exists and is called for every interactive page. `Wand3DWidget` has interactive buttons but lacks this method entirely.
- Suggested direction: Add `_configure_accessibility()` with accessible names for interactive elements.

---

## P2 Findings

| # | File | Line | Description |
|---|---|---|---|
| P2-01 | `logic/flash_worker.py`, `logic/model_uploader.py`, `logic/locale_manager.py`, `ui/mac_shell.py` | Various | Custom signals missing `sig_` prefix (`log_msg`, `status_msg`, `language_changed`, `nav_requested`) — violates `CODING_STANDARD.md` |
| P2-02 | `ui/page_primitive_collect.py:302`, `logic/handler.py:399` | 302, 399 | Signal wiring outside `_init_signals()` — `btn_train_encoder.clicked.connect(...)` in `_build_train_panel`, `finished.connect(...)` in `on_serial_disconnect` |
| P2-03 | `ui/page_record.py:311`, `ui/palettes.py:50`, `ui/color_utils.py:49` | Various | Hardcoded hex color literals (e.g. `#E5E5EA`) outside `ui/tokens.py`, bypassing design system |

---

## Verified OK

### Phase 0 — Inventory
- ✅ No `QtWidgets` imports found anywhere in `/logic` directory — architectural boundary at import level is strictly maintained.
- ✅ All dependencies in `requirements.txt` match actual imports in `/logic` and `/ui`. No unused or missing deps found.

### Phase 1 — Architecture
- ✅ MVC import boundary (`/logic` → no QtWidgets) is clean.

### Phase 2 — Threading
- ✅ **Serial port ownership lock** (`_port_owner`, `_can_use_port`, `_set_port_owner` in `handler.py`): safely acquired and released. On connection failures or stopped threads, `_set_port_owner(None)` is correctly called.
- ✅ **Stop blocking in ModelUploader, SerialWorker:** These workers correctly implement cooperative stopping without blocking the UI thread.
- ✅ **Double-start guard in DataRecorder and ModelUploader:** These workers correctly check `if not self.isRunning(): self.start()`.

### Phase 3 — ML Pipeline
- ✅ **Embedding normalization:** Both Python (`prototypical_recognizer.py:83`) and C++ (`main.cpp.template:556`) correctly L2-normalize embeddings before cosine similarity. Both handle quantization scale gracefully.
- ✅ **File-level split logic** exists and is the primary path — the fallback (P0-02) only triggers when a class has too few files.

### Phase 6 — Test Coverage
- ✅ **Malformed frame rejection:** PRESENT (`tests/unit/test_frame_protocol.py`)
- ✅ **Mode/connection guard enforcement:** PRESENT (`tests/integration/test_handler_phase6_guards.py`)
- ✅ **Protected system spell behavior:** PRESENT (`tests/unit/test_data_store.py`, `tests/integration/test_handler_phase6_guards.py`)
- ✅ No tests are skipped, xfail'd, or assert nothing meaningful.

### Phase 7 — Firmware
- ✅ **STEM_TFLM_ARENA_BYTES:** Arena is 96KB. Model uses ~44K params → ~44KB INT8 weights. ~52KB margin for activations — adequate for 64-sample window.
- ✅ **MicroMutableOpResolver:** Op list covers all ops emitted by the Keras architecture (Conv1D→Conv2D, GlobalAveragePooling→Mean, L2NormalizeLayer→L2Normalization).
- ✅ **INT8 quantization consistency:** Both `pipeline.py` and `encoder_trainer.py` set `inference_input_type`/`inference_output_type` to `tf.int8`. C++ template mirrors with `in_scale`/`in_zp` and `out_scale`/`out_zp` arithmetic.

### Phase 8 — Security
- ✅ **Flash worker** (`flash_worker.py`): `esptool` is called via Python API (`esptool.main(args)`), not shell-interpolated. The argument list itself is safe (fixed structure). Path traversal on `bin_path` is a separate finding (P0-13).

---

## Could Not Verify

| Item | Why | Human Action Required |
|---|---|---|
| On-device inference accuracy with current preprocessing | Requires physical ESP32 + trained model | Flash firmware, run live gesture recognition, compare accuracy to training metrics |
| Actual model size vs arena at runtime | Requires running full training pipeline | Train a model, check TFLite file size, flash and monitor `ESP_LOGI` arena usage |
| Serial frame timing under load | Requires USB-connected ESP32 at 50Hz | Monitor serial with logic analyzer, confirm no frame drops or buffer overflows |
| Atomic-write-with-backup in firmware_main_generator | Requires triggering a render exception mid-write | Force a Jinja2 template error during `_write_atomic_with_backup` and verify original `main.cpp` is unchanged |
| Dataset export functionality | No export tests exist (Phase 6 PARTIAL finding) | Manually test CSV export with various dataset sizes |
| Thread-safe signal flow under real concurrency | No integration tests verify actual cross-thread signal safety | Run the app under stress (rapid connect/disconnect, concurrent recording + DB refresh) |

---

## Test Coverage Gaps (Phase 6 Detail)

| Required Check | Status | Test File |
|---|---|---|
| Malformed frame rejection | ✅ PRESENT | `tests/unit/test_frame_protocol.py` |
| Mode/connection guard enforcement | ✅ PRESENT | `tests/integration/test_handler_phase6_guards.py` |
| Protected system spell behavior | ✅ PRESENT | `tests/unit/test_data_store.py`, `tests/integration/test_handler_phase6_guards.py` |
| Dataset save/delete/export reliability | ⚠️ PARTIAL | `tests/unit/test_data_store.py` (save+delete only, export missing) |
| Thread-safe signal flow | ❌ MISSING | No tests |

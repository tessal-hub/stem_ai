# Constructing the ESP-IDF project (MPU6050 + STEM AI)

Status: Active  
Language: English  
Owner: Hardware / Firmware Maintainers  
Last Updated: 2026-05-13

This page describes the **on-disk construction** of an ESP-IDF project that can feed the STEM AI desktop app: same partition layout, serial expectations, and (for inference) the same **TFLite Micro** + **gesture_model.cc** contract.

## 1. Target platform

- **Chip:** ESP32-S3 (matches `logic/flash_worker.py`: `esptool --chip esp32s3`, flash at **`0x10000`**).  
- **Sensor:** MPU6050 on **I2C** (default pins in app template: **SDA GPIO8**, **SCL GPIO9**, **400 kHz** — see `assets/firmware/main.cpp.template`).  
- **Framework:** ESP-IDF **5.x** recommended (align with `espressif/esp-tflite-micro` in `idf_component.yml`).

## 2. Repository reference tree (`mpu6050/`)

```
mpu6050/
  CMakeLists.txt          # project(mpu6050)
  partitions.csv          # factory app @ 0x10000 (must match flash worker)
  main/
    CMakeLists.txt        # idf_component_register(SRCS "main.cpp" "gesture_model.cc" ...)
    idf_component.yml     # dependency: espressif/esp-tflite-micro
    main.cpp              # hand-maintained demo (spell enum, window, etc.)
    gesture_model.cc      # generated / copied from model export
```

### 2.1 Root `CMakeLists.txt`

Minimal pattern (already in `mpu6050/CMakeLists.txt`):

- `cmake_minimum_required(VERSION 3.16)`  
- `include($ENV{IDF_PATH}/tools/cmake/project.cmake)`  
- `project(<your_name>)`

### 2.2 `partitions.csv`

The desktop app’s flasher writes the application image at **`0x10000`**. Your partition table must reserve a **factory** (or equivalent **app**) partition starting at that offset.

Reference (`mpu6050/partitions.csv`):

```text
factory,  app,  factory, 0x10000,  0x300000,
```

If you change the app offset, you must change **`FlashWorker._build_esptool_cmd`** in the Python project — not recommended.

### 2.3 `main/CMakeLists.txt`

Register **both** sources the app syncs:

- `main.cpp` — either maintained by you or **regenerated** from `assets/firmware/main.cpp.template` when you run a model build with “CC / both” output (see `logic/firmware_main_generator.py`).  
- `gesture_model.cc` — copied from the model build pipeline (`sync_firmware_sources`).

Example (matches `mpu6050/main/CMakeLists.txt`):

```cmake
idf_component_register(SRCS "main.cpp" "gesture_model.cc"
                       INCLUDE_DIRS ".")
```

### 2.4 `main/idf_component.yml`

Pull **TensorFlow Lite for Microcontrollers** from the Espressif component registry (see `mpu6050/main/idf_component.yml`):

```yaml
dependencies:
  idf:
    version: '>=4.1.0'
  espressif/esp-tflite-micro: '*'
```

Run `idf.py reconfigure` (or build) so the component manager fetches dependencies.

### 2.5 `gesture_model.cc`

- Produced by the STEM AI **model build** path as a **C array** embedding the quantized model (`g_model`, schema-compatible with TFLM).  
- The app copies this file into your IDF **`main/`** directory when **IDF main directory** is set and the build mode includes **CC** (see `sync_firmware_sources` in `logic/firmware_main_generator.py`).

### 2.6 `main.cpp` — two integration styles

**A. App-driven (recommended for full integration)**  

- Start from **`assets/firmware/main.cpp.template`** in this repo.  
- Do **not** hand-edit the generated sections between the `{{...}}` placeholders; the app overwrites **`main.cpp`** when syncing after a successful build with matching spell names.  
- You **may** add board-specific `CMakeLists.txt` compile definitions (e.g. `-DSTEM_I2C_SDA_PIN=...`) if your wiring differs; the template supports `STEM_I2C_*` overrides.

**B. Reference-only (`mpu6050/main/main.cpp`)**  

- Useful to verify **I2C**, **MPU6050 wake/read**, and **TFLM interpreter** on hardware.  
- Uses a **fixed** `SpellId` enum and window size that may **not** match your dataset or the template (`WINDOW_SIZE` 40 vs 64). Before relying on the app’s training pipeline, align window length, scales, and output class count with the trained model.

## 3. Serial protocol contract (recording)

For **data collection** firmware, the device must stream **newline-terminated CSV** over the UART used for the USB-serial bridge:

```text
aX,aY,aZ,gX,gY,gZ\n
```

Six numeric fields per line. This matches [ESP32_PROTOCOL.md](../03_HARDWARE_TINYML/ESP32_PROTOCOL.md) and the serial parser in the app.

**Important:** ESP-IDF log lines (`I (…) …`) must not be mistaken for data. Either:

- print only CSV on the UART used by the app, or  
- tag log lines distinctly and ensure the PC parser drops non-CSV lines (the app already filters invalid rows).

Inference-only firmware may use a different line format for predictions; see internal `skill.md` / wand contract for **infer** mode strings if you extend firmware.

## 4. Build commands (outside the Qt app, one-time per iteration)

From the IDF project directory (e.g. `mpu6050/`):

```bash
idf.py set-target esp32s3
idf.py build
```

Artifacts of interest:

- `build/<project>.bin` (merged image) or partition-specific binaries depending on your workflow.

The STEM AI app does **not** invoke `idf.py` today; it flashes **prebuilt** binaries from:

- `assets/firmware/collect.bin` — **data** / recording firmware  
- `assets/firmware/inference.bin` — **inference** firmware  

Copy the correct built binary to those paths (or automate copy in CI). Names and paths are fixed in `logic/handler.py` (`handle_firmware_flash`).

## 5. Flash parameters (must match app)

The desktop app uses:

- **Port:** user-selected COM / tty  
- **Baud:** `115200` for flash (see `FlashWorker`)  
- **Address:** `0x10000`  
- **Chip:** `esp32s3`

Your `sdkconfig` flash mode/frequency should be compatible with `dio` / `80m` as passed to esptool in `FlashWorker` (adjust only if you change the flasher code in lockstep).

## 6. Checklist before trusting “full integration”

- [ ] `partitions.csv` factory app at **0x10000**.  
- [ ] **Data** firmware emits **6-field CSV** at the baud rate configured in app settings (default **115200**).  
- [ ] **Inference** firmware: `gesture_model.cc` matches the last trained model; `main.cpp` regenerated from template with same spell list order as training labels.  
- [ ] `main/CMakeLists.txt` lists `gesture_model.cc`.  
- [ ] `idf.py build` succeeds; binaries copied to `assets/firmware/*.bin` for in-app flash buttons.  
- [ ] App **Settings → IDF main directory** points to the **`main`** folder of this IDF project (parent must contain root `CMakeLists.txt`).

## 7. Optional: VS Code / Dev Containers

The reference tree includes `.vscode/` and `.devcontainer/` for ESP-IDF development. They are **editor convenience** only; the STEM AI app does not require them.

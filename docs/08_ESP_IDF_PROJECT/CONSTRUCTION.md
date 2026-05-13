# Constructing the ESP-IDF project (MPU6050 + STEM AI)

Status: Active | EN | firmware maintainers | 2026-05-13

On-disk ESP-IDF project for STEM AI desktop: partitions + serial match; inference uses same **TFLite Micro** + **`gesture_model.cc`** contract.

## 1. Target platform

- **Chip:** ESP32-S3 (`logic/flash_worker.py`: `esptool --chip esp32s3`, flash **`0x10000`**).  
- **Sensor:** MPU6050 **I2C** (template defaults **SDA GPIO8**, **SCL GPIO9**, **400 kHz** — `assets/firmware/main.cpp.template`).  
- **Framework:** ESP-IDF **5.x** (`espressif/esp-tflite-micro` in `idf_component.yml`).

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

Pattern in `mpu6050/CMakeLists.txt`:

- `cmake_minimum_required(VERSION 3.16)`  
- `include($ENV{IDF_PATH}/tools/cmake/project.cmake)`  
- `project(<your_name>)`

### 2.2 `partitions.csv`

Desktop flasher writes app at **`0x10000`**. Partition table: **factory** / **app** starts there.

Reference (`mpu6050/partitions.csv`):

```text
factory,  app,  factory, 0x10000,  0x300000,
```

App offset change → edit **`FlashWorker._build_esptool_cmd`** — avoid.

### 2.3 `main/CMakeLists.txt`

Register both sources app syncs:

- `main.cpp` — either maintained by you or **regenerated** from `assets/firmware/main.cpp.template` when you run a model build with “CC / both” output (see `logic/firmware_main_generator.py`).  
- `gesture_model.cc` — copied from the model build pipeline (`sync_firmware_sources`).

Example (matches `mpu6050/main/CMakeLists.txt`):

```cmake
idf_component_register(SRCS "main.cpp" "gesture_model.cc"
                       INCLUDE_DIRS ".")
```

### 2.4 `main/idf_component.yml`

Pull **TensorFlow Lite for Microcontrollers** from Espressif registry (`mpu6050/main/idf_component.yml`):

```yaml
dependencies:
  idf:
    version: '>=4.1.0'
  espressif/esp-tflite-micro: '*'
```

Run `idf.py reconfigure` (or build) → component manager fetches deps.

### 2.5 `gesture_model.cc`

- STEM AI **model build** → **C array** w/ quantized model (`g_model`, TFLM schema).  
- App copies into IDF **`main/`** when **IDF main directory** set + build includes **CC** (`sync_firmware_sources` in `logic/firmware_main_generator.py`).

### 2.6 `main.cpp` — two integration styles

**A. App-driven (recommended for full integration)**  

- Start from **`assets/firmware/main.cpp.template`** in this repo.  
- Do **not** hand-edit `{{...}}` sections; app overwrites **`main.cpp`** after successful sync build w/ matching spell names.  
- You **may** add board-specific `CMakeLists.txt` compile definitions (e.g. `-DSTEM_I2C_SDA_PIN=...`) if your wiring differs; the template supports `STEM_I2C_*` overrides.

**B. Reference-only (`mpu6050/main/main.cpp`)**  

- Useful to verify **I2C**, **MPU6050 wake/read**, and **TFLM interpreter** on hardware.  
- **Fixed** `SpellId` + window may **not** match dataset / template (`WINDOW_SIZE` 40 vs 64). Align window, scales, class count w/ trained model before trusting app training path.

## 3. Serial protocol contract (recording)

**Data collection** firmware: stream **newline-terminated CSV** on USB-serial UART:

```text
aX,aY,aZ,gX,gY,gZ\n
```

Six fields / line. Same as [ESP32_PROTOCOL.md](../03_HARDWARE_TINYML/ESP32_PROTOCOL.md) + app serial parser.

**Important:** ESP-IDF logs (`I (…) …`) ≠ data. Either:

- print only CSV on the UART used by the app, or  
- tag logs; PC parser drops non-CSV (app filters bad rows).

Inference-only firmware: different prediction line format OK; see `skill.md` / wand contract for **infer** strings if extending firmware.

## 4. Build commands (outside the Qt app, one-time per iteration)

From IDF project dir (e.g. `mpu6050/`):

```bash
idf.py set-target esp32s3
idf.py build
```

Artifacts:

- `build/<project>.bin` (merged image) or partition-specific binaries depending on your workflow.

STEM AI app does **not** run `idf.py`; flashes **prebuilt** binaries:

- `assets/firmware/collect.bin` — **data** / recording firmware  
- `assets/firmware/inference.bin` — **inference** firmware  

Copy built binary → those paths (or CI). Paths fixed in `logic/handler.py` (`handle_firmware_flash`).

## 5. Flash parameters (must match app)

Desktop app uses:

- **Port:** user-selected COM / tty  
- **Baud:** `115200` for flash (see `FlashWorker`)  
- **Address:** `0x10000`  
- **Chip:** `esp32s3`

`sdkconfig` flash mode/frequency: match `dio` / `80m` esptool args in `FlashWorker` (change flasher code in lockstep if adjusting).

## 6. Checklist before trusting “full integration”

- [ ] `partitions.csv` factory app at **0x10000**.  
- [ ] **Data** firmware emits **6-field CSV** at the baud rate configured in app settings (default **115200**).  
- [ ] **Inference** firmware: `gesture_model.cc` matches the last trained model; `main.cpp` regenerated from template with same spell list order as training labels.  
- [ ] `main/CMakeLists.txt` lists `gesture_model.cc`.  
- [ ] `idf.py build` succeeds; binaries copied to `assets/firmware/*.bin` for in-app flash buttons.  
- [ ] App **Settings → IDF main directory** points to the **`main`** folder of this IDF project (parent must contain root `CMakeLists.txt`).

## 7. Optional: VS Code / Dev Containers

Reference tree has `.vscode/` + `.devcontainer/` for ESP-IDF — **editor convenience** only; STEM AI app does not need them.

# ESP-IDF project integration (STEM Spell Book)

Status: Active  
Language: English  
Owner: Hardware / Firmware Maintainers  
Last Updated: 2026-05-13

This section documents how to **construct and maintain** the ESP-IDF firmware tree so it matches what **STEM AI** expects: serial protocol, flash layout, model sync, and settings in the desktop app.

## Canonical pages

| Document | Purpose |
|----------|---------|
| [CONSTRUCTION.md](./CONSTRUCTION.md) | Scaffold an IDF project (CMake, `main/`, MPU6050 + TFLite Micro, partitions, build output). |
| [WORKFLOW_WITH_STEM_APP.md](./WORKFLOW_WITH_STEM_APP.md) | End-to-end workflow using **only** the app + this repo (IDF path, model build → `gesture_model.cc` / `main.cpp`, flash `collect.bin` / `inference.bin`). |

## Reference firmware in this repo

The checked-in reference project lives at repository root:

- **`mpu6050/`** — ESP-IDF CMake project targeting **ESP32-S3** with **MPU6050** on I2C and **TensorFlow Lite for Microcontrollers** (`espressif/esp-tflite-micro` via `main/idf_component.yml`).

Use it as a **known-good layout** when creating a new board-specific tree. Production integration with the app’s **auto-generated** spell classes uses `assets/firmware/main.cpp.template` (see [CONSTRUCTION.md](./CONSTRUCTION.md)).

## Related canonical docs

- [../03_HARDWARE_TINYML/ESP32_PROTOCOL.md](../03_HARDWARE_TINYML/ESP32_PROTOCOL.md) — UART CSV frame shape for **record** mode.  
- [../03_HARDWARE_TINYML/MODEL_PIPELINE.md](../03_HARDWARE_TINYML/MODEL_PIPELINE.md) — training → TFLite → embedded C.  
- [../01_ARCHITECTURE/DATA_FLOW.md](../01_ARCHITECTURE/DATA_FLOW.md) — serial → DataStore path in the app.

## Rules

1. Treat **`mpu6050/`** as reference implementation, not a second source of truth for protocol strings.  
2. Prefer **one** IDF project root per hardware SKU; point the app’s **IDF main directory** setting at that project’s `main/` folder.  
3. When changing window length, scales, or op resolver list, keep **training preprocessing** and **firmware** aligned (see MODEL_PIPELINE).

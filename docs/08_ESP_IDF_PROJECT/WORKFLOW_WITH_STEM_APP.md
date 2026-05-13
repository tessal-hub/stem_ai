# Workflow: ESP-IDF + STEM AI without leaving the app loop

Status: Active  
Language: English  
Owner: Hardware / Firmware Maintainers  
Last Updated: 2026-05-13

Goal: complete the **firmware side** of the loop using the **STEM Spell Book** desktop app and this repository, minimizing ad-hoc steps outside documented build commands.

**Reality check:** The app today flashes **prebuilt** `.bin` files and runs **training / export** on the PC. You still run **`idf.py build`** (or your CI) to produce those binaries from the IDF project. Everything else — dataset, training trigger, model export, copying `gesture_model.cc` / `main.cpp` into your IDF `main/` — can be driven from the app once paths and assets are set up as below.

## Phase 0 — One-time repository setup

1. **ESP-IDF environment** installed on the machine (toolchain + `IDF_PATH`).  
2. **Python venv** for STEM AI with `requirements.txt` (includes `esptool`, `pyserial`, etc.).  
3. **IDF project** created or copied (see [CONSTRUCTION.md](./CONSTRUCTION.md)); recommend starting from **`mpu6050/`** layout.

## Phase 1 — Wire the app to your IDF `main/` folder

1. Open **Settings** in STEM AI.  
2. Set **IDF main directory** to the **absolute path of the `main` folder** inside your ESP-IDF project (the folder that contains `main.cpp` and `gesture_model.cc`).  
3. **Save settings**.

Validation rules (enforced in the UI):

- Path must exist and be a directory named **`main`**.  
- Parent directory must contain **`CMakeLists.txt`** (IDF project root).

After this, a successful **model build** with CC output will:

- Copy **`gesture_model.cc`** into that `main/` folder.  
- Regenerate **`main.cpp`** from **`assets/firmware/main.cpp.template`** using your trained spell class list (`logic/firmware_main_generator.py`).

You can still use **Open IDF project** in Settings to jump the IDE to the project root.

## Phase 2 — Data firmware (recording / dataset)

**Purpose:** ESP32 streams `aX,aY,aZ,gX,gY,gZ` CSV lines so the **Record** page and **DataStore** can ingest samples.

1. Implement or reuse firmware that **only** streams CSV (see [ESP32_PROTOCOL.md](../03_HARDWARE_TINYML/ESP32_PROTOCOL.md)).  
2. `idf.py build` in the IDF project.  
3. Copy the built application image to:

   **`stem_ai/assets/firmware/collect.bin`**

   (Path is relative to the STEM AI project root; see `logic/handler.py` → `handle_firmware_flash("data")`.)

4. In the app: connect the wand **serial port**, then **Settings → Install data firmware** (flashes `collect.bin` at `0x10000`).

**Inside the app after flash:** use **Wand** to connect serial, **Record** to capture spells, **Statistics** / train flows as documented elsewhere.

## Phase 3 — Train and export model (PC, inside app)

1. Collect enough CSV per spell under `dataset/`.  
2. Run training / model build from the **Wand** / **Statistics** UI (handlers invoke build workers).  
3. Choose a build mode that includes **CC** (or “both”) if you want automatic **firmware source sync** to the IDF `main/` path from Phase 1.

On success, check the wand terminal for lines like:

- `Synced gesture_model.cc: …`  
- `Generated main.cpp (N classes): …`

If **IDF main directory** is empty, the app skips sync and logs a skip message — fix the setting and rebuild.

## Phase 4 — Inference firmware

**Purpose:** On-device **TFLite Micro** inference using the synced `gesture_model.cc` and generated `main.cpp`.

1. After Phase 3, run **`idf.py build`** in the IDF project (ensures `main.cpp` + `gesture_model.cc` compile together).  
2. Copy the resulting application binary to:

   **`stem_ai/assets/firmware/inference.bin`**

3. In the app: **Settings → Install AI engine** (flashes `inference.bin`).

## Phase 5 — Operate without bouncing between unknown tools

| Task | Where in app |
|------|----------------|
| Choose COM / baud | **Wand** (connection) |
| Persist sensor / window / ML / theme / language | **Settings** |
| Record samples | **Record** |
| Train / build / sync CC | **Wand** / **Statistics** (per UI wiring) |
| Flash data vs AI firmware | **Settings** firmware section |
| Open IDF project in editor | **Settings** (Open IDF project) |

**Single path rule:** keep **one** canonical IDF project directory on disk and always point **IDF main directory** at its `main/` folder. Avoid duplicate copies unless you automate copy-back into `assets/firmware`.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Flash fails “esptool not found” | Run STEM AI from the venv where `esptool` is installed (`pip install esptool`). |
| Flash fails “binary not found” | `collect.bin` / `inference.bin` missing under `assets/firmware/`. |
| Model sync skipped | **IDF main directory** unset or invalid. |
| Build OK on device, app shows garbage | CSV format or baud mismatch; log spam on UART. |
| Inference always UNKNOWN | Class count / order mismatch vs training; window size vs model input; quantization scale drift. |

## Future automation (non-normative)

Possible improvements (not implemented in code by this doc): invoke `idf.py build` from a worker, copy `build/flasher_args.json` outputs into `assets/firmware/`, or use **esp-idf-dfu** / USB OTG. Any such change must stay aligned with `FlashWorker` flash address and chip flags.

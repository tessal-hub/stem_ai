# Spell Sound Effects & RGB LED Color Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement per-spell sound effects (played on PC on spell recognition) and RGB LED colors (stored in NVS and driven by ESP32 PWM on spell recognition).

**Architecture:** 
- Presentation / Metadata: `SpellConfigStore` in `logic/spell_config_store.py` manages `app_data/spell_config.json`.
- Audio: `SoundPlayer` in `logic/sound_player.py` using `PyQt6.QtMultimedia` (`QMediaPlayer` + `QAudioOutput`) with 200ms debounce.
- UI: `SpellCardWidget` in `ui/spell_card_widget.py` (color dot + sound icon), `SoundSelectorDialog` in `ui/sound_selector_dialog.py`, dynamic pulse color in `ui/page_home.py`.
- TinyML / NVS: `logic/tensorflow/nvs_builder.py` extended to pack RGB bytes (72 bytes per blob, version 2 NVS key).
- Hardware / Firmware: GPIO 25 (R), 26 (G), 27 (B) LEDC PWM at 5kHz 8-bit in `mpu6050/main/main.cpp` & `assets/firmware/main.cpp.template`.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `config.py` | Add `SOUNDS_PRESET_DIR` and `SOUNDS_USER_DIR` | 1 |
| `requirements.txt` | Add `PyQt6-Qt6-Multimedia` | 1 |
| `logic/spell_config_store.py` | Per-spell color, sound, and volume persistence | 2 |
| `tests/unit/test_spell_config_store.py` | Unit tests for `SpellConfigStore` | 2 |
| `assets/sounds/*.mp3` | Preset MP3 sound effects (12 clips) | 3 |
| `logic/sound_player.py` | Audio playback engine with debounce and preview | 4 |
| `tests/unit/test_sound_player.py` | Unit tests for `SoundPlayer` | 4 |
| `logic/tensorflow/nvs_builder.py` | Pack RGB bytes (v2 blob) into `labels.bin` | 5 |
| `tests/unit/test_nvs_builder_rgb.py` | Unit tests for NVS RGB packing | 5 |
| `logic/ui_strings.json` | EN/VI i18n strings for color/sound UI | 6 |
| `ui/sound_selector_dialog.py` | Sound selector modal dialog (Presets + Custom) | 7 |
| `ui/spell_card_widget.py` | Custom QListWidget row widget with color dot & sound icon | 8 |
| `ui/page_record.py` | Wire `SpellCardWidget`, color picker, sound dialog | 9 |
| `logic/handler.py` | Integrate `SpellConfigStore` + `SoundPlayer`, prediction audio, NVS color flow | 10 |
| `ui/page_home.py` | Dynamic hero pulse matching spell color | 11 |
| `main.py` | App bootstrap with `SpellConfigStore` & `SoundPlayer` | 12 |
| `mpu6050/main/main.cpp` | ESP32 LEDC PWM setup & `OnSpellDetected` RGB handling | 13 |
| `assets/firmware/main.cpp.template` | Firmware template RGB placeholders | 13 |
| `logic/firmware_main_generator.py` | Render firmware RGB blocks | 13 |
| `tests/integration/test_spell_sound_rgb_flow.py` | End-to-end integration test | 14 |

---

## Task 1: Configuration & Dependencies

**Files:**
- Modify: `config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Update config.py with sound directories**
Add `SOUNDS_PRESET_DIR = WORKSPACE_ROOT / "assets" / "sounds"` and `SOUNDS_USER_DIR = USER_DATA_DIR / "sounds"` with directory creation in `ensure_data_dir()`.

- [ ] **Step 2: Add PyQt6-Qt6-Multimedia to requirements.txt**
Ensure multimedia support is included in dependencies.

- [ ] **Step 3: Verification**
Verify directory constants resolve properly via Python snippet.

---

## Task 2: SpellConfigStore Data Layer

**Files:**
- Create: `logic/spell_config_store.py`
- Create: `tests/unit/test_spell_config_store.py`

- [ ] **Step 1: Write test for SpellConfigStore**
Cover:
- Default values for unknown spells (`[255, 255, 255]`, `None`, `1.0`)
- `set_spell_color`, `set_spell_sound`, `set_spell_volume`
- Persistence to `app_data/spell_config.json`
- `get_all_colors()`
- `remove_spell_config()`
- Signal emission on mutation

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_spell_config_store.py -v`

- [ ] **Step 3: Implement SpellConfigStore**
Implement `SpellConfigStore(QObject)` according to the design spec.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_spell_config_store.py -v`

---

## Task 3: Preset Sound Assets

**Files:**
- Create: `assets/sounds/*.mp3` (12 preset files: `whoosh.mp3`, `zap.mp3`, `explosion.mp3`, `chime.mp3`, `thunder.mp3`, `shield.mp3`, `heal.mp3`, `ice.mp3`, `dark.mp3`, `wind.mp3`, `beam.mp3`, `summon.mp3`)

- [ ] **Step 1: Generate valid MP3 audio assets**
Create/bundle lightweight, valid MP3 sound files for all 12 presets in `assets/sounds/`.

- [ ] **Step 2: Verify asset presence**
Verify all 12 files exist and have valid headers.

---

## Task 4: SoundPlayer Audio Engine

**Files:**
- Create: `logic/sound_player.py`
- Create: `tests/unit/test_sound_player.py`

- [ ] **Step 1: Write test for SoundPlayer**
Cover:
- URI resolution for `preset:<name>` and `custom:<filename>`
- Debounce window (200ms suppression of duplicate requests)
- Graceful handling of missing files / disabled sound
- Volume adjustment

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_sound_player.py -v`

- [ ] **Step 3: Implement SoundPlayer**
Use `QMediaPlayer` + `QAudioOutput`, handle `play()`, `preview()`, `stop()`, and debounce timer.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_sound_player.py -v`

---

## Task 5: NVS Builder RGB Extension (labels.bin)

**Files:**
- Modify: `logic/tensorflow/nvs_builder.py`
- Create: `tests/unit/test_nvs_builder_rgb.py`

- [ ] **Step 1: Write test for NVS builder RGB packing**
Cover:
- Binary blob packing format: 64B centroid + 4B thresh + 1B is_spell + 3B RGB (72 bytes total)
- `version` key = 2
- Fallback default (255, 255, 255) when no color is provided

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_nvs_builder_rgb.py -v`

- [ ] **Step 3: Implement RGB packing in nvs_builder.py**
Update `build_config_bin()` to accept `colors` dictionary and pack 3 extra bytes per gesture.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_nvs_builder_rgb.py -v`

---

## Task 6: Localization (i18n)

**Files:**
- Modify: `logic/ui_strings.json`

- [ ] **Step 1: Add EN & VI strings**
Add translation keys for:
- `sound_selector_title`, `tab_presets`, `tab_custom`, `btn_import_sound`
- `btn_preview`, `no_sound`, `select_color_title`
- Preset display names

- [ ] **Step 2: Verification**
Verify JSON syntax and key presence in both languages.

---

## Task 7: SoundSelectorDialog

**Files:**
- Create: `ui/sound_selector_dialog.py`
- Create: `tests/unit/test_sound_selector_dialog.py`

- [ ] **Step 1: Write unit test for SoundSelectorDialog**
Cover:
- Dialog loading preset list
- Custom sound import copying to `user_data/sounds/`
- Selection return value

- [ ] **Step 2: Implement SoundSelectorDialog**
Two-tab dialog with Presets and Custom tabs, preview trigger, and import button.

- [ ] **Step 3: Run test to verify it passes**
Run: `pytest tests/unit/test_sound_selector_dialog.py -v`

---

## Task 8: SpellCardWidget for List Display

**Files:**
- Create: `ui/spell_card_widget.py`
- Create: `tests/unit/test_spell_card_widget.py`

- [ ] **Step 1: Write unit test for SpellCardWidget**
Cover:
- Rendering color dot with current RGB
- Speaker icon state (muted vs active)
- Emitting `sig_color_clicked` and `sig_sound_clicked`

- [ ] **Step 2: Implement SpellCardWidget**
Custom `QWidget` containing color circle label, spell name label, and speaker icon button.

- [ ] **Step 3: Run test to verify it passes**
Run: `pytest tests/unit/test_spell_card_widget.py -v`

---

## Task 9: Recording Page Integration

**Files:**
- Modify: `ui/page_record.py`

- [ ] **Step 1: Integrate SpellCardWidget into spell_list**
Replace plain `QListWidgetItem` text with `setItemWidget` using `SpellCardWidget`.

- [ ] **Step 2: Wire color picker & sound selector slots**
- Connect `sig_color_clicked` → `QColorDialog.getColor` → `SpellConfigStore.set_spell_color`
- Connect `sig_sound_clicked` → `SoundSelectorDialog` → `SpellConfigStore.set_spell_sound`
- Connect `SpellConfigStore.sig_spell_config_changed` → refresh item widget

- [ ] **Step 3: Verification with existing tests**
Run: `pytest tests/unit/ -k "record" -v`

---

## Task 10: Handler Integration & Audio Trigger

**Files:**
- Modify: `logic/handler.py`

- [ ] **Step 1: Wire SoundPlayer to prediction event**
On `sig_prediction_updated(action, confidence)`:
- If `action` is recognized spell (not STAND BY) and confidence > rejection threshold:
- Look up spell sound from `SpellConfigStore`
- Call `SoundPlayer.play(sound_id)`

- [ ] **Step 2: Pass spell colors to NVS builder during upload**
Pass `spell_config.get_all_colors()` into `NVSBuildWorker` / `build_config_bin`.

- [ ] **Step 3: Cleanup on spell deletion**
Call `spell_config.remove_spell_config(spell_name)` inside `on_spell_deleted`.

---

## Task 11: Home Page Dynamic Glow / Hero Pulse

**Files:**
- Modify: `ui/page_home.py`

- [ ] **Step 1: Apply spell color to recognition hero pulse**
When recognized spell is displayed, use the RGB color from `SpellConfigStore` for the pulse glow animation border/shadow.

---

## Task 12: Main App Bootstrap

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Instantiate SpellConfigStore & SoundPlayer**
Pass instances into `MainWindow` and `Handler`.

---

## Task 13: Firmware RGB LED Driver & Generator

**Files:**
- Modify: `mpu6050/main/main.cpp`
- Modify: `assets/firmware/main.cpp.template`
- Modify: `logic/firmware_main_generator.py`

- [ ] **Step 1: Implement LEDC PWM in mpu6050/main/main.cpp**
- Configure GPIO 25, 26, 27 for LEDC channels 0, 1, 2 (5kHz, 8-bit).
- Parse RGB from NVS labels v2 blob or default to white.
- Drive PWM in `OnSpellDetected(int class_index)`.
- Clear RGB duty on STAND BY.

- [ ] **Step 2: Update firmware_main_generator.py and main.cpp.template**
Add placeholders `{{RGB_PIN_DEFINES}}`, `{{RGB_INIT_BLOCK}}`, `{{RGB_COLOR_TABLE}}` to template and generator.

---

## Task 14: Verification & Integration Tests

**Files:**
- Create: `tests/integration/test_spell_sound_rgb_flow.py`

- [ ] **Step 1: Write and run full integration test**
Test:
- Spell creation → color set → sound set → config saved.
- Prediction signal → sound played + color verified.
- NVS labels generation produces valid 72-byte payload with expected RGB bytes.

- [ ] **Step 2: Run full test suite**
Run: `pytest tests/ -v`
Verify all tests pass without regressions.

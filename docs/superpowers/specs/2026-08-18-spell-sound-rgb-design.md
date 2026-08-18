# Spell Sound Effects & RGB LED Color — Design Spec

**Date:** 2026-08-18
**Status:** Approved
**Approach:** B — Dedicated spell metadata layer

---

## 1. Overview

Add two per-spell properties:

1. **Sound effect** — MP3 played on the PC when ESP32 recognizes a spell during inference mode.
2. **RGB LED color** — displayed on a new hardware RGB LED when the ESP32 recognizes a spell. Color stored on-device in NVS for autonomous operation without PC.

Users configure both from the spell card on the recording page: a color dot (click → color picker) and a sound icon (click → sound selector with presets + custom import). Sound preview available before committing.

---

## 2. Data Layer — SpellConfigStore

### 2.1 Storage

**File:** `app_data/spell_config.json`

```json
{
  "FIREBALL": {
    "color": [255, 60, 0],
    "sound": "preset:explosion",
    "volume": 0.8
  },
  "SHIELD": {
    "color": [0, 120, 255],
    "sound": "custom:my_shield_sound.wav",
    "volume": 1.0
  }
}
```

Spell names normalized via `constants.normalize_spell_name()`.

### 2.2 Class: `SpellConfigStore(QObject)`

**New file:** `logic/spell_config_store.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_spell_config` | `(name: str) → dict` | Returns `{color, sound, volume}` with defaults |
| `set_spell_color` | `(name: str, r: int, g: int, b: int)` | Save + emit signal |
| `set_spell_sound` | `(name: str, sound_id: str)` | Save + emit signal |
| `set_spell_volume` | `(name: str, volume: float)` | Save + emit signal |
| `get_all_colors` | `() → dict[str, tuple[int,int,int]]` | Bulk read for NVS builder |
| `remove_spell_config` | `(name: str)` | Delete entry on spell deletion |

**Signals:**
- `sig_spell_config_changed(str)` — emits spell name on any property change

**Defaults:**
- Color: `[255, 255, 255]` (white)
- Sound: `None` (no sound until user opts in)
- Volume: `1.0`

**Sound ID format:** `"preset:<name>"` or `"custom:<filename>"` — prefix distinguishes source.

Auto-saves on every change (file is <1KB for 20 spells).

---

## 3. Sound System

### 3.1 Preset Sounds

**Directory:** `assets/sounds/`

**Format:** MP3 files, short duration (0.5–2s).

| Preset ID | Description |
|-----------|-------------|
| `whoosh` | Air swoosh |
| `zap` | Electric spark |
| `explosion` | Fire burst |
| `chime` | Crystal bell |
| `thunder` | Rumble crack |
| `shield` | Energy hum |
| `heal` | Soft glow tone |
| `ice` | Frost crackle |
| `dark` | Low ominous pulse |
| `wind` | Gusting breeze |
| `beam` | Laser charge |
| `summon` | Rising mystical tone |

### 3.2 Custom Sounds

**Directory:** `user_data/sounds/`

User imports `.mp3` or `.wav` files via file dialog. App copies file into this directory (not reference external path — maintains portability).

### 3.3 Class: `SoundPlayer(QObject)`

**New file:** `logic/sound_player.py`

- Uses `QMediaPlayer` + `QAudioOutput` from `PyQt6.QtMultimedia`
- `play(sound_id: str, volume: float)` — resolves `preset:X` → `assets/sounds/X.mp3`, `custom:X` → `user_data/sounds/X`
- `preview(sound_id: str, volume: float)` — same as play, used on spell card
- `stop()` — stops current playback
- Caches resolved file paths (not QMediaPlayer instances — QMediaPlayer is reusable)
- **Cooldown:** 200ms debounce — won't re-trigger same sound within window (prevents rapid-fire during noisy predictions)

### 3.4 Dependency

Add `PyQt6-Qt6-Multimedia` to `requirements.txt`.

---

## 4. UI Changes

### 4.1 Spell Card Widget

**New file:** `ui/spell_card_widget.py`

`SpellCardWidget(QWidget)` — replaces plain `QListWidgetItem` text in `page_record.py`.

Layout:
```
[ ● color dot 16×16 ] [ Spell Name (count) ] [ 🔊 sound icon ]
```

- Color dot: rounded `QLabel` with `background-color` matching spell RGB. Click → emits `sig_color_clicked(str)`.
- Sound icon: `QLabel` with speaker icon. Muted icon (🔇) when no sound configured, speaker (🔊) when configured. Click → emits `sig_sound_clicked(str)`.
- `update_config(color: tuple, sound_id: str | None)` — refreshes visuals.

### 4.2 Color Picker

Standard `QColorDialog.getColor()` — built into Qt. No custom widget.

Flow: `sig_color_clicked` → `page_record._on_color_edit(name)` → `QColorDialog` → `spell_config.set_spell_color()`.

### 4.3 Sound Selector Dialog

**New file:** `ui/sound_selector_dialog.py`

`SoundSelectorDialog(QDialog)` — modal dialog with two tabs:

**Presets tab:**
- `QListWidget` — one row per bundled sound
- Each row: sound name + ▶ preview button
- Preview plays via `SoundPlayer.preview()`
- Click to select, double-click to confirm

**Custom tab:**
- `QListWidget` — imported sounds from `user_data/sounds/`
- "Import Sound..." button → `QFileDialog` (filter: `*.mp3 *.wav`)
- File copied to `user_data/sounds/`, list refreshed
- Preview + select same as presets tab

**Return:** selected sound_id string or `None` if cancelled.

### 4.4 Home Page Enhancement

`page_home.py` — on `sig_prediction_updated`:
- Hero banner pulse animation uses spell's RGB color instead of fixed color
- Color read from SpellConfigStore on each prediction

### 4.5 i18n

All new labels added to `logic/ui_strings.json` in both EN and VI:
- "Select Color", "Select Sound", "Presets", "Custom", "Import Sound...", "No sound", "Preview"
- Vietnamese equivalents

---

## 5. Firmware — RGB LED

### 5.1 Hardware

**Component:** Standard common-cathode RGB LED, 3 PWM pins.

| Pin | Color | ESP32 GPIO |
|-----|-------|------------|
| R | Red | GPIO 25 |
| G | Green | GPIO 26 |
| B | Blue | GPIO 27 |

Current-limiting resistors (220Ω–330Ω) on each pin. User wires externally.

### 5.2 LEDC PWM Configuration

- 3 LEDC channels (0, 1, 2)
- Frequency: 5 kHz
- Resolution: 8-bit (0–255 duty range)
- Speed mode: `LEDC_LOW_SPEED_MODE`

### 5.3 NVS labels.bin Extension

**Current per-gesture blob** (69 bytes):
```
float[16] centroid (64B) | float threshold (4B) | uint8 is_spell (1B)
```

**New per-gesture blob** (72 bytes):
```
float[16] centroid (64B) | float threshold (4B) | uint8 is_spell (1B) | uint8 R (1B) | uint8 G (1B) | uint8 B (1B)
```

+3 bytes per gesture. Backward compatible: firmware checks for `version` NVS key.

**Changes to `nvs_builder.py`:**
- `build_config_bin()` accepts `colors: dict[str, tuple[int,int,int]]` parameter
- Appends `struct.pack("<3B", r, g, b)` after `is_spell` byte
- Adds NVS key `version` = `2` (uint8) for format detection
- Missing color defaults to `(255, 255, 255)`

### 5.4 Firmware Code Changes

**Both `mpu6050/main/main.cpp` and `assets/firmware/main.cpp.template` modified.**

**Initialization (app_main or setup):**
```c
#define RGB_PIN_R 25
#define RGB_PIN_G 26
#define RGB_PIN_B 27

static uint8_t gesture_colors[MAX_CLASSES][3];

void init_rgb_led() {
    // Configure LEDC channels for R, G, B
    // 5kHz, 8-bit resolution, LEDC_LOW_SPEED_MODE
    // Initial state: LED off (duty=0)
}

void load_gesture_colors_from_nvs() {
    // Read version key; if >= 2, parse RGB from blob tail
    // Otherwise default all to (255, 255, 255)
}
```

**OnSpellDetected implementation:**
```c
void OnSpellDetected(int class_index) {
    uint8_t r = gesture_colors[class_index][0];
    uint8_t g = gesture_colors[class_index][1];
    uint8_t b = gesture_colors[class_index][2];
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, r);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, g);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_2, b);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_2);
}
```

- LED stays showing last recognized spell color
- STAND_BY / no detection → LED off `(0, 0, 0)`

**Template placeholders added to `firmware_main_generator.py`:**
- `{{RGB_PIN_DEFINES}}` — pin constant definitions
- `{{RGB_INIT_BLOCK}}` — LEDC setup code
- `{{RGB_COLOR_TABLE}}` — gesture_colors array initialization from NVS

---

## 6. Integration — Handler Wiring

### 6.1 Initialization (`main.py`)

```python
spell_config = SpellConfigStore(app_data_dir=APP_DATA_DIR)
sound_player = SoundPlayer(spell_config_store=spell_config)
handler = Handler(..., spell_config=spell_config, sound_player=sound_player)
```

### 6.2 Sound-on-Prediction Chain

```
ESP32 → PREDICT:Fireball:0.95
  → SerialWorker.sig_prediction_received(str, float)
  → DataStore.update_prediction()
  → sig_prediction_updated(str, float)
  → Handler._on_prediction_for_sound(action, confidence)
      → spell_config.get_spell_config(action)
      → if sound configured: sound_player.play(sound_id, volume)
  → page_home.show_recognized_spell(action, confidence)  [existing]
```

Handler filters: only play if confidence > rejection threshold and spell has sound configured. Respects 200ms cooldown.

### 6.3 Color-on-Upload Chain

```
Handler._start_upload_immediately()
  → NVSBuildWorker receives spell_config.get_all_colors()
  → build_config_bin(..., colors=colors_dict)
  → labels.bin includes RGB per gesture
  → FlashWorker flashes to 0x390000
```

### 6.4 Spell Deletion Cleanup

```
Handler.on_spell_deleted(name)
  → [existing delete flow]
  → spell_config.remove_spell_config(name)
```

### 6.5 UI Signal Wiring in page_record

```
SpellCardWidget.sig_color_clicked
  → page_record._on_color_edit(name)
  → QColorDialog
  → spell_config.set_spell_color(name, r, g, b)
  → sig_spell_config_changed → refresh card dot

SpellCardWidget.sig_sound_clicked
  → page_record._on_sound_edit(name)
  → SoundSelectorDialog
  → spell_config.set_spell_sound(name, sound_id)
  → sig_spell_config_changed → refresh card icon
```

---

## 7. Config & Paths

**Changes to `config.py`:**
- `SOUNDS_PRESET_DIR = WORKSPACE_ROOT / "assets" / "sounds"`
- `SOUNDS_USER_DIR = USER_DATA_DIR / "sounds"`

**Changes to `requirements.txt`:**
- Add `PyQt6-Qt6-Multimedia`

---

## 8. Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `logic/spell_config_store.py` | **Create** | Per-spell color+sound JSON storage |
| `logic/sound_player.py` | **Create** | MP3 playback via QMediaPlayer |
| `ui/spell_card_widget.py` | **Create** | Custom list item: color dot + sound icon |
| `ui/sound_selector_dialog.py` | **Create** | Preset/custom sound picker dialog |
| `logic/tensorflow/nvs_builder.py` | **Modify** | Pack RGB bytes into labels.bin blob |
| `logic/handler.py` | **Modify** | Wire sound playback on prediction, pass colors to NVS build, cleanup on delete |
| `ui/page_record.py` | **Modify** | Use SpellCardWidget, connect color/sound edit flows |
| `ui/page_home.py` | **Modify** | Spell color flash on prediction |
| `main.py` | **Modify** | Init SpellConfigStore + SoundPlayer |
| `config.py` | **Modify** | Add SOUNDS_PRESET_DIR, SOUNDS_USER_DIR |
| `requirements.txt` | **Modify** | Add PyQt6-Qt6-Multimedia |
| `logic/ui_strings.json` | **Modify** | EN/VI strings for new UI elements |
| `assets/sounds/*.mp3` | **Create** | ~12 bundled preset sound effects |
| `mpu6050/main/main.cpp` | **Modify** | RGB LED init + OnSpellDetected |
| `assets/firmware/main.cpp.template` | **Modify** | RGB LED template placeholders |
| `logic/firmware_main_generator.py` | **Modify** | Render RGB placeholders |

---

## 9. Out of Scope

- No speaker/buzzer on ESP32 hardware (sound is PC-only)
- No NeoPixel/WS2812 addressable LED support
- No per-primitive color/sound (spells only)
- No sound volume per-spell UI slider in initial version (`set_spell_volume()` API exists and volume stored in JSON for future use, all spells default to 1.0)
- No LED animation patterns (solid color only)

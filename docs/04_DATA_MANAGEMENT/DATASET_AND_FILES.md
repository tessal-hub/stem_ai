# Dataset and File Conventions

Status: Active
Language: English
Owner: Data Maintainers
Last Updated: 2026-04-21

## Runtime Structure

- app_data/dataset/<SPELL_NAME>/*.csv
- app_data/model.tflite
- app_data/gesture_model.cc

## Spell Naming

- Spell names are normalized to uppercase.
- System spell STAND BY is protected and cannot be removed.

## Sample CSV Format

Header:

accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z

Rules:

- Exactly 6 columns.
- Values are normalized floats.
- One file stores one cropped sample sequence.

## Data IO Flow

- Save, delete, export, and refresh run via DataIOWorker.
- DataStore emits database updates after refresh.

## Settings and Artifacts

- Persistent settings are stored via QSettings.
- Firmware and model outputs are validated before flash/upload.

# TinyML Model Pipeline

Status: Active
Language: English
Owner: ML Maintainers
Last Updated: 2026-04-21

## End-to-End Flow

1. Prepare sensor dataset and labels.
2. Train compact TensorFlow model suitable for MCU memory limits.
3. Convert to TFLite.
4. Apply post-training int8 quantization using representative data.
5. Validate model size and basic accuracy.
6. Export binary model to C byte array for firmware embedding.
7. Flash and test on ESP32 runtime.

## Design Constraints

- Keep model size as small as practical for ESP32 SRAM and flash constraints.
- Prefer lightweight architectures for time-series IMU data.
- Keep preprocessing identical between Python and firmware.

## Quantization Rules

- Use full int8 path for inference input and output where possible.
- Use representative dataset matching production distribution.
- Compare baseline and quantized accuracy before deployment.

## Artifacts

- Input model: .h5 or SavedModel.
- Deployment model: .tflite (quantized).
- Firmware include: generated C array header.

## Legacy Sources

This canonical page replaces overlapping legacy docs:

- ../ARCHIVE/2026-04/tinyml_info_legacy_2026-04.md
- ../ARCHIVE/2026-04/tf_tinyml_training_legacy_2026-04.md

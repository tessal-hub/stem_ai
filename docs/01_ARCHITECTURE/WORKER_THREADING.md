# Worker Threading

Status: Active
Language: English
Owner: Core Team
Last Updated: 2026-04-21

## Core Rule

Never block the Qt main thread.

## Worker Inventory

- SerialWorker: UART input/output loop.
- UdpWorker: UDP listener.
- DataIOWorker: file save/delete/export jobs.
- FeatureWorker: feature extraction and FFT.
- FlashWorker: firmware flashing.
- ModelUploader: model chunk upload.
- GestureModelBuildWorker: TinyML training/build.

## Thread Safety Rules

1. Use queued signal connections across threads.
2. Keep UI rendering calls in main thread only.
3. Stop long-running workers asynchronously.
4. Do not call blocking wait patterns on main thread during active UI flow.

## Port Ownership

Use a single owner model for COM port operations.
Serial, flash, and upload actions are mutually exclusive.

## Performance Targets

- Plot update remains responsive under live serial input.
- Feature extraction remains bounded and non-blocking.
- Signal roundtrip should stay within low-latency thresholds used by tests.

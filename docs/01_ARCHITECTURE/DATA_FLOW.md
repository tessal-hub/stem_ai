# Data Flow

Status: Active
Language: English
Owner: Core Team
Last Updated: 2026-04-21

## Serial Ingestion Path

1. ESP32 sends IMU frames over UART.
2. Serial worker parses and normalizes frames.
3. Handler routes data to DataStore, UI widgets, and feature pipeline.
4. UI reads snapshots from DataStore and renders plots/3D orientation.

## UDP Path

1. UDP worker receives telemetry packets.
2. Main window parses payload and updates DataStore.
3. Health metrics are emitted and shown in wand statistics.

## Recording Path

1. Record start signal enters handler.
2. Handler validates mode and connection state.
3. Samples are appended into live buffer and recorder.
4. Snip action sends cropped data to DataIO worker for CSV write.

## Training and Build Path

1. UI requests train/build.
2. Handler starts model build worker.
3. Worker emits status and progress updates.
4. On success, outputs are synced for firmware use.

## Flash and Upload Path

1. Handler validates port ownership and mode guards.
2. Serial session is stopped safely before flash/upload.
3. Flash or upload worker runs in background thread.
4. Progress and completion events are propagated to UI.

## Invariants

- UI does not directly control workers.
- Handler is the orchestration boundary.
- Cross-thread updates must be queued.
- DataStore is the shared runtime state hub.

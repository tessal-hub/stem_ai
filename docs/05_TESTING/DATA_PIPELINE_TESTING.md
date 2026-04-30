# Data Pipeline Testing Scenarios

Status: Active
Language: English
Owner: QA and Runtime Team
Last Updated: 2026-04-21

## Goal

Verify end-to-end serial data flow from ESP32 to UI plots and 3D orientation.

## Scenario A: Serial Connectivity

1. Scan and connect to UART port.
2. Confirm terminal receives CSV frames.
3. Confirm connection state updates in UI.

## Scenario B: Buffer and Plot Updates

1. Open record page while streaming.
2. Confirm live buffer growth and plot updates.
3. Confirm all six axes are rendered.

## Scenario C: 3D Orientation

1. Move device physically.
2. Confirm wand orientation changes in home page.

## Scenario D: Record, Stop, Snip

1. Start recording with a valid spell label.
2. Stop and verify freeze/crop behavior.
3. Snip and verify sample CSV write.

## Scenario E: Reconnect Stability

1. Disconnect and reconnect serial.
2. Confirm no crash and stream resumes.

## Failure Triage

- No terminal data: check port and firmware stream.
- No plots with data present: inspect handler routing and UI timer.
- No 3D update: inspect orientation signal path.

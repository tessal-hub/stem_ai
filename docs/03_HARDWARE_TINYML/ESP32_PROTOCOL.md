# ESP32 Data Protocol

Status: Active
Language: English
Owner: Firmware and Runtime Maintainers
Last Updated: 2026-04-21

## Transport

- Link: UART serial
- Stream pattern: newline-delimited CSV
- Nominal sampling: 50 Hz

## Packet Shape

aX,aY,aZ,gX,gY,gZ\n

- 6 fields per frame.
- Raw values are parsed in logic layer and normalized before UI use.

## Parsing Rules

1. Read line, decode UTF-8, trim whitespace.
2. Split by comma and require exactly 6 values.
3. Drop malformed packets without crashing UI path.
4. Convert to float and normalize using configured sensor scales.
5. Push normalized frame into datastore buffer.

## Stability Rules

- Do not pass raw unvalidated packet strings to UI pages.
- Keep parser resilient to intermittent serial corruption.
- Keep protocol changes backward-compatible or versioned.

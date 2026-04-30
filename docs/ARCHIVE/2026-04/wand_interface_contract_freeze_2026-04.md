# PageWand Interface Contract Freeze (Phase 4)

Status: Frozen for UI decomposition.

This document captures the external PageWand contract that must remain stable while the UI is split into focused panels.

## 1) Outbound signals (PageWand -> Handler)

- sig_serial_scan()
- sig_serial_connect(str)
- sig_serial_disconnect()
- sig_bt_scan()
- sig_bt_connect(str)
- sig_bt_disconnect()
- sig_flash_compile(list)
- sig_flash_upload()
- sig_term_clear()

Notes:

- Signal names are frozen.
- Payload shapes are frozen.

## 2) Inbound methods (Handler/MainWindow -> PageWand)

- append_terminal_text(text: str)
- update_flash_progress(percentage: int, status_text: str = "")
- set_serial_status(connected: bool, port_name: str = "")
- update_serial_port_list(ports: list[str])
- set_bluetooth_status(connected: bool, device_name: str = "")
- update_bt_device_list(devices: list[str])
- update_esp_stats(stats: dict[str, str])
- load_spell_payload_list(spell_counts: dict[str, int])

## 3) Legacy attribute compatibility (used by Handler)

- combo_serial_ports

Compatibility rule:

- combo_serial_ports must remain available on PageWand and provide currentText().

## 4) Worker -> UI path (unchanged orchestration)

The worker contract remains orchestrated by Handler:

- SerialWorker.sig_connection_status(bool, str)
  -> Handler.\_on_connection_status_changed
  -> PageWand.set_serial_status

- SerialWorker.sig_error(str)
  -> Handler wiring
  -> PageWand.append_terminal_text

- ModelUploader.sig_progress(int)
  -> Handler wiring
  -> PageWand.update_flash_progress

- ModelUploader.status_msg(str)
  -> Handler wiring
  -> PageWand.append_terminal_text

- ModelUploader.sig_error(str)
  -> Handler wiring
  -> PageWand.append_terminal_text

- DataStore.sig_stats_updated(dict)
  -> Handler wiring
  -> PageWand.update_esp_stats

- DataStore.sig_db_updated(dict)
  -> Handler.\_on_db_updated
  -> PageWand.load_spell_payload_list

## 5) Panel mapping inside PageWand (internal only)

- WandConnectionPanel: serial/bt controls and status labels
- WandStatsPanel: ESP telemetry labels and spell bar chart
- WandTerminalPanel: terminal widget and clear action
- WandFlashPanel: compile/upload controls and flash progress
- WandSpellPayloadPanel: payload checklist with rarity badges
- ConnectionStatusPresenter: shared status label/button presenter for serial and bt

Internal rule:

- Panel internals may change, but the external contract sections above cannot change without updating this freeze document and coordinating dependent code.

# Protocol notes

This is a partial implementation derived from observing ordinary Adjust lighting operations and statically inspecting its public browser implementation. No vendor JavaScript bundle is included here.

## Transport

| Field | Tested value |
| --- | --- |
| USB VID / PID | `0x36BC / 0x1003` |
| Interface | `0` |
| HID usage page / usage | `0xFF00 / 0x0001` |
| Input / output report length | `64` bytes, including report ID |
| Report ID | `0x02` |
| Pump subdevice, wire ID | `0x01` |
| Controller-reported RGB count | `22` |

No additional leading zero is inserted. SignalRGB uses `device.write(report, 64)` and `device.read([2], 64, 2000)`. Each response must repeat the report/command prefix and have a zero status byte.

## RGB discovery and multi-zone frames (0.2.0)

At startup `02 A4 08 01` reads the controller RGB table. Response byte 4 contains the entry count; triples from byte 5 contain wire ID, position count and protocol type. Empty entries are skipped. The known pump entry is `01/22`; the confirmed ARGB1 fan entry is `11/16`. Counts are read from the controller, not inferred from fan quantity.

Each active subdevice gets its own selection/header/data sequence. Header byte 8 is the total number of active zones in the batch. A changed frame sends every active zone; unchanged entire batches are skipped. For N positions, the data length is `3 * (2 + 3*N)` bytes, encoded big-endian, fragmented into at most 60 data bytes per report. Each timestamp block contains that zone's N RGB triples. The pump-only example below remains a useful regression vector.

The plugin does not set RGB port types or LED counts. The tested fan output was configured once as ARGB1 with 16 positions before use. No cooling control is involved.

## One changed pump-only frame

1. Select pump: `02 A4 0A 01 01`, zero-padded to 64 bytes.
2. Send timestamp-effect header: `02 A4 11`.
3. Send four `02 A4 12` data fragments, holding 60, 60, 60 and 24 bytes.

Header offsets include the report ID:

| Offset | Meaning in this implementation |
| --- | --- |
| 0â€“2 | `02 A4 11` |
| 3 | Regular effect, `01` |
| 4 | Sum of all effect-data bytes modulo 256 |
| 5â€“6 | Effect-data length, big-endian `00 CC` (204) |
| 7 | Preview flag, `01` |
| 8 | Active-zone count (`01` in this pump-only example) |
| 9â€“11 | Custom metadata `99 01 64` |
| 12â€“14 | First RGB position as the metadata main color |
| 15 | Brightness metadata, `64` (100) |
| Remaining | Zero padding |

The 204-byte stream consists of three 68-byte blocks. Each has a two-byte big-endian timestamp followed by 22 RGB triples. Timestamps are `0000`, `0232`, `0464`; the real time unit is not established here. All three blocks contain the same current 22-position frame.

For a fragment, byte 3 is its valid data count; bytes 4 onward hold data followed by zero padding.

The implementation uses repeated preview frames and does not send `A4 13` (commit), `A5` commands, PWM commands or firmware commands. This does not establish what the firmware internally stores.

## Evidence and scope

Uniform blue/orange vectors match a visibly confirmed hardware test. The owner subsequently confirmed individual color effects through SignalRGB. The repository fixture contains only host-to-device reports, with personal metadata and original capture files omitted. Offline tests independently decode mixed-position frames and check their block content and checksum.

Radius 240 RGB with three daisy-chained NYOTA Ultra fans has been visibly confirmed. The tested controller exposes 22 pump positions plus one 16-position fan zone; physical per-fan independence is not established. Cold-start behavior, long-term behavior, precise physical geometry and numeric achieved FPS remain open.

## Primary references

- [Fractal Adjust](https://adjust.fractal-design.com/)
- [SignalRGB plugin documentation](https://docs.signalrgb.com/developer/plugins/)
- [SignalRGB Writes and Reads](https://docs.signalrgb.com/developer/plugins/writes-and-reads/)
- [SignalRGB Plugin Exports](https://docs.signalrgb.com/developer/plugins/plugin-exports/)
- [SignalRGB plugin directories](https://docs.signalrgb.com/developer/plugins/how-is-a-plugin-loaded-/)
- [SignalRGB changelogs](https://docs.signalrgb.com/changelogs/), including `setFrameRateTarget` behavior


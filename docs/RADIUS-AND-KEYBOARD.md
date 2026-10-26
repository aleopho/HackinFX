# Radius and ASUS keyboard implementation — 2.1.1

## Fractal Radius

The native adapter ports the user's [SignalRGB Radius plugin](https://github.com/aleopho/signalrgb-fractal-radius), pinned at e86cabf7154c0022fd23799a55d0fc3e24154744. Its MIT source, license and recorded packet fixture are retained in `vendor/radius`. The plugin was user-confirmed on Windows for a Radius 240 RGB with a 22-position pump and configured 16-position fan RGB output. Radius has since been user-reported working on macOS; firmware variants, sustained colors and synchronization still need broader validation.

Native transport matches 36bc:1003, interface 0, vendor usage page ff00/usage 1. It schedules an input callback only on that lighting collection. Each request is exactly 64 bytes including report ID 02; it waits up to two seconds for a matching response and validates the zero status. No keyboard/mouse event input is read.

Discovery sends only the documented RGB-zone table query. Pump and fan counts come from the table, not fan quantity. Only the verified 22-position pump and known active RGB port/protocol shapes are accepted. Each changed batch sends every active zone with the plugin's selection/header/timestamp data, checksum, and complete-batch metadata. Colors are validated before the first packet. Unchanged batches are deduplicated only within 0.25 seconds; static colors are renewed periodically to retain the preview lease, including during pause; ACK loss or incomplete transactions stop output without automatic retry. A batch deadline bounds stop latency.

The Core schedules a maximum of 20 host frames/s; no achieved hardware FPS is claimed. There is no commit/flash, firmware, fan/pump PWM, port-type or LED-count reconfiguration. Unlike the original plugin's normal orange shutdown, HackinFX leaves its last acknowledged colors in place. Fan RGB must already be configured in Adjust; parallel wiring may mirror positions. Close Adjust/SignalRGB or other Radius writers before testing.

## ASUS ROG Strix Scope II 96 Wireless

The user reports no visible lighting from the previous LampArray path, while mouse/mainboard/GPU work. ASUS keyboards can expose a standard LampArray collection while taking lighting control back in firmware. Version 2.0.2 prefers the vendor keyboard channel and suppresses the duplicate LampArray entry for the same USB parent.

- Exact wired model: 0b05:1aae, vendor page ff00. HID report ID 0 is represented as a 65-byte hidapi-style packet; IOKit receives the 64-byte payload without a zero ID. Input callbacks prepend the omitted zero ID for normalization.
- OMNI receiver: 0b05:1ace, descriptor-validated report 2 for the keyboard. A nonzero layout reply is required; sleeping/disconnected devices do not become Ready. Report 1's paired list can provide the exact wireless product ID/name. Unknown paired models keep a generic name.
- The Core renders shared effects and sends whole-keyboard RGB through the documented volatile Static `51 2c` packet path. This avoids an independently timed onboard animation. Gradient and animated looks use the host renderer; this is not per-key mapping.
- No profile save, pairing or firmware commands are sent. Group throughput is constrained by slow/wireless outputs, and command timing is not a measurement of physical LED timing. Pause retains the last requested color; Lights off sends black.

References include the pinned MIT-licensed RIGStats keyboard/OMNI implementation (bf0f1f3e8ab1b387dd7cd914a44ba0d95ad1cd96) and OpenRGB ASUS controller sources. Original MIT notices are retained in `vendor/rigstats`. The current screenshot shows the wired Scope II 96 as Ready. Actual effects/connection variants still require visual validation; Ready is not an optical measurement.

## Reliability and interface changes

- Lighting / Needs attention / All devices filters reduce noise without hiding raw inventory.
- Select compatible excludes devices that cannot play the chosen scene.
- Device details list scene capabilities, zone counts and setup actions.
- Errors survive status polling until dismissed or a subsequent operation succeeds.
- Failed writes disable that target until rediscovery instead of leaving a misleading Ready badge.
- Failed multi-target activation releases acquired LampArray control; failed scene completion is no longer labeled successful.

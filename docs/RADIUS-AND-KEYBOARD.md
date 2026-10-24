# Radius and ASUS keyboard implementation — 2.0.2

## Fractal Radius

The native adapter ports the user's [SignalRGB Radius plugin](https://github.com/aleopho/signalrgb-fractal-radius), pinned at e86cabf7154c0022fd23799a55d0fc3e24154744. Its MIT source, license and recorded packet fixture are retained in `vendor/radius`. The plugin was user-confirmed on Windows for a Radius 240 RGB with a 22-position pump and configured 16-position fan RGB output. That does not establish macOS operation.

Native transport matches 36bc:1003, interface 0, vendor usage page ff00/usage 1. It schedules an input callback only on that lighting collection. Each request is exactly 64 bytes including report ID 02; it waits up to two seconds for a matching response and validates the zero status. No keyboard/mouse event input is read.

Discovery sends only the documented RGB-zone table query. Pump and fan counts come from the table, not fan quantity. Only the verified 22-position pump and known active RGB port/protocol shapes are accepted. Each changed batch sends every active zone with the plugin's selection/header/timestamp data, checksum, and complete-batch metadata. Colors are validated before the first packet. Unchanged batches are skipped; ACK loss or incomplete transactions stop output without automatic retry. A batch deadline bounds stop latency.

The Core schedules a maximum of 20 host frames/s; no achieved hardware FPS is claimed. There is no commit/flash, firmware, fan/pump PWM, port-type or LED-count reconfiguration. Unlike the original plugin's normal orange shutdown, HackinFX leaves its last acknowledged colors in place. Fan RGB must already be configured in Adjust; parallel wiring may mirror positions. Close Adjust/SignalRGB or other Radius writers before testing.

## ASUS ROG Strix Scope II 96 Wireless

The user reports no visible lighting from the previous LampArray path, while mouse/mainboard/GPU work. ASUS keyboards can expose a standard LampArray collection while taking lighting control back in firmware. Version 2.0.2 prefers the vendor keyboard channel and suppresses the duplicate LampArray entry for the same USB parent.

- Exact wired model: 0b05:1aae, vendor page ff00. HID report ID 0 is represented as a 65-byte hidapi-style packet; IOKit receives the 64-byte payload without a zero ID. Input callbacks prepend the omitted zero ID for normalization.
- OMNI receiver: 0b05:1ace, descriptor-validated report 2 for the keyboard. A nonzero layout reply is required; sleeping/disconnected devices do not become Ready. Report 1's paired list can provide the exact wireless product ID/name. Unknown paired models keep a generic name.
- Static, Breathing and Spectrum use documented onboard `51 2c` effects, speed/brightness fields and the per-key marker. No profile save, pairing or firmware commands are sent. Gradient/Wave are not advertised by this first keyboard path.
- Onboard effects are sent once, not streamed over the radio, and do not share the host animation clock. Stop halts host streaming; onboard effects continue until changed or Blackout is applied.

References include the pinned MIT-licensed RIGStats keyboard/OMNI implementation (bf0f1f3e8ab1b387dd7cd914a44ba0d95ad1cd96) and OpenRGB ASUS controller sources. Original MIT notices are retained in `vendor/rigstats`. Actual colors via these new native paths still need visual confirmation from the normal installed app.

## Reliability and interface changes

- Lighting / Needs attention / All devices filters reduce noise without hiding raw inventory.
- Select compatible excludes devices that cannot play the chosen scene.
- Device details list scene capabilities, zone counts and setup actions.
- Errors survive status polling until dismissed or a subsequent operation succeeds.
- Failed writes disable that target until rediscovery instead of leaving a misleading Ready badge.
- Failed multi-target activation releases acquired LampArray control; failed scene completion is no longer labeled successful.

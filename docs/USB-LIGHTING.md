# Native USB/HID lighting and device recognition

HackinFX now uses a signed x86-64 IOKit helper rather than depending on `system_profiler SPUSBDataType` for device recognition. The latter returned an empty USB list on the development Hackintosh even though IOKit exposed its peripherals. HID collections are grouped by their parent USB device; ordinary keyboard/mouse interfaces and generic USB devices remain visible without pretending they have RGB controls. Hubs are omitted. Serial numbers, key events and mouse movement are neither read nor exported.

## Imported OpenRGB identities

`app/openrgb_usb_catalog.json` contains 1,150 concrete USB/HID detector registrations at OpenRGB commit `817834cfab034c97927451e31c4a2deb60a44725`. They cover keyboards, mice, mainboards, coolers, lighting/fan controllers and other peripherals. Disabled upstream registrations remain disabled identity data. Eleven unresolved macro registrations are retained in the audit section, not guessed. Universal HID LampArray detection uses descriptor inspection instead of fixed product IDs.

`vendor/openrgb/usb-sources.zip` retains 932 original detector/header files plus the upstream license. The import is reproducible offline with `python3 tools/import_openrgb_usb_catalog.py`. Controller references, per-file notices and exact hashes for the native protocols are under `vendor/openrgb/usb-protocols`. Recognition is distinct from implementing a driver and from physical user verification.

## Direct native paths

| Path | Devices / scope | Current behavior |
| --- | --- | --- |
| HID LampArray | Standard page 0x59, usage 1; compatible keyboards, mainboards, chassis lighting and controllers | Descriptor-derived report IDs, strict canonical field layout; read lamp count/kind/update interval; inspect programmability before explicit scene start; shared five effects with per-lamp frames |
| ASUS Spatha X | 0b05:1977 USB and 0b05:1979 wireless; lighting collection 0xff01 | Three hardware zones, Static and Gradient, transient lighting packets. No flash saves. The dock is not controlled by the native mouse adapter |
| NZXT Kraken X2 / M2 | 1e71:170e and 1e71:1715 | Logo and eight ring LEDs, bounded shared scene updates using lighting-only 02:4c packets. No pump/fan speed writes. Other Kraken generations use different protocols and are not enabled by this path |
| OpenRGB SDK bridge | Other actual controllers exposed by a working local SDK server | Existing shared Direct-mode scene controls; catalog recognition alone never enables writes |

The development system exposes a ROG OMNI Receiver with a canonical LampArray descriptor, an ASUS Spatha X wireless controller, and a GIGABYTE/ITE 048d:5711 mainboard with the same standard LampArray interface. The user identifies the paired keyboard as a ROG Strix Scope II 96 Wireless. The receiver's generic product string does **not** independently prove which keyboard model is paired, so the app labels the receiver/keyboard interface honestly. A Fractal Radius and additional USB devices are now inventoried, with no invented native lighting protocol.

The native read/access attempt from the agent execution environment is denied by macOS (`-536870174`). This proves enumeration and descriptor recognition, not successful physical lighting. Such devices stay visible as **Access required**, with the OS error in device details. Launch the installed app normally and retry discovery; if access remains denied, close other lighting applications and inspect macOS privacy/device access. Do not disable system protections or run arbitrary firmware/SMBus commands. A successful build or mocked transport test is not hardware verification.

## Runtime behavior

Discovery performs no color, mode or flash writes. It may open only allowed lighting collections to check access or read LampArray metadata. Explicit scene Start selects lamp metadata and then disables autonomous lighting. Multi-update packets commit only after their final chunk; device minimum intervals are respected. Closing the Core or rediscovering returns activated LampArray devices to autonomous mode. Stop halts scene streaming while keeping the last applied colors. Spatha X is intentionally excluded from host-streamed animation because its wireless hardware-mode update path is slow. Exact catalog-name matching prevents duplicate OpenRGB and native writers; a mouse dock remains separate.

ARGB fans attached to a compatible mainboard or controller are part of that controller's exposed lighting array. A conventional PWM fan is not itself a USB RGB controller. DRAM, fan speed control, firmware updates, channel resizing and saving to device flash are not enabled by the catalog import.

## Validation

Tests cover real standard descriptors, malformed layouts, access denial, keyboard-interface deduplication, catalog-only gating, LampArray metadata and exact frame packets, update intervals, autonomous release, exact ASUS matching/zone bytes and NZXT lighting-only packets. Actual colors on the keyboard, mainboard and mouse still need user confirmation. Native Kraken hardware is not available for a physical test.

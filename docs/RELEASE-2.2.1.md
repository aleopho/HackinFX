# HackinFX 2.2.1 — scoped DRAM LED transport

## Concrete observations

On the development system 2.2.0 produced about 26 FPS for the PNY GPU and about
27 FPS on the fast AIO/USB output; the user confirms these look fluid. Scope II
96 remains a whole-device fallback because the layout reply is unrecognized;
no physical per-key success is claimed. Its first eight layout-reply bytes are
now attached as bounded diagnostics for exact parsing work.

Normal Terminal diagnostics reported macUSPCIO loaded, host 8086:7f23,
HSTS=0x40, HCTL=0x08, host config=0x11, PCI command=1, BAR low=0x4001.
The bus was not hardware-busy, but its software semaphore was already set.
This is not evidence of a working RGB controller.

## Semaphore correction

Intel HSTS bit 6 is read-to-acquire: a read returning zero acquires the semaphore;
subsequent reads return one until the owner releases it. The prior helper treated
it as a generic busy flag and could retain its own lease. Diagnostic reads could
also leave it set. The corrected helper releases only a lease it actually acquired,
on success and failure. Foreign/stale ownership is not forcibly cleared. No
controller reset/KILL, host-configuration change or forced unlock is added.

Reference: [Intel HSTS register semantics](https://edc.intel.com/content/www/us/en/design/publications/core-ultra-series-3-processors-i-o-registers/host-status-register-address-hsts-offset-0_1/).
A system restart may be required to clear an old stranded semaphore; merely
quitting the app need not reset the hardware register.

## RGB-only constraints

- Native writes remain restricted to the exact Intel host and documented Corsair
  RGB addresses 0x18–0x1f / 0x58–0x5f. SPD 0x50–0x57 is excluded.
- Preliminary controller signatures precede device-info buffer selection. Final
  Corsair vendor/product IDs and device-info CRC gate color writes.
- Only the documented RGB buffer/Static-apply registers and values are allowed.
  No bootloader switch, firmware, SPD, memory timings or voltage controls.
- Automatic OpenRGB I2C/SMBus detectors are disabled via a complete name catalog
  derived from the pinned engine source (800 names, no unresolved registrations).
  USB/HID detection remains available; native NVIDIA stays separate. Broad
  automatic SMBus compatibility is deliberately not claimed.
- RAM is excluded from automatic startup colors and automatic target selection,
  even if already ready. Explicit probe and manual selection are required.

## Startup and validation

Default lighting is mint (#A7F3D0) Twinkle, 65% speed, 30 FPS adaptive output,
for ready streaming devices except RAM. Static-only non-RAM devices receive
mint as a fallback. Saved local profiles/guards remain unchanged.

162 Python tests pass; native semaphore/CRC/allowlist self-tests require no
hardware. Full WidgetKit / installer / signature CI is separate. The provided
Terminal test only applies dim mint after exact controller/CRC verification and
explicit --mint. Transport success still needs visible LED confirmation.
RAM is not labeled fixed until that physical test succeeds.

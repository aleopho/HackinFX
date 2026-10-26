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

## Titanium hardware follow-up

Four PID 0801 / protocol 4 controllers were identified with valid device-info CRC
at RGB addresses 0x18–0x1B. The effect-configuration test darkened the first DIMM
and the subsequent status read at register 0x30 returned NACK (host status 0x44).
This is not a successful lighting verification. The remaining DIMMs were not sent colors.

The helper now disables effect-configuration writes entirely and uses the vendored
OpenRGB protocol-4 direct LED word-write fallback, restricted to PID 0801 / protocol 4.
A fixed 38-byte packet contains 12 RGB colors and CRC-8; a native self-test decodes
the word/nibble packing independently. No status-0x30 polling or effect-configuration
apply occurs on this path. Native transport completion still requires optical confirmation.
The standalone test defaults to a single DIMM at 0x18; --address selects one of the
four observed addresses. RAM remains excluded from automatic startup effects.

### Direct transport follow-up (not optically verified)

The first word-write fallback test completed without host errors but the user saw
mixed purple/blue/green LEDs rather than uniform mint. This is a failed color test,
not confirmation of usable RAM control. A packet/nibble audit matches the vendored
OpenRGB fallback; no proven packing defect was identified.

The next diagnostic uses OpenRGB's preferred SMBus Block Write transport: a fixed
38-byte direct LED packet split into 32 bytes at RGB command 0x31 and 6 at 0x32.
The native adapter implements the Intel i801 BYTE_DONE handshake, bounded waits,
error handling and ownership release. It stops if the existing AUXCTL mode is not
byte-handshake/no-PEC; it never changes AUXCTL or PCI host configuration. No word
fallback or configuration apply is attempted after a block error. Native tests
exercise 32/6-byte handshakes, data ordering, errors and rejected lengths/modes.
The diagnostic identifies itself as titanium-block-v1 so the script rejects a
stale helper before sending colors. Only PID 0801 / protocol 4 / 12 LEDs is enabled.

References:
- OpenRGB Controllers/CorsairDRAMController/CorsairDRAMController.cpp,
  SetColorsPerLED (vendored GPL-2.0-or-later source).
- Linux drivers/i2c/busses/i2c-i801.c, i801_block_transaction_byte_by_byte
  (GPL-2.0-or-later), https://codebrowser.dev/linux/linux/drivers/i2c/busses/i2c-i801.c.html

Hardware acceptance remains pending; do not list RAM as tested/working yet.

### Physical milestone and frame integration

The user confirmed a uniform mint color on the left DIMM with titanium-block-v1.
The block transport therefore has one optically confirmed Static result. The other
three controllers are identified but are not yet optically confirmed.

Revision titanium-block-v2 keeps the successful block transport and adds exactly
12 independently validated RGB colors per frame, reversing physical LED order as
OpenRGB does for Titanium. The RAM adapter exposes 12 LEDs and participates in the
existing shared-clock adaptive renderer only after explicit probe and selection.
No automatic RAM color at startup is enabled. A bus failure disables all RAM rows
and prevents further writes until explicit recovery. Animation rate is not yet measured.
The terminal --mint --remaining test colors only 0x19, 0x1A and 0x1B, once each,
and stops on the first error. It does not enable continuous streaming.

### Four-DIMM Static confirmation

The user confirmed all four DIMMs display uniform mint after the bounded block
write test. Static color on addresses 0x18–0x1B is optically confirmed on this host.
A separate --effects test now shows three 4-LED color regions for three seconds,
then renders the actual Core mint Twinkle at 65% speed / 40% brightness for eight
seconds. It measures completed four-DIMM frames per second and completion skew,
then restores fixed mint after success. No cleanup writes follow any error.
Neither the separate LED regions nor animated output is yet optically confirmed.

### Animated test failure and paced diagnostic

The user saw the separate RGB regions, but the --effects run stopped with NACK
0xC4 on block 0x32. There was no completed-FPS result, so animated RAM is not
verified. The old diagnostic did not identify which phase/DIMM failed.
Revision titanium-block-v3-paced reports address, block and completed byte count,
logs map/Twinkle phase boundaries, and conservatively spaces complete frames by
50ms per DIMM plus 2ms between blocks. This is a timing hypothesis under test, not
a proven root-cause correction. No failed transaction is retried. The diagnostic
default target is 20 FPS; actual completed rate is measured separately.

### Paced animation physically confirmed

On 2026-10-26 the user confirmed the paced test displayed a very fluid effect.
The diagnostic completed all four DIMMs, then restored fixed mint without errors.
Measured: 134 complete four-DIMM frames in 8.046 seconds, 16.65 completed FPS per
DIMM, 14.92ms mean frame-command latency and 24.79ms maximum inter-DIMM completion
skew. Requested rate was 20 FPS; this does not demonstrate 20 FPS or simultaneous
physical LED presentation. Mint Twinkle used speed 65%, brightness 40%.
Scope: Intel 8086:7f23, macUSPCIO, four Corsair Titanium PID 0801 / protocol 4
controllers at RGB addresses 0x18–0x1B, twelve LEDs per DIMM. Other kits/hosts and
long-duration animation stability remain unverified.

### App integration follow-up

The app build now uses the physically tested paced block helper. A UI selection
bug was corrected: status polling previously removed RAM from the selected set
even after an explicit successful probe. Startup still excludes RAM, while manually
selected verified DIMMs now remain selected during normal polling. Probe resumes
previously selected non-RAM output without automatically selecting/lighting RAM.
Settings and installer text now describe mint Twinkle at 65% speed rather than
the obsolete white-startup policy. Combined-device physical soak testing is pending.

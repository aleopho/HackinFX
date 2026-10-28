# Shared-clock effect library

HackinFX renders 41 effects and 82 curated looks from one monotonic scene clock.
`effects.py` is the hardware renderer; `EffectLibrary.swift` mirrors the same
math for native previews. `tools/verify_effect_previews.py` compares both.

## Refined canvas engine

All effects sample physical canvas coordinates. Device-local LED indices no
longer seed particles, palette choices or flicker: a canvas point returns the
same color regardless of which device samples it. Mirror mapping repeats the
same normalized field per device; Canvas mapping follows device placement.
Different physical positions are intentionally different colors, not a loss of
synchronization. Transport latency and hardware refresh limits still apply.

Palette transitions use smooth interpolation. Particle envelopes, trails,
scanners, waves and atmosphere effects have broader, continuous movement rather
than narrow flashes and abrupt wraparound. The MAKR 75 reference layout now
contains distinct staggered positions for every key, preserving all verified
RGB packet offsets and the separate dial ring.

Fireplace uses an advected multi-scale flame field, with deep red, burnt orange
and amber. Its fixed warm gradient deliberately avoids white-hot and blue
flashes. Brightness, speed, scale and direction remain available.

The gallery uses original procedural illustrations above a continuous effect
field. Gallery art is illustrative, never LED readback. Reduced Motion pauses
its animation. No SignalRGB effect source, stock photographs or remote assets
are included. Canvas concepts were reviewed in SignalRGB's public developer
documentation: https://docs.signalrgb.com/lightscripts

## Legacy PNY onboard protocol reference

The following documents the standalone GPU protocol. Shared-clock effects in
Lighting use host-rendered Direct frames instead of independent onboard clocks.

Protocol adaptation from OpenRGB PNYLovelaceGPUController.cpp by yufan (2023),
GPL-2.0-or-later; reviewed 2026-10-23:
https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/PNYLovelaceGPUController.cpp

All writes use the verified register 0x02 at 7-bit address 0x60, RM port 1.
Packet construction:
- static: 06 ff zone 00 R G B, zone 0–2
- gradient: static packet per zone with three independent colors
- cycle: 03 brightness (0xb2-speed) 00 aa 00 00
- breath: 02 ff (0x19-speed) 01 R G B
- wave: 04 brightness (0xbf-speed) 00 aa 00 00
- off: seven zero bytes

GUI speed is linearly mapped from 0–100 to the upstream mode's valid range.
RGB brightness is scaled for static/gradient/breath, without changing the source
color in the picker. Cycle/wave use their brightness byte. No flash mode included.
The previous single-LED CLI behavior remains the default for static mode.

The hardware carries out animation; the app sends one effect packet, not an
animation loop. Effects may persist after app termination. Apply static to replace
them. Every apply creates a separate JSON report, with stop-on-first-error.

Static, Gradient, Spectrum, Breathing and Wave have been visibly confirmed by
the user on the PNY 10de:2704 / 196e:13bc development configuration. Off and the
physical mapping of each zone remain unconfirmed. This is a three-zone color arrangement, not a claim of arbitrary
per-LED gradients. Hardware support for other GPUs is not inferred from these
packets or from their PCI vendor.

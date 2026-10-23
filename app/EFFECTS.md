# PNY effects, 0.4.0

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

# HackinFX 2.7.0 — Lighting Studio + Android Remote

A unified lighting workspace for x86-64 Hackintoshes running macOS 15 or later.

## Individual device brightness
Each controllable device now has its own live brightness slider on desktop device cards and in device details. Android Remote exposes the same control. Device brightness multiplies master brightness: 80% master × 50% device = 40%. It does not change effect speed or the shared clock. Levels persist for uniquely identified devices. Identical devices without a distinct persistent identity keep independent levels for the current session.

## Included upgrades since 2.4.0
- Native Android Remote 1.2.0: encrypted same-network pairing with QR or pasted pairing details, device selection/brightness, effect gallery, 80 curated looks and private crash diagnostics. The camera flow was replaced after a reported launch crash. Physical phone pairing/camera validation is still required; errors are now shown explicitly.
- MAKR 75: 81 keys plus six dial-ring LEDs, documented interface-2 volume handling. The user confirmed the volume knob works with HackinFX. Fixed-volume digital outputs may not expose a software volume scalar.
- Automatic native USB topology refresh preserves scene timing and existing deselections; compatible new devices join. OpenRGB hotplug still depends on the controller implementation and the device list it exposes.
- RAM startup authorization with normalized physical identity, persistent revocation reasons and bounded RGB-only migration for the two previously verified Titanium SKUs on the exact supported Intel host. No SPD/timing/voltage writes. Bus faults still stop control and require manual validation.
- 22 offline desktop language variants, a cleaner workspace, Canvas background rendering from the shared effect clock, and a read-only WidgetKit loopback data feed. Translations need community review. Actual desktop widget refresh behavior remains unconfirmed.

## Install
Quit HackinFX and install the PKG. Leave the optional OpenCore driver component unselected if your RAM driver already works. This update does not require an EFI change. The application is ad-hoc signed; it is not Developer ID signed or notarized.

Install the signed Remote APK on Android 8 or later. Open desktop Settings → Android Remote, enable local control and generate a new pairing code. Both devices must use the same local network. Allow local-network/firewall access if prompted. Windows is deferred and is not part of this release.

## Credits
aleopho and contributors; OpenRGB; NullMoth (external NVIDIA driver); OpenLinkHub / Nikola Jurkovic; Nanoleaf protocol contributors and the upstream dependencies listed in THIRD-PARTY-NOTICES.md. Combined application: GPL-3.0-or-later; bundled components retain their original notices and corresponding sources.

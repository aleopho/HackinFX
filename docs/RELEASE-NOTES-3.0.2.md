# HackinFX 3.0.2 — Lighting Studio

A major desktop and Android upgrade from 2.7.0.

## Effects and Canvas

- Rebuilt shared-clock effect formulas with smooth palette interpolation, broader particle envelopes and spatial consistency across devices with different LED counts.
- New Fireplace: deep red, burnt orange and amber, with continuous rising flame/ember movement and no white-hot flashes.
- 41 effects and 82 curated looks, themed animated gallery illustrations and larger cards.
- Corrected physical MAKR 75 key positions; all 81 key payload offsets and the six-LED dial ring are preserved.
- Layer Studio composes a base plus four layers using Screen, Add, Multiply or Normal blends and independent opacity/palette/speed.
- Canvas rotation, size and mirror transforms; per-device RGB gains, gamma and brightness.
- Independent native HID collection channels reduce cross-device blocking. 60 FPS host target respects hardware limits; Nanoleaf retains interpolated 10 Hz packets. Exact physical synchronization is not guaranteed.

## Reliability and identity

- Graceful Core shutdown drains output before helper teardown; shutdown-only pipe interruption preserves a saved RAM profile. Real bus errors still revoke it.
- RAM setup reports stored validation failures, including the unexpected identity fields. Exact inventory, identity and CRC checks remain mandatory. No SPD, firmware, voltage, timing, fan or pump commands were added.
- A development setup briefly reported one 0800/protocol-1 controller among three 0801/protocol-4 controllers. The mismatch correctly blocked output; all four worked again after a cold power cycle. This remains a troubleshooting limitation, not newly enabled protocol-1 support.
- New original orbital FX app icon and matching menu-bar template mark.

## HackinFX Remote 2.0.1

- Redesigned dark/mint native Android workspace, color wheel, device brightness, effect gallery and Layer Studio controls.
- Corrected bottom-navigation caption alignment and text metrics.
- Same application ID and signing identity for upgrades; existing local pairing and TLS pinning retained. Phone camera/pairing behavior still requires device-specific testing.

## Downloads and installation

Quit HackinFX, then run the PKG installer or use the DMG to replace the app in Applications. macOS 15 or later, x86-64 Hackintosh; Intel and AMD CPUs are in scope. Apple Silicon is not targeted.

The optional OpenCore SMBus component is separate and not needed for USB lighting. Existing working RAM users do not need to reinstall the driver. Saved profiles remain under Documents/HackinFX. If an older version removed RAM authorization, perform one successful RAM Probe; never bypass an unexpected identity or bus error.

Apps and helpers are ad-hoc signed, without Developer ID notarization. macOS may require approval. The Android APK is signed with the existing project key.

## Validation and credits

246 hardware-free Python tests and 2,214 Python/Swift effect samples passed locally; Android tests, native-graphics layouts, lint and release build passed. Installer expansion and nested signatures were verified. Automated tests do not measure actual LED frame rate or optical synchronization. The maintainer confirmed all four development DIMMs operating after recovery.

GPL-3.0-or-later combined distribution; original upstream license notices remain included. OpenRGB, NullMoth, OpenLinkHub and other contributors are credited in the repository, app and bundled corresponding sources. Effect formulas and gallery art are original; SignalRGB's public Canvas documentation informed the design without importing its effect code or assets.

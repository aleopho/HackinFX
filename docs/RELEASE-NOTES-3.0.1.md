# HackinFX 3.0.1 and Remote 2.0

## Desktop

- Independent native HID helper/RPC channels per lighting collection remove cross-device head-of-line blocking. A slow wireless mouse no longer holds the same RPC mutex as a keyboard, cooling RGB controller or LampArray device.
- Host output defaults to 60 FPS. Device-reported LampArray minimum intervals are respected with a 60 Hz software ceiling, replacing the previous unconditional 20 Hz ceiling. Nanoleaf's 10 Hz packets and panel-side interpolation remain unchanged. Physical transport limits still apply; 60 FPS is a target, not a universal hardware guarantee.
- Quit requests stop/drain the Core before the app exits. The Core signals output workers immediately before closing network services or helpers. A helper pipe closing during explicitly requested shutdown preserves the verified RAM profile. Real bus errors still revoke it.
- The UI now shows a stored RAM revocation reason instead of presenting every revoked profile as a first-time setup.
- New code-owned monochrome orbital FX icon and matching template menu-bar mark.

If an earlier version already deleted a verified RAM profile while quitting, perform one successful RAM Probe in this version to recreate it. Subsequent starts still validate the physical inventory and RGB controller identity. No SPD, firmware, timings, voltage, fan or pump commands were added.

## Android Remote 2.0

- Redesigned dark/mint native workspace with an animated composition cover, orbital branding, icon navigation and clearer device cards.
- Color wheel with exact hex entry; existing brightness, speed, effects, saved looks and secure pairing retained.
- Layer Studio edits the Mac's base effect and up to four additional layers, including blend, opacity, color and speed.
- Host-only targets are selected for layered scenes; hardware setup remains on the Mac.
- Reduced-motion system settings suppress navigation/press animations and animated effect illustrations.
- Existing Android package ID, signing identity, pairing storage and TLS pinning are preserved for upgrades.

## Verification

242 hardware-free Python regressions cover the shared renderer, protocols, profile persistence, shutdown fault classification and independent HID channels. Android unit/lint/build checks and native-graphics UI tests render all five Remote pages with explicit fixture data. These checks do not replace real-device pairing, camera or lighting validation. The frame-rate improvement and RAM restart behavior need verification on the user's physical setup.

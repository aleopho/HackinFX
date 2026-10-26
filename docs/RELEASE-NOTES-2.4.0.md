# HackinFX 2.4.0 — Effect Gallery

A shared library of **40 distinct effect algorithms** and **80 curated looks**
replaces the nine-effect picker. Browse Essentials, Motion, Atmosphere, Particles
and Geometry, search the library, favorite cards locally and save custom looks.
Animated cards use the same effect formulas as the hardware renderer, verified
with a cross-language sample test. Reduce Motion pauses animated previews.

New patterns include Fire, Candlelight, Ocean, Ice, Plasma, Nebula, Fog, Heartbeat,
Ripple, Scanner, Bounce, Orbit, Meteor Shower, Starfield, Fireflies, Rain,
Digital Rain, Confetti, Fireworks, Snowfall, Stripes, Checkerboard, Spiral,
Pinwheel, Vortex, Radar, Marquee, Chase, Pulse and Rainbow Wave.

Speed, brightness, motion scale, density, reverse, palette and spatial mapping can
be tuned. Color generation and some controls depend on the effect. Saved looks
restore their full configuration; built-in cards preserve current brightness and
device selection. Existing saved scenes receive compatible defaults. Mint Twinkle
at 65% speed remains the startup look; its default sparkle curve is retained.

The app starts in a larger workspace (up to 1380×940 points) clamped to the display.
Lighting keeps a compact selector and opens the gallery on demand. The Effects
page is the full gallery with animated cards and live controls.

Includes the preceding Shapes/Scope/Radius integration: automatic local Nanoleaf
Shapes pairing (user-confirmed working), wired Scope ISO-203 / 102-LED mapping,
acknowledged atomic Radius frames, jitter metrics and estimated presentation-delay
compensation. Other physical behavior remains subject to device/transport limits.

All effects use the existing host-rendered output path. No driver, firmware,
OpenCore, SPD or new hardware command path is added by the gallery. Preview cells
illustrate the algorithm, not a physical LED readback or guaranteed output FPS.
Sources, existing OpenRGB/NullMoth/macUSPCIO/Radius credits and licenses remain included.

Android remote control is the next planned phase, not included or exposed here.
The app's control API remains authenticated and bound to localhost only.

Validation: 191 Python tests, 2,160 native-preview/renderer comparisons, native
helper self-tests, actual WidgetKit build, nested signatures and PKG/DMG checks
passed. The developer confirmed the installed update runs well before publication.

Downloads include PKG, drag-and-drop DMG, source ZIP and SHA-256 checksums.
OpenRGB, NullMoth, macUSPCIO and other third-party license notices remain bundled;
NullMoth is a separately installed driver. macOS 15+ x86-64; Intel and AMD CPU
Hackintosh systems in scope, with hardware-specific adapter limits as documented.

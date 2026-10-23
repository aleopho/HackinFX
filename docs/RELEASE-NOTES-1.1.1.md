# HackinFX 1.1.1 — by aleopho

macOS 15 or later · x86-64 Hackintosh (Intel or AMD CPU)

- Correct DMG creation so nested WidgetKit signatures are preserved. The prior hybrid image could add FinderInfo attributes that invalidate code-signature verification after copying the app.
- Verify both the mounted image app and a copied installation before publishing.
- Remove the stale PREVIEW footer.
- Clearer button press/release animation, effect selection transitions and moving navigation highlight. Reduce Motion is respected.
- Widget fallback explains how to populate the status when no snapshot can be read. The widget shows GPU, last applied mode, palette and supported brightness once data is available.
- Updated README, genuine screenshot supplied by aleopho and current compatibility information.

The app and widget remain ad-hoc signed, not Developer ID signed or notarized. A valid ad-hoc signature does not guarantee warning-free Gatekeeper acceptance. No quarantine flags or macOS security controls are modified.

Quit the old app through the menu bar, replace it in Applications, launch it and apply a lighting mode. Remove and re-add an existing blank widget if macOS retains the previous extension instance. Actual widget gallery/data behavior still requires normal desktop testing.

Controller coverage is unchanged: 38 exact NVIDIA test candidates across PNY Lovelace, EVGA Pascal and ASUS Aura; physical user confirmation determines tested status. Profiles remain in ~/Documents/HackinFX/.

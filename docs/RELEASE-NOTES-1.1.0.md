# HackinFX 1.1.0 — by aleopho

**macOS 15 or later · x86-64 Hackintosh (Intel or AMD CPU)**

- Refined Lighting Studio, accessible Apply/Off controls and subtle button feedback that respects Reduce Motion.
- Real WidgetKit widget: GPU model, last successfully applied mode, color palette and brightness where supported. WidgetKit controls refresh timing; this is not live LED readback.
- OpenRGB identity catalog: 752 exact PCI tuples. Lighting-test implementations for 38 configurations: 12 PNY Lovelace, 5 EVGA Pascal and 21 NVIDIA ASUS Aura.
- Controller-specific automatic startup tests. Successful visual user confirmation saves a local profile and queues a community database submission; a matching local profile skips the test next time.
- Exact model/vendor display, with user-supplied corrections preserved in local profiles and submissions.
- GPL-2.0-or-later source, OpenRGB/NullMoth/NVIDIA attribution and corresponding source included.

## Compatibility

The original PNY XLR8 RTX 4080 VERTO is physically user-tested. The additional PNY, EVGA and ASUS configurations are implemented test candidates, **not 38 physically verified cards**. Available modes vary by controller; other OpenRGB families are recognized but do not yet have a macOS lighting driver. ASUS requires its controller signature before lighting writes. AMD/Intel GPU transports and RAM RGB are later work.

The genuine widget is built and packaged, but ad-hoc-signed gallery registration and refresh behavior still require broader desktop validation. The app is ad-hoc signed, not Developer ID signed or notarized; macOS may warn when opening downloads. A compatible separately installed NullMoth/NVRM driver and /usr/bin/python3 are required. AMD CPU operation has not been physically validated.

## Install

Quit the running HackinFX from its menu-bar menu. Open the DMG, drag HackinFX.app to Applications, replace the older app, then launch it. Add the widget using the desktop’s Edit Widgets gallery. Apply a lighting mode once to populate the new widget color fields.

Checks: 53 Python tests, 25 Swift assertions, 12 backend tests, SQLite schema test, genuine WidgetKit build, entitlement/signature checks and DMG verification. New EVGA/ASUS hardware was not physically tested by the agent.

Confirmed profiles are saved in the current user’s `~/Documents/HackinFX/` directory, one JSON file per hardware fingerprint. Existing matching profiles are migrated automatically.

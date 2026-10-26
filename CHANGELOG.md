# Changelog

## 2.1.1 — 2026-10-26

- Expand HackinFX into a multi-device Lighting Studio with bundled OpenRGB 1.1, native NVIDIA and USB/HID paths.
- Live controls, nine effects, Canvas placement and editable Effect Studio palettes/parameters.
- Shared-frame mirrored group output with a frame barrier and measured command-duration compensation; USB rate limits no longer silently skip group frames.
- Host-rendered whole-keyboard ASUS colors, Radius preview renewal and corrected startup selection/white.
- Lighting-first navigation, menu-bar lifecycle, launch at login and startup/manual software-update checks.
- Feedback with fresh allowlisted system specifications, user notes, review, explicit private submission and export.
- Rebuilt Core-fed WidgetKit view; actual desktop registration/refresh needs wider validation.
- Optional backed-up OpenCore transport installation recognizes GPT and FAT/MBR boot volumes. **RAM remains non-working on the development system.**
- Refresh repository documentation, current fan branding, real desktop screenshot, licenses and regular-release packaging.

[Release details and known limits](docs/RELEASE-NOTES-2.1.1.md).


## 1.1.1

- Preserve nested WidgetKit signing through native DMG creation; verify mounted and copied app signatures.
- Replace the stale PREVIEW footer with the release number.
- Add visible press/rebound/highlight animations and effect/navigation transitions, respecting Reduce Motion.
- Update repository description and genuine 1.1.0 screenshot; preserve source/license credits.


## 1.0.0 — 2026-10-23

Initial public community release by aleopho.

- Native English SwiftUI/AppKit lighting studio and persistent menu-bar controls.
- Thin two-fan GPU line icon, dark interface and subtle reduced-motion-aware intro.
- Visible automatic inventory and seven-stage first-run lighting validation.
- Full visual confirmation before local profile reuse; exact hardware/driver/OS matching.
- Separate GPU/board identity and manual model correction with origin metadata.
- Static, three-zone Gradient, Spectrum, Breathing, Wave and Off controls for the exact PNY XLR8 RTX 4080 VERTO subsystem.
- Durable optional community-confirmation queue with retry and automatic public catalog aggregation.
- Reviewed private troubleshooting uploads and local diagnostics export.
- Cloudflare Worker/D1 source, tests, schemas and retention policy.
- Ad-hoc signed x86-64 app and drag-and-drop DMG, corresponding source and license notices.

Limits: one supported RGB profile, no universal controller discovery or remote driver installation; Off not separately visually confirmed; native first-run/install and Sequoia/Tahoe desktop checks remain outstanding. This release does not have Developer ID/notarization or email report notifications.

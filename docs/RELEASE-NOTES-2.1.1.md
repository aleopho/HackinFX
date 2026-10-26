# HackinFX 2.1.1 — Lighting Studio

HackinFX now brings multiple RGB device classes into one native macOS workspace,
with the bundled OpenRGB 1.1 engine and native NVIDIA / USB adapters.

## Highlights

- Lighting, Devices, Canvas and a parameter-editable Effect Studio.
- Nine live effects, palette editing, brightness, tempo and direction; no Apply.
- Shared-frame group rendering with mirrored output by default, measured command-
  duration compensation and USB pacing that waits instead of dropping frames.
- Native ASUS whole-keyboard color, Spatha X, HID LampArray and Radius paths,
  alongside available OpenRGB macOS drivers and confirmed native NVIDIA profiles.
- White at app/login startup, menu-bar persistence and software-update checks.
- Loopback Core startup avoids unnecessary reverse DNS that can delay discovery.
- Feedback with a fresh allowlisted system scan, user description, JSON review,
  explicit private submission/receipt and local export.
- Rebuilt WidgetKit state: mode, palette, brightness, GPU, ready count and status.
- Optional OpenCore SMBus transport setup with EFI backup, GPT/MBR boot detection,
  constrained config edit and rollback.

## Download and upgrade

Use **HackinFX-2.1.1-Installer.pkg**, or the DMG for drag-and-drop installation.
Quit the existing app before upgrading. macOS **15 or later**, **x86-64**; Intel
and AMD CPU Hackintoshes are in scope. No ARM build. Native NVIDIA lighting
requires the separately installed NullMoth NVRM driver. System Python 3 is required.
The complete tagged source and SHA-256 checksums are attached.

Remove old diagnostic widgets and re-add HackinFX after launching the new app.
The optional RAM component is unnecessary for normal USB lighting. Read
[RAM setup/recovery](https://github.com/aleopho/HackinFX/blob/v2.1.1/docs/RAM-SETUP.md)
before enabling it, and reboot after installation.

## Known limits

- **RAM RGB is not yet working on the development system.** The included scoped
  development transport is not a general RAM support claim.
- Detection/catalog identity is not proof of working lighting. Other native GPU
  candidates require exact matching and visual confirmation. Windows/Linux
  OpenRGB support does not imply an available macOS transport.
- Group throughput follows the slowest output. Command timing is not optical LED
  measurement; firmware/wireless buffering can still affect visible alignment.
- Native ASUS keyboard control is whole-keyboard RGB, not per-key mapping.
- Radius is user-reported working; sustained color and firmware variants need
  wider validation. Widget desktop rendering/refresh also needs wider testing.
- White applies after sign-in/discovery, not before the macOS login screen.
- Private reports use the configured HTTPS inbox; SourceForge tickets are not
  integrated. Reports need triage rather than automatic driver implementation.
- Ad-hoc signed, not Developer ID signed or notarized. macOS may request approval.

## Validation and credits

150 Python tests plus backend/schema, native helper/profile/version, catalog,
WidgetKit, signature, installer and DMG checks. Automated checks do not replace
physical-device validation.

Created by **aleopho**. Thanks to **OpenRGB and its contributors, NullMoth Systems,
NVIDIA, Radius/rigstats contributors, macUSPCIO, Qt and runtime dependency authors**.
Original licenses and notices are preserved. HackinFX application source is
GPL-2.0-or-later; dependencies retain their own terms. NullMoth's NVIDIA driver
is separate and not redistributed. See
[full licensing inventory](https://github.com/aleopho/HackinFX/blob/v2.1.1/THIRD-PARTY-NOTICES.md).

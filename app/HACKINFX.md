# HackinFX 2.0.3 — by aleopho

Requires macOS 15 or later. Native GPU-lighting app for x86-64 Hackintosh systems (Intel or AMD CPU; AMD-CPU operation is not yet physically validated). Locally ad-hoc codesigned, not Developer ID
signed or notarized. Local codesign does not guarantee warning-free launch of a
downloaded app. No security settings or quarantine flags are modified.

## Control Center and installation

Install the PKG into Applications, then launch HackinFX. Under Customize, the
optional OpenCore SMBus driver component detects the boot EFI, backs up the
complete EFI and adds/enables macUSPCIO in the existing config. Ambiguous EFI
layouts stop without writes. Reboot after installing the driver. No SIP changes
or immediate kext loading. See Source/docs/RAM-SETUP.md for recovery and limits.

The full official OpenRGB 1.1 macOS CLI driver set is bundled and managed by the
app. No separate OpenRGB install is required. Native drivers reserve matching
controllers to avoid concurrent writes. Devices need a real working controller;
identity catalog entries alone cannot enable control.

Ready non-RAM devices start mint Twinkle at 65% speed once per app/Core session. RAM requires explicit probe and selection.
Unconfirmed native GPUs and inventory-only devices are not written. Live edits
replace the Apply step. Static, Gradient, Spectrum, Breathing, Wave, Aurora,
Comet, Twinkle and Color shift are available according to device capabilities.
Autostart runs after macOS sign-in and may require Login Items approval.

Settings offers Launch at login and Check for Updates. Advanced tools contain
the native GPU lab, diagnostics and credits. Profiles/scenes are saved in
~/Documents/HackinFX. Closing the window keeps the menu-bar app running.

## Native GPU startup check

A visible hardware check reads GPU vendor/model, board vendor, driver binding
and the configuration fingerprint. A matching confirmed profile skips its
visual lighting test. Unknown identities remain inventory-only until an actual
controller/transport exists. Board/model names can be corrected manually.

## Setup

Without a matching local confirmation, a known controller automatically starts a visible guided test after inventory. The test runs red, green and blue, followed by each effect implemented for the detected controller. It ends with the final effect running.
Changing an effect or color applies it automatically. Each lighting operation stops on driver failure.

“All tests worked” requires completed transport calls plus the user's visual
confirmation. It saves a local profile and a compatibility entry for the detected
PCI subsystem, vendor and tested functions. Partial or failed tests remain failures:
users describe missing zones, incorrect colors, errors or no light in the text field.
Notes and bounded command evidence are saved to a local troubleshooting draft.
Review / send report shows the exact private report before any manual upload.

Profiles are reused only when the hardware/driver/OS fingerprint matches. Failed
retests suppress reuse without deleting the old record. Test again remains available.
Old basic-RGB profiles remain readable but require the complete test before reuse.

## Growing compatibility database

A separate catalog holds user-confirmed hardware. On full confirmation it updates
locally without maintainer approval. The contribution checkbox controls whether a
small structured confirmation is queued for the shared database. Its state persists.
The confirmation includes card/vendor/subsystem IDs, module, tested effects, software
environment and a random installation ID for deduplication. No troubleshooting notes,
serial numbers, hostname or raw device tree are included. Sharing can be turned off.

An enabled inbox automatically receives queued confirmations; failures keep them
locally for later retry. The shared catalog is fetched when connected and cached.
The server upserts one row per installation/card, so retries do not inflate counts.
Successful user confirmations enter the public compatibility catalog automatically.
They are self-reported observations, not independently audited certifications.
Remote catalog entries never enable hardware writes or executable code.

A suitable local controller/transport module is still required to test a new GPU.
Unsupported hardware opens the scanner and cannot send lighting commands. A public
community claim alone never bypasses that guard. Module implementation is necessary
before previously unknown RGB protocols can work.

The Cloudflare inbox is deployed and live-tested. report-endpoint.json contains the real HTTPS /reports URL. Confirmations upload automatically when sharing is enabled; private troubleshooting reports require Review and Send. The account owner reads reports through the authenticated D1 dashboard. No email notifications are configured.

## Confirmed development device

PNY XLR8 RTX 4080 VERTO — NVIDIA 10de:2704 / PNY 196e:13bc.
User-confirmed: Static, Gradient, Spectrum, Breathing, Wave.
Environment reported previously: Intel macOS 26.7.1, NVRM bundle 2.5.2.
Off is implemented but has not been explicitly visually confirmed.

## Interface and reports

The 2D line icon has editable SVG source and a CoreGraphics renderer. It uses no
3D effects. The prior generated neon icon is retained in source assets only.

Closing the window hides the Dock icon and keeps the FX menu running. Open Lighting
restores it; Quit exits. Colors and effects are sent only on explicit Apply/menu
commands or during the visible automatic first-run setup test. A matching saved profile skips that lighting sequence; passive inventory still runs at every start.

Data is local under ~/Library/Application Support/HackinFX:
- compatibility.json: local user-confirmed hardware
- VerificationQueue: unacknowledged community contributions
- Reports / Scans / Troubleshooting: diagnostic files
The reusable setup and sharing preference are stored in this app's preferences.

## Source, packaging and validation

Build: python3 -B build_community.py (Xcode command line tools required).
DMG: python3 -B package_dmg.py. The image contains the app, Applications symlink and
installation notes. The build uses the existing /usr/bin/python3 at runtime.
No Apple Developer account or notarization step is used.

App/source licenses and OpenRGB, NullMoth and NVIDIA credits are bundled. NullMoth
is a separately installed dependency. See LICENSE.md, COPYING and NOTICE.txt.
Native deployment target: macOS 15.0, x86_64. The icon and APIs do not depend on
Tahoe-only rendering; interactive Sequoia validation has not been performed.

Live Cloudflare tests passed for real storage receipts, duplicate retries, confirmation upserts, public aggregation and private report read rejection. Synthetic records were removed. The native UI compiles, but interactive first-run, visual test dialog and Sequoia installation still require a check outside Codex; the sandbox cannot render native AppKit windows.

Missing board/model identity opens editable fields. User corrections are stored with the PCI identity, reported to the database as user-supplied, and retain the original detected model as additional private metadata. Remote confirmations never install a new RGB driver.

Confirmed profiles are saved in the current user’s `~/Documents/HackinFX/` directory, one JSON file per hardware fingerprint. Existing matching profiles are migrated automatically.

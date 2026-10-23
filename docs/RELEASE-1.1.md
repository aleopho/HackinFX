# HackinFX 1.1.0: design, GPU controllers and WidgetKit

HackinFX 1.1.0 requires macOS 15 or later. Controller implementation and physical user verification are separate; the full OpenRGB catalog is not a claim of universal RGB control.

## Interface

Redesigned dark graphite surface, clearer type hierarchy, larger navigation with single-line labels, a controller schematic, refined effect selectors and a pinned action/status footer. The window is resizable with a minimum usable content size. Apply/Off remain reachable when content scrolls. The schematic remains an illustration, not hardware feedback.

## OpenRGB identity import

The importer reads pinned GPU detector sources at OpenRGB commit 817834cfab034c97927451e31c4a2deb60a44725. It deterministically produces **769 PCI registrations, 752 unique PCI tuples, 25 GPU controller families and one separate USB identity**. The snapshot preserves source paths, original headers and per-file SHA-256 hashes in vendor/openrgb. GPL-2.0-or-later attribution remains in force.

This covers the selected upstream GPU detector families, not every peripheral supported by OpenRGB. Entries come from PCI/I2C registrations and the NVIDIA Illumination PCI table. Intel Arc's HID identity remains separate; no USB controller is inferred solely from an unrelated PCI ID.

Exact tuples resolve to upstream names and candidate controllers. Reused PCI tuples retain all aliases/controllers and are marked ambiguous; an arbitrary precise marketing name is not invented. Unknown subsystem IDs do not inherit a close model. Known entries are displayed as catalog matches when a local macOS lighting module is missing.

**NVIDIA-first controller work:** exact, unambiguous OpenRGB PNY Lovelace registrations can now enter the existing NVIDIA/NullMoth lighting test with the shared PNY protocol. Only the original PNY card has been physically tested by the author; other entries are candidates until the user confirms the visible test. EVGA Pascal is also implemented below; other NVIDIA families remain pending. Upstream names/address registrations do not prove a working macOS transport, RM port mapping, controller identity or effects. Broad automatic testing needs controller modules and suitable native transports. A catalog match never bypasses those guards. The catalog supplies identity metadata; executable lighting tests require an implemented macOS controller.

Rebuild offline: python3 tools/import_openrgb_catalog.py. It rejects changed upstream inputs and unresolved numeric symbols instead of silently omitting registrations. It never executes C++ or downloads anything.

## Real macOS widget

app/Widget contains a real Xcode WidgetKit app-extension target, not an NSPanel substitute. Small/medium widgets show card/profile state and the last successful lighting command, labeled LAST SENT rather than live readback. Links open HackinFX Studio/Hardware; clicking a widget does not send GPU writes. A JSON snapshot in a dedicated Widget subdirectory excludes reports, notes, credentials and installation IDs.

The extension uses App Sandbox with a narrow read-only home-relative exception for Library/Application Support/HackinFX/Widget. It does not request an App Group or invent a Team ID. The host writes an atomic snapshot and requests timeline reloads; WidgetKit controls refresh frequency. A timestamp in the medium widget makes stale data visible.

Building the compiled extension requires a full Xcode installation, but no Apple account is configured by the build script. Command-line-tools-only local builds include the source but omit the extension unless HACKINFX_WIDGET_PATH points to a separately Xcode-built .appex. CI verifies the real extension exists before producing the release DMG. The app and widget both require macOS 15 or later.

Ad-hoc WidgetKit gallery registration, snapshot access, timeline updates, deep links, and actual Sequoia/Tahoe behavior still require normal desktop testing. No signing, provisioning or quarantine bypass is performed. If the genuine extension cannot be made reliable under the project's distribution constraints, omit it; do not ship a floating-window replacement.

## Checks

53 Python tests cover transport/scanner and the catalog importer/lookup. 25 Swift assertions include profile/queue and widget snapshot handling. Backend tests remain separate. Native app/widget packaging is checked in GitHub Actions. No new GPU writes or physical controller tests were performed by this change.

The widget now displays the last successfully applied mode, its color palette, brightness and GPU model. Unapplied UI changes and failed commands do not change the snapshot. Spectrum/Wave use a schematic rainbow; this is not an animation or live LED readback.


### Additional NVIDIA vendor: EVGA

Exact OpenRGB EVGA Pascal PCI registrations now use the EVGA GPU v1 volatile register protocol over the existing NVIDIA/NullMoth transport. Static, Spectrum and Breathing are available; Gradient/Wave and hardware speed are not offered. Spectrum brightness is controller-defined. The start test and confirmation payload contain only that controller's effects. No EVGA hardware has been physically tested yet, so these remain test candidates, not author-verified cards. Other NVIDIA families still require their own controller ports.

Future roadmap (not this release): RAM RGB as a separate device type. AMD and Intel GPU transports follow the NVIDIA work.


### Additional NVIDIA vendor: ASUS

21 exact NVIDIA ASUS Aura registrations at address 0x29 are test candidates. The transport requires a matching 0x1589 controller signature at registers 0x20/0x21 before any lighting write. Static, Spectrum and Breathing are offered. Off uses black Static (the upstream Off mode is not functional); the explicit save/apply register is never written. Speed and Spectrum brightness are controller-defined. This is an untested macOS port, not a physical compatibility confirmation. Other Aura variants/addresses are not inferred.

Release: **1.1.0**. The three implemented NVIDIA controller families cover 38 exact PCI configurations as test candidates, not 38 physically verified cards.

Confirmed local profiles are stored per user at `~/Documents/HackinFX/profile-<hardware-fingerprint>.json`. Existing matching confirmations are migrated from the former preferences storage. Profile files include GPU/model, board vendor and confirmed effects. Widget snapshots and private troubleshooting queues remain in Application Support.

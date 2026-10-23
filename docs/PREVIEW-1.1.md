# 1.1 preview: design, GPU catalog and WidgetKit

This is a development preview, not a claim that all OpenRGB GPU controllers now work on macOS. The stable release remains 1.0.0 until normal desktop validation.

## Interface

Redesigned dark graphite surface, clearer type hierarchy, larger navigation with single-line labels, a controller schematic, refined effect selectors and a pinned action/status footer. The window is resizable with a minimum usable content size. Apply/Off remain reachable when content scrolls. The schematic remains an illustration, not hardware feedback.

## OpenRGB identity import

The importer reads pinned GPU detector sources at OpenRGB commit 817834cfab034c97927451e31c4a2deb60a44725. It deterministically produces **769 PCI registrations, 752 unique PCI tuples, 25 GPU controller families and one separate USB identity**. The snapshot preserves source paths, original headers and per-file SHA-256 hashes in vendor/openrgb. GPL-2.0-or-later attribution remains in force.

This covers the selected upstream GPU detector families, not every peripheral supported by OpenRGB. Entries come from PCI/I2C registrations and the NVIDIA Illumination PCI table. Intel Arc's HID identity remains separate; no USB controller is inferred solely from an unrelated PCI ID.

Exact tuples resolve to upstream names and candidate controllers. Reused PCI tuples retain all aliases/controllers and are marked ambiguous; an arbitrary precise marketing name is not invented. Unknown subsystem IDs do not inherit a close model. Known entries are displayed as catalog matches when a local macOS lighting module is missing.

**NVIDIA-first controller work:** exact, unambiguous OpenRGB PNY Lovelace registrations can now enter the existing NVIDIA/NullMoth lighting test with the shared PNY protocol. Only the original PNY card has been physically tested by the author; other entries are candidates until the user confirms the visible test. This is not yet cross-vendor NVIDIA RGB support. Upstream names/address registrations do not prove a working macOS transport, RM port mapping, controller identity or effects. Broad automatic testing needs controller modules and suitable native transports. A catalog match never bypasses those guards. This preview establishes broader identification and auditability; it is not the completed universal-light-test feature.

Rebuild offline: python3 tools/import_openrgb_catalog.py. It rejects changed upstream inputs and unresolved numeric symbols instead of silently omitting registrations. It never executes C++ or downloads anything.

## Real macOS widget

app/Widget contains a real Xcode WidgetKit app-extension target, not an NSPanel substitute. Small/medium widgets show card/profile state and the last successful lighting command, labeled LAST SENT rather than live readback. Links open HackinFX Studio/Hardware; clicking a widget does not send GPU writes. A JSON snapshot in a dedicated Widget subdirectory excludes reports, notes, credentials and installation IDs.

The extension uses App Sandbox with a narrow read-only home-relative exception for Library/Application Support/HackinFX/Widget. It does not request an App Group or invent a Team ID. The host writes an atomic snapshot and requests timeline reloads; WidgetKit controls refresh frequency. A timestamp makes stale data visible.

Building the compiled extension requires a full Xcode installation, but no Apple account is configured by the build script. Command-line-tools-only local builds include the source but omit the extension unless HACKINFX_WIDGET_PATH points to a separately Xcode-built .appex. CI verifies the real extension exists before producing the widget preview DMG. The widget targets macOS 14+, while the host app keeps a macOS 13 minimum.

Ad-hoc WidgetKit gallery registration, snapshot access, timeline updates, deep links, and actual Sequoia/Tahoe behavior still require normal desktop testing. No signing, provisioning or quarantine bypass is performed. If the genuine extension cannot be made reliable under the project's distribution constraints, omit it; do not ship a floating-window replacement.

## Checks

48 Python tests cover transport/scanner and the catalog importer/lookup. 20 Swift assertions include profile/queue and widget snapshot handling. Backend tests remain separate. Native app/widget packaging is checked in GitHub Actions. No new GPU writes or physical controller tests were performed by this change.

The widget now displays the last successfully applied mode, its color palette, brightness and GPU model. Unapplied UI changes and failed commands do not change the snapshot. Spectrum/Wave use a schematic rainbow; this is not an animation or live LED readback.

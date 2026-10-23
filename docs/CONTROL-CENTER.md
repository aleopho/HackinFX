# HackinFX Control Center — 2.0 implementation

This branch expands the x86-64/macOS 15 app from a GPU panel into a device workspace. It does not claim that every OpenRGB-listed device now works on macOS.

## Implemented architecture

- The native SwiftUI/AppKit application manages a separate Python Core process. It remains alive with the menu-bar app and stops at app quit; an owner-process watchdog also stops an orphaned Core. No launch daemon, kernel extension or system helper is installed.
- Core owns device discovery, capability routing, shared scene rendering, local scene storage and device placement. The API is versioned under `/v1`, binds only to 127.0.0.1 on an ephemeral port, rejects browser Origins/foreign Hosts and requires a random per-process credential. Discovery credentials are stored in a mode-0600 file inside a private Core directory, not exported in reports. Android/LAN access is not enabled.
- Native NVIDIA and OpenRGB are separate functional adapters. USB and DRAM inventory never inherits control access from a vendor/model match.

## OpenRGB bridge

Enable the SDK server in an independently installed OpenRGB, on local port 6742. Discover devices in HackinFX. The bridge negotiates SDK 3 serialization with servers supporting version 3 or later, including newer version-6 servers. It reads actual controller records, modes, zones and LED counts; serial and OS-location strings are discarded, not hashed or stored.

Direct/Custom modes with per-LED color support can receive shared Static, Gradient, Spectrum, Breathing and Wave scenes. This may include supported keyboards, mice, USB cooling lighting, DRAM and lighting controllers **only when the server actually exposes working access on that macOS system**. Hardware-only controllers are listed without Direct scene controls. Detection does not issue lighting writes. The bridge never requests bus rescans, controller resizing, profile/flash saving, firmware updates or fan/pump speed changes.

A device-list change invalidates streaming and requires rediscovery. SDK device IDs are session-scoped, preventing saved targets from silently binding to an unrelated device index after a restart. No physical OpenRGB peripheral has been tested by the agent; protocol integration tests use a local simulated SDK server and are explicitly not hardware validation.

## Native GPU adapter

The existing 68 exact NVIDIA test candidates remain in GPU Lab. Core writes require a matching confirmed profile in Documents/HackinFX. Shared Static scenes are available; three-zone PNY profiles can also join shared Gradient. Other animated hardware modes remain in GPU Lab. Native GPU streaming is deliberately not advertised or enabled.

A process-wide native write lock prevents GPU Lab and Core from overlapping GPU transactions. The Core CLI request also requires the exact selected profile key; hardware selection is repeated by the existing transport. OpenRGB GPU targets are disabled when the native NVIDIA backend owns GPU control, avoiding duplicate writers to the same GPU.

## Scenes and layout

One monotonic clock drives shared effects, with a maximum target rate of 20 frames per second. Frames use RGBX SDK packets and bounded device/LED/payload counts. Failed targets are isolated. Stop halts streaming and leaves the last hardware color; Blackout explicitly sends black.

Palette, brightness, speed and spatial axis are editable drafts until Start scene. Scenes are stored in `~/Documents/HackinFX/scenes.json`. Loading a saved scene never sends commands or guesses device targets. Unique device placement is remembered using non-serial descriptive fingerprints; identical devices require manual placement after rediscovery. Internal LED order is linear in this implementation; keyboard matrix mapping is not yet implemented.

The new interface contains Overview, Devices, Scenes, Layout, Connections, GPU Lab, Diagnostics and Credits. The design renderer is an explicit CLI-only path using labeled sample data, not a fake discovery mode in the normal app.

## Device coverage and remaining hardware work

| Device class | Current control path | Native work still required |
| --- | --- | --- |
| NVIDIA GPU | Existing confirmed native profiles; static shared scenes | More native controller families and validated streaming |
| Keyboards / mice / USB coolers | OpenRGB Direct-mode bridge when working on macOS | Native HID/USB device-specific adapters |
| DRAM | Passive macOS inventory; OpenRGB bridge if a working RAM controller is exposed | A documented macOS host-SMBus transport and exact controller validation |
| Lighting controllers / strips | OpenRGB Direct-mode bridge | Additional native transports |

The Corsair RAM inventory prototype remains read-only. It has not changed any memory lighting. No SPD writes, bus-address sweeps or unreviewed kernel driver installation are implemented.

The real WidgetKit diagnostics from the earlier branch remain available, but its desktop failure is unresolved and is not a prerequisite for using the new Core. There is no floating-window widget substitute.

## Validation and release status

Run Python tests with `PYTHONPATH=app python3 -B -m unittest discover -s app/tests`. Tests cover SDK framing/parser bounds, fragmenting socket responses, hotplug invalidation, authentication/origin/Host rejection, multi-device effects, selected-target validation, device failure isolation, safe persistence, GPU ownership/write exclusion and real Core process lifecycle.

The full Xcode build packages the real WidgetKit extension. CI checks x86-64/minimum macOS 15, preserved entitlements, signatures in the DMG and after a copied installation. GUI interaction and actual peripheral behavior still require desktop testing. The renderer output, when available, is labeled sample data.

This is the 2.0 implementation branch, not a newly published stable release. Publishing markers/workflow remain unchanged until validation. OpenRGB is an optional external backend dependency; NullMoth is required only for the native NVIDIA path. Source and third-party credits remain GPL-compliant.

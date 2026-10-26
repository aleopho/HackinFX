# Using HackinFX 2.1.1

## Install and start

Use the release PKG to install into Applications. Quit previous copies first.
The DMG is an alternative drag-and-drop distribution. macOS 15+, x86-64 and a
working system Python 3 are required. Packages are ad-hoc signed, not notarized;
macOS can request approval. Do not disable system protection globally.

Native NVIDIA control needs the separately installed NullMoth NVRM driver.
Ordinary USB lighting does not require that driver. The optional OpenCore SMBus
installer component is for RAM development only; RAM is not yet working on the
development system. See [RAM setup](RAM-SETUP.md) before enabling it.

## Lighting and devices

Launch opens Lighting. The bundled OpenRGB engine starts locally and discovery
combines native and OpenRGB adapters. Ready devices are selected automatically
and receive static white at 100% once per session. Inventory-only or access-
required entries remain visible under Devices; identification alone grants no
lighting access. Rediscover refreshes devices and applies the current look.

Select devices, choose an effect and change palette, brightness or speed. Changes
apply after a short debounce without Apply. Lights off sends black. Pause stops
animation and retains the last color; Radius preview renewal continues where
needed. The visualization shows requested colors, not LED feedback.

## Canvas and Effect Studio

Mirrored group output is the default: the same timeline/frame reaches each
output, and the next frame waits for the whole group. Measured command durations
help delay faster outputs. Slow devices reduce group frame rate. Physical LED
latency is not measured; exact optical synchronization is not guaranteed.

Canvas provides device placement and a choice between mirroring and spatial
mapping across the setup. Animated groups require streaming-capable devices;
independently timed hardware effects cannot be treated as synchronized streams.
ASUS native keyboard effects currently change the whole keyboard, not each key.

Effects is a parameter editor: palette stops, animation, speed, brightness,
direction, preview and saved looks. Profiles/scenes are stored in the current
user's `~/Documents/HackinFX`.

## Menu bar, startup and updates

Window close leaves HackinFX running in the menu bar. Reopen from there; choose
Quit to stop the Core and managed OpenRGB engine. Host-generated animations need
the app to remain running; onboard lighting may retain its last state.

Settings includes launch at login and software updates. White is applied after
sign-in and app discovery, not before macOS login. Updates are checked at launch
and can also be checked manually. An update check is separate from a lighting
command failure.

## GPU Lab

Advanced → GPU Lab handles exact native NVIDIA test profiles. An implemented
controller without a valid saved profile runs a visible test. Confirm only when
all displayed colors/effects visibly work. Stop, partial or failed results do
not create a verified profile. Matching confirmed profiles can be reused later.
OS/driver/hardware changes can require another test.

Missing/generic GPU or board names can be corrected. Original IDs are preserved;
a marketing name cannot override the hardware guard. Optional sharing queues a
minimal user-confirmed compatibility record, not an independent certification.

## Feedback and diagnostics

Open Advanced → Diagnostics. In Feedback & compatibility, describe the device,
expected behavior, actual behavior and reproduction steps. Scan & submit
feedback… automatically refreshes allowlisted CPU, RAM, USB, PCI and storage
specifications before opening the report preview. Partial scans include errors.
Review the exact JSON, then Send; only a server receipt confirms delivery. Export
JSON remains available if offline. Private reports go to the configured HTTPS
inbox, not to public SourceForge tickets. Support still requires investigation.

Core device status and errors are attached. Serial numbers, raw trees, volume
labels and mount paths are excluded from automatic inventory. Notes are sent as
typed: remove any private content. [Privacy](PRIVACY.md).

## Widget

Install and launch the app before adding HackinFX from Edit Widgets. For upgrades,
remove old diagnostic widgets and re-add the main HackinFX widget. It shows Core
mode, palette, brightness, GPU, ready count and attention status. WidgetKit controls
refresh timing. A useful fallback is shown when no state is readable; real desktop
registration/rendering still needs wider community validation.

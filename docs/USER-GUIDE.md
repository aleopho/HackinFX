# Using HackinFX 2.4.0

## Install and start

Use the release PKG to install into Applications. Quit previous copies first.
The DMG is an alternative drag-and-drop distribution. macOS 15+, x86-64 and a
working system Python 3 are required. Packages are ad-hoc signed, not notarized;
macOS can request approval. Do not disable system protection globally.

Native NVIDIA control needs the separately installed NullMoth NVRM driver.
Ordinary USB lighting does not require that driver. The optional OpenCore SMBus
installer component is only needed for the scoped RAM transport. Four Corsair
Titanium DIMMs are confirmed on Intel 8086:7f23 with the loaded driver. See [RAM setup](RAM-SETUP.md) before enabling it.

## Lighting and devices

Launch opens Lighting. The bundled OpenRGB engine starts locally and discovery
combines native and OpenRGB adapters. Ready non-RAM, non-network devices are selected automatically
and receive mint Twinkle at 65% speed once per session. Inventory-only or access-
required entries remain visible under Devices; identification alone grants no
lighting access. Rediscover refreshes devices and applies the current look.

Select devices, choose an effect and change palette, brightness or speed. Changes
apply after a short debounce without Apply. Lights off sends black. Pause stops
animation and retains the last color; Radius preview renewal continues where
needed. The visualization shows requested colors, not LED feedback.

## Effect Gallery and Canvas

Effects opens the gallery: 41 effects and 82 curated looks in five
categories. Search by name/description, filter categories and star favorites.
Click a card to apply it to selected compatible devices. Built-in cards preserve
brightness and device selection; saved looks restore their full configuration.
Use speed, brightness, scale, density, reverse and palette controls to customize
then Save look. Lighting also has a compact effect menu and Browse effects.
Preview cards illustrate algorithms rather than live physical feedback.
Reduce Motion pauses animated preview playback.

Canvas places devices in a shared spatial field. Mirroring uses each device's
local layout; Canvas mapping uses its position across the setup. Recognized
keyboards and Shapes panels supply actual LED/panel coordinates. Adaptive output
keeps fast devices moving when another device is slower. Lockstep waits for all
outputs. Latency compensation is an estimate; exact optical sync is not guaranteed.

## Memory and Nanoleaf

For the supported Corsair/Intel setup, open a Memory device in Devices, choose
Probe RAM RGB, then select the resulting DIMMs in Lighting. RAM is not colored
automatically at startup. Existing macUSPCIO installations need no reinstallation.
[RAM setup and boundaries](RAM-SETUP.md).

For Shapes, choose Settings → Find Nanoleaf and select the discovered controller.
Hold its power button for 5–7 seconds until flashing, then Pair Shapes within
30 seconds. Pairing reads layout and stores a private local token. Select the
paired Shapes in Lighting to start control. No fixed IP or cloud account is needed.
The stream uses up to 10Hz with panel interpolation. [Nanoleaf details](NANOLEAF.md).

## Menu bar, startup and updates

Window close leaves HackinFX running in the menu bar. Reopen from there; choose
Quit to stop the Core and managed OpenRGB engine. Host-generated animations need
the app to remain running; onboard lighting may retain its last state.

Settings includes launch at login and software updates. The startup look begins after
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

## Layer Studio and refined effects

Studio composes a base effect with up to four layers. Choose Screen, Add,
Multiply or Normal blend and tune opacity, palette and speed. Layered scenes
require Direct host-streamed devices. In Canvas, arrange and rotate devices;
RGB gains and gamma in device details fine-tune color matching.

Fireplace is a fixed deep-red/orange ember palette with smooth rising motion.
Gallery illustrations are artwork, not live optical feedback. Mirror repeats
one normalized effect field per device; Canvas samples each physical placement.
Different positions can display different colors while sharing the same clock.
Physical transport latency and refresh limits remain relevant.

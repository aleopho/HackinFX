# Device compatibility

HackinFX 2.4.0 targets macOS 15+ x86-64 Hackintoshes with Intel or AMD CPUs.
CPU manufacturer is not a gate; AMD-CPU operation still needs physical community
validation. Apple Silicon is not targeted. Hardware RGB support is separate from
CPU compatibility and display-driver support.

## Three distinct states

| State | Meaning |
| --- | --- |
| Detected / catalog match | Identity is known; no proof of macOS RGB access |
| Ready / controllable | An included adapter can attempt permitted lighting commands |
| User-confirmed | A user reports the visible test worked on their exact hardware |

No catalog entry or manual marketing name can install a protocol implementation,
override native PCI guards or prove an optical result.

## OpenRGB and native adapters

HackinFX bundles the pinned OpenRGB 1.1 Intel macOS engine, compiled drivers,
runtime dependencies and corresponding source archives. It also includes native
NVIDIA and USB/HID paths, with ownership rules to avoid duplicate writers.
OpenRGB support on another operating system does not guarantee a macOS transport.
Device status exposes inventory-only, access-required and setup-required cases.

Native NVIDIA paths cover **68 exact test profiles** across PNY Lovelace,
ASUS Aura, EVGA Pascal, EVGA Turing and Zotac Turing. This is a list of implemented
test candidates, not 68 independently verified cards. The identity catalog is
broader and is not an executable support list. Exact-profile testing, successful
transport and visual user confirmation are required before native profile reuse.

## Development-system evidence

| Hardware | Evidence / limitation |
| --- | --- |
| PNY XLR8 RTX 4080 VERTO (`10de:2704 / 196e:13bc`) | Static, Gradient, Spectrum, Breathing and Wave visually confirmed by aleopho |
| ASUS ROG Spatha X | User-reported working; firmware/connection variants need their own checks |
| ASUS ROG Strix Scope II 96 Wireless, USB path | Actual ISO-203 USB reply maps 102 OpenRGB LED addresses; whole-device fallback for unknown layouts. Physical key mapping needs broader validation |
| GIGABYTE HID LampArray | User-reported working; other boards need their own validation |
| Fractal Design Radius | User-reported working; preview renewal and physical timing need broader tests |
| Corsair Titanium / SMBus development path | Four Titanium PID 0801 / protocol 4 DIMMs on Intel 8086:7f23 + macUSPCIO visibly confirmed: Static mint, separate LED regions and paced Twinkle (16.65 FPS per DIMM in the short test). Other hosts/kits unverified |
| Nanoleaf Shapes Triangles | NL42 discovery, pairing and visible lighting user-confirmed; other Nanoleaf families not enabled |
| NZXT Kraken X2/M2 and other OpenRGB devices | Included paths where available, not physically verified by this project |

An active command/frame counter reports commands, not light emitted by LEDs.
Group timing uses shared frames and command latency compensation; it cannot
measure firmware buffering or promise exact optical synchronization.

## Add or troubleshoot a device

Use Feedback in the main sidebar for a fresh read-only hardware scan,
notes and reviewed private submission. Include connection mode, exact model,
firmware if known, expected/actual behavior and a reproducible sequence. Report
export works without an online inbox. Do not publish private raw reports.

Implementation needs a documented protocol, macOS transport, exact identity,
license-compatible reference, bounded lighting-only commands, failure cleanup
and physical validation. OpenRGB references and vendor notices must remain.
A confirmation grows evidence; it does not automatically deploy new drivers.

Native profiles and scenes are stored in `~/Documents/HackinFX`.
[Build/testing](DEVELOPMENT.md) · [RAM setup](RAM-SETUP.md) · [USB details](USB-LIGHTING.md).

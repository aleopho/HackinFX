<p align="center"><img src="app/assets/hackinfx-mark-v2.png" width="120" alt="HackinFX orbital FX icon"></p>
<h1 align="center">HackinFX</h1>
<p align="center">Lighting Studio for macOS Hackintosh systems · by <a href="https://github.com/aleopho">aleopho</a></p>
<p align="center"><a href="https://github.com/aleopho/HackinFX/releases/latest">Download</a> · <a href="docs/USER-GUIDE.md">Getting started</a> · <a href="docs/COMPATIBILITY.md">Device compatibility</a> · <a href="THIRD-PARTY-NOTICES.md">Licenses & credits</a></p>

HackinFX brings GPUs, keyboards, mice, USB lighting controllers and supported
coolers into one native **Lighting Studio**. Built for **macOS 15 or later** on
**x86-64 Hackintoshes with Intel or AMD CPUs**, it combines the bundled
**OpenRGB 1.1 macOS engine** with native NVIDIA, USB/HID, scoped RAM and
local Nanoleaf Shapes adapters.

**Current release: [3.0.2](https://github.com/aleopho/HackinFX/releases/tag/v3.0.2).**
Scoped Corsair Dominator Titanium DDR5 RGB support uses exact host and RGB
identity checks. This is not generic RAM or chipset support.
Nanoleaf Shapes pairing and visible lighting are user-confirmed.
Apple Silicon is outside the current target.

![HackinFX 3.0.2 Lighting Studio with ten active devices](docs/images/lighting-studio-3.0.2.png)

Actual desktop screenshot supplied by aleopho on 28 October 2026. The effect
visualization shows requested colors, not optical LED feedback.

## New in 3.0.2

- Shared-clock Layer Studio: base effect plus four layers, blend modes and opacity; Canvas transforms, per-device RGB calibration and brightness.
- Rebuilt effect math with smooth palette transitions, spatially consistent particles and softer motion. **Fireplace** adds deep red/orange embers without white flashes. **41 effects and 82 looks**.
- Corrected staggered MAKR 75 key geometry so particles and waves spread across individual keys; existing verified RGB byte offsets and dial handling stay intact.
- Independent native HID output channels prevent a slow USB collection from blocking every device. The host targets 60 FPS while respecting actual hardware refresh limits.
- Original animated gallery illustrations, larger cards and new orbital FX branding in the app and menu bar.
- Graceful Core shutdown protects saved RAM authorization from helper-pipe interruption. Real bus errors and changed/unexpected RGB identities still stop RAM output. One observed controller state recovered after a cold power cycle; do not treat this as generic RAM compatibility.
- **HackinFX Remote 2.0.1**: redesigned native Android workspace, color wheel, Layer Studio, device brightness and centered navigation captions. The existing package ID and signing identity are preserved.
- Existing hotplug, local Nanoleaf Shapes pairing, 22 offline desktop languages, diagnostics/export and WidgetKit integration remain available. Widget refresh and Android camera/pairing still need device-specific validation.

Windows work is deferred while macOS remains the priority. No Windows build is advertised by this release.

## Effect Gallery

![HackinFX 3.0.2 gallery artwork rendered from native views](docs/images/effect-gallery-3.0.2.png)

Native render of six gallery illustrations, not a live desktop screenshot. **41 effects and
82 curated looks**, organized into Essentials, Motion, Atmosphere, Particles and
Geometry. Search, favorite, tune and save looks; animated cards respect Reduce Motion.

## One workspace for your lighting

- **Live lighting:** 41 host-rendered patterns, including Fire, Plasma, Nebula,
  Ripple, Scanner, Meteor Shower, Digital Rain, Snowfall and the original favorites.
  Palette, brightness, speed, scale, density and reverse controls apply live.
- **Shared effects:** adaptive output follows a common timeline with bounded
  pending frames and measured per-device latency. Slower outputs do not stall
  faster devices. Optional lockstep uses a frame barrier. Visible timing still
  depends on hardware; exact physical synchronization is not guaranteed.
- **Canvas:** arrange devices in a shared effect space or mirror a look across
  the setup. Only outputs with a suitable streaming path join animated groups.
- **Effect Gallery:** 82 curated looks, five categories, search, local favorites,
  native animated previews and saved custom looks. Larger screen-aware workspace.
- **OpenRGB inside:** the pinned macOS engine and its compiled device drivers
  start locally with HackinFX. No separate OpenRGB installation or account.
- **Native paths:** confirmed NVIDIA profiles, HID LampArray, ASUS Spatha X,
  ASUS wired Scope II 96 ISO-203 / 102-LED mapping, Fractal Radius and scoped
  NZXT support. Unknown keyboard layouts retain a whole-device fallback.
- **Nanoleaf Shapes:** automatic local discovery and explicit pairing in Settings,
  actual panel geometry in Canvas, and per-panel streaming. No fixed IP required.
- **Daily use:** launch at login, green Twinkle at 65% speed on app/login startup
  for ready devices, including paired panels and previously probed RAM, persistent menu-bar
  controls and software-update checks. Closing the window keeps lighting active.
- **Diagnostics & feedback:** fresh hardware specifications, device status and
  your description, reviewed before private submission; JSON export remains available.
- **WidgetKit:** app name, current effect, palette, active-device count and
  attention state. Desktop rendering and refresh behavior need wider validation.

## Install

Download the **[3.0.2 installer](https://github.com/aleopho/HackinFX/releases/download/v3.0.2/HackinFX-3.0.2-Installer.pkg)**,
quit older copies and install into **Applications**. A DMG is also available.
Launch the installed app, let discovery finish and inspect **Devices** for ready
outputs or setup requirements. Ready devices start green Twinkle (#9BED4B) at
65% speed once per app/Core session, after macOS sign-in. RAM needs one successful
**Devices → Memory details → Probe RAM RGB** in this version. It saves a private
profile under Documents/HackinFX; subsequent starts revalidate exact inventory and
RGB identities before including those DIMMs automatically. Paired Nanoleaf panels
join when reachable. Unverified or unavailable devices remain visible with setup status.

Requirements:

- macOS 15+, x86-64. Intel and AMD CPU systems are in scope; AMD-CPU operation
  has not been independently verified on physical hardware by this project.
- A working `/usr/bin/python3` from Apple's command line tools.
- Device access supported on macOS. An OpenRGB catalog match or working Windows
  driver does not prove that macOS can control the device.
- For native NVIDIA lighting: separately install the
  [NullMoth NVRM driver](https://github.com/nullmoth/nvidia-macos-driver).
  It is not required for every USB device and is not bundled.

The installer offers **Customize → OpenCore SMBus driver (RAM RGB)**. This is an
optional development transport, not a guarantee of working RAM lighting. It
backs up the EFI before adding the driver/config entry, recognizes GPT and
FAT/MBR boot volumes, and requires reboot. **Do not install it just to use USB
lighting.** Read [RAM setup and recovery](docs/RAM-SETUP.md) first.

App, helpers, widget and nested engine are **ad-hoc signed**, without Apple
Developer ID or notarization. macOS may require approval for downloaded software.

## Device coverage: detection is not control

| Device class | Included paths | Current evidence / limits |
| --- | --- | --- |
| NVIDIA GPUs | 68 exact native test profiles across PNY Lovelace, ASUS Aura, EVGA Pascal/Turing and Zotac Turing; OpenRGB paths where available | PNY XLR8 RTX 4080 VERTO visually confirmed; other native profiles need their own test and confirmation |
| Keyboards | OpenRGB macOS drivers, native HID LampArray, MAKR 75 and ASUS Scope II 96 / supported OMNI paths | Scope II 96 USB appears ready on the development setup; recognized USB ISO-203 layout maps 102 LED addresses; physical per-key mapping still needs broader validation |
| Mice | OpenRGB macOS drivers and native ASUS Spatha X | Spatha X user-reported working; connection mode and firmware can differ |
| Mainboards / controllers | OpenRGB macOS drivers and native HID LampArray | Development GIGABYTE LampArray user-reported working; no universal board claim |
| USB cooling / lighting | OpenRGB macOS drivers, native Fractal Radius and NZXT Kraken X2/M2 paths | Radius user-reported working; sustained color and timing need broader firmware testing; NZXT not physically verified here |
| Nanoleaf Shapes | Native NL42 Bonjour discovery, local pairing and extControl v2 | Shapes Triangles user-confirmed working; other Nanoleaf families are not enabled |
| DRAM | Scoped Corsair Dominator Titanium direct RGB with the macUSPCIO transport | Exact host, module and RGB identity guards apply. Other kits/chipsets remain unverified. No SPD/timing/voltage writes. |

The OpenRGB identity catalogs help name devices. They do not download drivers,
turn every catalog entry into a controllable output or bypass exact native
hardware guards. Automatic generic OpenRGB SMBus detectors are disabled pending
transport review; bundled USB/HID drivers and scoped native GPU/RAM paths remain
available. [Compatibility details and contribution process](docs/COMPATIBILITY.md).

For Shapes: **Settings → Find Nanoleaf**, select the controller, hold its power
button for 5–7 seconds until flashing and choose **Pair Shapes** within 30 seconds.
Then select Shapes in Lighting. [Nanoleaf setup](docs/NANOLEAF.md).

## Profiles, feedback and privacy

Confirmed native GPU profiles and saved scenes use **`~/Documents/HackinFX`**.
Core logs and private state use `~/Library/Application Support/HackinFX/Core`.
Native GPU setup tests implemented controllers and saves a reusable profile only
after successful calls and your visual confirmation. Manual identity corrections
retain the original detected PCI identity.

Under **Feedback** in the sidebar, describe the problem in **Feedback &
compatibility**, then choose **Scan & submit feedback…**. A fresh read-only scan
attaches allowlisted CPU, RAM, USB, PCI and storage specifications, alongside
Core device/error details. Review the JSON before sending. Serials, raw device
trees, volume labels and mount paths are excluded from this inventory; free text
is sent as typed. The existing private HTTPS report inbox returns a receipt.
SourceForge ticket submission is not integrated. Reports require investigation;
they do not automatically create driver support in the next release.
[Data flow and privacy](docs/PRIVACY.md).

## Documentation

- [Installation and everyday use](docs/USER-GUIDE.md)
- [Devices, tests and compatibility](docs/COMPATIBILITY.md)
- [Layer Studio and composition](docs/STUDIO-3.0.md)
- [Core, engine and synchronization architecture](docs/ARCHITECTURE.md)
- [RAM / OpenCore setup and recovery](docs/RAM-SETUP.md)
- [USB lighting](docs/USB-LIGHTING.md) · [Radius and ASUS keyboard](docs/RADIUS-AND-KEYBOARD.md)
- [Build and release checks](docs/DEVELOPMENT.md)
- [Report service](report-inbox/README.md) · [Contributing](CONTRIBUTING.md)
- [Release notes](docs/RELEASE-NOTES-3.0.2.md) · [Changelog](CHANGELOG.md)
- [Licenses and acknowledgements](THIRD-PARTY-NOTICES.md)

## Build from source

```sh
python3 tools/prepare_openrgb_runtime.py
python3 app/build_community.py
python3 app/package_installer.py
python3 app/package_dmg.py
```

Use Intel macOS with full Xcode for the real WidgetKit extension. Runtime
preparation explicitly downloads hash-pinned upstream binaries and corresponding
sources. Build/CI checks never probe real hardware. See [development](docs/DEVELOPMENT.md).

## Credits and license

Created by **aleopho**. The combined HackinFX application is **GPL-3.0-or-later**;
components retain their own terms. [LICENSE](LICENSE) · [Full third-party inventory](THIRD-PARTY-NOTICES.md).

- **OpenRGB / Adam Honse and contributors**, including yufan, Jan Rettig,
  TheRogueZeta, David Henry, Martin Hartl and the authors preserved upstream:
  bundled macOS engine, identity data and adapted controller protocols.
- **NullMoth Systems:** separately installed NVIDIA NVRM bridge, under its own
  terms; not bundled or relicensed by HackinFX.
- **NVIDIA:** public RM ABI definitions; MIT notices preserved.
- **OpenLinkHub / Nikola Jurkovic:** MAKR 75 protocol, key-layout and dial-event references; GPL-3.0-or-later sources and notices retained.
- **Fractal Radius plugin contributors, Daniel Valfridsson / rigstats, macUSPCIO,
  Qt and bundled runtime dependencies:** original source and notices preserved
  as documented in the third-party inventory and release bundles.

Independent community project, without affiliation or endorsement by device
manufacturers, Apple, NullMoth, OpenRGB or SignalRGB. Provided without warranty.

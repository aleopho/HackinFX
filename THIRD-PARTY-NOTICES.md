# Licensing and acknowledgements

## HackinFX

Copyright (c) 2026 aleopho and contributors. The combined application is distributed as **GPL-3.0-or-later**. See the full [GPL version 3 text](LICENSE), also bundled as `app/COPYING-GPL3`. Preexisting GPL-2.0-or-later files retain their notices and are combined under the permitted later version. The original GPL version 2 text remains in `app/COPYING`. The upstream GPL text is preserved verbatim, including its historical example appendix; examples in the license text do not name this project's author.

The corresponding application source, build and packaging scripts, tests, editable icon and backend source are included. Third-party components retain their respective terms. This document is an attribution inventory, not a claim that different licenses have become identical.

## OpenRGB

PNY lighting packet/effect construction in `app/rgb.py` is adapted from the OpenRGB PNY Lovelace GPU controller by **yufan (2023) and OpenRGB contributors**, licensed GPL-2.0-or-later. The source header identifies yufan and 1 October 2023.

- [OpenRGB project](https://gitlab.com/CalcProgrammer1/OpenRGB)
- [PNY controller implementation](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/PNYLovelaceGPUController.cpp)
- [Controller header](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/PNYLovelaceGPUController.h)
- [PNY RGB controller](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/RGBController_PNYLovelaceGPU.cpp)

The 1.1 development catalog also vendors pinned OpenRGB GPU detector/header source inputs with original author/license notices preserved under vendor/openrgb. tools/import_openrgb_catalog.py derives passive identity metadata from those files; they are not executed as a universal macOS driver.

The adaptation is acknowledged in the Python file, the app's Credits page, this document and README. HackinFX 2.1.1 bundles the pinned OpenRGB 1.1 Intel macOS executable, its dependency closure, corresponding source archives and original notices. See `vendor/openrgb-runtime/manifest.json` and the runtime section below. Upstream master links are moving references; they do not imply all later upstream changes are in HackinFX.

## NullMoth

[NullMoth NVIDIA driver for macOS](https://github.com/nullmoth/nvidia-macos-driver) supplies the separately installed NVRM interface. The reviewed [NVRM.cpp at v2.5.3](https://github.com/nullmoth/nvidia-macos-driver/blob/v2.5.3/kexts/NVRM/NVRM.cpp) contains:

- Copyright (c) 2026 NullMoth Systems.
- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0.

No NullMoth kext binary, NVRM source or Mesa patch is redistributed in this repository or the DMG. HackinFX contains a new Python ctypes client for the installed interface; it does not relicense NullMoth. Obtain the driver from upstream and follow that project's applicable terms and installation guidance. A reported NVRM bundle version is not sufficient to identify an upstream driver release.

## NVIDIA

RM structure layouts/constants use the public SDK definitions from [NVIDIA/open-gpu-kernel-modules 610.57.04](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/610.57.04), including nvos.h, nv_escape.h, cl0080.h, cl2080.h, cl402c.h, ctrl0000gpu.h and ctrl402c.h.

Copyright notices and MIT permission/disclaimer are preserved in [licenses/NVIDIA-MIT.txt](licenses/NVIDIA-MIT.txt) and `app/NOTICE.txt`. [Detailed paths and ABI references](app/SOURCES.md).

## Development tools and platform frameworks

AppKit, SwiftUI, Foundation and IOKit are platform frameworks; their binaries are not copied into this repository. Python standard-library facilities are used at runtime. Cloudflare Wrangler and its development dependencies are installed from their upstream package registry when developing the optional report service; node_modules and credentials are not distributed here. Their licenses remain their own.

## Branding and independence

HackinFX name/icon are project assets by aleopho. Product/vendor names identify compatibility and source credits. No affiliation, endorsement or partnership with Apple, PNY, NVIDIA, NullMoth or OpenRGB is claimed. No third-party logo is used as the HackinFX logo.

## EVGA Pascal controller adaptation

The volatile EVGA Pascal RGB register/mode implementation is adapted from Adam Honse (CalcProgrammer1), OpenRGB, 11 September 2020, GPL-2.0-or-later. The exact upstream implementation at commit `817834cfab034c97927451e31c4a2deb60a44725` is preserved in `vendor/openrgb/implementations/EVGAGPUv1Controller.cpp`; its corresponding header and detector are also included. The adaptation never calls the controller flash-save command. Physical macOS testing on EVGA hardware remains pending.

## ASUS Aura controller adaptation

ASUS Aura signature checks and volatile register/mode handling are adapted from Jan Rettig (Klapstuhl), OpenRGB, 14 February 2020, GPL-2.0-or-later. The exact upstream implementation at commit `817834cfab034c97927451e31c4a2deb60a44725` is preserved in `vendor/openrgb/implementations/AsusAuraGPUController.cpp`, with its detector and header. No flash-save/apply register is written by HackinFX. Physical macOS testing remains pending.

## Additional NVIDIA controller adaptations

EVGA Turing volatile unlock/color/mode/relock sequences are adapted from TheRogueZeta, OpenRGB, 15 April 2021. Zotac Turing enable/mode/readback handling is adapted from David Henry, OpenRGB, 7 January 2023. Both are GPL-2.0-or-later. Exact implementations from pinned commit `817834cfab034c97927451e31c4a2deb60a44725` and hashes are in `vendor/openrgb/implementations/`. Original detector/header notices remain preserved. These macOS ports are unverified on physical EVGA/Zotac hardware. No upstream flash-save operation is implemented.

## OpenRGB SDK protocol references

The new Python SDK client is implemented from OpenRGB's network protocol and SDK-3 controller serialization. Original protocol/interface/serialization sources at commit `817834cfab034c97927451e31c4a2deb60a44725` are preserved with their original Adam Honse/OpenRGB author notices and per-file hashes under `vendor/openrgb/sdk/`. They remain GPL-2.0-or-later protocol references; the separately pinned bundled executable and its sources are documented below. HackinFX does not claim OpenRGB's entire catalog as working macOS hardware support.

## OpenRGB USB/HID identities and lighting protocols

The USB/HID identity catalog is deterministically imported from OpenRGB commit `817834cfab034c97927451e31c4a2deb60a44725`. Original detector/header bytes and the upstream GPL license are retained in `vendor/openrgb/usb-sources.zip`. `tools/import_openrgb_usb_catalog.py` rebuilds the catalog offline. Unsupported/disabled registrations do not authorize hardware writes.

Native lighting protocol references are preserved under `vendor/openrgb/usb-protocols`, with exact paths and hashes in `SOURCES.json`. Credits include Adam Honse (HID LampArray, GPL-2.0-only; ASUS Aura Mouse, GPL-2.0-or-later), Martin Hartl (NZXT Kraken, GPL-2.0-or-later), and the per-file contributors and copyright notices. The native HackinFX USB adapter uses Apple's IOKit transport. The bundled OpenRGB engine retains its own runtime dependencies, including hidapi, with original licenses/notices. Distribution remains compatible with GPL version 2; all original notices are retained.

## Radius, ASUS keyboard and RAM references (2.0.2)

The Fractal Radius adapter ports aleopho/signalrgb-fractal-radius at e86cabf7154c0022fd23799a55d0fc3e24154744 (MIT; Copyright 2026 SignalRGB Fractal Radius contributors). Original plugin, protocol notes, fixture and MIT license are retained in vendor/radius.

ASUS keyboard/OMNI protocol references include dvalfrid/rigstats at bf0f1f3e8ab1b387dd7cd914a44ba0d95ad1cd96 (MIT; Copyright 2026 Daniel Valfridsson); original reference files and license are retained in vendor/rigstats.

Corsair DRAM and macOS i801 protocol references are from the existing pinned OpenRGB tree and preserved under vendor/openrgb/ram, with original contributor/license notices. Credits include Adam Honse, Erik Gilling and Shady Nawara. macUSPCIO is a separately installed GPL-3.0 driver; it is not embedded, installed or loaded by the HackinFX application. The external OpenCore preparation package retains its original archives, source and license separately.

## Bundled OpenRGB 1.1 runtime

The official Intel macOS CLI executable and its dynamic dependency closure are
bundled with complete OpenRGB source, Qt base/GLib/gettext/libusb release source
archives and license notices. See [runtime provenance and licenses](vendor/openrgb-runtime/README.md)
and the hash-pinned [manifest](vendor/openrgb-runtime/manifest.json). Existing
OpenRGB, NullMoth and Radius credits above continue to apply.

## macUSPCIO optional OpenCore transport

Unchanged ShadyNawara/macUSPCIO v1.0 driver and corresponding source archive,
GPL-3.0 license and checksums are retained in vendor/macUSPCIO and the app Source.
The optional installer component copies the original kext; no driver code is changed.

## Scope II 96 per-key layout and packets (2.2.0)

Wired Scope II 96 RGB packet construction, ANSI/ISO key IDs and matrix positions
are adapted from Mola19 and OpenRGB contributors, GPL-2.0-or-later. Exact original
OpenRGB 1.1 sources at 8e16de27858cf2be6af54a33ce003df74cb9fd3e are preserved in
vendor/openrgb/keyboard with per-file hashes. OMNI per-key support is not claimed.

## Nanoleaf local protocol integration

The native Shapes adapter implements Nanoleaf's documented OpenAPI and
extControl v2 wire format. Protocol references include OpenRGB's
`NanoleafController.cpp/.h` and detector, by Nikita Rushmanov (2022),
GPL-2.0-or-later, and the official Nanoleaf OpenAPI documentation.
See [Nanoleaf setup and protocol notes](docs/NANOLEAF.md).
No Nanoleaf cloud SDK or vendor firmware is bundled.

## OpenLinkHub / MAKR 75

Nikola Jurkovic, OpenLinkHub, GPL-3.0-or-later. Protocol, dial-event and US key-layout references for the wired MAKR 75. Exact supported identities are enforced by the adapter source. Reference sources and full license are preserved in vendor/openlinkhub-makr75; the adapter and compact derived layout are included in the application source. The combined distribution is GPL-3.0-or-later; preexisting files and separately bundled components retain their notices. See app/COPYING-GPL3.

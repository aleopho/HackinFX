# Licensing and acknowledgements

## HackinFX

Copyright (c) 2026 aleopho and contributors. Application UI and new Python implementation: **GPL-2.0-or-later**. See the full [GPL version 2 text](LICENSE), also bundled as `app/COPYING`. The project permits GPL version 2 or any later version. The upstream GPL text is preserved verbatim, including its historical example appendix; examples in the license text do not name this project's author.

The corresponding application source, build and packaging scripts, tests, editable icon and backend source are included. Third-party components retain their respective terms. This document is an attribution inventory, not a claim that different licenses have become identical.

## OpenRGB

PNY lighting packet/effect construction in `app/rgb.py` is adapted from the OpenRGB PNY Lovelace GPU controller by **yufan (2023) and OpenRGB contributors**, licensed GPL-2.0-or-later. The source header identifies yufan and 1 October 2023.

- [OpenRGB project](https://gitlab.com/CalcProgrammer1/OpenRGB)
- [PNY controller implementation](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/PNYLovelaceGPUController.cpp)
- [Controller header](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/PNYLovelaceGPUController.h)
- [PNY RGB controller](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/Controllers/PNYLovelaceGPUController/RGBController_PNYLovelaceGPU.cpp)

The 1.1 development catalog also vendors pinned OpenRGB GPU detector/header source inputs with original author/license notices preserved under vendor/openrgb. tools/import_openrgb_catalog.py derives passive identity metadata from those files; they are not executed as a universal macOS driver.

The adaptation is acknowledged in the Python file, the app's Credits page, this document and README. OpenRGB itself is not bundled as an executable. Upstream master links are moving references; they do not imply all later upstream changes are in HackinFX.

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

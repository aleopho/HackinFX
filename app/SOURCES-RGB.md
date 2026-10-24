# PNY lighting protocol references

The exact supported board and confirmed effects are documented in [compatibility](../docs/COMPATIBILITY.md). The Python adaptation is GPL-2.0-or-later, credited to OpenRGB/yufan and contributors; see ../THIRD-PARTY-NOTICES.md and COPYING.

[OpenRGB PNY Lovelace controller](https://gitlab.com/CalcProgrammer1/OpenRGB/-/tree/master/Controllers/PNYLovelaceGPUController) supplies the controller packet/effect reference. Static packet: `06 ff zone 00 R G B`, register `02`; zone indices 0, 1, 2. Controller-generated effects and brightness/speed handling are implemented in rgb.py.

[NVIDIA ctrl402c.h at 610.57.04](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/610.57.04/src/common/sdk/nvidia/inc/ctrl/ctrl402c.h) supplies TABLE_GET_DEV_INFO 0x402c0104 and INDEXED 0x402c0102 ABI definitions. The indexed address field uses shifted address 0xc0 for 7-bit device 0x60, one index byte and seven payload bytes. ABI sizes, alignment and response codes are checked locally.

Physical observations established RM port 1 on this exact board; port 2 returned RM status 0x1f in an earlier trial. The GUI uses only port 1. No general NvAPI-to-RM port equivalence or support for other boards is inferred. No automatic port fallback or address scan is used. A successful RM response alone never establishes visible light.

### Native USB/HID lighting and identity catalog

See `vendor/openrgb/usb-protocols/SOURCES.json` and `vendor/openrgb/usb-sources.zip` in the repository and bundled Source directory for the pinned OpenRGB original files, contributor notices and licenses. Identity data is rebuilt by `tools/import_openrgb_usb_catalog.py`. The native IOKit helper `HIDBridge.swift` does not read keyboard events, mouse movement or serial numbers. HID LampArray follows USB HID Lighting and Illumination page 0x59, with strict descriptor-derived report IDs and field-layout validation.

### Radius, ASUS keyboard and RAM additions

Fractal Radius packets are adapted from aleopho's MIT-licensed SignalRGB plugin at commit `e86cabf7154c0022fd23799a55d0fc3e24154744`. The original plugin, protocol notes and recorded packet fixture are in `vendor/radius`; an offline cross-language test compares complete output against that original implementation.

ASUS keyboard vendor reports and OMNI paired-device identification use the MIT-licensed RIGStats references at commit `bf0f1f3e8ab1b387dd7cd914a44ba0d95ad1cd96`, preserved in `vendor/rigstats`. No flash/profile-save commands are implemented.

Corsair DDR5 effect buffers, CRC and Intel i801 transactions reference OpenRGB commit `817834cfab034c97927451e31c4a2deb60a44725`, with original GPL sources in `vendor/openrgb/ram`. The separately installed GPL macUSPCIO driver supplies the PCI I/O transport; it is not bundled or installed by the app. See `docs/RAM-SETUP.md` for exact host/controller limits and the required separate boot step.

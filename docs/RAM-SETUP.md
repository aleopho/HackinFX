# Corsair Titanium DDR5 RAM RGB setup

The first native RAM adapter is deliberately limited to the development machine's **Intel Arrow Lake SMBus 8086:7f23** and CRC-validated **Corsair Dominator Titanium DDR5** lighting controllers (PIDs 0800/0801/0810/0811, 12 LEDs). The known installed modules are CMP32GX5M2B6000Z30. This is not generic support for every RAM kit or AMD/Intel host controller.

## Required transport

RAM lighting is attached to the motherboard SMBus, not GPU NVRM or USB. HackinFX uses the documented user-client interface of the separately installed [macUSPCIO driver](https://github.com/ShadyNawara/macUSPCIO), as OpenRGB's macOS i801 transport does. The current preflight finds the Intel controller but no available macUSPCIO service. No RAM transactions or color writes have been executed on this host.

The app **does not install/load a kernel extension, mount/edit an EFI partition, change SIP or modify OpenCore**. Adding the driver is a separate boot configuration change requiring review and a reboot. The upstream driver exposes PCI I/O to user space; HackinFX's scoped helper restricts its own use, but cannot restrict other applications' use of that driver. Its modern-OS/Arrow-Lake behavior is not physically verified here.

## Separate OpenCore preparation package

The accompanying `HackinFX-RAM-OpenCore-Setup.zip` contains the unchanged upstream v1.0 driver ZIP, corresponding upstream source archive, GPL license, checksums, and a **fragment** for one OpenCore Kernel/Add entry. The driver binary was checked as x86-64; this is not a boot or hardware validation.

1. Review the upstream source and package, and preserve your current working EFI/configuration before making a boot change.
2. Extract `macUSPCIO_Smbus.kext` from its original archive into your existing `EFI/OC/Kexts`. Merge the sample entry into the existing `Kernel -> Add` array using your normal OpenCore configuration workflow. The supplied plist is only a fragment; never replace your complete config.plist with it. Validate the resulting configuration with the matching OpenCore tools.
3. Reboot normally. In HackinFX, rediscover devices, open a RAM device's details, and choose **Probe RAM RGB**. Probe checks only documented Corsair lighting addresses/signatures, then validates device information and CRC. It does not send colors.
4. Only successfully identified controllers become selectable. Select a DIMM, choose **Static**, and explicitly start the scene. Confirm the visible color yourself. The initial adapter offers one uniform color per DIMM; no RAM gradient/streaming support is claimed.

If the service is missing, access is denied, more than one host is present, the I/O BAR is invalid, the host is disabled/SMI-owned, or controller identity/CRC fails, control remains disabled. Host registers/configuration are not enabled or rewritten to bypass such failures. Busy/error/timeouts stop the session rather than forcing a reset or retry. Inspect/export diagnostics instead.

## Implemented protocol boundaries

- Preflight enumerates PCI identities and driver presence without opening an SMBus user client.
- Explicit probe opens the exact host through macUSPCIO, validates configuration/BAR, and checks only Corsair lighting ranges 18–1F / 58–5F. No general bus sweep or SPD reading/writing is implemented.
- Only recognized Corsair signatures proceed to device-info selection and CRC validation. Unknown vendors, product IDs and CRC mismatches cannot receive color commands.
- Static lighting uses the OpenRGB Corsair effect buffer, CRC check and apply command. There are no bootloader, firmware-update or SPD commands. Firmware-internal storage behavior is not independently established; this is not a promise that firmware never persists settings internally.
- A private process lock serializes HackinFX RAM helpers; it is not a lock against unrelated RGB tools or firmware. Close other RAM RGB applications before testing.

The low-level implementation and original OpenRGB protocol references are included in Source. Runtime testing of actual RAM color remains blocked on the missing driver/boot step and subsequent hardware validation.

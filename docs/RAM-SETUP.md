# Corsair Titanium DDR5 RAM RGB setup

The first native RAM adapter is deliberately limited to the development machine's **Intel Arrow Lake SMBus 8086:7f23** and CRC-validated **Corsair Dominator Titanium DDR5** lighting controllers (PIDs 0800/0801/0810/0811, 12 LEDs). The known installed modules are CMP32GX5M2B6000Z30. This is not generic support for every RAM kit or AMD/Intel host controller.

## Required transport

RAM lighting is attached to the motherboard SMBus, not GPU NVRM or USB. HackinFX uses the documented user-client interface of the separately installed [macUSPCIO driver](https://github.com/ShadyNawara/macUSPCIO), as OpenRGB's macOS i801 transport does. The current preflight finds the Intel controller but no available macUSPCIO service. No RAM transactions or color writes have been executed on this host.

## Installer-assisted OpenCore setup

The PKG installer offers **OpenCore SMBus driver (RAM RGB)** under Customize.
Selecting it detects EFI partitions, prefers the actual boot partition GUID
when exposed by firmware, and otherwise accepts only one unambiguous OpenCore
installation. Ambiguous/malformed configurations stop the component without
writing to an EFI. The component is optional and off by default.

Before changes it saves a complete EFI backup under
`/Library/Application Support/HackinFX/EFI Backups/<timestamp>/EFI` (administrator
access). It copies the unchanged upstream `macUSPCIO_Smbus.kext` into
`EFI/OC/Kexts` and adds/enables exactly its Kernel/Add entry in the existing
config. It preserves other settings and the original plist format, rejects
conflicting/duplicate transport entries, and rolls back failed writes.
Reboot afterward, then use Probe RAM RGB. No immediate kext loading, SIP changes,
security-setting changes or whole-config replacement is performed.

The app itself never edits EFI. A real boot with this transport on macOS 15+
and Arrow Lake still needs physical validation. The upstream driver exposes
PCI I/O access to user space; HackinFX only scopes its own use of that service.
For recovery, boot your known-working backup EFI and restore the saved EFI
contents to the original partition. Installer transaction metadata accompanies
the backup. The automatic setup is tested against fixture EFIs, not by changing
the development host's live boot partition.

## Separate OpenCore preparation package

The accompanying `HackinFX-RAM-OpenCore-Setup.zip` contains the unchanged upstream v1.0 driver ZIP, corresponding upstream source archive, GPL license, checksums, and a **fragment** for one OpenCore Kernel/Add entry. The driver binary was checked as x86-64; this is not a boot or hardware validation.

1. Review the upstream source and package, and preserve your current working EFI/configuration before making a boot change.
2. Extract `macUSPCIO_Smbus.kext` from its original archive into your existing `EFI/OC/Kexts`. Merge the sample entry into the existing `Kernel -> Add` array using your normal OpenCore configuration workflow. The supplied plist is only a fragment; never replace your complete config.plist with it. Validate the resulting configuration with the matching OpenCore tools.
3. Reboot normally. In HackinFX, rediscover devices, open a RAM device's details, and choose **Probe RAM RGB**. Probe checks only documented Corsair lighting addresses/signatures, then validates device information and CRC. It does not send colors.
4. Only successfully identified controllers become selectable. Select a DIMM, choose **Static**, and change the color (lighting is live). Confirm the visible color yourself. The initial adapter offers one uniform color per DIMM; no RAM gradient/streaming support is claimed.

If the service is missing, access is denied, more than one host is present, the I/O BAR is invalid, the host is disabled/SMI-owned, or controller identity/CRC fails, control remains disabled. Host registers/configuration are not enabled or rewritten to bypass such failures. Busy/error/timeouts stop the session rather than forcing a reset or retry. Inspect/export diagnostics instead.

## Implemented protocol boundaries

- Preflight enumerates PCI identities and driver presence without opening an SMBus user client.
- Explicit probe opens the exact host through macUSPCIO, validates configuration/BAR, and checks only Corsair lighting ranges 18–1F / 58–5F. No general bus sweep or SPD reading/writing is implemented.
- Only recognized Corsair signatures proceed to device-info selection and CRC validation. Unknown vendors, product IDs and CRC mismatches cannot receive color commands.
- Static lighting uses the OpenRGB Corsair effect buffer, CRC check and apply command. There are no bootloader, firmware-update or SPD commands. Firmware-internal storage behavior is not independently established; this is not a promise that firmware never persists settings internally.
- A private process lock serializes HackinFX RAM helpers; it is not a lock against unrelated RGB tools or firmware. Close other RAM RGB applications before testing.

The low-level implementation and original OpenRGB protocol references are included in Source. Runtime testing of actual RAM color remains blocked on the missing driver/boot step and subsequent hardware validation.

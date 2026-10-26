# Corsair Titanium DDR5 RAM RGB setup

**Development 2.2.1: a uniform mint color is physically confirmed on all four DIMMs.**
Four Corsair Titanium controllers were identified at RGB addresses 0x18–0x1B.
The tested host is Intel Arrow Lake SMBus **8086:7f23**, with a loaded macUSPCIO
user client; PID **0801**, protocol **4**, and 12 LEDs are required for lighting.
This is scoped support, not generic support for other memory kits or host controllers.
Separate RGB regions and paced Mint Twinkle were visually confirmed on all four DIMMs. The eight-second animation test measured 16.65 completed FPS per DIMM; long-duration validation is still pending.

## Required transport

RAM RGB uses the separately installed [macUSPCIO driver](https://github.com/ShadyNawara/macUSPCIO).
Only the explicit probe opens the exact SMBus host and validates documented RGB
controller identity and CRC. Startup inventory does not send RAM colors.

## Installer-assisted OpenCore setup

The PKG installer offers **OpenCore SMBus driver (RAM RGB)** under Customize.
Selecting it detects GPT EFI and FAT/MBR OpenCore partitions, prefers the actual boot partition identity
using the OpenCore NVRAM boot-path (GPT UUID or MBR disk signature plus partition number), and otherwise accepts only one unambiguous OpenCore
installation. If that path is unavailable or ambiguous, an interactive EFI selection dialog
asks which OpenCore installation to use. Cancelling changes nothing. Malformed
configurations stop the component without writing to an EFI. The component is optional and off by default.

Before changes it saves a complete EFI backup under
`/Library/Application Support/HackinFX/EFI Backups/<timestamp>/EFI` (administrator
access). It copies the unchanged upstream `macUSPCIO_Smbus.kext` into
`EFI/OC/Kexts` and adds/enables exactly its Kernel/Add entry in the existing
config. It preserves other settings and the original plist format, rejects
conflicting/duplicate transport entries, and rolls back failed writes.
Reboot afterward, then use Probe RAM RGB. No immediate kext loading, SIP changes,
security-setting changes or whole-config replacement is performed.

The app itself never edits EFI. The development host now boots with this driver loaded; all four DIMMs have passed a visible Static mint test. The upstream driver exposes
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
4. Only successfully identified controllers become selectable. Select a DIMM, choose **Static**, and change the color (lighting is live). Confirm the visible color yourself. The adapter exposes 12 LEDs per DIMM and sends host-rendered frames on the shared timeline after explicit selection. Animated output and achieved frame rate still need hardware validation.

If the service is missing, access is denied, more than one host is present, the I/O BAR is invalid, the host is disabled/SMI-owned, or controller identity/CRC fails, control remains disabled. Host registers/configuration are not enabled or rewritten to bypass such failures. Busy/error/timeouts stop the session rather than forcing a reset or retry. Inspect/export diagnostics instead.

## Implemented protocol boundaries

- Preflight enumerates PCI identities and driver presence without opening an SMBus user client.
- Explicit probe opens the exact host through macUSPCIO, validates configuration/BAR, and checks only Corsair lighting ranges 18–1F / 58–5F. No general bus sweep or SPD reading/writing is implemented.
- Only recognized Corsair signatures proceed to device-info selection and CRC validation. Unknown vendors, product IDs and CRC mismatches cannot receive color commands.
- Lighting uses CRC-8 protected direct packets: 32-byte and 6-byte SMBus blocks at RGB commands 0x31/0x32. Titanium LED order follows OpenRGB. Effect configuration writes, word fallback, bootloader/firmware commands and SPD addresses are excluded. Existing host mode is checked and left unchanged.
- A private process lock serializes HackinFX RAM helpers; it is not a lock against unrelated RGB tools or firmware. Close other RAM RGB applications before testing.

The low-level implementation and original OpenRGB protocol references are included in Source. All four controllers at 0x18–0x1B have passed visible mint verification. No automatic RAM startup, arbitrary bus scanning or forced reset is enabled. The user confirmed separate RGB regions and fluid Mint Twinkle; measured completed rate was 16.65 FPS per DIMM across all four. This is a short test, not a long-duration stability result.

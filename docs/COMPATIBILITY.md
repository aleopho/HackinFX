# Compatibility and new hardware

## Included profile

| Field | Value |
| --- | --- |
| Board | PNY XLR8 RTX 4080 VERTO |
| GPU / board vendor | NVIDIA / PNY |
| PCI | `10de:2704` |
| PCI subsystem | `196e:13bc` |
| Local module key | `pny-4080-196e-13bc` |
| Native RM I2C port | 1 |
| Controller address / register | `0x60` / `0x02` |
| Zones | 0, 1, 2 |
| Visually confirmed | Static, Gradient, Spectrum, Breathing, Wave |
| Implemented but not separately visually confirmed | Off |

Development hardware observations reported Intel macOS 26.7.1 and NVRM bundle 2.5.2. The bundle number alone does not identify a NullMoth release. Driver implementation references are pinned separately to v2.5.3. No general claim is made for all PNY, RTX 4080, Lovelace, AMD or Intel hardware.

## Three distinct meanings

- **Detected:** PCI/registry/driver inventory produced identity information. This does not prove RGB capability.
- **User confirmed:** transport completed and the user says the physical test worked. Shared confirmations automatically grow the informational catalog.
- **Supported local RGB profile:** this release includes a controller/transport implementation guarded by an exact hardware match. This is what permits commands.

A catalog entry does not transform an unknown controller into an implemented module. Community evidence informs the next release; it does not install a driver remotely. Registry labels and user-supplied model names never override PCI guards.

## To help add a card

1. Run passive inventory and send a reviewed report with exact manufacturer/model/revision and a description of the lighting behavior.
2. Identify a documented controller, protocol, suitable macOS transport and license-compatible implementation reference.
3. Add a narrowly scoped profile, not a broad vendor/device wildcard. Preserve unknown-device rejection and failure cleanup.
4. Test packet construction and rejection paths offline, then perform an explicitly bounded physical test on that exact board.
5. Record visible results per effect, port/address/register/zone evidence and environment. Update source, tests, documentation and bundled compatibility data for a reviewed release.

Reports help match subsystems and compare environments; they do not reveal an unknown I2C controller address, firmware protocol or physical zone geometry. Please do not run random bus sweeps or reuse a profile solely because a card looks similar.

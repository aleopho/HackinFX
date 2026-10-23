# SPDX-License-Identifier: GPL-2.0-or-later
"""Verified device profiles. Add support only after controller/transport validation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    key: str
    name: str
    pci: tuple
    port: int
    address: int
    register: int
    zones: int

    def matches(self, device):
        return tuple(device.get(key) for key in ('vendor-id', 'device-id', 'subsystem-vendor-id', 'subsystem-id')) == self.pci


PROFILES = (Profile('pny-4080-196e-13bc', 'PNY XLR8 RTX 4080 VERTO',
                    (0x10de, 0x2704, 0x196e, 0x13bc), 1, 0x60, 0x02, 3),)


def select(devices):
    if len(devices) != 1:
        raise ValueError('Exactly one NVRM-backed GPU required')
    matches = [profile for profile in PROFILES if profile.matches(devices[0])]
    if len(matches) != 1:
        raise ValueError('No verified RGB profile for this PCI subsystem')
    return matches[0]

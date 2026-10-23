# SPDX-License-Identifier: GPL-2.0-or-later
"""Executable controller profiles; a profile permits testing, not a claim of user verification."""
import gpu_catalog
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
    controller: str = "PNYLovelaceGPUController"
    effects: tuple = ("static","gradient","cycle","breath","wave")

    def matches(self, device):
        return tuple(device.get(key) for key in ('vendor-id', 'device-id', 'subsystem-vendor-id', 'subsystem-id')) == self.pci


# This macOS transport implements PNY Lovelace and EVGA Pascal. Exact upstream
# registrations sharing that implementation can enter the visual test. Never
# infer write compatibility from a board vendor or GPU generation alone.
def controller_profiles():
    rows = gpu_catalog.load()[0]['pci_registrations']
    result = {}
    for row in rows:
        if (row['controller'],row['address_7bit']) not in (('PNYLovelaceGPUController',0x60),('EVGAPascalGPUController',0x49),('AsusAuraGPUController',0x29)):
            continue
        pci = tuple(int(value, 16) for value in row['pci'])
        identity = gpu_catalog.identify(dict(zip(gpu_catalog.PCI_FIELDS,pci)))
        if pci[0] != 0x10de or identity['controllers'] != [row['controller']]:
            continue
        key = 'pny-4080-196e-13bc' if pci == (0x10de,0x2704,0x196e,0x13bc) else 'pny-lovelace-' + '-'.join(row['pci'])
        name = 'PNY XLR8 RTX 4080 VERTO' if pci == (0x10de,0x2704,0x196e,0x13bc) else row['name']
        if row['controller'] == 'AsusAuraGPUController':
            key = 'asus-aura-' + '-'.join(row['pci'])
            result[pci] = Profile(key,row['name'],pci,1,0x29,0x07,1,row['controller'],('static','cycle','breath'))
        elif row['controller'] == 'EVGAPascalGPUController':
            key = 'evga-pascal-' + '-'.join(row['pci'])
            result[pci] = Profile(key,row['name'],pci,1,0x49,0x0c,1,row['controller'],('static','cycle','breath'))
        else:
            result[pci] = Profile(key,name,pci,1,0x60,0x02,3)
    return tuple(result.values())


PROFILES = controller_profiles()


def select(devices):
    if len(devices) != 1:
        raise ValueError('Exactly one NVRM-backed GPU required')
    matches = [profile for profile in PROFILES if profile.matches(devices[0])]
    if len(matches) != 1:
        raise ValueError('No executable RGB controller for this exact PCI subsystem')
    return matches[0]

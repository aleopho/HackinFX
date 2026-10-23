# SPDX-License-Identifier: GPL-2.0-or-later
"""Passive exact-ID catalog lookup. Never selects a transport or permits writes."""
import json
from functools import lru_cache
from pathlib import Path

PCI_FIELDS = ('vendor-id', 'device-id', 'subsystem-vendor-id', 'subsystem-id')


@lru_cache(maxsize=1)
def load():
    data = json.loads(Path(__file__).with_name('openrgb_gpu_catalog.json').read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported GPU catalog schema')
    index = {}
    for row in data['pci_registrations']:
        index.setdefault(tuple(int(v, 16) for v in row['pci']), []).append(row)
    return data, index


def identify(pci):
    data, index = load()
    values = tuple(pci.get(key) for key in PCI_FIELDS)
    matches = index.get(values, []) if all(type(v) is int and 0 <= v <= 65535 for v in values) else []
    names = sorted({row['name'] for row in matches})
    controllers = sorted({row['controller'] for row in matches})
    subvendor = pci.get('subsystem-vendor-id')
    board = data['subsystem_vendors'].get('%04x' % subvendor, []) if type(subvendor) is int else []
    return dict(matched=bool(matches), name=names[0] if len(names) == 1 else None,
                aliases=names, controllers=controllers, ambiguous=len(names) > 1 or len(controllers) > 1,
                board_vendor=' / '.join(board) if board else None,
                upstream_commit=data['upstream']['commit'],
                transport_requirements=sorted({row['transport'] for row in matches}),
                # These rows are evidence for a port, never an executable profile.
                status='upstream-known; macOS controller/transport validation required' if matches else 'not-in-upstream-catalog')

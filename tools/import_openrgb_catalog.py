#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline, deterministic import of pinned OpenRGB GPU identity registrations.
No hardware access, downloads, C++ execution or macOS compatibility inference.
"""
import ast
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'vendor/openrgb'
DEST = ROOT / 'app/openrgb_gpu_catalog.json'


def without_comments(text):
    return re.sub(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*',
                  lambda m: m[0] if m[0].startswith('"') else ' ', text)


def symbols(text):
    text = without_comments(text)
    values = dict(re.findall(r'^\s*#define\s+(\w+)\s+([^\n]+)', text, re.M))
    values.update(re.findall(r'\b([A-Z][A-Z0-9_]+)\s*=\s*(0[xX][0-9a-fA-F]+|\d+)\s*[,;]', text))
    return values


def number(value, constants, stack=()):
    value = value.strip()
    if value in constants:
        if value in stack: raise ValueError('recursive symbol: ' + value)
        return number(constants[value], constants, stack + (value,))
    if not re.fullmatch(r'(?:0[xX][\da-fA-F]+|\d+)[uUlL]*', value):
        raise ValueError('unresolved numeric symbol: ' + value)
    return int(re.sub(r'[uUlL]+$', '', value), 0) if not value.isdigit() else int(value)


def registrations(text):
    clean = without_comments(text)
    for m in re.finditer(r'\b(REGISTER_I2C_PCI_DETECTOR|REGISTER_HID_DETECTOR_IPU|REGISTER_HID_DETECTOR_IP)\s*\(([^;]*?)\)\s*;', clean, re.S):
        args = next(csv.reader([m[2]], skipinitialspace=True))
        yield m[1], [v.strip() for v in args]


def build(source=SOURCE):
    manifest = json.loads((source / 'manifest.json').read_text())
    # Hashes make a stale/mixed local source tree fail instead of silently changing provenance.
    for item in manifest['files']:
        if hashlib.sha256((source / item['local']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('upstream source hash mismatch: ' + item['local'])
    constants = symbols((source / 'pci_ids.h').read_text())
    entries, usb, controllers = [], [], set()
    for item in manifest['files']:
        if not item['local'].endswith('.cpp'): continue
        text = (source / item['local']).read_text()
        local = dict(constants)
        for header in manifest['files']:
            if header.get('owner') == item.get('file'): local.update(symbols((source / header['local']).read_text()))
        local.update(symbols(text))
        controller = item['controller']
        controllers.add(controller)
        for macro, args in registrations(text):
            if macro == 'REGISTER_I2C_PCI_DETECTOR':
                if len(args) != 7: raise ValueError('unhandled registration shape: ' + item['path'])
                ids = [number(a, local) for a in args[2:6]]
                address = number(args[6], local)
                if any(not 0 <= n <= 65535 for n in ids) or not 0 <= address <= 127:
                    raise ValueError('invalid PCI ID/address')
                entries.append(dict(name=args[0], pci=['%04x' % n for n in ids], controller=controller,
                                    detector=args[1], transport='i2c', address_7bit=address, source_path=item['path']))
            else:
                usb.append(dict(name=args[0], controller=controller, transport='usb-hid',
                                vendor_id='%04x' % number(args[2], local), product_id='%04x' % number(args[3], local), source_path=item['path']))
        # NvAPI uses a fixed PCI table rather than REGISTER_I2C_PCI_DETECTOR.
        if controller == 'NVIDIAIlluminationController':
            body = re.search(r'device_list\[\]\s*=\s*\{([\s\S]*?)\n\};', without_comments(text))
            if not body: raise ValueError('missing NvAPI PCI table')
            for row in re.findall(r'\{([^{}]+)\}', body[1]):
                args = next(csv.reader([row], skipinitialspace=True))
                if len(args) != 7: raise ValueError('unhandled NvAPI table row')
                ids = [number(a, local) for a in args[:4]]
                entries.append(dict(name=args[6].strip(), pci=['%04x' % n for n in ids], controller=controller,
                                    detector='DetectNVIDIAIllumGPUs', transport='nvapi', address_7bit=None, source_path=item['path']))
    entries.sort(key=lambda row:(row['pci'], row['controller'], row['name'], row['address_7bit'] or -1))
    usb.sort(key=lambda row:(row['vendor_id'], row['product_id'], row['name']))
    # Subvendor names are ID-owner labels, not a guarantee of marketing-brand identity.
    vendors = {}
    for key in constants:
        if key.endswith('_SUB_VEN'):
            value = '%04x' % number(key, constants)
            vendors.setdefault(value, []).append(key[:-8].replace('_', ' '))
    gpu_names = {}
    for key in constants:
        if key.startswith('NVIDIA_') and key.endswith('_DEV'):
            value = '%04x' % number(key, constants)
            gpu_names.setdefault(value, []).append(key[7:-4].replace('_', ' '))
    return dict(schema_version=1, upstream=dict(project='OpenRGB', commit=manifest['commit'], license='GPL-2.0-or-later',
                 url='https://gitlab.com/CalcProgrammer1/OpenRGB', scope='Pinned GPU detector sources; identity metadata only, not macOS driver support'),
                controller_families=sorted(controllers), pci_registrations=entries, usb_registrations=usb,
                subsystem_vendors={key:sorted(set(value)) for key,value in sorted(vendors.items())},
                nvidia_device_labels={key:sorted(set(value)) for key,value in sorted(gpu_names.items())})


if __name__ == '__main__':
    result = build()
    DEST.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print('%d PCI registrations / %d unique PCI tuples / %d USB registrations / %d GPU controller families' %
          (len(result['pci_registrations']),len({tuple(r['pci']) for r in result['pci_registrations']}),len(result['usb_registrations']),len(result['controller_families'])))

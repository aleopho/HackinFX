#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only GPU inventory for HackinFX. No RM connections or I2C calls."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys
import time
import uuid
import probe
import profiles
import gpu_catalog

VERSION = '1.2.0'
DRIVER = re.compile(r'(com\.(?:nullmoth[\w.]*|nvidia[\w.]*|apple\.(?:GeForce|NVDA|AMD|ATI|AppleIntel)[\w.]*))\s+\(([^)]+)\)')


def clean_text(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace').rstrip('\0')
    if not isinstance(value, str):
        return None
    return ''.join(c for c in value if c.isprintable())[:160]


def adapters_from_tree(roots):
    """Persist only explicit public hardware fields, never the raw tree."""
    result, seen = [], set()
    for node in probe.walk(roots):
        class_code = probe.pci_value(node, 'class-code')
        device_type = clean_text(node.get('device_type'))
        if not (class_code is not None and class_code >> 16 == 3) and device_type != 'display':
            continue
        vendor = probe.pci_value(node, 'vendor-id')
        device = probe.pci_value(node, 'device-id')
        if vendor is None or device is None:
            continue
        # Entry IDs are used locally only to deduplicate overlapping ioreg roots.
        ident = node.get('IORegistryEntryID')
        if ident is not None and ident in seen:
            continue
        if ident is not None:
            seen.add(ident)
        pci = {key: probe.pci_value(node, key) for key in
               ('vendor-id','device-id','subsystem-vendor-id','subsystem-id')}
        matches = [profile for profile in profiles.PROFILES if profile.matches(pci)]
        upstream = gpu_catalog.identify(pci)
        bound = any(child.get('IOObjectClass') == 'NVRM' for child in probe.walk([node]))
        result.append(dict(pci=pci, pci_hex={key: '%04x' % value if value is not None else None for key,value in pci.items()},
                           class_code=class_code, openrgb=upstream, catalog_name=upstream['name'], catalog_status=upstream['status'], gpu_name={0x2704:'GeForce RTX 4080'}.get(device) if vendor==0x10de else clean_text(node.get('model')), board_vendor=upstream['board_vendor'] or ('PNY' if pci['subsystem-vendor-id']==0x196e else ('PCI %04x' % pci['subsystem-vendor-id'] if pci['subsystem-vendor-id'] is not None else 'Unknown')), profile_name=matches[0].name if len(matches)==1 else None, vendor_name={0x10de:'NVIDIA',0x1002:'AMD',0x8086:'Intel'}.get(vendor,'Other'), gpu_type={0:'VGA-compatible display controller',1:'XGA display controller',2:'3D controller'}.get((class_code >> 8) & 255 if class_code is not None else -1,'Display controller'), model=clean_text(node.get('model')),
                           registry_name=clean_text(node.get('IORegistryEntryName')),
                           nvrm_bound=bound, verified_profile=matches[0].key if len(matches)==1 else None,
                           available_effects=list(matches[0].effects) if len(matches)==1 else [], controller=matches[0].controller if len(matches)==1 else None, rgb_support='verified-profile' if matches and bound else 'not-verified'))
    return result


def lighting_configuration(adapters, inventory_failed=False, arch=None):
    if inventory_failed:
        return dict(status='unknown', reason='PCI inventory failed; lighting remains disabled')
    if (arch or platform.machine()) != 'x86_64':
        return dict(status='unsupported', reason='Lighting transport requires x86-64 macOS')
    bound = [adapter for adapter in adapters if adapter['nvrm_bound']]
    if len(bound) != 1:
        return dict(status='unsupported', reason='Exactly one NVRM-bound display adapter is required')
    if bound[0]['rgb_support'] != 'verified-profile':
        return dict(status='unsupported', reason='No macOS lighting controller for the NVRM-bound adapter')
    return dict(status='supported', reason='Exact OpenRGB controller profile and NVRM binding found; visual confirmation required', profile=bound[0]['verified_profile'])


def hardware_inventory(value):
    """Allowlist public model/specification fields; never store raw profiler output."""
    fields={'_name','machine_model','model_name','chip_type','cpu_type','current_processor_speed','number_processors','total_number_cores','physical_memory','dimm_size','dimm_type','dimm_speed','dimm_manufacturer','dimm_part_number','vendor_id','product_id','manufacturer','device_name','sppci_vendor-id','sppci_device-id','sppci_model','sppci_name','size','physical_interconnect'}
    rows=[]
    def visit(node,category):
        if isinstance(node,list):
            for child in node[:128]:visit(child,category)
        elif isinstance(node,dict):
            row={key:clean_text(str(val)) for key,val in node.items() if key in fields and not (category == "SPStorageDataType" and key == "_name") and isinstance(val,(str,int,float))}
            if row and len(rows)<128:rows.append(dict(category=category,**row))
            for val in node.values():
                if isinstance(val,(dict,list)):visit(val,category)
    for category,items in value.items():visit(items,category)
    return rows


def collect(run=subprocess.run):
    report = dict(schema_version=1, tool='HackinFX', tool_version=VERSION,
                  scan_id=str(uuid.uuid4()), created_at=datetime.now(timezone.utc).isoformat(),
                  runtime=dict(macos=platform.mac_ver()[0], arch=platform.machine(), python=platform.python_version()),
                  scan_mode='read-only-inventory', rm_connections=0, i2c_transactions=0,
                  adapters=[], driver_bundles=[], events=[], errors=[])
    commands = [('pci-inventory', ['/usr/sbin/ioreg','-a','-r','-c','IOPCIDevice']),
                ('loaded-graphics-drivers', ['/usr/sbin/kextstat']),
                ('system-hardware', ['/usr/sbin/system_profiler','SPHardwareDataType','SPMemoryDataType','SPUSBDataType','SPPCIDataType','SPStorageDataType','-json'])]
    for name, command in commands:
        started = time.monotonic()
        event = dict(step=name)
        try:
            process = run(command, capture_output=True, timeout=25)
            event['returncode'] = process.returncode
            if process.returncode:
                raise RuntimeError('System command failed with exit code %d' % process.returncode)
            if name == 'pci-inventory':
                report['adapters'] = adapters_from_tree(plistlib.loads(process.stdout))
            elif name == 'system-hardware':
                report['setup'] = {'system_hardware':hardware_inventory(json.loads(process.stdout))}
            else:
                output = process.stdout.decode('utf-8', errors='replace')
                report['driver_bundles'] = [dict(identifier=match.group(1), version=clean_text(match.group(2))) for match in DRIVER.finditer(output)]
            event['status'] = 'ok'
        except Exception as exc:
            event['status'] = 'error'
            # No raw command output, device trees, user paths or exception repr.
            error = dict(step=name, type=type(exc).__name__, message='Read-only system query did not complete')
            report['errors'].append(error)
        event['elapsed_ms'] = round((time.monotonic()-started)*1000)
        report['events'].append(event)
    if not report['adapters'] and not any(e['step']=='pci-inventory' for e in report['errors']):
        report['events'].append(dict(step='adapter-selection', status='no-display-pci-device'))
    report['lighting_configuration'] = lighting_configuration(report['adapters'], any(error['step']=='pci-inventory' for error in report['errors']), report['runtime']['arch'])
    identity = dict(module='pny-lovelace-v1', arch=report['runtime']['arch'], macos=report['runtime']['macos'], adapters=sorted([dict(pci=a['pci'], nvrm_bound=a['nvrm_bound']) for a in report['adapters']], key=lambda a: json.dumps(a, sort_keys=True)), drivers=sorted(report['driver_bundles'], key=lambda d: d['identifier']))
    report['configuration_fingerprint'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest() if not any(e['step'] in ('pci-inventory','loaded-graphics-drivers') for e in report['errors']) else None
    report['led_availability'] = 'documented-for-matched-profile; visual test required' if report['lighting_configuration']['status']=='supported' else 'unknown; PCI inventory cannot establish LED availability'
    report['development_assessment'] = dict(useful_for=['PCI subsystem matching', 'driver and platform comparison', 'selecting hardware for targeted testing'], not_proven=['RGB controller identity/address', 'I2C port mapping or permissions', 'lighting protocol and physical zone layout'], next_step='Identify a documented controller and transport, then validate a narrowly scoped hardware test')
    report['privacy'] = 'Allowlisted CPU, memory, USB, PCI and storage model/specification fields and driver versions only. No serial numbers, raw IORegistry, hostname or kernel addresses.'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        handle = args.output.open('x', encoding='utf-8')
    except OSError as exc:
        parser.exit(2, 'Cannot reserve report; scan not started: %s\n' % exc)
    with handle:
        report = collect()
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps(report, indent=2))
    return int(bool(report['errors']))


if __name__ == '__main__':
    sys.exit(main())

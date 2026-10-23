#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Experimental RAM inventory. No SPD reads, bus probing, driver opens or writes."""
import argparse
import json
from pathlib import Path
import plistlib
import subprocess
from datetime import datetime, timezone
import probe

FIELDS = {'_name':'slot','dimm_manufacturer':'manufacturer','dimm_part_number':'part_number',
          'dimm_type':'type','dimm_size':'size','dimm_speed':'speed'}


def modules(tree):
    result = []
    def visit(value):
        if isinstance(value,dict):
            if value.get('dimm_size') not in (None,'empty','Empty'):
                row = {target:str(value[key])[:160] for key,target in FIELDS.items() if key in value}
                result.append(row)
            for item in value.values(): visit(item)
        elif isinstance(value,list):
            for item in value: visit(item)
    visit(tree)
    return result


def collect(run=subprocess.run):
    result = dict(schema_version=1,tool='HackinFX RAM research',created_at=datetime.now(timezone.utc).isoformat(),
                  mode='read-only-inventory',modules=[],smbus_controllers=[],errors=[],
                  spd_reads=0,bus_transactions=0,hardware_writes=0,
                  lighting_transport='not-implemented',
                  next_step='Identify a documented macOS host-SMBus interface before any RAM lighting test. The GPU NVRM transport cannot access DIMMs.')
    try:
        response=run(['/usr/sbin/system_profiler','SPMemoryDataType','-json'],capture_output=True,check=True,timeout=30)
        result['modules']=modules(json.loads(response.stdout))
    except Exception as exc: result['errors'].append('memory inventory: '+type(exc).__name__)
    try:
        response=run(['/usr/sbin/ioreg','-a','-r','-c','IOPCIDevice'],capture_output=True,check=True,timeout=25)
        for node in probe.walk(plistlib.loads(response.stdout)):
            code=probe.pci_value(node,'class-code')
            if code is not None and code >> 8 == 0x0c05:
                result['smbus_controllers'].append({key:'%04x'%value for key in ('vendor-id','device-id','subsystem-vendor-id','subsystem-id') if (value:=probe.pci_value(node,key)) is not None})
    except Exception as exc: result['errors'].append('SMBus PCI inventory: '+type(exc).__name__)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Reserve destination before querying hardware; never overwrite a report.
    with args.output.open('x',encoding='utf-8') as handle:
        report=collect()
        json.dump(report,handle,indent=2);handle.write('\n')
    print('Saved read-only RAM inventory:',args.output)


if __name__=='__main__': main()

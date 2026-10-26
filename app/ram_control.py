# SPDX-License-Identifier: GPL-2.0-or-later
"""Explicit Corsair DDR5 RGB setup. Driver discovery never opens or writes the bus."""
import hashlib,json,subprocess
from pathlib import Path
from usb_devices import HIDTransport
from ram_probe import modules

class RAMAdapter:
    name='native-ram'
    def __init__(self,transport=None,module_reader=None):
        self.transport=transport or HIDTransport(Path(__file__).with_name('HackinFXSMBus'),timeout=20);self.reader=module_reader or self.read_modules;self.rows=[];self.allowed={};self.status={};self.dimms=[];self.probe_error="";self.host_diagnostics={}
    @staticmethod
    def read_modules():
        output=subprocess.run(['/usr/sbin/system_profiler','SPMemoryDataType','-json'],capture_output=True,check=True,timeout=30)
        return modules(json.loads(output.stdout))
    def discover(self):
        self.status=self.transport.call(dict(command='status'));self.dimms=self.reader()
        if not self.status['driver_loaded'] or self.status['controllers']!=[dict(vendor_id='8086',device_id='7f23')]:self.allowed={};self.rows=[]
        if self.rows:return self.rows
        controller=', '.join(r['vendor_id']+':'+r['device_id'] for r in self.status['controllers']) or 'not detected'
        supported=self.status['controllers']==[dict(vendor_id='8086',device_id='7f23')]
        loaded=self.status['driver_loaded']
        rows=[]
        for i,d in enumerate(self.dimms):
            family=d.get('manufacturer','').lower()=='corsair' and d.get('part_number','').startswith('CMP')
            state='probe-failed' if family and supported and loaded and self.probe_error else 'unsupported-memory' if not family else 'unsupported-host' if not supported else 'driver-required' if not loaded else 'setup-required'
            detail='This RAM family is currently inventory-only.' if not family else 'The initial native adapter is restricted to Intel 8086:7f23.' if not supported else 'macUSPCIO is not loaded. Install the optional driver into the OpenCore volume actually used at boot, then restart. An installed package is not proof of a running kernel driver.' if not loaded else 'Use Probe RAM RGB to validate exact Corsair identity and CRC. No SPD data or firmware commands are written.'
            if state=='probe-failed':detail='RGB identity probe failed: '+self.probe_error+'. No RAM lighting has been verified. Export diagnostics before another attempt.'
            rows.append(dict(id='ram-inventory:'+str(i),fingerprint='',name=d.get('part_number','Memory')+' · '+d.get('size',''),vendor=d.get('manufacturer',''),category='dram',backend='inventory',led_count=0,direct=False,controllable=False,status=state,detail='SMBus '+controller+'. '+detail,hardware_state=self.host_diagnostics,static_modes=[],zones=[],modes=[],driver='corsair-ddr5-i801'))
        return rows

    def probe(self):
        # A known module family and exact host are prerequisites, not write authorization by name alone.
        self.discover()
        if not any(d.get('manufacturer','').lower()=='corsair' and d.get('part_number','').startswith('CMP') for d in self.dimms):raise ValueError('This first RAM adapter requires Corsair Dominator Titanium DDR5 inventory')
        if not self.status['driver_loaded']:raise ValueError('RAM RGB requires the macUSPCIO OpenCore driver and reboot; see RAM setup')
        if self.status['controllers']!=[dict(vendor_id='8086',device_id='7f23')]:raise ValueError('Only the exact Intel 8086:7f23 host is enabled in this adapter')
        try:found=self.transport.call(dict(command='probe'))['devices']
        except Exception as exc:
            self.probe_error=str(exc)[:300]
            try:self.host_diagnostics=self.transport.call(dict(command='diagnostics'))
            except Exception:self.host_diagnostics={}
            raise
        self.probe_error='';rows=[];allowed={}
        for d in found:
            if type(d.get('address'))is not int or d['address'] not in list(range(0x18,0x20))+list(range(0x58,0x60)) or d.get('product_id')!='0801' or d.get('protocol')!=4 or d.get('led_count')!=12:raise ValueError('RAM helper returned an unexpected controller identity')
            key='corsair-ram:%02x'%d['address']
            if key in allowed:raise ValueError('Duplicate RAM controller address')
            allowed[key]=d['address'];rows.append(dict(id=key,fingerprint=hashlib.sha256(key.encode()).hexdigest()[:24],name=d['name']+' · 0x%02X'%d['address'],vendor='Corsair',category='dram',backend=self.name,led_count=12,direct=True,controllable=True,status='ready',detail='Exact Corsair controller identity and CRC passed. 12 individually addressed LEDs via direct SMBus blocks. Select explicitly for shared-clock effects. Visual verification is specific to each DIMM.',static_modes=['static'],zones=[dict(name='DIMM lighting · 12 LEDs',led_count=12)],led_positions=[dict(x=0.5,y=i/11) for i in range(12)],modes=[],driver='corsair-ddr5-i801'))
        self.allowed=allowed;self.rows=rows
        if not rows:raise ValueError('No verified Corsair Titanium lighting controller responded; no color commands were sent')
        return rows
    def activate(self,device):
        if device['id'] not in self.allowed:raise ValueError('Probe RAM RGB before lighting control')
    def write_frame(self,device,colors,mode):
        if len(colors)!=12 or any(len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in colors):raise ValueError('RAM frame requires exactly 12 RGB colors in range 0–255')
        address=self.allowed[device['id']]
        try:self.transport.call(dict(command='frame',address=address,colors=[list(c) for c in colors]))
        except Exception:
            self.allowed={}
            for row in self.rows:row.update(controllable=False,direct=False,status='transport-error',detail='RAM streaming stopped after a bus error. Restart Core and explicitly probe again; no automatic retry or bus reset.')
            raise
    def close(self):self.allowed={};self.rows=[];self.transport.close()

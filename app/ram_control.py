# SPDX-License-Identifier: GPL-2.0-or-later
"""Corsair DDR5 RGB setup with saved, identity-bound startup authorization.
Unprofiled discovery stays passive; saved profiles permit fresh RGB identity checks."""
import hashlib,json,subprocess,os,tempfile,threading
from pathlib import Path
from usb_devices import HIDTransport
from ram_probe import modules

class RAMAdapter:
    name='native-ram'
    def __init__(self,transport=None,module_reader=None,profile_path=None,auto_known=None):
        self.stopping=threading.Event();self.profile_path=Path(profile_path) if profile_path else (Path.home()/'Documents/HackinFX/ram-rgb-profile.json' if transport is None else None);self.profile_checked=False;self.inventory_id='';self.auto_known=(transport is None) if auto_known is None else bool(auto_known)
        self.transport=transport or HIDTransport(Path(__file__).with_name('HackinFXSMBus'),timeout=20);self.reader=module_reader or self.read_modules;self.rows=[];self.allowed={};self.status={};self.dimms=[];self.probe_error="";self.host_diagnostics={}
    @staticmethod
    def read_modules():
        output=subprocess.run(['/usr/sbin/system_profiler','SPMemoryDataType','-json'],capture_output=True,check=True,timeout=30)
        return modules(json.loads(output.stdout))
    def inventory_fingerprint(self,legacy=False):
        fields=('manufacturer','part_number','slot','size','type')
        canonical=sorted([dict(d) if legacy else {k:' '.join(str(d.get(k,'' )).split()).casefold() for k in fields} for d in self.dimms],key=lambda d:json.dumps(d,sort_keys=True))
        return hashlib.sha256(json.dumps(dict(controllers=self.status['controllers'],modules=canonical),sort_keys=True).encode()).hexdigest()
    @property
    def revocation_path(self):return self.profile_path.with_suffix('.revoked.json') if self.profile_path else None
    def forget_profile(self,reason=None):
        self.allowed={};self.rows=[]
        if self.profile_path:
            self.profile_path.unlink(missing_ok=True)
            if reason:
                self.profile_path.parent.mkdir(parents=True,exist_ok=True)
                fd=os.open(str(self.revocation_path),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                with os.fdopen(fd,'w') as file:json.dump(dict(schema=1,reason=str(reason)[:300]),file)
    def known_startup_family(self):
        # Only these physically verified Titanium SKUs may migrate without an old profile.
        verified={'CMP32GX5M2B6000Z30','CMP32GX5M2X7200C34'}
        return bool(self.dimms) and len(self.dimms)<=8 and all(d.get('manufacturer','').strip().casefold()=='corsair' and d.get('part_number','').strip().upper() in verified for d in self.dimms)
    def save_profile(self,identities):
        if not self.profile_path:return
        self.profile_path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='.ram-rgb-',dir=self.profile_path.parent)
        try:
            with os.fdopen(fd,'w') as file:json.dump(dict(schema=2,inventory=self.inventory_id,devices=identities),file)
            os.replace(name,self.profile_path)
            self.revocation_path.unlink(missing_ok=True)
        finally:Path(name).unlink(missing_ok=True)
    def discover(self,_restore=True):
        self.status=self.transport.call(dict(command='status'));self.dimms=self.reader()
        current=self.inventory_fingerprint()
        if self.inventory_id and self.inventory_id!=current:self.forget_profile("RAM inventory changed")
        self.inventory_id=current
        compatible=self.status['driver_loaded'] and self.status['controllers']==[dict(vendor_id='8086',device_id='7f23')]
        if not compatible:self.allowed={};self.rows=[]
        if self.rows:return self.rows
        if _restore and compatible and not self.profile_checked and self.profile_path:
            self.profile_checked=True
            try:
                if self.profile_path.stat().st_size>16384:raise ValueError('RAM profile too large')
                saved=json.loads(self.profile_path.read_text())
                expected_inventory=self.inventory_fingerprint(legacy=True) if saved.get('schema')==1 else current
                if saved.get('schema') not in (1,2) or saved.get('inventory')!=expected_inventory or not isinstance(saved.get('devices'),list) or not saved['devices']:raise ValueError('RAM inventory changed; probe again')
                self.probe(_from_discover=True,_expected=saved.get('devices'))
                return self.rows
            except FileNotFoundError:
                if self.revocation_path.exists():
                    try:
                        if self.revocation_path.stat().st_size>2048:raise ValueError('Invalid RAM revocation record')
                        self.probe_error=str(json.loads(self.revocation_path.read_text()).get('reason','Previous RAM validation failed'))[:300]
                    except (OSError,ValueError,TypeError):self.probe_error='Previous RAM validation failed'
                if self.auto_known and self.known_startup_family() and not self.revocation_path.exists():
                    try:
                        self.probe(_from_discover=True,_startup=True);return self.rows
                    except Exception as exc:self.forget_profile(exc);self.probe_error=str(exc)[:300]
            except Exception as exc:self.forget_profile(exc);self.probe_error=str(exc)[:300]

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

    def probe(self,_from_discover=False,_expected=None,_startup=False):
        # A known module family and exact host are prerequisites, not write authorization by name alone.
        if not _from_discover:self.discover(_restore=False)
        self.profile_checked=True
        if not any(d.get('manufacturer','').lower()=='corsair' and d.get('part_number','').startswith('CMP') for d in self.dimms):raise ValueError('This first RAM adapter requires Corsair Dominator Titanium DDR5 inventory')
        if not self.status['driver_loaded']:raise ValueError('RAM RGB requires the macUSPCIO OpenCore driver and reboot; see RAM setup')
        if self.status['controllers']!=[dict(vendor_id='8086',device_id='7f23')]:raise ValueError('Only the exact Intel 8086:7f23 host is enabled in this adapter')
        self.forget_profile("RAM identity validation incomplete; manual probe required")
        try:found=self.transport.call(dict(command='probe'))['devices']
        except Exception as exc:
            self.forget_profile(exc);self.probe_error=str(exc)[:300]
            try:self.host_diagnostics=self.transport.call(dict(command='diagnostics'))
            except Exception:self.host_diagnostics={}
            raise
        self.probe_error='';rows=[];allowed={}
        if _startup and len(found)!=len(self.dimms):raise ValueError('RAM RGB controller count does not match known physical DIMMs')
        for d in found:
            if type(d.get('address'))is not int or d['address'] not in list(range(0x18,0x20))+list(range(0x58,0x60)) or d.get('product_id')!='0801' or d.get('protocol')!=4 or d.get('led_count')!=12:raise ValueError('RAM helper returned an unexpected controller identity')
            key='corsair-ram:%02x'%d['address']
            if key in allowed:raise ValueError('Duplicate RAM controller address')
            allowed[key]=d['address'];rows.append(dict(id=key,fingerprint=hashlib.sha256(key.encode()).hexdigest()[:24],name=d['name']+' · 0x%02X'%d['address'],vendor='Corsair',category='dram',backend=self.name,led_count=12,direct=True,controllable=True,status='ready',detail='Exact Corsair controller identity and CRC passed. 12 individually addressed LEDs via direct SMBus blocks. Saved probe profile enables automatic startup after exact inventory and RGB identity revalidation. Visual verification is specific to each DIMM.',static_modes=['static'],zones=[dict(name='DIMM lighting · 12 LEDs',led_count=12)],led_positions=[dict(x=0.5,y=i/11) for i in range(12)],modes=[],driver='corsair-ddr5-i801'))
        if not rows:raise ValueError('No verified Corsair Titanium lighting controller responded; no color commands were sent')
        identities=sorted([dict(address=d['address'],product_id=d['product_id'],protocol=d['protocol'],led_count=d['led_count']) for d in found],key=lambda d:d['address'])
        if _expected is not None and identities!=_expected:raise ValueError('RAM RGB identity changed; probe again')
        self.save_profile(identities);self.allowed=allowed;self.rows=rows
        return rows
    def activate(self,device):
        if device['id'] not in self.allowed:raise ValueError('Probe RAM RGB before lighting control')
    def write_frame(self,device,colors,mode):
        if len(colors)!=12 or any(len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in colors):raise ValueError('RAM frame requires exactly 12 RGB colors in range 0–255')
        address=self.allowed[device['id']]
        try:self.transport.call(dict(command='frame',address=address,colors=[list(c) for c in colors]))
        except Exception as exc:
            # A helper pipe closed during an explicitly requested shutdown is not a bus fault.
            interrupted=isinstance(exc,(BrokenPipeError,EOFError)) or str(exc)=='Native HID helper stopped'
            if self.stopping.is_set() and interrupted:raise
            failed_rows=list(self.rows)
            self.forget_profile("RAM lighting transport failed; manual probe required")
            for row in failed_rows:row.update(controllable=False,direct=False,status='transport-error',detail='RAM streaming stopped after a bus error. Restart Core and explicitly probe again; no automatic retry or bus reset.')
            raise
    def begin_shutdown(self):self.stopping.set()
    def close(self):self.begin_shutdown();self.allowed={};self.rows=[];self.transport.close()

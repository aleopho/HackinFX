# SPDX-License-Identifier: GPL-2.0-or-later
"""Native lighting-only IOKit adapters and pinned OpenRGB USB identity catalog."""
import base64,collections,hashlib,json,os,select,struct,subprocess,threading,time
from pathlib import Path
import radius_protocol
import asus_keyboard
import makr75

class HIDError(ValueError):pass

def lamp_descriptor(data):
    """Accept canonical HID LampArray feature layout, with descriptor-provided IDs.
    Unrecognized offsets/counts fail closed; no assumed report IDs are sent.
    """
    if not 1<=len(data)<=16384:raise HIDError('Invalid HID descriptor length')
    page=rid=size=count=0;usages=[];stack=[];globals_stack=[];offsets=collections.defaultdict(int);reports={};fields=collections.defaultdict(list);pos=0
    while pos<len(data):
        prefix=data[pos];pos+=1
        if prefix==0xfe:raise HIDError('Unsupported HID long item')
        length=[0,1,2,4][prefix&3]
        if pos+length>len(data):raise HIDError('Truncated HID descriptor')
        value=int.from_bytes(data[pos:pos+length],'little');pos+=length;tag=prefix&0xfc
        if tag==0x04:page=value
        elif tag==0x08:usages.append((value>>16,value&65535) if length==4 else (page,value))
        elif tag==0x74:size=value
        elif tag==0x94:count=value
        elif tag==0x84:rid=value
        elif tag==0xa4:globals_stack.append((page,rid,size,count))
        elif tag==0xb4:
            if not globals_stack:raise HIDError('Unbalanced HID global state')
            page,rid,size,count=globals_stack.pop()
        elif tag==0xa0:
            stack.append(usages[-1] if usages else (0,0));usages=[]
        elif tag==0xc0:
            if not stack:raise HIDError('Unbalanced HID collection')
            stack.pop();usages=[]
        elif tag in (0x80,0x90,0xb0):
            if size>64 or count>4096 or size*count>65536:raise HIDError('HID report too large')
            if tag==0xb0:
                collection=next((usage for p,usage in reversed(stack) if p==0x59 and usage!=1),0)
                if collection:
                    if not 1<=rid<=255:raise HIDError('LampArray requires explicit report IDs')
                    if collection in reports and reports[collection]!=rid:raise HIDError('Ambiguous LampArray report')
                    reports[collection]=rid
                    for i in range(count):
                        usage=usages[min(i,len(usages)-1)] if usages else (0,0)
                        fields[collection].append((usage,offsets[rid]+i*size,size))
                offsets[rid]+=size*count
            usages=[]
    if stack or globals_stack:raise HIDError('Unbalanced HID descriptor')
    expected={2:[(3,16),(4,32),(5,32),(6,32),(7,32),(8,32)],0x20:[(0x21,16)],0x22:[(0x21,16)]+[(u,32) for u in [0x23,0x24,0x25,0x27,0x26]]+[(u,8) for u in range(0x28,0x2e)],0x50:[(3,8),(0x55,8)]+[(0x21,16)]*8+[(u,8) for _ in range(8) for u in range(0x51,0x55)],0x60:[(0x55,8),(0x61,16),(0x62,16)]+[(u,8) for u in range(0x51,0x55)],0x70:[(0x71,8)]}
    for collection,shape in expected.items():
        offset=0;actual=fields[collection]
        if len(actual)!=len(shape):raise HIDError('Unsupported LampArray feature shape')
        for field,(usage,bits) in zip(actual,shape):
            if field!=((0x59,usage),offset,bits):raise HIDError('Unsupported LampArray field layout')
            offset+=bits
        if offsets[reports[collection]]!=offset:raise HIDError('Unexpected LampArray padding')
    if len(set(reports[c] for c in expected))!=len(expected):raise HIDError('Overlapping LampArray reports')
    return {c:dict(id=reports[c],size=offsets[reports[c]]//8+1) for c in expected}

class HIDTransport:
    def __init__(self,executable=None,timeout=4):
        self.executable=Path(executable) if executable else Path(__file__).with_name('HackinFXHID');self.process=None;self.lock=threading.RLock();self.timeout=timeout
    def call(self,value,timeout=None):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                if not self.executable.is_file():raise HIDError('Native HID helper missing; rebuild or reinstall HackinFX')
                self.process=subprocess.Popen([str(self.executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
            data=json.dumps(value).encode()+b'\n'
            if len(data)>65536:raise HIDError('HID request too large')
            try:
                self.process.stdin.write(data);self.process.stdin.flush();output=bytearray();deadline=time.monotonic()+(self.timeout if timeout is None else timeout)
                while b'\n' not in output:
                    if time.monotonic()>=deadline or not select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:raise TimeoutError('HID transport timed out')
                    part=os.read(self.process.stdout.fileno(),65536)
                    if not part:raise HIDError('Native HID helper stopped')
                    output.extend(part)
                    if len(output)>1048576:raise HIDError('HID response too large')
                response=json.loads(output)
                if 'error' in response:raise HIDError(response['error'])
                return response
            except (BrokenPipeError,TimeoutError,json.JSONDecodeError):self.close();raise
    def exchange_batch(self,handle,packets):
        response=self.call(dict(command='radius_batch',handle=handle,report_id=2,packets=[base64.b64encode(p).decode() for p in packets]),timeout=14)
        if response.get('sent')!=len(packets):raise HIDError('Incomplete Radius acknowledged frame')
    def inventory(self):return self.call(dict(command='inventory'))
    def check(self,handle):return self.call(dict(command='access',handle=handle,report_id=0))
    def get(self,handle,report):
        data=base64.b64decode(self.call(dict(command='feature_get',handle=handle,report_id=report['id'],size=report['size']))['data'],validate=True)
        if len(data)!=report['size'] or data[0]!=report['id']:raise HIDError('HID feature size / ID mismatch')
        return data
    def send(self,handle,packet,feature=False):
        return self.call(dict(command='feature_set' if feature else 'output',handle=handle,report_id=packet[0],data=base64.b64encode(packet).decode()))
    def send_batch(self,handle,packets):
        return self.call(dict(command='output_batch',handle=handle,report_id=0,packets=[base64.b64encode(p).decode() for p in packets]))
    def exchange(self,handle,packet):
        reply=self.call(dict(command='exchange',handle=handle,report_id=packet[0],data=base64.b64encode(packet).decode()))
        return base64.b64decode(reply['data'],validate=True)
    def close(self):
        if self.process:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.process=None

class Catalog:
    def __init__(self,path=None):
        self.entries=json.loads((Path(path) if path else Path(__file__).with_name('openrgb_usb_catalog.json')).read_text())['entries']
        self.by_id=collections.defaultdict(list)
        for row in self.entries:self.by_id[(row['vendor_id'],row['product_id'])].append(row)
    def match(self,vid,pid):return self.by_id.get((vid,pid),[])

def asus_mouse_packet(zone,rgb):
    if zone not in range(3) or len(rgb)!=3 or any(type(v)is not int or not 0<=v<=255 for v in rgb):raise HIDError('Invalid ASUS lighting values')
    packet=bytearray(65);packet[:7]=bytes([0,0x51,0x28,zone,0,0,100]);packet[7:10]=bytes(rgb);return bytes(packet)

def kraken_packets(colors):
    if len(colors)!=9:raise HIDError('Kraken X2 / M2 requires nine lighting zones')
    packet=bytearray(64);packet[:5]=bytes([2,0x4c,0,0,2])
    packet[5:8]=bytes([colors[0][1],colors[0][0],colors[0][2]]) # Logo uses GRB.
    ring=bytearray(64);ring[:5]=bytes([2,0x4c,1,0,2])
    for i,c in enumerate(colors[1:]):ring[5+3*i:8+3*i]=bytes(c)
    return [bytes(packet),bytes(ring)]

class NativeUSBAdapter:
    name='native-usb'
    def __init__(self,transport=None,catalog=None):
        self.transport=transport or HIDTransport();self.catalog=catalog or Catalog();self.records={};self.active=set();self.next_frame={};self.inventory_count=0
    def discover(self):
        self.release();self.transport.close();snapshot=self.transport.inventory();self.records={};rows=[];claimed=set();groups=collections.defaultdict(list)
        for record in snapshot['devices']:groups[record['physical_id']].append(record)
        keyboards={}
        for physical,records in groups.items():
            candidates=[r for r in records if r['vendor_id']==0x0b05 and r['product_id'] in (0x1ace,0x1aae) and r['usage_page']>=0xff00 and r.get('descriptor')]
            if candidates:
                candidate=sorted(candidates,key=lambda r:r['usage_page']!=0xff02)[0]
                try:keyboards[physical]=dict(record=candidate,paired=asus_keyboard.discover(self.transport,candidate),error='')
                except Exception as exc:keyboards[physical]=dict(record=candidate,paired=None,error=str(exc))
        for record in snapshot['devices']:
            keyboard=keyboards.get(record['physical_id'])
            if keyboard and keyboard['record']['handle']!=record['handle']:continue
            vid,pid,page,handle=record['vendor_id'],record['product_id'],record['usage_page'],record['handle'];kind=None;count=0;category='usb';reports=None;status='ready';detail='Native lighting transport; confirm the visible result on your hardware.';direct=False
            if keyboard:
                kind='asus-keyboard';count=1;category='keyboard';direct=False
                if keyboard['error']:status='setup-required';detail=keyboard['error']
                elif record.get('keyboard_topology'):
                    count=len(record['keyboard_topology']['keys']);direct=True;detail='Per-key RGB from exact OpenRGB Scope II 96 layout and device layout reply. Confirm physical key mapping.'
                else:detail='Host-streamed whole-keyboard RGB. Shared timing uses volatile Static color packets; per-key mapping is not implemented.'
            elif vid==0x1b1c and pid==0x2b04 and page==0xff42 and record['usage']==1 and record.get('interface')==1:
                kind='corsair-makr75';category='keyboard';record['makr']=makr75.Controller(self.transport,handle)
                try:
                    record['firmware']=record['makr'].discover();count=len(makr75.KEYS);direct=True
                    detail='User-tested wired MAKR 75, firmware 7.11.104. Individually mapped key LEDs; volatile lighting only. US reference layout.'
                except Exception as exc:status='setup-required';detail=str(exc)
            elif vid==0x36bc and pid==0x1003 and page==0xff00 and record['usage']==1 and record.get('interface')==0:
                kind='radius';category='cooler';record['radius']=radius_protocol.Radius(self.transport,handle)
                try:
                    record['radius_zones']=record['radius'].discover();count=sum(z['count'] for z in record['radius_zones']);direct=True;record['interval']=.05
                    detail='Fractal Radius pump and configured fan RGB zones. Every lighting packet is acknowledged; no PWM, firmware, flash or port-resize commands.'
                except Exception as exc:status='setup-required';detail=str(exc)
            elif page==0x59 and record['usage']==1:
                kind='lamp';direct=True
                try:
                    reports=lamp_descriptor(base64.b64decode(record['descriptor'],validate=True));attributes=self.transport.get(handle,reports[2]);count=struct.unpack_from('<H',attributes,1)[0];array_kind=struct.unpack_from('<I',attributes,15)[0]
                    if not 1<=count<=512:raise HIDError('LampArray count outside supported range')
                    category={1:'keyboard',2:'mouse',3:'gamepad',7:'controller'}.get(array_kind,'controller')
                    interval=max(.05,struct.unpack_from('<I',attributes,19)[0]/1000000)
                    if interval>5:raise HIDError('LampArray update interval outside supported range')
                    record['interval']=interval
                except Exception as exc:
                    count=0;status='access-required';direct=False;detail='HID LampArray detected. '+str(exc)
                    category='keyboard' if any(r['usage_page']==1 and r['usage']==6 for r in groups[record['physical_id']]) else 'mainboard' if vid==0x048d else 'controller'
            elif vid==0x0b05 and pid in (0x1977,0x1979) and page==0xff01:
                kind='asus-spatha';direct=True;count=3;category='mouse'
                detail='Native ASUS Spatha X lighting. Three hardware zones; Static and Gradient. Wireless updates are deliberately bounded.'
            elif vid==0x1e71 and pid in (0x170e,0x1715) and page>=0xff00:
                kind='kraken-x2';count=9;category='cooler';direct=True;record['interval']=.1
            if not kind:continue
            if kind not in ('lamp','radius','asus-keyboard','corsair-makr75'):
                try:self.transport.check(handle)
                except Exception as exc:status='access-required';direct=False;detail=str(exc)
            # A single physical collection is exposed once; no duplicate input interfaces.
            key='hid:'+handle;identity=hashlib.sha256(repr((vid,pid,page,category,count)).encode()).hexdigest()[:24]
            matches=self.catalog.match(vid,pid);names=sorted(set(r['name'] for r in matches if r['enabled']))
            name='ASUS ROG Spatha X'+(' · Wireless' if pid==0x1979 else ' · USB') if kind=='asus-spatha' else record['name'].strip() or (names[0] if len(names)==1 else 'HID lighting device')
            if kind=='radius':name='Fractal Design Radius'
            if kind=='asus-keyboard':name=keyboard['paired']['name'] if keyboard['paired'] else 'ASUS ROG Keyboard · OMNI'
            if kind=='lamp':name+= ' · '+('Keyboard' if category=='keyboard' else 'LampArray')
            row=dict(id=key,fingerprint=identity,name=name,vendor='ASUS' if vid==0x0b05 else 'GIGABYTE / ITE' if vid==0x048d else record['vendor'],category=category,backend=self.name,led_count=count,direct=direct,controllable=count>0 and status=='ready',status=status,detail=detail,static_modes=['static','gradient'],zones=[dict(name='LampArray' if kind=='lamp' else 'Lighting',led_count=count)],modes=[],usb_id='%04x:%04x'%(vid,pid),catalog_matches=names[:12],ownership_names=[record['name'].strip()]+[name for name in names if kind!='asus-spatha' or 'dock' not in name.lower()],driver=kind,refresh_interval=.5 if kind=='radius' else 5 if kind=='corsair-makr75' else 0)
            if kind=='corsair-makr75':
                row.update(color_scope='per-led',physical_led_count=count,led_positions=[dict(x=k['x'],y=k['y']) for k in makr75.KEYS],layout=makr75.LAYOUT['layout'],topology_source=makr75.LAYOUT['source'],hardware_state=dict(firmware=record.get('firmware','')))
            if kind=='radius':row['zones']=[dict(name='Pump' if z['id']==1 else 'Fan RGB %02X'%z['id'],led_count=z['count']) for z in record.get('radius_zones',[])]
            if kind=='asus-keyboard':
                row.update(direct=True,static_modes=['static','gradient'],onboard_modes=[])
                row['zones']=[dict(name='Keyboard · per-key RGB' if record.get('keyboard_topology') else 'Whole keyboard · one color zone',led_count=count)]
                row['hardware_state']={'keyboard_layout_reply':record.get('keyboard_layout_reply',''),'per_key_layout':'mapped' if record.get('keyboard_topology') else 'unrecognized; whole-device fallback'}
                row['color_scope']='per-led' if record.get('keyboard_topology') else 'whole-device'
                row['physical_led_count']=count if record.get('keyboard_topology') else None
                if record.get('keyboard_topology'):
                    row['led_positions']=record['keyboard_topology']['positions'];row['topology_source']=record['keyboard_topology']['source'];row['layout']=record['keyboard_topology']['layout']
            rows.append(row);claimed.add(record['physical_id']);self.records[key]=dict(record,kind=kind,reports=reports,count=count)
        usb={r['physical_id']:r for r in snapshot.get('usb',[])}
        for physical,records in groups.items():
            if physical not in usb:usb[physical]=records[0]
        for physical,record in usb.items():
            if physical in claimed:continue
            name=record['name'].strip();vid,pid=record['vendor_id'],record['product_id'];matches=self.catalog.match(vid,pid);enabled=[r for r in matches if r['enabled']];usages={(r['usage_page'],r['usage']) for r in groups[physical]};category='keyboard' if (1,6) in usages else 'mouse' if (1,2) in usages else enabled[0]['category'] if enabled else 'usb'
            if 'hub' in name.lower():continue
            names=sorted(set(r['name'] for r in enabled));detail='OpenRGB identity match; native controller not implemented. Use the OpenRGB SDK bridge for control.' if enabled else 'Detected by native macOS IOKit. No matching lighting controller attached.'
            rows.append(dict(id='usb:'+physical,fingerprint='',name=name or (names[0] if names else 'USB device'),vendor=record.get('vendor',''),category=category,backend='inventory',led_count=0,direct=False,controllable=False,status='catalog-match' if enabled else 'inventory-only',detail=detail,static_modes=[],zones=[],modes=[],usb_id='%04x:%04x'%(vid,pid),catalog_matches=names[:12]))
        self.inventory_count=len(rows)
        return rows
    def activate(self,device):
        record=self.records[device['id']]
        if record['kind']=='corsair-makr75':record['makr'].activate()
        if record['kind']=='lamp':
            reports=record['reports'];levels=[]
            # Attribute requests select metadata only. Autonomous mode changes only after explicit Start.
            for index in range(record['count']):
                self.transport.send(record['handle'],struct.pack('<BH',reports[0x20]['id'],index),True)
                raw=self.transport.get(record['handle'],reports[0x22])
                if struct.unpack_from('<H',raw,1)[0]!=index or raw[27]!=1:raise HIDError('Lamp metadata is not programmable or has an unexpected ID')
                levels.append(tuple(raw[23:27]))
            record['levels']=levels
            self.transport.send(record['handle'],bytes([reports[0x70]['id'],0]),True)
        self.active.add(device['id']);self.next_frame[device['id']]=0
    def write_frame(self,device,colors,mode):
        key=device['id'];record=self.records[key]
        if key not in self.active or len(colors)!=record['count']:raise HIDError('Native device requires activation / exact color count')
        if record['kind']=='corsair-makr75':record['makr'].write(colors);return
        if record['kind']=='radius':
            record['radius'].write(colors);return
        if record['kind']=='asus-keyboard':
            if record.get('keyboard_topology'):
                packets=asus_keyboard.per_key_packets(record['keyboard_topology'],colors)
                if hasattr(self.transport,'send_batch'):self.transport.send_batch(record['handle'],packets)
                else:
                    for packet in packets:self.transport.send(record['handle'],packet)
                return
            brightness=100
            self.transport.send(record['handle'],asus_keyboard.effect_packet('static',colors[0],brightness,record.get('keyboard_report_id',2),record.get('keyboard_length',64)));return
        if record['kind']=='asus-spatha':
            for zone,rgb in enumerate(colors):self.transport.send(record['handle'],asus_mouse_packet(zone,rgb))
            return
        now=time.monotonic()
        if now<self.next_frame.get(key,0):
            time.sleep(self.next_frame[key]-now)
            now=time.monotonic()
        if record['kind']=='lamp':
            for start in range(0,len(colors),8):
                chunk=colors[start:start+8];packet=bytearray(51);packet[0]=record['reports'][0x50]['id'];packet[1]=len(chunk);packet[2]=int(start+len(chunk)==len(colors))
                for j,rgb in enumerate(chunk):
                    index=start+j;struct.pack_into('<H',packet,3+2*j,index);levels=record['levels'][index]
                    packet[19+4*j:23+4*j]=bytes([round(rgb[k]*levels[k]/255) for k in range(3)]+[levels[3]])
                self.transport.send(record['handle'],bytes(packet),True)
        elif record['kind']=='kraken-x2':
            for packet in kraken_packets(colors):self.transport.send(record['handle'],packet)
        self.next_frame[key]=now+record.get('interval',.05)
    def release(self):
        for key in list(self.active):
            record=self.records.get(key)
            if record and record['kind']=='corsair-makr75':
                try:record['makr'].release()
                except Exception:pass
            if record and record['kind']=='lamp':
                try:self.transport.send(record['handle'],bytes([record['reports'][0x70]['id'],1]),True)
                except Exception:pass
        self.active.clear();self.next_frame.clear()
    def close(self):self.release();self.transport.close()

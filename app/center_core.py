# SPDX-License-Identifier: GPL-2.0-or-later
"""HackinFX Core: device adapters, shared scene renderer and private local state."""
from concurrent.futures import ThreadPoolExecutor
import colorsys
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid
import center_sdk
import usb_devices
import ram_control


def atomic_json(path,value,mode=0o600):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    try:
        fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
        with os.fdopen(fd,'w') as out:json.dump(value,out,allow_nan=False)
        os.replace(str(tmp),str(path))
    finally:
        try:tmp.unlink()
        except FileNotFoundError:pass


def number(value,low,high):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Numeric value outside allowed range')
    return float(value)


def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{6}',value):raise ValueError('Use six-digit RGB colors')
    return tuple(bytes.fromhex(value))


def scene_config(value):
    if not isinstance(value,dict):raise ValueError('Scene must be an object')
    mode=value.get('mode','static')
    if mode not in ('static','gradient','spectrum','breathing','wave','aurora','comet','twinkle','color shift'):raise ValueError('Unknown scene')
    synchronized=value.get('synchronized',False)
    if type(synchronized) is not bool:raise ValueError('Synchronized must be boolean')
    palette=value.get('palette',['c6ed91','42d6ce','9f8bff'])
    if not isinstance(palette,list) or not 1<=len(palette)<=8:raise ValueError('One to eight colors required')
    for item in palette:color(item)
    axis=value.get('axis','x')
    if axis not in ('x','y'):raise ValueError('Invalid scene axis')
    return dict(synchronized=synchronized,mode=mode,palette=[v.lower() for v in palette],brightness=number(value.get('brightness',70),0,100),speed=number(value.get('speed',35),1,100),axis=axis)


def frame(scene,count,position,elapsed):
    palette=[color(v) for v in scene['palette']];out=[]
    speed=scene['speed']/100;brightness=scene['brightness']/100
    for index in range(count):
        local=index/max(1,count-1)
        x=position.get('x',0.5)+(local-0.5)*position.get('width',0.3)
        y=position.get('y',0.5)
        coord=x if scene['axis']=='x' else y
        phase=(elapsed*speed*0.25+coord)%1
        mode=scene['mode']
        if mode=='spectrum':rgb=tuple(round(c*255) for c in colorsys.hsv_to_rgb((elapsed*speed*0.2)%1,0.8,1))
        elif mode=='wave':
            offset=phase*len(palette);a=int(offset)%len(palette);b=(a+1)%len(palette);f=offset-int(offset)
            rgb=tuple(round(palette[a][i]*(1-f)+palette[b][i]*f) for i in range(3))
        elif mode=='gradient':
            offset=max(0,min(1,coord))*(len(palette)-1);a=int(offset);b=min(a+1,len(palette)-1);f=offset-a
            rgb=tuple(round(palette[a][i]*(1-f)+palette[b][i]*f) for i in range(3))
        elif mode=='aurora':
            hue=(coord*.28+elapsed*speed*.06)%1
            rgb=tuple(round(c*255) for c in colorsys.hsv_to_rgb(.38+hue*.36,.78,.6+.4*math.sin(coord*5+elapsed*speed)**2))
        elif mode=='comet':
            distance=((elapsed*speed*.25)%1-coord)%1
            rgb=tuple(round(c*math.exp(-distance*12)) for c in palette[0])
        elif mode=='twinkle':
            sparkle=max(0,math.sin(index*12.9898+coord*78.233+elapsed*speed*3))**12
            rgb=tuple(round(c*(.08+.92*sparkle)) for c in palette[index%len(palette)])
        elif mode=='color shift':
            offset=(elapsed*speed*.12)%len(palette);a=int(offset);b=(a+1)%len(palette);f=offset-a
            rgb=tuple(round(palette[a][i]*(1-f)+palette[b][i]*f) for i in range(3))
        else:rgb=palette[0]
        level=brightness*(0.08+0.92*(0.5-0.5*math.cos(elapsed*speed*math.pi))) if mode=='breathing' else brightness
        out.append(tuple(round(c*level) for c in rgb))
    return out


def project_usb(tree):
    devices=[]
    def visit(v):
        if isinstance(v,dict):
            if 'product_id' in v and 'vendor_id' in v:
                def ident(key):
                    found=re.search(r'0x([0-9a-fA-F]{1,4})',str(v[key]))
                    return found.group(1).lower().zfill(4) if found else None
                vid,pid=ident('vendor_id'),ident('product_id')
                name=str(v.get('_name','USB device'))[:160]
                if vid and pid and 'hub' not in name.lower():
                    category=next((kind for label,kind in [('keyboard','keyboard'),('mouse','mouse'),('kraken','cooler'),('hydro','cooler'),('commander','controller'),('lighting','controller')] if label in name.lower()),'usb')
                    devices.append(dict(name=name,vendor=str(v.get('manufacturer','USB'))[:100],category=category,usb_id=vid+':'+pid))
            for item in v.values():visit(item)
        elif isinstance(v,list):
            for item in v:visit(item)
    visit(tree);return devices[:128]


class NativeGPU:
    def __init__(self,profiles_dir):self.profiles_dir=Path(profiles_dir);self.identities={}
    def discover(self):
        import scanner,profiles
        report=scanner.collect();rows=[];self.identities={}
        fp=report.get('configuration_fingerprint')
        for index,adapter in enumerate(report.get('adapters',[])):
            executable=next((p for p in profiles.PROFILES if p.key==adapter.get('verified_profile')),None)
            saved={}
            if isinstance(fp,str) and re.fullmatch('[a-f0-9]{64}',fp):
                try:saved=json.loads((self.profiles_dir/('profile-'+fp+'.json')).read_text())
                except (OSError,ValueError):pass
            confirmed=bool(adapter.get('nvrm_bound') is True and report.get('lighting_configuration',{}).get('status')=='supported' and executable and saved.get('schema')==1 and saved.get('fingerprint')==fp and saved.get('successfulSteps')==3 and saved.get('userConfirmed') is True and set(executable.effects).issubset(set(saved.get('verifiedEffects',[]))))
            identity='native:'+hashlib.sha256(repr(adapter['pci']).encode()).hexdigest()[:24]
            key=identity+':'+str(index)
            row=dict(id=key,fingerprint=identity,name=saved.get('gpuName') or adapter.get('profile_name') or adapter.get('catalog_name') or adapter.get('gpu_name') or 'Display adapter',vendor=saved.get('boardVendor') or adapter.get('board_vendor') or adapter.get('vendor_name') or '',category='gpu',backend='native',led_count=executable.zones if executable else 0,zones=[],direct=False,status='ready' if confirmed else 'setup-required',detail='Confirmed native controller. Static scenes; Gradient on three-zone PNY profiles.' if confirmed else 'Complete the native GPU visual test before control-center writes.',static_modes=['static']+(['gradient'] if executable and executable.zones==3 else []),controllable=confirmed,owns_gpu=adapter.get('nvrm_bound',False))
            if confirmed and executable.controller=='PNYLovelaceGPUController' and executable.zones==3:
                row.update(direct=True,host_stream=True,detail='Confirmed PNY RGB zones follow the shared host timeline. Actual rate depends on NVRM transaction latency.')
            rows.append(row)
            if confirmed:self.identities[key]=(fp,executable)
        return rows
    def apply(self,device,colors,mode):
        # Re-inventory inside rgb.py and compare the fingerprint immediately before writes.
        fp,profile=self.identities[device['id']]
        saved=json.loads((self.profiles_dir/('profile-'+fp+'.json')).read_text())
        if saved.get('fingerprint')!=fp or saved.get('userConfirmed') is not True or not set(profile.effects).issubset(set(saved.get('verifiedEffects',[]))):raise ValueError('Native GPU confirmation changed; rescan and confirm again')
        if mode not in device['static_modes']:raise ValueError('Native GPU does not support this shared scene')
        path=self.profiles_dir/'CoreReports'/('rgb-'+uuid.uuid4().hex+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        hexes=[''.join('%02x'%v for v in c) for c in colors]
        args=['/usr/bin/python3','-B',str(Path(__file__).with_name('rgb.py')),'--apply','--port',str(profile.port),'--expected-profile',profile.key,'--led','all','--effect',mode,'--color',hexes[0],'--brightness','255','--output',str(path)]
        if mode=='gradient':args+=['--colors',','.join(hexes)]
        result=subprocess.run(args,capture_output=True,timeout=30)
        if result.returncode:
            failed=sorted(path.parent.glob('rgb-*.json'),key=lambda p:p.stat().st_mtime)
            for old in failed[:-12]:old.unlink(missing_ok=True)
            raise RuntimeError('Native GPU command failed; inspect its local CoreReports diagnostic')
        path.unlink(missing_ok=True) # Successful streamed frames must not grow a report archive.


class OpenRGBAdapter:
    name='openrgb'
    def __init__(self,client,engine=None):self.client=client;self.engine=engine
    def discover(self):
        if self.engine:self.client.port=self.engine.ensure_started()
        return self.client.discover()
    def activate(self,device):self.client.activate(device['index'])
    def write_frame(self,device,colors,mode):self.client.colors(device['index'],colors)
    def close(self):
        self.client.close()
        if self.engine:self.engine.close()


class NativeGPUAdapter:
    name='native'
    def __init__(self,driver):self.driver=driver
    def discover(self):return self.driver.discover()
    def activate(self,device):pass  # A native static request is a single bounded transaction group.
    def write_frame(self,device,colors,mode):self.driver.apply(device,colors,'gradient' if device.get('host_stream') else mode)
    def close(self):pass


class AdapterRegistry:
    """Explicit code-owned adapters; no downloaded or arbitrary plugins execute."""
    def __init__(self,adapters):
        self.adapters={}
        for adapter in adapters:
            if not re.fullmatch('[a-z][a-z0-9-]{0,30}',adapter.name) or adapter.name in self.adapters:raise ValueError('Invalid or duplicate adapter name')
            self.adapters[adapter.name]=adapter
    def activate(self,device):self.adapters[device['backend']].activate(device)
    def write_frame(self,device,colors,mode):self.adapters[device['backend']].write_frame(device,colors,mode)
    def close(self):
        for adapter in self.adapters.values():adapter.close()


class Center:
    def __init__(self,store,profiles_dir,sdk=None,native=None,adapters=None):
        self.store=Path(store);self.sdk=sdk or center_sdk.SDKClient();self.native=native or NativeGPU(profiles_dir)
        self.engine=None
        if sdk is None and adapters is None:
            from openrgb_runtime import ManagedEngine
            self.engine=ManagedEngine(Path.home()/'Library/Application Support/HackinFX/Core/OpenRGB')
        defaults=[OpenRGBAdapter(self.sdk,self.engine),NativeGPUAdapter(self.native)]
        if sdk is None and native is None:defaults.extend([usb_devices.NativeUSBAdapter(),ram_control.RAMAdapter()])
        self.registry=AdapterRegistry(adapters if adapters is not None else defaults)
        self.lock=threading.RLock();self.operation=threading.RLock();self.stop_event=threading.Event();self.worker=None
        self.devices=[];self.layout={};self.scene=scene_config(dict(palette=["ffffff"],brightness=100));self.running=False;self.frames=0;self.errors=[];self.bridge='disconnected';self.scenes=[];self.message='Ready to discover devices';self.generation='';self.saved_layout={};self.initialized=False;self.clock_started=time.monotonic();self.sync_stats=dict(clock="shared-monotonic",dropped=0,frames=0)
        try:
            if self.store.stat().st_size>524288:raise ValueError('Scene file is too large')
            saved=json.loads(self.store.read_text())
            for key,position in list(saved.get('layout',{}).items())[:192]:
                if isinstance(key,str) and len(key)<=80:
                    self.saved_layout[key]=dict(x=number(position['x'],0,1),y=number(position['y'],0,1),width=number(position.get('width',.22),.01,1))
            for row in saved.get('scenes',[])[:64]:
                if isinstance(row,dict) and isinstance(row.get('name'),str):self.scenes.append(dict(name=row['name'][:60],config=scene_config(row['config'])))
        except (OSError,ValueError,KeyError,TypeError):pass
    def status(self):
        with self.lock:return dict(schema=1,devices=[dict(d) for d in self.devices],layout=dict(self.layout),scene=dict(self.scene),running=self.running,frames=self.frames,errors=list(self.errors[-12:]),bridge=self.bridge,scenes=list(self.scenes),message=self.message,local_only=True,sync=dict(self.sync_stats))
    def refresh(self,inventory=True):
        with self.operation:
            self.stop();rows=[];errors=[];self.generation=uuid.uuid4().hex[:12]
            bridge='disconnected'
            for name,adapter in self.registry.adapters.items():
                try:
                    for index,record in enumerate(adapter.discover()):
                        d=dict(record);d['backend']='inventory' if record.get('backend')=='inventory' and not record.get('controllable') else name
                        d.setdefault('id',name+':'+self.generation+':'+str(index))
                        d.setdefault('controllable',d.get('direct',False))
                        d.setdefault('static_modes',['static','gradient'] if d.get('direct',False) else [])
                        rows.append(d)
                    if name=='openrgb':bridge='connected'
                except Exception as exc:errors.append(name+': '+str(exc))
            if any(d.get('owns_gpu') for d in rows if d['backend']=='native'):
                for d in rows:
                    if d['backend']=='openrgb' and d['category']=='gpu':
                        d.update(controllable=False,direct=False,status='native-owned',detail='Native NVIDIA owns GPU control; duplicate GPU bridge writers are disabled.')
            native_rows=[d for d in rows if d['backend']=='native-usb' and d.get('controllable')]
            for d in rows:
                if d['backend']=='openrgb' and any(d['name'].casefold() in {n.casefold() for n in row.get('ownership_names',[])} for row in native_rows):
                    d.update(controllable=False,direct=False,status='native-owned',detail='The native HID adapter owns this exact catalog-matched controller. Duplicate bridge writes are disabled.')
            if inventory:
                try:
                    import ram_probe
                    result=subprocess.run(['/usr/sbin/system_profiler','SPUSBDataType','SPMemoryDataType','-json'],capture_output=True,check=True,timeout=35)
                    tree=json.loads(result.stdout)
                    passive=([] if any(name=='native-usb' for name in self.registry.adapters) and any(d['backend'] in ('native-usb','inventory') for d in rows) else project_usb(tree))+[dict(name=d.get('part_number','Memory module')+' · '+d.get('size',''),vendor=d.get('manufacturer',''),category='dram') for d in ([] if 'native-ram' in self.registry.adapters else ram_probe.modules(tree))]
                    # Inventory entries never inherit write access from a similar name.
                    for i,d in enumerate(passive):
                        d.update(id='inventory:'+self.generation+':'+str(i),fingerprint='',backend='inventory',led_count=0,zones=[],modes=[],direct=False,controllable=False,static_modes=[],status='inventory-only',detail='Detected by macOS. No direct native controller implemented; a matching OpenRGB device may appear separately.')
                        rows.append(d)
                except Exception as exc:errors.append('USB / DRAM inventory unavailable: '+type(exc).__name__)
            with self.lock:
                self.devices=rows;self.errors=errors;self.bridge=bridge
                fingerprints=[d.get('fingerprint','') for d in rows]
                self.layout={d['id']:(dict(self.saved_layout[d['fingerprint']]) if d.get('fingerprint') in self.saved_layout and fingerprints.count(d['fingerprint'])==1 else dict(x=(i%4+0.5)/4,y=(i//4+0.5)/max(1,math.ceil(len(rows)/4)),width=0.22)) for i,d in enumerate(rows)}
                self.message=str(sum(bool(d['controllable']) for d in rows))+' controllable devices; '+str(len(rows))+' detected entries'
            return self.status()
    def stop(self):
        with self.operation:
            self.stop_event.set()
            worker=self.worker
            if worker and worker is not threading.current_thread():worker.join(timeout=35)
            if worker and worker.is_alive():raise RuntimeError('A controller is still responding; retry after it stops')
            with self.lock:self.running=False;self.worker=None
    def probe_ram(self):
        with self.operation:
            self.stop()
            adapter=self.registry.adapters.get('native-ram')
            if adapter is None:raise ValueError('Native RAM adapter is unavailable')
            if self.engine:
                self.sdk.close();self.engine.claim_native_ram()
            adapter.probe()
            return self.refresh()
    def initialize(self,inventory=True):
        # Exactly once per Core session; later discovery never resets a user's colors.
        with self.operation:
            if self.initialized:return self.status()
            self.refresh(inventory=inventory);self.initialized=True
            ids=[d['id'] for d in self.devices if d['controllable'] and (d['direct'] or 'static' in d['static_modes'])]
            if not ids:return self.status()
            discovery_errors=list(self.errors)
            self.start(dict(config=dict(mode='static',palette=['ffffff'],brightness=100),devices=ids),isolate_failures=True,initial_errors=discovery_errors)
            return self.status()
    def start(self,value,isolate_failures=False,initial_errors=None):
        with self.operation:
            config=scene_config(value.get('config',{}));ids=value.get('devices',[])
            if not isinstance(ids,list) or not 1<=len(ids)<=64 or len(set(ids))!=len(ids):raise ValueError('Select one to 64 different devices')
            with self.lock:
                targets=[]
                for key in ids:
                    target=next((d for d in self.devices if d['id']==key),None)
                    if not target or not target['controllable']:raise ValueError('A selected device is not controllable; refresh or complete its setup')
                    if config['synchronized'] and not target['direct']:raise ValueError('Canvas sync requires host-streamed Direct devices; onboard effects have independent clocks')
                    if not target['direct'] and config['mode'] not in target['static_modes']:raise ValueError('A selected device cannot play this effect. Select only compatible targets.')
                    targets.append(dict(target,scene_brightness=config['brightness']))
                if sum(d['led_count'] for d in targets)>16384:raise ValueError('Scene exceeds the 16,384 LED limit')
            self.stop();self.stop_event=threading.Event()
            # Direct/Custom activation follows a live edit or the startup-white policy.
            activation_errors=list(initial_errors or []);ready=[]
            for target in targets:
                try:self.registry.activate(target);ready.append(target)
                except Exception as exc:
                    if isolate_failures:
                        activation_errors.append(target['name']+': '+str(exc))
                        with self.lock:
                            for device in self.devices:
                                if device['id']==target['id']:device.update(status='command-failed',controllable=False,detail=str(exc))
                        continue
                    for adapter in self.registry.adapters.values():
                        if hasattr(adapter,'release'):
                            try:adapter.release()
                            except Exception:pass
                    self.message='Could not activate all targets. Some devices may already be in Direct mode.'
                    raise
            with self.lock:self.scene=config;self.running=True;self.frames=0;self.errors=activation_errors;self.message='Scene active; commands sent, not live LED readback'
            self.worker=threading.Thread(target=self.render,args=(ready,config,self.stop_event),daemon=True);self.worker.start()
            return self.status()
    def render(self,targets,config,event):
        active={d['id']:d for d in targets};pending={};animated=config['mode'] not in ('static','gradient')
        pool=ThreadPoolExecutor(max_workers=max(1,len(targets)),thread_name_prefix='lighting-output')
        def collect(key,future):
            try:future.result()
            except Exception as exc:
                active.pop(key,None)
                with self.lock:
                    self.errors=(self.errors+[targets_by_id[key]['name']+': '+str(exc)])[-12:]
                    for device in self.devices:
                        if device['id']==key:device.update(status='command-failed',controllable=False,detail=str(exc))
            if config['mode'] in targets_by_id[key].get('onboard_modes',[]):active.pop(key,None)
        targets_by_id={d['id']:d for d in targets}
        try:
            while active and not event.is_set():
                tick=time.monotonic();elapsed=tick-self.clock_started
                for key,future in list(pending.items()):
                    if future.done():collect(key,future);del pending[key]
                # Render ALL outputs from the same timestamp before any I/O.
                frames=[]
                for key,target in list(active.items()):
                    if key in pending:
                        with self.lock:self.sync_stats['dropped']+=1
                        continue # Bounded latest-frame policy; never queue stale frames.
                    mode='static' if config['mode'] in target.get('onboard_modes',[]) else config['mode']
                    pixels=frame(dict(config,mode=mode),target['led_count'],self.layout[key],elapsed)
                    frames.append((key,target,pixels))
                for key,target,pixels in frames:
                    if event.is_set():break
                    pending[key]=pool.submit(self.registry.write_frame,target,pixels,config['mode'])
                with self.lock:self.frames+=1;self.sync_stats['frames']+=1
                if not animated:break
                event.wait(max(0,.05-(time.monotonic()-tick)))
            for key,future in list(pending.items()):collect(key,future)
        finally:
            pool.shutdown(wait=True)
            with self.lock:
                self.running=False
                self.message='Some outputs failed; inspect device details.' if self.errors else 'Shared-clock streaming paused; last colors kept.' if animated else 'Static colors sent.'
    def set_layout(self,values):
        if not isinstance(values,dict) or len(values)>192:raise ValueError('Invalid layout')
        with self.operation:
            self.stop()
            with self.lock:
                known={d['id'] for d in self.devices}
                if set(values)-known:raise ValueError('Layout refers to missing devices')
                updates={key:dict(x=number(v['x'],0,1),y=number(v['y'],0,1),width=number(v.get('width',0.22),0.01,1)) for key,v in values.items()}
                layout=dict(self.layout);layout.update(updates)
                fingerprints=[d.get('fingerprint','') for d in self.devices]
                saved=dict(self.saved_layout)
                for d in self.devices:
                    fp=d.get('fingerprint','')
                    if fp and fingerprints.count(fp)==1:saved[fp]=layout[d['id']]
                atomic_json(self.store,dict(schema=1,scenes=self.scenes,layout=saved))
                self.layout=layout;self.saved_layout=saved
        return self.status()
    def save_scene(self,value):
        name=value.get('name','').strip()
        if not 1<=len(name)<=60 or any(ord(c)<32 for c in name):raise ValueError('Scene name must have 1–60 printable characters')
        config=scene_config(value.get('config',{}))
        with self.lock:
            scenes=[s for s in self.scenes if s['name']!=name]+[dict(name=name,config=config)]
            if len(scenes)>64:raise ValueError('Maximum 64 saved scenes')
            atomic_json(self.store,dict(schema=1,scenes=scenes,layout=self.saved_layout));self.scenes=scenes
        return self.status()
    def close(self):self.stop();self.registry.close()

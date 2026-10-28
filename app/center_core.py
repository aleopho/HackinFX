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
import nanoleaf_control
import effects


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


def calibration_config(value):
    if not isinstance(value,dict):raise ValueError('Calibration must be an object')
    return dict(red=number(value.get('red',1),0,1),green=number(value.get('green',1),0,1),blue=number(value.get('blue',1),0,1),gamma=number(value.get('gamma',1),.5,3))

def layout_config(value):
    if not isinstance(value,dict):raise ValueError('Placement must be an object')
    result=dict(x=number(value['x'],0,1),y=number(value['y'],0,1),width=number(value.get('width',.22),.01,1),height=number(value.get('height',value.get('width',.22)),.01,1),rotation=number(value.get('rotation',0),-180,180))
    for key in ('mirror_x','mirror_y'):
        if type(value.get(key,False)) is not bool:raise ValueError('Mirror flags must be boolean')
        result[key]=value.get(key,False)
    return result


def scene_config(value):
    if not isinstance(value,dict):raise ValueError('Scene must be an object')
    mode=value.get('mode','static')
    if mode not in effects.MODES:raise ValueError('Unknown scene')
    synchronized=value.get('synchronized',True)
    if type(synchronized) is not bool:raise ValueError('Synchronized must be boolean')
    palette=value.get('palette',['c6ed91','42d6ce','9f8bff'])
    if not isinstance(palette,list) or not 1<=len(palette)<=8:raise ValueError('One to eight colors required')
    for item in palette:color(item)
    mapping=value.get('mapping','mirror')
    if mapping not in ('mirror','canvas'):raise ValueError('Invalid effect mapping')
    axis=value.get('axis','x')
    if axis not in ('x','y'):raise ValueError('Invalid scene axis')
    policy=value.get('sync_policy','adaptive')
    if policy not in ('adaptive','lockstep'):raise ValueError('Invalid synchronization policy')
    fps=number(value.get('fps',60),1,120)
    reverse=value.get('reverse',False)
    if type(reverse)is not bool:raise ValueError('Reverse must be boolean')
    result=dict(scale=number(value.get('scale',1),.25,4),density=number(value.get('density',55),0,100),reverse=reverse,fps=fps,sync_policy=policy,mapping=mapping,synchronized=synchronized,mode=mode,palette=[v.lower() for v in palette],brightness=number(value.get('brightness',70),0,100),speed=number(value.get('speed',35),1,100),axis=axis)
    layers=value.get('layers',[])
    if not isinstance(layers,list) or len(layers)>4:raise ValueError('Up to four effect layers supported')
    result['layers']=[]
    for layer in layers:
        if not isinstance(layer,dict) or layer.get('layers'):raise ValueError('Nested layers are not supported')
        blend=layer.get('blend','screen')
        if blend not in ('screen','add','multiply','normal'):raise ValueError('Invalid layer blend')
        result['layers'].append(dict(scene_config(dict(layer,layers=[])),blend=blend,opacity=number(layer.get('opacity',50),0,100)))
    return result


def frame(scene,count,position,elapsed):
    return effects.frame(scene,count,position,elapsed)


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
    def __init__(self,profiles_dir):self.profiles_dir=Path(profiles_dir);self.identities={};self.streams={}
    def discover(self):
        import scanner,profiles
        self.close()
        report=scanner.collect();rows=[];self.identities={}
        fp=report.get('configuration_fingerprint')
        primary=next((i for i,a in enumerate(report.get('adapters',[])) if a.get('nvrm_bound') is True),0)
        for index,adapter in enumerate(report.get('adapters',[])):
            executable=next((p for p in profiles.PROFILES if p.key==adapter.get('verified_profile')),None)
            saved={}
            if isinstance(fp,str) and re.fullmatch('[a-f0-9]{64}',fp):
                try:saved=json.loads((self.profiles_dir/('profile-'+fp+'.json')).read_text())
                except (OSError,ValueError):pass
            confirmed=bool(adapter.get('nvrm_bound') is True and report.get('lighting_configuration',{}).get('status')=='supported' and executable and saved.get('schema')==1 and saved.get('fingerprint')==fp and saved.get('successfulSteps')==3 and saved.get('userConfirmed') is True and set(executable.effects).issubset(set(saved.get('verifiedEffects',[]))))
            identity='native:'+hashlib.sha256(repr(adapter['pci']).encode()).hexdigest()[:24]
            key=identity+':'+str(index)
            row=dict(id=key,fingerprint=identity,name=saved.get('gpuName') or adapter.get('profile_name') or adapter.get('catalog_name') or adapter.get('gpu_name') or 'Display adapter',vendor=saved.get('boardVendor') or adapter.get('board_vendor') or adapter.get('vendor_name') or '',category='gpu',backend='native',setup_fingerprint=fp,setup_candidate=bool(index==primary and executable and adapter.get('nvrm_bound') is True and report.get('lighting_configuration',{}).get('status')=='supported'),led_count=executable.zones if executable else 0,zones=[],direct=False,status='ready' if confirmed else 'setup-required',detail='Confirmed native controller. Static scenes; Gradient on three-zone PNY profiles.' if confirmed else 'Complete the native GPU visual test before control-center writes.',static_modes=['static']+(['gradient'] if executable and executable.zones==3 else []),controllable=confirmed,owns_gpu=adapter.get('nvrm_bound',False))
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
        if device.get('host_stream'):
            from gpu_stream import Client
            if device['id'] not in self.streams:self.streams[device['id']]=Client(self.profiles_dir,fp,profile.key)
            self.streams[device['id']].write(colors)
            return
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

    def close(self):
        for stream in self.streams.values():stream.close()
        self.streams={}


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
    def release(self):
        if hasattr(self.driver,'close'):self.driver.close()
    def close(self):self.release()


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
        self.nanoleaf_candidates=[];self.store=Path(store);self.sdk=sdk or center_sdk.SDKClient();self.native=native or NativeGPU(profiles_dir)
        self.engine=None
        if sdk is None and adapters is None:
            from openrgb_runtime import ManagedEngine
            self.engine=ManagedEngine(Path.home()/'Library/Application Support/HackinFX/Core/OpenRGB')
        defaults=[OpenRGBAdapter(self.sdk,self.engine),NativeGPUAdapter(self.native)]
        if sdk is None and native is None:defaults.extend([usb_devices.NativeUSBAdapter(),ram_control.RAMAdapter(),nanoleaf_control.NanoleafAdapter()])
        self.registry=AdapterRegistry(adapters if adapters is not None else defaults)
        self.lock=threading.RLock();self.operation=threading.RLock();self.stop_event=threading.Event();self.worker=None
        self.closing=False;self.calibration={};self.saved_calibration={};self.output_locks={};self.device_brightness={};self.saved_brightness={};self.devices=[];self.layout={};self.scene=scene_config(dict(mode='twinkle',palette=['9bed4b'],brightness=100,speed=65));self.running=False;self.frames=0;self.errors=[];self.bridge='disconnected';self.scenes=[];self.message='Ready to discover devices';self.generation='';self.saved_layout={};self.initialized=False;self.scene_revision=0;self.selected_devices=[];self.active_devices=set();self.output_latencies={};self.output_stats={};self.leased_frames={};self.clock_started=time.monotonic();self.sync_stats=dict(clock="shared-monotonic",dropped=0,frames=0)
        try:
            if self.store.stat().st_size>524288:raise ValueError('Scene file is too large')
            saved=json.loads(self.store.read_text())
            for key,position in list(saved.get('layout',{}).items())[:192]:
                if isinstance(key,str) and len(key)<=80:
                    self.saved_layout[key]=layout_config(position)
            for fp,level in list(saved.get('device_brightness',{}).items())[:192]:
                if isinstance(fp,str) and len(fp)<=80:self.saved_brightness[fp]=number(level,0,100)
            for fp,value in list(saved.get('calibration',{}).items())[:192]:
                if isinstance(fp,str) and len(fp)<=80:self.saved_calibration[fp]=calibration_config(value)
            for row in saved.get('scenes',[])[:64]:
                if isinstance(row,dict) and isinstance(row.get('name'),str):self.scenes.append(dict(name=row['name'][:60],config=scene_config(row['config'])))
        except (OSError,ValueError,KeyError,TypeError):pass
    def performance(self):
        now=time.monotonic()
        return {key:dict(frames=v['frames'],fps=round(v['fps'],1),command_ms=round(v['latency']*1000,2),age_ms=round(max(0,now-v['last'])*1000),missed=v['missed'],interval_ms=round(v.get('interval',0)*1000,2),jitter_ms=round(v.get('jitter',0)*1000,2),max_interval_ms=round(v.get('max_interval',0)*1000,2)) for key,v in self.output_stats.items()}
    def status(self):
        with self.lock:return dict(schema=1,calibration=dict(self.calibration),device_brightness=dict(self.device_brightness),host_media_devices=sorted(getattr(self.registry.adapters.get('native-usb'),'active',set())),scene_revision=self.scene_revision,selected_devices=list(self.selected_devices),active_devices=sorted(k for k in self.active_devices if self.device_brightness.get(k,100)>0) if self.scene['brightness']>0 else [],nanoleaf_candidates=list(self.nanoleaf_candidates),scene_elapsed=max(0,time.monotonic()-self.clock_started),devices=[dict(d) for d in self.devices],layout=dict(self.layout),scene=dict(self.scene),running=self.running,frames=self.frames,errors=list(self.errors[-12:]),bridge=self.bridge,scenes=list(self.scenes),message=self.message,local_only=True,sync=dict(self.sync_stats,outputs=self.performance()))
    def refresh(self,inventory=True):
        with self.operation:
            self.stop();self.leased_frames={};self.active_devices=set();self.selected_devices=[];rows=[];errors=[];self.generation=uuid.uuid4().hex[:12]
            bridge='disconnected'
            for name,adapter in self.registry.adapters.items():
                try:
                    for index,record in enumerate(adapter.discover()):
                        d=dict(record);d['discovery_adapter']=name;d['backend']='inventory' if record.get('backend')=='inventory' and not record.get('controllable') else name
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
                self.devices=rows;self.restore_device_brightness(rows);self.errors=errors;self.bridge=bridge
                fingerprints=[d.get('fingerprint','') for d in rows]
                self.layout={d['id']:(dict(self.saved_layout[d['fingerprint']]) if d.get('fingerprint') in self.saved_layout and fingerprints.count(d['fingerprint'])==1 else dict(x=(i%4+0.5)/4,y=(i//4+0.5)/max(1,math.ceil(len(rows)/4)),width=0.22)) for i,d in enumerate(rows)}
                self.message=str(sum(bool(d['controllable']) for d in rows))+' controllable devices; '+str(len(rows))+' detected entries'
            return self.status()
    def restore_device_brightness(self,rows):
        counts={d.get('fingerprint'):sum(r.get('fingerprint')==d.get('fingerprint') for r in rows) for d in rows}
        self.calibration={d['id']:self.calibration.get(d['id'],self.saved_calibration.get(d.get('fingerprint'),calibration_config({})) if counts.get(d.get('fingerprint'))==1 else calibration_config({})) for d in rows}
        self.device_brightness={d['id']:self.device_brightness.get(d['id'],self.saved_brightness.get(d.get('fingerprint'),100) if counts.get(d.get('fingerprint'))==1 else 100) for d in rows}
    def set_device_brightness(self,values):
        if not isinstance(values,dict) or not 1<=len(values)<=64:raise ValueError('Device brightness requires one to 64 device levels')
        with self.operation:
            updates={key:number(level,0,100) for key,level in values.items()}
            with self.lock:
                known={d['id']:d for d in self.devices}
                if any(key not in known or not known[key]['controllable'] for key in updates):raise ValueError('Brightness target is not controllable')
                levels=dict(self.device_brightness);levels.update(updates);saved=dict(self.saved_brightness)
                for key,level in updates.items():
                    fp=known[key].get('fingerprint')
                    if fp and sum(d.get('fingerprint')==fp for d in self.devices)==1:saved[fp]=level
                atomic_json(self.store,dict(schema=1,scenes=self.scenes,layout=self.saved_layout,device_brightness=saved,calibration=self.saved_calibration))
                self.device_brightness=levels;self.saved_brightness=saved;config=dict(self.scene);selected=set(self.selected_devices)
                targets=[dict(known[k]) for k in updates if k in selected]
                steady=config['mode'] in ('static','gradient') and not config.get('layers')
            # Streaming picks up levels on the next write. Steady scenes need one new frame.
            if steady:
                for target in targets:
                    pixels=frame(config,target['led_count'],dict(self.layout[target['id']],led_positions=target.get('led_positions',[])),max(0,time.monotonic()-self.clock_started))
                    self.write_output(target,pixels,config['mode'])
                    if target['backend']=='native':self.registry.adapters['native'].release()
            elif not self.running:
                for target in targets:
                    if target['id'] in self.leased_frames:self.write_output(target,self.leased_frames[target['id']],'static')
            return self.status()
    def hotplug_refresh(self):
        """Refresh USB adapters only; no GPU setup or RAM rediscovery/probe."""
        with self.operation:
            with self.lock:
                old=[dict(d) for d in self.devices];selected=set(self.selected_devices);config=dict(self.scene);running=self.running;positions=dict(self.layout)
            selected_fp={d.get('fingerprint') for d in old if d['id'] in selected and d.get('fingerprint')}
            known_fp={d.get('fingerprint') for d in old if d.get('fingerprint')}
            names=[n for n in ('native-usb','openrgb') if n in self.registry.adapters]
            if not names:return self.status()
            self.stop();rows=[d for d in old if d.get('discovery_adapter',d['backend']) not in names];errors=[]
            for name in names:
                try:
                    for index,record in enumerate(self.registry.adapters[name].discover()):
                        d=dict(record);d['discovery_adapter']=name;d['backend']='inventory' if record.get('backend')=='inventory' and not record.get('controllable') else name
                        d.setdefault('id',name+':hotplug:'+str(index));d.setdefault('controllable',d.get('direct',False));d.setdefault('static_modes',['static','gradient'] if d.get('direct') else []);rows.append(d)
                except Exception as exc:errors.append(name+': '+str(exc))
            native=[d for d in rows if d['backend']=='native-usb' and d.get('controllable')]
            for d in rows:
                if d['backend']=='openrgb' and ((d.get('category')=='gpu' and any(r.get('owns_gpu') for r in rows if r['backend']=='native')) or any(d['name'].casefold() in {n.casefold() for n in r.get('ownership_names',[])} for r in native)):
                    d.update(controllable=False,direct=False,status='native-owned',detail='Native adapter owns this device; duplicate bridge writes disabled.')
            targets=[]
            for d in rows:
                fp=d.get('fingerprint');chosen=d['id'] in selected or fp and (fp in selected_fp or fp not in known_fp)
                compatible=d.get('direct') or config['mode'] in d.get('static_modes',[])
                if chosen and compatible and d.get('controllable') and not d.get('startup_excluded'):targets.append(d['id'])
            with self.lock:
                self.devices=rows;self.restore_device_brightness(rows);self.active_devices=set();self.selected_devices=targets;self.scene_revision+=1
                self.layout={d['id']:positions.get(d['id'],dict(x=(i%4+.5)/4,y=(i//4+.5)/max(1,math.ceil(len(rows)/4)),width=.22)) for i,d in enumerate(rows)}
                self.errors=(self.errors+errors)[-12:];self.message='USB devices updated automatically'
            targets=list(dict.fromkeys(targets))[:64]
            if running and targets:return self.start(dict(config=config,devices=targets),isolate_failures=True,initial_errors=errors)
            return self.status()
    def stop(self):
        with self.operation:
            self.stop_event.set()
            worker=self.worker
            if worker and worker is not threading.current_thread():worker.join(timeout=35)
            if worker and worker.is_alive():raise RuntimeError('A controller is still responding; retry after it stops')
            with self.lock:self.running=False;self.worker=None
            native=self.registry.adapters.get('native')
            if native and hasattr(native,'release'):native.release()
    def probe_ram(self):
        with self.operation:
            self.stop()
            adapter=self.registry.adapters.get('native-ram')
            if adapter is None:raise ValueError('Native RAM adapter is unavailable')
            if self.engine:
                self.sdk.close();self.engine.claim_native_ram()
            try:adapter.probe()
            except Exception:
                self.refresh();raise
            return self.refresh()
    def scan_nanoleaf(self):
        with self.operation:
            self.nanoleaf_candidates=nanoleaf_control.discover_shapes()
            return self.status()
    def pair_nanoleaf(self,value):
        with self.operation:
            adapter=self.registry.adapters.get('native-nanoleaf')
            if adapter is None:raise ValueError('Native Nanoleaf adapter is unavailable')
            ip=nanoleaf_control.local_ip(value.get('address'))
            candidate=next((d for d in self.nanoleaf_candidates if d['address']==ip),None)
            self.stop();adapter.pair(ip,candidate['id'] if candidate else None)
            return self.refresh()
    def initialize(self,inventory=True):
        # Exactly once per Core session; later discovery never resets a user's colors.
        with self.operation:
            if self.initialized:return self.status()
            self.refresh(inventory=inventory);self.initialized=True
            # Ready RAM targets have passed a saved-profile match and fresh RGB identity validation.
            direct=[d['id'] for d in self.devices if d['controllable'] and d['direct'] and not d.get('startup_excluded')]
            fallback=[d['id'] for d in self.devices if d['controllable'] and not d['direct'] and 'static' in d['static_modes'] and not d.get('startup_excluded')]
            errors=list(self.errors)
            if fallback:
                self.start(dict(config=dict(mode='static',palette=['9bed4b'],brightness=100),devices=fallback),isolate_failures=True,initial_errors=errors)
                if self.worker:self.worker.join(timeout=30)
                errors=list(self.errors)
            if direct:self.start(dict(config=dict(mode='twinkle',palette=['9bed4b'],brightness=100,speed=65,fps=60,sync_policy='adaptive'),devices=direct),isolate_failures=True,initial_errors=errors)
            return self.status()
    def start(self,value,isolate_failures=False,initial_errors=None):
        with self.operation:
            if self.closing:raise RuntimeError('Core is shutting down')
            config=scene_config(value.get('config',{}));ids=value.get('devices',[])
            if not isinstance(ids,list) or not 1<=len(ids)<=64 or len(set(ids))!=len(ids):raise ValueError('Select one to 64 different devices')
            with self.lock:
                targets=[]
                for key in ids:
                    target=next((d for d in self.devices if d['id']==key),None)
                    if not target or not target['controllable']:raise ValueError('A selected device is not controllable; refresh or complete its setup')
                    if config.get('layers') and not target['direct']:raise ValueError('Effect layers require host-streamed Direct devices')
                    if config['synchronized'] and config['mode'] not in ('static','gradient') and not target['direct']:raise ValueError('Canvas sync requires host-streamed Direct devices; onboard effects have independent clocks')
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
            if self.closing:raise RuntimeError('Core is shutting down')
            with self.lock:self.scene_revision+=1;self.selected_devices=[d['id'] for d in ready];self.active_devices=set();self.scene=config;self.running=True;self.frames=0;self.output_stats={};self.errors=activation_errors;self.message='Scene active; commands sent, not live LED readback'
            self.worker=threading.Thread(target=self.render,args=(ready,config,self.stop_event),daemon=True);self.worker.start()
            return self.status()
    def render(self,targets,config,event):
        active={d['id']:d for d in targets};pending={};last_sent={};animated=config['mode'] not in ('static','gradient') or bool(config.get('layers'))
        pool=ThreadPoolExecutor(max_workers=max(1,len(targets)),thread_name_prefix='lighting-output')
        def collect(key,future):
            try:future.result()
            except Exception as exc:
                active.pop(key,None)
                with self.lock:
                    self.active_devices.discard(key)
                    self.errors=(self.errors+[targets_by_id[key]['name']+': '+str(exc)])[-12:]
                    for device in self.devices:
                        if device['id']==key:device.update(status='command-failed',controllable=False,detail=str(exc))
            if not animated and targets_by_id[key]['backend']=='native':
                adapter=self.registry.adapters.get('native')
                if adapter and hasattr(adapter,'release'):adapter.release()
            if not config.get('layers') and config['mode'] in targets_by_id[key].get('onboard_modes',[]):active.pop(key,None)
        targets_by_id={d['id']:d for d in targets}
        try:
            while active and not event.is_set():
                tick=time.monotonic();grouped=animated and config['synchronized'] and config['sync_policy']=='lockstep'
                latency=max([self.output_latencies.get(key,.05)+active[key].get('presentation_delay',0) for key in active]+[.05]) if grouped else 0
                presentation=tick+latency;elapsed=presentation-self.clock_started
                for key,future in list(pending.items()):
                    if future.done():collect(key,future);del pending[key]
                # Render ALL outputs from the same timestamp before any I/O.
                frames=[]
                for key,target in list(active.items()):
                    if not animated and key in last_sent and (not target.get('refresh_interval') or tick-last_sent[key]<target['refresh_interval']):continue
                    if key in pending:
                        with self.lock:
                            self.sync_stats['dropped']+=1
                            if key in self.output_stats:self.output_stats[key]['missed']+=1
                        continue # Bounded latest-frame policy; never queue stale frames.
                    mode='static' if not config.get('layers') and config['mode'] in target.get('onboard_modes',[]) else config['mode']
                    sample_time=(tick+min(.25,self.output_latencies.get(key,0)+target.get('presentation_delay',0))-self.clock_started) if animated and config['synchronized'] and not grouped else elapsed
                    pixels=frame(dict(config,mode=mode),target['led_count'],dict(self.layout[key],device_id=key,led_positions=target.get('led_positions',[])),sample_time)
                    frames.append((key,target,pixels))
                for key,target,pixels in frames:
                    if event.is_set():break
                    pending[key]=pool.submit(self.timed_output,target,pixels,config['mode'],presentation if grouped else 0,event);last_sent[key]=tick
                if grouped:
                    for key,future in list(pending.items()):collect(key,future);del pending[key]
                with self.lock:self.frames+=1;self.sync_stats['frames']+=1
                if not animated and not any(d.get('refresh_interval') for d in active.values()):break
                event.wait(max(0,1/config['fps']-(time.monotonic()-tick)))
            for key,future in list(pending.items()):collect(key,future)
        finally:
            pool.shutdown(wait=True)
            native=self.registry.adapters.get('native')
            if native and hasattr(native,'release'):native.release()
            with self.lock:
                self.running=False
                self.message='Some outputs failed; inspect device details.' if self.errors else 'Shared-clock streaming paused; last colors kept.' if animated else 'Static colors sent.'
    def timed_output(self,target,pixels,mode,presentation,event):
        expected=self.output_latencies.get(target['id'],.05)+target.get('presentation_delay',0)
        delay=max(0,presentation-time.monotonic()-expected) if presentation else 0
        if event.wait(delay):return
        self.write_output(target,pixels,mode)
    def write_output(self,target,pixels,mode):
        with self.lock:output_lock=self.output_locks.setdefault(target['id'],threading.RLock())
        with output_lock:self._write_output(target,pixels,mode)
    def _write_output(self,target,pixels,mode):
        started=time.monotonic()
        level=self.device_brightness.get(target['id'],100)/100
        correction=self.calibration.get(target['id'],calibration_config({}))
        gains=(correction['red'],correction['green'],correction['blue']);gamma=correction['gamma']
        scaled=[tuple(max(0,min(255,round(255*(c/255)**gamma*gains[i]*level))) for i,c in enumerate(rgb)) for rgb in pixels]
        self.registry.write_frame(target,scaled,mode)
        measured=time.monotonic()-started
        key=target['id'];now=time.monotonic()
        with self.lock:
            self.active_devices.add(key)
            previous=self.output_latencies.get(key,measured)
            self.output_latencies[key]=.2*measured+.8*previous
            old=self.output_stats.get(key)
            interval=now-old['last'] if old else 0
            observed=1/interval if interval>0 else 0
            mean_interval=(.2*interval+.8*old.get('interval',interval)) if old and interval>0 else interval
            jitter=(.2*abs(interval-old.get('interval',interval))+.8*old.get('jitter',0)) if old and old.get('interval',0)>0 else 0
            self.output_stats[key]=dict(interval=mean_interval,jitter=jitter,max_interval=max(interval,old.get('max_interval',0) if old else 0),frames=(old['frames']+1 if old else 1),fps=(.2*observed+.8*old['fps'] if old and old['fps'] else observed),latency=self.output_latencies[key],last=now,missed=old['missed'] if old else 0)
        with self.lock:self.leased_frames[target['id']]=list(pixels)
    def pause(self):
        with self.operation:
            self.stop()
            targets=[dict(d) for d in self.devices if d.get('refresh_interval') and d['controllable'] and d['id'] in self.leased_frames]
            if not targets:return self.status()
            self.stop_event=threading.Event();event=self.stop_event
            def maintain():
                while not event.wait(.5):
                    for target in targets:
                        if event.is_set():return
                        try:self.write_output(target,self.leased_frames[target['id']],'static')
                        except Exception as exc:
                            with self.lock:self.errors=(self.errors+[target['name']+': '+str(exc)])[-12:]
                            return
            self.worker=threading.Thread(target=maintain,daemon=True);self.worker.start()
            self.message='Effects paused; preview-based devices retain their last colors.'
            return self.status()
    def set_calibration(self,values):
        if not isinstance(values,dict) or not 1<=len(values)<=64:raise ValueError('Invalid calibration batch')
        with self.operation:
            with self.lock:
                known={d['id']:d for d in self.devices if d['controllable']}
                if set(values)-set(known):raise ValueError('Calibration refers to unavailable devices')
                updates={key:calibration_config(value) for key,value in values.items()}
                current=dict(self.calibration);current.update(updates);saved=dict(self.saved_calibration)
                fingerprints=[d.get('fingerprint') for d in self.devices]
                for key,value in updates.items():
                    fp=known[key].get('fingerprint')
                    if fp and fingerprints.count(fp)==1:saved[fp]=value
                atomic_json(self.store,dict(schema=1,scenes=self.scenes,layout=self.saved_layout,device_brightness=self.saved_brightness,calibration=saved))
                self.calibration=current;self.saved_calibration=saved
                targets=[dict(known[key]) for key in updates if key in self.leased_frames]
            if not self.running:
                for target in targets:
                    self.write_output(target,self.leased_frames[target['id']],'static')
                    if target['backend']=='native':self.registry.adapters['native'].release()
        return self.status()
    def set_layout(self,values):
        if not isinstance(values,dict) or len(values)>192:raise ValueError('Invalid layout')
        with self.operation:
            with self.lock:
                known={d['id'] for d in self.devices}
                if set(values)-known:raise ValueError('Layout refers to missing devices')
                updates={key:layout_config(dict(self.layout.get(key,{}),**v)) for key,v in values.items()}
                layout=dict(self.layout);layout.update(updates)
                fingerprints=[d.get('fingerprint','') for d in self.devices]
                saved=dict(self.saved_layout)
                for d in self.devices:
                    fp=d.get('fingerprint','')
                    if fp and fingerprints.count(fp)==1:saved[fp]=layout[d['id']]
                atomic_json(self.store,dict(schema=1,scenes=self.scenes,layout=saved,device_brightness=self.saved_brightness,calibration=self.saved_calibration))
                self.layout=layout;self.saved_layout=saved
                targets=[dict(d) for d in self.devices if d['id'] in updates and d['id'] in self.selected_devices and d.get('controllable')]
            if not self.running and self.scene['mode'] in ('static','gradient') and not self.scene.get('layers'):
                for target in targets:
                    pixels=frame(self.scene,target['led_count'],dict(self.layout[target['id']],led_positions=target.get('led_positions',[])),max(0,time.monotonic()-self.clock_started))
                    self.write_output(target,pixels,self.scene['mode'])
                    if target['backend']=='native':self.registry.adapters['native'].release()
        return self.status()
    def save_scene(self,value):
        name=value.get('name','').strip()
        if not 1<=len(name)<=60 or any(ord(c)<32 for c in name):raise ValueError('Scene name must have 1–60 printable characters')
        config=scene_config(value.get('config',{}))
        with self.lock:
            scenes=[s for s in self.scenes if s['name']!=name]+[dict(name=name,config=config)]
            if len(scenes)>64:raise ValueError('Maximum 64 saved scenes')
            atomic_json(self.store,dict(schema=1,scenes=scenes,layout=self.saved_layout,device_brightness=self.saved_brightness,calibration=self.saved_calibration));self.scenes=scenes
        return self.status()
    def begin_shutdown(self):
        self.closing=True
        self.stop_event.set()
        for adapter in self.registry.adapters.values():
            if hasattr(adapter,'begin_shutdown'):adapter.begin_shutdown()
    def close(self):self.begin_shutdown();self.stop();self.registry.close()

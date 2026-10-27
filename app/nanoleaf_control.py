# SPDX-License-Identifier: GPL-2.0-or-later
"""Local Shapes OpenAPI + extControl v2. Tokens never enter device/report records.
References: Nanoleaf OpenAPI; OpenRGB NanoleafController (Nikita Rushmanov, GPL-2.0-or-later).
"""
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

def local_ip(value):
    try:ip=ipaddress.IPv4Address(value)
    except (ValueError,TypeError):raise ValueError('Enter the Shapes controller local IPv4 address') from None
    if not (ip.is_private and not (ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved)):
        raise ValueError('Nanoleaf requires a local LAN IPv4 address')
    return str(ip)

def token_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',value):raise ValueError('Nanoleaf returned an invalid pairing token')
    return value

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def request(ip,token,method,suffix='',body=None):
    ip=local_ip(ip)
    path='/api/v1/new' if token is None else '/api/v1/'+token_value(token)+suffix
    data=json.dumps(body).encode() if body is not None else (b'' if method=='POST' else None)
    req=urllib.request.Request('http://'+ip+':16021'+path,data=data,method=method,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(req,timeout=3) as response:
            raw=response.read(262145)
            if len(raw)>262144:raise ValueError('Nanoleaf response exceeds the supported size')
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        if exc.code==403:raise ValueError('Hold the Shapes power button 5–7 seconds until flashing, then pair within 30 seconds') from None
        if exc.code==401:raise ValueError('Nanoleaf pairing expired; pair this controller again') from None
        raise ValueError('Nanoleaf HTTP request failed (%d)'%exc.code) from None
    except (urllib.error.URLError,TimeoutError,OSError,json.JSONDecodeError):
        raise ValueError('Nanoleaf is unavailable or returned an invalid response; check its LAN address') from None

def layout(info):
    if info.get('model')!='NL42':raise ValueError('This first native adapter requires Nanoleaf Shapes (NL42)')
    raw=info.get('panelLayout',{}).get('layout',{}).get('positionData',[])
    if not isinstance(raw,list) or not 1<=len(raw)<=500:raise ValueError('Nanoleaf layout is missing or too large')
    panels=[];seen=set()
    for p in raw:
        if not isinstance(p,dict):raise ValueError('Invalid Nanoleaf panel record')
        if p.get('shapeType')==12:continue # Shapes controller has no panel LEDs.
        if p.get('shapeType') not in (7,8,9):raise ValueError('Unsupported Shapes panel type; no guessed LEDs')
        pid=p.get('panelId');x=p.get('x');y=p.get('y')
        if type(pid)is not int or not 0<pid<=65535 or pid in seen:raise ValueError('Invalid or duplicate Nanoleaf panel ID')
        if any(type(v)not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in (x,y)):raise ValueError('Invalid Nanoleaf panel coordinates')
        seen.add(pid);panels.append(dict(panel_id=pid,x=x,y=y))
    if not panels or len(panels)>150:raise ValueError('Shapes layout requires 1–150 light panels') # Keep datagrams below typical MTU.
    panels.sort(key=lambda p:p['panel_id'])
    xs=[p['x'] for p in panels];ys=[p['y'] for p in panels]
    return [p['panel_id'] for p in panels],[dict(x=(p['x']-min(xs))/(max(xs)-min(xs)) if max(xs)!=min(xs) else .5,y=1-(p['y']-min(ys))/(max(ys)-min(ys)) if max(ys)!=min(ys) else .5) for p in panels]

def packet(ids,colors):
    if not 1<=len(ids)<=150 or len(set(ids))!=len(ids) or len(colors)!=len(ids):raise ValueError('Nanoleaf frame must match the exact panel layout')
    if any(type(v)is not int or not 0<v<=65535 for v in ids):raise ValueError('Invalid Nanoleaf panel ID')
    if any(len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in colors):raise ValueError('Nanoleaf requires RGB bytes')
    # Official recommendation: at most 10Hz, with 100ms panel-side interpolation.
    return struct.pack('>H',len(ids))+b''.join(struct.pack('>HBBBBH',pid,*c,0,1) for pid,c in zip(ids,colors))

def discover_shapes(run=None):
    """User-initiated, bounded Bonjour discovery; no subnet scan, pairing or colors."""
    if run is None:
        if not Path('/usr/bin/dns-sd').is_file():return []
        def run(args,seconds):
            process=subprocess.Popen(['/usr/bin/dns-sd']+args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
            try:output,_=process.communicate(timeout=seconds)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:output,_=process.communicate(timeout=1)
                except subprocess.TimeoutExpired:process.kill();output,_=process.communicate()
            return output[:65536]
    browse=run(['-B','_nanoleafapi._tcp','local.'],3)
    names=[]
    for line in browse.splitlines():
        fields=line.split(None,6)
        if len(fields)==7 and fields[1]=='Add' and fields[5]=='_nanoleafapi._tcp.' and fields[6] not in names:
            if len(fields[6])<=128:names.append(fields[6])
    result=[];seen=set()
    for name in names[:4]:
        resolved=run(['-L',name,'_nanoleafapi._tcp','local.'],2)
        if not re.search(r'(?:^|\s)md=NL42(?:\s|$)',resolved):continue
        match=re.search(r'can be reached at ([A-Za-z0-9_.-]+):16021',resolved)
        if not match:continue
        identity=re.search(r'(?:^|\s)id=([A-Fa-f0-9:]{17})(?:\s|$)',resolved)
        if not identity:continue
        service_id=hashlib.sha256(identity.group(1).lower().encode()).hexdigest()[:24]
        host=match.group(1)
        addresses=run(['-G','v4',host],2)
        for candidate in re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',addresses):
            try:ip=local_ip(candidate)
            except ValueError:continue
            if ip not in seen:
                seen.add(ip);result.append(dict(id=service_id,address=ip,name=name,model='NL42'))
    return result[:16]

class NanoleafAdapter:
    name='native-nanoleaf'
    def __init__(self,path=None,http=request,socket_factory=socket.socket):
        self.path=Path(path) if path else Path.home()/'Library/Application Support/HackinFX/Core/nanoleaf-pairings.json'
        self.http=http;self.socket_factory=socket_factory;self.records={};self.sockets={};self.last={};self.locks={};self.paired=[]
        try:
            saved=json.loads(self.path.read_text())
            if saved.get('schema')==1 and isinstance(saved.get('devices'),list) and len(saved['devices'])<=16:
                self.paired=[dict(ip=local_ip(d['ip']),token=token_value(d['token']),service_id=d.get('service_id') if re.fullmatch('[0-9a-f]{24}',str(d.get('service_id',''))) else None,serial_hash=d.get('serial_hash') if re.fullmatch('[0-9a-f]{64}',str(d.get('serial_hash',''))) else None) for d in saved['devices']]
        except (OSError,ValueError,KeyError,TypeError):pass
    def pair(self,ip,service_id=None):
        ip=local_ip(ip)
        token=token_value(self.http(ip,None,'POST').get('auth_token'))
        info=self.http(ip,token,'GET');layout(info) # No mode, brightness or color changes during pairing.
        if service_id is not None and not re.fullmatch('[0-9a-f]{24}',service_id):raise ValueError('Invalid discovered controller identity')
        devices=[d for d in self.paired if d['ip']!=ip and (service_id is None or d.get('service_id')!=service_id)]+[dict(ip=ip,token=token,service_id=service_id,serial_hash=hashlib.sha256(str(info.get('serialNo') or '').encode()).hexdigest())]
        if len(devices)>16:raise ValueError('At most 16 Nanoleaf controllers are supported')
        self.save(devices)
    def save(self,devices):
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        tmp=self.path.with_name('.'+uuid.uuid4().hex+'.tmp')
        try:
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump(dict(schema=1,devices=devices),f)
            os.replace(tmp,self.path)
        finally:
            try:tmp.unlink()
            except FileNotFoundError:pass
        self.paired=devices
    def discover(self):
        self.close();self.records={};rows=[];candidates=None
        for entry in self.paired:
            ip=entry['ip'];key='nanoleaf:'+(entry.get('service_id') or hashlib.sha256(ip.encode()).hexdigest()[:20])
            try:
                try:info=self.http(ip,entry['token'],'GET')
                except Exception:
                    if not entry.get('service_id'):raise
                    if candidates is None:candidates=discover_shapes()
                    found=next((d for d in candidates if d['id']==entry['service_id']),None)
                    if found is None or found['address']==ip:raise
                    new_ip=local_ip(found['address']);info=self.http(new_ip,entry['token'],'GET')
                    serial_hash=hashlib.sha256(str(info.get('serialNo') or '').encode()).hexdigest()
                    if not entry.get('serial_hash') or serial_hash!=entry['serial_hash']:raise ValueError('Discovered Nanoleaf identity changed; pair again')
                    layout(info);entry['ip']=new_ip;ip=new_ip;self.save(self.paired)
                ids,positions=layout(info)
                identity=hashlib.sha256(str(info.get('serialNo') or ip).encode()).hexdigest()[:24]
                self.records[key]=dict(entry,ids=ids);self.locks[key]=threading.Lock()
                rows.append(dict(id=key,fingerprint=identity,name=str(info.get('name') or 'Nanoleaf Shapes')[:100],vendor='Nanoleaf',category='light',backend=self.name,led_count=len(ids),direct=True,controllable=True,status='ready',detail='Local Shapes panel streaming, 10 Hz with 100 ms panel interpolation. UDP delivery is not acknowledged. Paired panels join the startup scene when reachable.',static_modes=['static','gradient'],zones=[dict(name='Shapes panels',led_count=len(ids))],modes=[],led_positions=positions,driver='nanoleaf-shapes-v2',presentation_delay=.1,startup_excluded=False))
            except Exception:
                rows.append(dict(id=key,fingerprint='',name='Nanoleaf Shapes',vendor='Nanoleaf',category='light',backend=self.name,led_count=0,direct=False,controllable=False,status='offline',detail='Controller unavailable, pairing invalid or panel layout unsupported. Check Settings and pair again.',static_modes=[],zones=[],modes=[],startup_excluded=False))
        return rows
    def activate(self,device):
        key=device['id'];record=self.records[key]
        if key in self.sockets:return
        self.http(record['ip'],record['token'],'PUT','/effects',dict(write=dict(command='display',animType='extControl',extControlVersion='v2')))
        self.http(record['ip'],record['token'],'PUT','/state',dict(on=dict(value=True),brightness=dict(value=100)))
        sock=self.socket_factory(socket.AF_INET,socket.SOCK_DGRAM)
        try:sock.settimeout(.2);sock.connect((record['ip'],60222))
        except Exception:sock.close();raise ValueError('Could not open the Nanoleaf local stream') from None
        self.sockets[key]=sock
    def write_frame(self,device,colors,mode):
        key=device['id'];record=self.records[key];data=packet(record['ids'],colors)
        with self.locks[key]:
            wait=.1-(time.monotonic()-self.last.get(key,0))
            if wait>0:time.sleep(wait)
            try:
                if self.sockets[key].send(data)!=len(data):raise OSError('short datagram')
                self.last[key]=time.monotonic()
            except OSError:raise ValueError('Nanoleaf stream failed; rediscover before continuing') from None
    def close(self):
        for sock in self.sockets.values():sock.close()
        self.sockets={};self.last={}

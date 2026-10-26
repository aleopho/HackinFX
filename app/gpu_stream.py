# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded persistent PNY lighting worker. Exact identity checked before opening RM.
The worker owns the GPU write lock and RM object tree until EOF/stop/failure.
Only the existing three-zone volatile RGB packet is permitted, never raw I2C.
"""
import ctypes as C
import json
import os
from pathlib import Path
import platform
import re
import select
import subprocess
import sys
import threading
import time
import probe
import profiles
import rgb

MAX_LINE=4096

def confirmed_profile(directory,fingerprint,key):
    if not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{64}',fingerprint):raise ValueError('Invalid GPU fingerprint')
    path=Path(directory)/('profile-'+fingerprint+'.json')
    if path.stat().st_size>16384:raise ValueError('GPU profile exceeds limit')
    saved=json.loads(path.read_text())
    profile=next((p for p in profiles.PROFILES if p.key==key),None)
    if not profile or profile.controller!='PNYLovelaceGPUController' or profile.zones!=3 or profile.address!=0x60 or profile.register!=2:raise ValueError('Persistent streaming is restricted to exact PNY three-zone profiles')
    if saved.get('schema')!=1 or saved.get('fingerprint')!=fingerprint or saved.get('successfulSteps')!=3 or saved.get('userConfirmed') is not True or not set(profile.effects).issubset(set(saved.get('verifiedEffects',[]))):raise ValueError('GPU profile is no longer confirmed; rescan required')
    return profile

def validate_pixels(value):
    if not isinstance(value,list) or len(value)!=3 or any(not isinstance(c,list) or len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in value):raise ValueError('Exactly three RGB zones required')
    return value

class Stream(rgb.RGB):
    def __init__(self,transport,profile,source,sink,check):
        super().__init__(transport,{},profile.port,apply=False,profile=profile)
        self.source,self.sink,self.check=source,sink,check
    def reply(self,value):self.sink.write(json.dumps(value,separators=(',',':'))+'\n');self.sink.flush()
    def call(self,escape,data):
        super().call(escape,data)
        self.report['calls']=self.report['calls'][-24:]
    def after_ports(self,obj,ports):
        super().after_ports(obj,ports) # DCB metadata once; apply=False sends no color.
        if ports[self.port]&0x15!=0x11:raise ValueError('PNY port validation failed')
        self.reply(dict(ready=True))
        while True:
            line=self.source.readline(MAX_LINE+1)
            if not line:return
            if len(line)>MAX_LINE or not line.endswith('\n'):raise ValueError('GPU frame exceeds limit')
            request=json.loads(line)
            if not isinstance(request,dict) or set(request)!={'pixels','sequence'} or type(request['sequence'])is not int or not 0<=request['sequence']<2**53:raise ValueError('Invalid GPU frame')
            pixels=validate_pixels(request['pixels']);self.check()
            # Reuse existing tested packet builder; address/port cannot come from IPC.
            for packet in rgb.effect_packets('gradient',pixels[0],'all',brightness=255,colors=pixels):
                payload=(C.c_uint8*7)(*packet)
                indexed=rgb.Indexed(port=self.port,write=1,address=0xc0,flags=0,index_length=1,index=(C.c_uint8*4)(2,0,0,0),length=7,message=C.addressof(payload))
                command=probe.Control(self.client,obj,0x402c0102,0,C.addressof(indexed),C.sizeof(indexed),0xffffffff)
                self.call(0x2a,command)
            self.reply(dict(sequence=request['sequence'],ok=True))

class Client:
    def __init__(self,directory,fingerprint,key,timeout=4):
        self.directory,self.fingerprint,self.key=Path(directory),fingerprint,key
        self.timeout=timeout;self.process=None;self.sequence=0;self.lock=threading.RLock()
    def read(self,timeout):
        data=bytearray();deadline=time.monotonic()+timeout
        while b'\n' not in data:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([self.process.stdout],[],[],remaining)[0]:raise TimeoutError('GPU stream timed out')
            part=os.read(self.process.stdout.fileno(),MAX_LINE+1)
            if not part:raise RuntimeError('GPU stream closed; rescan required')
            data.extend(part)
            if len(data)>MAX_LINE:raise ValueError('GPU worker response exceeds limit')
        response=json.loads(data)
        if not isinstance(response,dict) or 'error' in response:raise RuntimeError(str(response.get('error','Invalid GPU response'))[:300])
        return response
    def start(self):
        with self.lock:
            if self.process is not None:
                if self.process.poll() is None:return
                raise RuntimeError('GPU stream stopped; rescan required')
            confirmed_profile(self.directory,self.fingerprint,self.key)
            self.process=subprocess.Popen(['/usr/bin/python3','-B',str(Path(__file__).resolve()),str(self.directory),self.fingerprint,self.key],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
            try:
                if self.read(30)!={'ready':True}:raise RuntimeError('GPU stream initialization failed')
            except Exception:self.close();raise
    def write(self,pixels):
        with self.lock:
            validate_pixels([list(c) for c in pixels]);self.start();self.sequence+=1
            try:
                self.process.stdin.write((json.dumps(dict(sequence=self.sequence,pixels=pixels),separators=(',',':'))+'\n').encode());self.process.stdin.flush()
                if self.read(self.timeout)!={'sequence':self.sequence,'ok':True}:raise RuntimeError('GPU frame acknowledgement mismatch')
            except Exception:self.close();raise
    def close(self):
        with self.lock:
            process=self.process;self.process=None
            if process is None:return
            try:
                if process.stdin:process.stdin.close()
                process.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):
                process.kill();process.wait(timeout=3)
            finally:
                if process.stdout:process.stdout.close()

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    native=lock=None
    try:
        if len(args)!=3 or sys.platform!='darwin' or platform.machine()!='x86_64':raise ValueError('Exact GPU profile on x86-64 macOS required')
        directory,fingerprint,key=args
        check=lambda:confirmed_profile(directory,fingerprint,key)
        profile=check();rgb.check_abi();probe.check_abi()
        # Fresh exact hardware guard once per RM session. The allocated object tree
        # remains bound to this GPU; a disconnect/error ends the worker, no reconnect.
        actual=profiles.select(probe.inventory())
        if actual.key!=profile.key:raise ValueError('GPU changed; rescan required')
        lock=rgb.acquire_write_lock();native=probe.Native();native.open()
        stream=Stream(native,profile,sys.stdin,sys.stdout,check);stream.run()
        if stream.report.get('cleanup_error'):raise RuntimeError('GPU cleanup failed')
        return 0
    except Exception as exc:
        sys.stdout.write(json.dumps(dict(error=str(exc)[:300]))+'\n');sys.stdout.flush();return 1
    finally:
        if native:native.close()
        if lock:lock.close()

if __name__=='__main__':raise SystemExit(main())

# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded OpenRGB SDK 3 client, interoperable with newer servers.
Protocol reference: OpenRGB 817834cf, NetworkProtocol.h / RGBController.cpp.
Only color streaming/custom mode; never profile saves, resize, firmware or fan writes.
"""
import hashlib
import select
import socket
import struct
import threading

MAX_PACKET = 8*1024*1024
CATEGORIES = ['mainboard','dram','gpu','cooler','strip','keyboard','mouse','mousepad','headset','stand','gamepad','light','speaker','virtual','storage','case','microphone','accessory','keypad','laptop','monitor','unknown']


class ProtocolError(ValueError): pass


class Reader:
    def __init__(self,data): self.data,self.pos=data,0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data): raise ProtocolError('Truncated controller data')
        out=self.data[self.pos:self.pos+n];self.pos+=n;return out
    def u16(self): return struct.unpack('<H',self.take(2))[0]
    def u32(self): return struct.unpack('<I',self.take(4))[0]
    def text(self):
        size=self.u16()
        if not 1<=size<=4096: raise ProtocolError('Invalid SDK string')
        raw=self.take(size)
        if raw[-1]!=0: raise ProtocolError('Unterminated SDK string')
        return ''.join(c for c in raw[:-1].decode('utf-8',errors='replace') if c.isprintable())[:200]
    def count(self,maximum):
        value=self.u16()
        if value>maximum: raise ProtocolError('Controller count exceeds supported limits')
        return value


def parse_controller(data):
    r=Reader(data)
    if r.u32()!=len(data): raise ProtocolError('Controller size mismatch')
    kind=r.u32();name=r.text();vendor=r.text();description=r.text();version=r.text()
    r.text()  # Serial intentionally discarded; never returned, hashed or stored.
    r.text()  # OS location intentionally discarded as potentially identifying.
    mode_count=r.count(128);active=r.u32();modes=[]
    for _ in range(mode_count):
        label=r.text();fields=[r.u32() for _ in range(12)]
        colors=r.count(4096);r.take(colors*4)
        modes.append(dict(name=label,flags=fields[1]))
    zones=[]
    for _ in range(r.count(128)):
        label=r.text();kind_zone=r.u32();minimum=r.u32();maximum=r.u32();count=r.u32()
        if count>4096: raise ProtocolError('Zone too large')
        matrix_size=r.u16();r.take(matrix_size)
        zones.append(dict(name=label,led_count=count,type=kind_zone))
    led_count=r.count(4096)
    for _ in range(led_count): r.text();r.u32()
    colors=r.count(4096);r.take(colors*4)
    if colors!=led_count or r.pos!=len(data): raise ProtocolError('Inconsistent LED data')
    category=CATEGORIES[kind] if kind<len(CATEGORIES) else 'unknown'
    direct=any((m['flags'] & 32) and ('direct' in m['name'].lower() or m['name'].lower()=='custom') for m in modes)
    identity=hashlib.sha256(repr((name,vendor,category,led_count,[(z['name'],z['led_count']) for z in zones])).encode()).hexdigest()[:24]
    return dict(name=name,vendor=vendor,category=category,led_count=led_count,zones=zones,modes=modes,direct=direct and led_count>0,fingerprint=identity,backend='openrgb',status='ready' if direct and led_count else 'hardware-modes-only',detail='Live OpenRGB connection; physical lighting is not confirmed.')


class SDKClient:
    def __init__(self,port=6742,connector=socket.create_connection):
        if type(port) is not int or not 1<=port<=65535: raise ValueError('Invalid OpenRGB port')
        self.port,self.connector=port,connector;self.sock=None;self.lock=threading.RLock();self.dirty=False
    def close(self):
        if self.sock:
            try:self.sock.close()
            finally:self.sock=None
    def exact(self,n):
        out=bytearray()
        while len(out)<n:
            part=self.sock.recv(n-len(out))
            if not part: raise ConnectionError('OpenRGB disconnected')
            out.extend(part)
        return bytes(out)
    def packet(self):
        magic,device,kind,size=struct.unpack('<4sIII',self.exact(16))
        if magic!=b'ORGB' or size>MAX_PACKET: raise ProtocolError('Invalid SDK packet')
        return device,kind,self.exact(size)
    def send(self,kind,device=0,data=b''):
        self.sock.sendall(struct.pack('<4sIII',b'ORGB',device,kind,len(data))+data)
    def request(self,kind,device=0,data=b''):
        self.send(kind,device,data)
        for _ in range(128):
            dev,event,payload=self.packet()
            if event==100:self.dirty=True;raise ProtocolError('OpenRGB device list changed; refresh devices')
            if event==kind and dev==device:return payload
        raise ProtocolError('Too many SDK notifications')
    def discover(self):
        with self.lock:
            self.close();self.dirty=False
            try:
                self.sock=self.connector(('127.0.0.1',self.port),timeout=2);self.sock.settimeout(2)
                version=self.request(40,data=struct.pack('<I',3))
                if len(version)!=4 or struct.unpack('<I',version)[0]<3:raise ProtocolError('OpenRGB SDK 3 or later required')
                self.send(50,data=b'HackinFX Core\0')
                count_data=self.request(0)
                if len(count_data)!=4:raise ProtocolError('Invalid controller count')
                count=struct.unpack('<I',count_data)[0]
                if count>64:raise ProtocolError('More than 64 controllers; connection stopped')
                return [dict(parse_controller(self.request(1,i,struct.pack('<I',3))),index=i) for i in range(count)]
            except Exception:self.close();raise
    def check_notifications(self):
        for _ in range(128):
            if not select.select([self.sock],[],[],0)[0]:return
            _,kind,_=self.packet()
            if kind==100:self.dirty=True
        raise ProtocolError('SDK notification flood')
    def activate(self,index):
        with self.lock:
            if not self.sock:raise ConnectionError('OpenRGB is not connected')
            self.check_notifications()
            if self.dirty:raise ProtocolError('Device list changed; refresh before writing')
            self.send(1100,index)
    def colors(self,index,colors):
        with self.lock:
            if not self.sock:raise ConnectionError('OpenRGB is not connected')
            self.check_notifications()
            if self.dirty:raise ProtocolError('Device list changed; refresh before writing')
            if not 1<=len(colors)<=4096:raise ValueError('Invalid frame size')
            values=[]
            for color in colors:
                if len(color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in color):raise ValueError('Invalid RGB frame')
                values.append(bytes((*color,0)))
            payload=struct.pack('<IH',6+4*len(colors),len(colors))+b''.join(values)
            try:self.send(1050,index,payload)
            except Exception:self.close();raise

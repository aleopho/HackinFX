# SPDX-License-Identifier: GPL-2.0-or-later
# Port of aleopho/signalrgb-fractal-radius (MIT); original source/license in vendor/radius.
"""Fractal Radius acknowledged Still-preview lighting protocol. No cooling/flash writes."""
import time

class RadiusError(ValueError):pass

def pad(values):
    data=bytes(values)
    if len(data)>64:raise RadiusError('Radius report exceeds 64 bytes')
    return data.ljust(64,b'\0')

def topology(reply):
    if len(reply)!=64 or reply[:4]!=bytes([2,0xa4,8,0]):raise RadiusError('Radius topology ACK mismatch')
    count=reply[4]
    if not 1<=count<=19:raise RadiusError('Radius RGB table length invalid')
    zones=[];seen=set()
    for i in range(count):
        key,leds,protocol=reply[5+i*3:8+i*3]
        if key in seen:raise RadiusError('Radius RGB table has duplicate zones')
        seen.add(key)
        if not leds:continue
        if key!=1 and key>>4!=1:raise RadiusError('Radius RGB port outside known topology')
        if protocol not in (0,1,2,5):raise RadiusError('Unknown Radius RGB protocol')
        zones.append(dict(id=key,count=leds,type=protocol))
    pump=next((z for z in zones if z['id']==1),None)
    if not pump or pump['count']!=22:raise RadiusError('Expected verified 22-position Radius pump')
    if len({2 if z['type']==0 else z['type'] for z in zones if z['id']!=1})>1:raise RadiusError('Mixed Radius fan protocols; check configured topology in Adjust')
    if sum(z['count'] for z in zones)>4096:raise RadiusError('Radius lighting array exceeds supported size')
    return sorted(zones,key=lambda z:z['id'])

def packets(zones,colors):
    if len(colors)!=sum(z['count'] for z in zones):raise RadiusError('Radius color count does not match active zones')
    if any(len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in colors):raise RadiusError('Radius needs exact RGB bytes')
    if not 1<=len(zones)<=19 or any(not 1<=z['count']<=255 for z in zones):raise RadiusError('Invalid Radius zone dimensions')
    result=[];first=0
    for zone in zones:
        frame=bytes(v for c in colors[first:first+zone['count']] for v in c);first+=zone['count']
        stream=b''.join(stamp.to_bytes(2,'big')+frame for stamp in (0,562,1124))
        result.extend([pad([2,0xa4,0x0a,1,zone['id']]),pad([2,0xa4,0x11,1,sum(stream)&255,len(stream)>>8,len(stream)&255,1,len(zones),0x99,1,100,*frame[:3],100])])
        result.extend(pad([2,0xa4,0x12,len(stream[i:i+60]),*stream[i:i+60]]) for i in range(0,len(stream),60))
    return result

class Radius:
    def __init__(self,transport,handle):self.transport=transport;self.handle=handle;self.zones=[];self.previous=None;self.failed=False;self.last_sent=0
    def exchange(self,packet):
        if self.failed:raise RadiusError('Radius transaction stopped; rediscover before further writes')
        try:
            reply=self.transport.exchange(self.handle,packet)
            if len(reply)!=64 or reply[:3]!=packet[:3] or reply[3]!=0:raise RadiusError('Radius ACK mismatch for command %02x'%packet[2])
            return reply
        except Exception:self.failed=True;raise
    def discover(self):
        try:self.zones=topology(self.exchange(pad([2,0xa4,8,1])));return self.zones
        except Exception:self.failed=True;raise
    def write(self,colors):
        if self.failed:raise RadiusError('Radius transaction stopped; rediscover before further writes')
        batch=packets(self.zones,colors) # Validate the complete batch before sending anything.
        key=tuple(tuple(c) for c in colors)
        if key==self.previous and time.monotonic()-self.last_sent<.25:return
        if hasattr(self.transport,'exchange_batch'):
            try:self.transport.exchange_batch(self.handle,batch)
            except Exception:self.failed=True;raise
        else:
            deadline=time.monotonic()+12
            for packet in batch:
                if time.monotonic()>deadline:self.failed=True;raise RadiusError('Radius batch deadline exceeded; output stopped without retry')
                self.exchange(packet)
        self.previous=key;self.last_sent=time.monotonic()

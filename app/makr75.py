# SPDX-License-Identifier: GPL-3.0-or-later
"""Native MAKR 75 volatile RGB. OpenLinkHub / Nikola Jurkovic protocol reference.
Exact wired interface, acknowledged commands, no input/configuration/profile writes.
"""
import json,struct,time
from pathlib import Path
LAYOUT=json.loads(Path(__file__).with_name('makr75-layout.json').read_text())
KEYS=LAYOUT['keys']
# OpenLinkHub MAKR reference: RGB ring occupies payload bytes 420 through 437.
DIAL=[dict(name='DIAL '+str(i+1),offset=420+i*3,x=.96,y=.06+i*.012) for i in range(6)]
if len(KEYS)!=81 or len({k['offset'] for k in KEYS})!=81 or any(type(k['offset'])!=int or k['offset']%3 or not 0<=k['offset']<=435 for k in KEYS):raise ValueError('Invalid MAKR layout')
if any(k['offset']>=420 for k in KEYS):raise ValueError('Key map overlaps dial ring')
KEYS=KEYS+DIAL

def packet(command,data=b''):
    if len(command)+len(data)>511:raise ValueError('MAKR packet too large')
    return bytes([0,8])+bytes(command)+bytes(data)+bytes(511-len(command)-len(data))

def color_packet(colors):
    if len(colors)!=len(KEYS):raise ValueError('MAKR requires exactly 87 mapped RGB values')
    payload=bytearray(440)
    for key,color in zip(KEYS,colors):
        if len(color)!=3 or any(type(c)!=int or not 0<=c<=255 for c in color):raise ValueError('Invalid MAKR RGB value')
        payload[key['offset']:key['offset']+3]=bytes(color)
    return packet([6,1],struct.pack('<H',440)+b'\x00\x00\x12\x00'+payload)

class Controller:
    def __init__(self,transport,handle):self.transport=transport;self.handle=handle;self.active=False;self.mode_attempted=False;self.failed=False;self.last_keepalive=0
    def exchange(self,command,data=b''):
        raw=self.transport.exchange(self.handle,packet(command,data))
        if len(raw)!=512 or raw[0]!=0 or raw[1]!=command[0] or raw[2]!=0:raise ValueError('MAKR RGB acknowledgement mismatch: '+raw[:8].hex())
        return raw
    def discover(self):
        raw=self.exchange([2,0x13]);version='%d.%d.%d'%(raw[3],raw[4],int.from_bytes(raw[5:7],'little'))
        if version!='7.11.104':raise ValueError('MAKR firmware '+version+' is not yet verified; lighting disabled')
        self.version=version;return version
    def activate(self):
        if self.failed:raise ValueError('MAKR session failed; rediscover before retrying')
        self.mode_attempted=True
        try:
            self.exchange([1,3,0,2]);self.exchange([0x0d,1,0x22]);time.sleep(.5);self.last_keepalive=time.monotonic();self.active=True
        except Exception:
            self.failed=True;self.release();raise
    def write(self,colors):
        if not self.active or self.failed:raise ValueError('MAKR lighting session is not active')
        p=color_packet(colors)
        try:
            if time.monotonic()-self.last_keepalive>=15:self.exchange([0x12]);self.last_keepalive=time.monotonic()
            self.exchange([6,1],p[4:450])
        except Exception:self.failed=True;raise
    def release(self):
        try:
            if self.mode_attempted:self.exchange([1,3,0,1])
        finally:self.active=False;self.mode_attempted=False

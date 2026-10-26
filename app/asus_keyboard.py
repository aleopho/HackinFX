# SPDX-License-Identifier: GPL-2.0-or-later
# Protocol references: OpenRGB and MIT-licensed RIGStats (vendor/rigstats).
"""ASUS OMNI keyboard hardware effects; no profile/flash or pairing commands."""
import struct

def output_reports(data):
    page=rid=size=count=0;stack=[];bits={};pos=0
    if len(data)>16384:raise ValueError('HID descriptor too large')
    while pos<len(data):
        p=data[pos];pos+=1
        if p==0xfe:raise ValueError('HID long item unsupported')
        n=(0,1,2,4)[p&3]
        if pos+n>len(data):raise ValueError('Truncated HID descriptor')
        v=int.from_bytes(data[pos:pos+n],'little');pos+=n;tag=p&0xfc
        if tag==0x84:rid=v
        elif tag==0x74:size=v
        elif tag==0x94:count=v
        elif tag==0xa4:stack.append((rid,size,count))
        elif tag==0xb4:
            if not stack:raise ValueError('Invalid HID push/pop')
            rid,size,count=stack.pop()
        elif tag==0x90:
            if size*count>4096:raise ValueError('Output report too large')
            bits[rid]=bits.get(rid,0)+size*count
    return {k:(v+7)//8+1 for k,v in bits.items()}

def query(command,report_id=2,length=64):return bytes([report_id,0x12,command]).ljust(length,b'\0')

def paired_keyboard(reply):
    if len(reply)!=64 or reply[:3]!=bytes([1,0xa0,0]) or reply[3]>14:raise ValueError('OMNI paired list mismatch')
    result=None
    names={0x1ab0:'ASUS ROG Strix Scope II 96 Wireless',0x1c25:'ASUS ROG Azoth X'}
    for i in range(reply[3]):
        offset=5+4*i
        if offset+4>len(reply):raise ValueError('Truncated OMNI paired table')
        pid,channel,kind=struct.unpack_from('<HBB',reply,offset)
        if channel==2 and pid in names:
            if result is not None:raise ValueError('Ambiguous OMNI keyboard channel')
            result=dict(product_id=pid,name=names[pid])
    return result

def discover(transport,record):
    import base64
    reports=output_reports(base64.b64decode(record.get('descriptor',''),validate=True))
    receiver=record['product_id']==0x1ace;report_id=2 if receiver else 0;length=64 if receiver else 65
    if reports.get(report_id)!=length:raise ValueError('ASUS keyboard output report is not supported')
    record['keyboard_report_id']=report_id;record['keyboard_length']=length
    reply=transport.exchange(record['handle'],query(0x12,report_id,length))
    if len(reply)!=length or reply[:3]!=bytes([report_id,0x12,0x12]) or not any(reply[3:8]):raise ValueError('OMNI keyboard did not return a layout; wake it or connect USB for diagnosis')
    record['keyboard_layout_reply']=reply[:8].hex()
    record['keyboard_topology']=scope_topology(record['product_id'],reply)
    paired=None
    if not receiver:return dict(product_id=record['product_id'],name='ASUS ROG Strix Scope II 96 Wireless · USB')
    if reports.get(1)==64:
        try:paired=paired_keyboard(transport.exchange(record['handle'],bytes([1,0xa0,0]).ljust(64,b'\0')))
        except ValueError:pass
    return paired

def effect_packet(mode,rgb,brightness=100,report_id=2,length=64):
    if mode not in ('static','breathing','spectrum') or len(rgb)!=3 or any(type(v)is not int or not 0<=v<=255 for v in rgb):raise ValueError('Unsupported ASUS keyboard effect or color')
    if type(brightness)is not int or not 0<=brightness<=100:raise ValueError('Invalid keyboard brightness')
    if (report_id,length) not in ((2,64),(0,65)):raise ValueError('Invalid ASUS keyboard transport shape')
    packet=bytearray(length);packet[:7]=bytes([report_id,0x51,0x2c,{'static':0,'breathing':1,'spectrum':2}[mode],0,30,brightness]);packet[9]=2;packet[10:13]=bytes(rgb)
    return bytes(packet)

# OpenRGB 1.1 AsusAuraTUFKeyboardController / layouts, Mola19 and contributors,
# GPL-2.0-or-later. Exact preserved inputs: vendor/openrgb/keyboard/SOURCES.json.
def scope_topology(product_id,reply):
    if product_id!=0x1aae or len(reply)!=65 or reply[:3]!=bytes([0,0x12,0x12]):return None
    from pathlib import Path
    import json
    code=reply[4]*100+reply[5]
    if code//100 not in (1,2):return None
    # Same documented fallback as OpenRGB: 2xx ISO, 1xx ANSI.
    variant='NO' if code%100==11 else 'UK' if code//100==2 else 'US'
    layout=json.loads(Path(__file__).with_name('asus_scope_layouts.json').read_text())['layouts'][variant]
    return dict(layout_code=code,layout=variant,keys=layout['keys'],positions=layout['positions'],source='OpenRGB 1.1 / device layout reply')

def per_key_packets(topology,colors):
    keys=topology['keys']
    if not 1<=len(keys)<=102 or len(colors)!=len(keys) or len(set(k['id'] for k in keys))!=len(keys):raise ValueError('Keyboard topology / frame mismatch')
    if any(type(k['id'])is not int or not 0<=k['id']<=0x94 for k in keys) or any(len(c)!=3 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in colors):raise ValueError('Invalid keyboard LED / RGB value')
    packets=[]
    for start in range(0,len(keys),15):
        count=min(15,len(keys)-start);packet=bytearray(65);packet[:5]=bytes([0,0xc0,0x81,count,0])
        for j in range(count):packet[5+4*j:9+4*j]=bytes([keys[start+j]['id'],*colors[start+j]])
        packets.append(bytes(packet))
    return packets

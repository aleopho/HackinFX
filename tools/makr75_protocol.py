# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline MAKR 75 packet prototype; no transport or automatic activation.
Protocol reference: OpenLinkHub / Nikola Jurkovic (vendor/openlinkhub-makr75).
"""
import json,struct
from pathlib import Path
REFERENCE=Path(__file__).resolve().parents[1]/'vendor/openlinkhub-makr75/makr75.json'

def packet(command,data=b''):
    if len(command)+len(data)>511:raise ValueError('MAKR packet exceeds 512-byte payload')
    return bytes([0,8])+bytes(command)+bytes(data)+bytes(511-len(command)-len(data))

def firmware_query():return packet([2,0x13])

def key_layout():
    source=json.loads(REFERENCE.read_text());result=[];seen=set()
    for row in source['row'].values():
        for key in row['keys'].values():
            if key.get('noColor'):continue
            for offset in key.get('packetIndex',[]):
                if type(offset)!=int or offset%3 or not 0<=offset<=435 or offset in seen:raise ValueError('Invalid or duplicate MAKR RGB offset')
                seen.add(offset);result.append(dict(name=key['keyName'],offset=offset,x=key.get('left',0),y=key.get('top',0)))
    return result

def color_packet(colors):
    layout=key_layout()
    if len(colors)!=len(layout):raise ValueError('One RGB triplet per mapped LED required')
    payload=bytearray(440)
    for key,color in zip(layout,colors):
        if len(color)!=3 or any(type(c)!=int or not 0<=c<=255 for c in color):raise ValueError('Invalid RGB channel')
        payload[key['offset']:key['offset']+3]=bytes(color)
    return packet([6,1],struct.pack('<H',440)+b'\x00\x00\x12\x00'+payload)

def validate_reply(raw,command):
    if len(raw)!=512 or raw[0]!=0 or raw[1]!=command or raw[2]!=0:
        raise ValueError('MAKR acknowledgement mismatch: '+raw[:8].hex())
    return raw

def firmware_version(raw):
    validate_reply(raw,2)
    return '%d.%d.%d'%(raw[3],raw[4],int.from_bytes(raw[5:7],'little'))

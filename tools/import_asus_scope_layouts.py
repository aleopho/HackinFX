#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Rebuild exact Scope II 96 layout from preserved OpenRGB 1.1 source, offline."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'vendor/openrgb/keyboard/AsusAuraTUFKeyboardLayouts.h').read_text();start=s.index('static std::map<int,layout_info> AsusROGStrixScopeII96WirelessLayouts');end=s.find('static std::map',start+20);section=s[start:end if end>0 else None]
layouts={}
for name,body in re.findall(r'ASUS_TUF_K7_LAYOUT_(NO|UK|US),\s*\{(.*?)(?=\n    \},|\Z)',section,re.S):
 keys=[dict(name=label.strip().strip('"'),id=int(ident,16)) for label,ident in re.findall(r'\{\s*([^,{}]+),\s*(0x[0-9A-Fa-f]+)\s*\}',body)]
 matrixname='ISO' if name!='US' else 'ANSI'
 grid=re.search(r'ASUS_ROG_STRIX_SCOPE_II_96_WIRELESS_LAYOUT_KEYS_'+matrixname+r'\[6\]\[19\]\s*=\s*\{(.*?)\};',s,re.S).group(1)
 grid=[[None if x.strip()=='NA' else int(x.strip()) for x in row.split(',')] for row in re.findall(r'\{([^{}]+)\}',grid)]
 assert len(keys)==(101 if name=='US' else 102), (name,len(keys))
 assert len(set(k['id'] for k in keys))==len(keys)
 positions=[None]*len(keys)
 for y,row in enumerate(grid):
  for x,index in enumerate(row):
   if index is not None:positions[index]=dict(x=x/18,y=y/5)
 assert all(p is not None for p in positions)
 layouts[name]=dict(keys=keys,positions=positions)
assert set(layouts)=={'NO','UK','US'}
(ROOT/'app/asus_scope_layouts.json').write_text(json.dumps(dict(schema=1,model='ASUS ROG Strix Scope II 96 Wireless',source='OpenRGB 1.1 / Mola19 and contributors, GPL-2.0-or-later',layouts=layouts),separators=(',',':'))+'\n')

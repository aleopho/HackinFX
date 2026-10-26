#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic identity import. Source registrations never grant write capability."""
import ast,csv,hashlib,io,json,re,zipfile
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
PIN='817834cfab034c97927451e31c4a2deb60a44725'
SOURCE=ROOT/'vendor/openrgb/usb-sources.zip'
DEST=ROOT/'app/openrgb_usb_catalog.json'
def clean(text):
    return re.sub(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*',lambda m:m[0] if m[0].startswith('"') else ' ',text)
def symbols(text):
    text=clean(text)
    out=dict(re.findall(r'^\s*#define\s+(\w+)\s+([^\n]+)',text,re.M))
    out.update(re.findall(r'\b([A-Z][A-Z0-9_]+)\s*=\s*(0[xX][0-9a-fA-F]+|\d+)\s*[,;]',text))
    return out
def category(name,family):
    text=(name+' '+family).lower()
    for pattern,label in [('keyboard|keychron|ducky|scope|azoth|falchion|blackwidow|huntsman','keyboard'),('mousemat|mousepad|firefly','mousepad'),('mouse|mice|spatha|gladius|pugio|keris|harpe|naga|deathadder|g502|g203|g903|basilisk','mouse'),('kraken|hydro|aio|water|ryuo|ryujin|capellix|cooler','cooler'),('mainboard|motherboard|fusion2usb|aurausb|mysticlight','mainboard'),('dram|memory|ramcontroller','dram'),('headset','headset'),('fan|lightingnode|commander|hue|controller|strip','controller')]:
        if re.search(pattern,text):return label
    return 'usb'
def build():
    with zipfile.ZipFile(SOURCE) as archive:
        files={name:archive.read(name).decode('utf8',errors='replace') for name in archive.namelist() if name.endswith(('.h','Detect.cpp'))}
    all_values=defaultdict(set)
    for content in files.values():
        for k,v in symbols(content).items():all_values[k].add(v.strip())
    global_symbols={k:next(iter(v)) for k,v in all_values.items() if len(v)==1}
    def resolve(value,defs,stack=()):
        value=value.strip()
        if value in defs:
            if value in stack or len(stack)>20:raise ValueError('Recursive symbol')
            return resolve(defs[value],defs,stack+(value,))
        if re.fullmatch(r'(?:0[xX][0-9a-fA-F]+|\d+)[uUlL]*',value):return int(re.sub('[uUlL]+$','',value),0) if not value.isdigit() else int(value)
        if value.startswith('"'):return ast.literal_eval(value)
        raise ValueError('Unresolved symbol')
    entries=[];skipped=[];sources=[]
    pattern=r'\b(REGISTER_(?:HID|USB)_DETECTOR(?:_[A-Z_]+)?)\s*\(([^;]*?)\)\s*;'
    for path,text in sorted(files.items()):
        if not path.endswith('Detect.cpp'):continue
        family=path.split('/')[1];defs=dict(global_symbols)
        for other,content in files.items():
            if other.startswith('Controllers/'+family+'/'):defs.update(symbols(content))
        defs.update(symbols(text));sources.append(dict(path=path,sha256=hashlib.sha256(text.encode()).hexdigest()))
        for match in re.finditer(pattern,clean(text),re.S):
            macro=match[1];args=[v.strip() for v in next(csv.reader([match[2]],skipinitialspace=True,quoting=csv.QUOTE_NONE))]
            try:
                if '_ONLY' in macro:continue # Universal usage detectors handled by native descriptor matching.
                name=resolve(args[0],defs);vid=resolve(args[2],defs);pid=resolve(args[3],defs)
                if not isinstance(name,str) or not isinstance(vid,int) or not isinstance(pid,int) or not 0<=vid<=65535 or not 0<=pid<=65535:raise ValueError('Invalid identity')
                entries.append(dict(name=name,vendor_id=vid,product_id=pid,category=category(name,family),controller=family,detector=args[1],enabled='_DISABLED' not in macro,registration=macro,source=path))
            except (ValueError,IndexError,SyntaxError):skipped.append(dict(source=path,registration=match[0][:240]))
    entries=sorted({json.dumps(r,sort_keys=True):r for r in entries}.values(),key=lambda r:(r['vendor_id'],r['product_id'],r['name']))
    return dict(schema=1,source=dict(project='OpenRGB',commit=PIN,url='https://github.com/CalcProgrammer1/OpenRGB/tree/'+PIN,archive_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest()),entries=entries,unresolved=skipped,source_files=sources)
if __name__=='__main__':
    result=build();DEST.write_text(json.dumps(result,indent=2)+'\n');print(len(result['entries']),'USB/HID registrations;',len(result['unresolved']),'unresolved registrations retained for audit')

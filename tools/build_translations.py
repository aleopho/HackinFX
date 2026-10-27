#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build-time machine translations of public UI messages. No app runtime networking.
Resources are checked in; human linguistic/community review remains separate.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import collections,json,re,time,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'app/Localization'
LANGUAGES=['de','fr','es','it','pt-BR','pt-PT','nl','pl','cs','sv','tr','uk','ru','ar','hi','id','vi','ja','ko','zh-Hans','zh-Hant']
TARGETS={'pt-BR':'pt','pt-PT':'pt-PT','zh-Hans':'zh-CN','zh-Hant':'zh-TW'}
BRANDS=['~/Documents/HackinFX','Documents/HackinFX','Application Support','HackinFX','OpenRGB','NullMoth','macUSPCIO','Nanoleaf','NVRM','OpenCore','WidgetKit','Fractal','Corsair','ASUS','PNY','NZXT','GPU','RAM','USB','RGB','PCI','LED','FPS','JSON','DHCP']
def protect(text):
    values={}
    for placeholder in re.findall(r'\{[0-9]+\}',text):
        if placeholder not in values.values():
            marker='ZQPH%04dQZ'%len(values);values[marker]=placeholder;text=text.replace(placeholder,marker)
    for brand in BRANDS:
        if brand in text:
            marker='ZQPH%04dQZ'%len(values);values[marker]=brand;text=text.replace(brand,marker)
    return text,values

def fetch(query,code):
    url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl='en',tl=TARGETS.get(code,code),dt='t',q=query))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'HackinFX-build-localization/1.0'}),timeout=20) as response:data=json.load(response)
            return ''.join(item[0] for item in data[0] if item[0])
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)

def restore(value,source,brands):
    value=re.sub(r'ZQPH\s*([0-9]{4})\s*QZ',lambda m:'ZQPH'+m.group(1)+'QZ',value,flags=re.I)
    if collections.Counter(re.findall('ZQPH[0-9]{4}QZ',source))!=collections.Counter(re.findall('ZQPH[0-9]{4}QZ',value)):return None
    for marker,brand in brands.items():value=value.replace(marker,brand)
    return value.strip() or None

def translate_batch(keys,code):
    protected=[protect(k) for k in keys]
    text=fetch('\n'.join('X%04dX %s'%(i,p[0]) for i,p in enumerate(protected)),code)
    matches=list(re.finditer(r'X\s*([0-9]{4})\s*X\s*',text,re.I));out={}
    for n,match in enumerate(matches):
        i=int(match.group(1))
        if not 0<=i<len(keys):continue
        raw=text[match.end():matches[n+1].start() if n+1<len(matches) else len(text)].strip()
        value=restore(raw,*protected[i])
        if value:out[keys[i]]=value
    for i,key in enumerate(keys):
        if key not in out:
            value=restore(fetch(protected[i][0],code),*protected[i])
            if not value:raise ValueError('Placeholder validation failed: '+code+' '+key[:80])
            out[key]=value
    return out

def build(code,base):
    path=FOLDER/(code+'.json')
    try:result=json.loads(path.read_text())
    except (OSError,ValueError):result={}
    pending=[k for k in base if not result.get(k)]
    batches=[];batch=[];size=0
    for key in pending:
        length=len(key)+20
        if size+length>1800 and batch:batches.append(batch);batch=[];size=0
        batch.append(key);size+=length
    if batch:batches.append(batch)
    for batch in batches:
        result.update(translate_batch(batch,code));path.write_text(json.dumps({k:result[k] for k in base if k in result},ensure_ascii=False,indent=2)+'\n');print(code,len(result),flush=True);time.sleep(.1)
    return code,len(result)
if __name__=='__main__':
    base=json.loads((FOLDER/'en.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(build,code,base) for code in LANGUAGES]
        for future in as_completed(futures):print(*future.result(),flush=True)
    metadata=dict(source='en',languages=['en']+LANGUAGES,translation_method='Build-time machine translation with protected placeholders/brands and local overrides; linguistic community review pending. No translation service is contacted by the app.')
    (FOLDER/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Extract all pinned OpenRGB I2C detector names for explicit automatic-scan exclusion."""
import tarfile,re,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'.build-cache/openrgb/openrgb-1.1-source.tar.gz';files={};defines={};hashes={}
manifest=json.loads((ROOT/'vendor/openrgb-runtime/manifest.json').read_text())
expected=next(r['sha256'] for r in manifest['downloads'] if r['name']==archive.name)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
with tarfile.open(archive) as t:
 for m in t.getmembers():
  if m.isfile() and m.name.endswith(('.cpp','.h')):
   raw=t.extractfile(m).read();hashes[m.name]=hashlib.sha256(raw).hexdigest();s=raw.decode(errors='replace');files[m.name]=s
   for k,v in re.findall(r'^\s*#define\s+(\w+)\s+"([^"\n]+)"',s,re.M):defines.setdefault(k,set()).add(v)
rows=[];missing=[]
pattern=r'\bREGISTER_I2C_(?:DETECTOR|DRAM_DETECTOR|PCI_DETECTOR(?:_IP)?|PCI_DETECTOR_P)\s*\(\s*("[^"\n]+"|\w+)\s*,'
for name,s in files.items():
 if '/Controllers/' not in name:continue
 for token in re.findall(pattern,s):
  if token.startswith('"'):value=token[1:-1]
  else:
   local=dict(re.findall(r'^\s*#define\s+(\w+)\s+"([^"\n]+)"',s,re.M))
   choices={local[token]} if token in local else defines.get(token,set())
   if len(choices)!=1:missing.append([name,token]);continue
   value=next(iter(choices))
  rows.append(dict(name=value,path=name,sha256=hashes[name]))
print('names',len(set(r['name'] for r in rows)),'unresolved',missing)
(ROOT/'app/openrgb_smbus_detectors.json').write_text(json.dumps(dict(schema=1,source='OpenRGB 1.1',commit='8e16de27858cf2be6af54a33ce003df74cb9fd3e',disabled=sorted(set(r['name'] for r in rows)),unresolved=missing),indent=2)+'\n')
provenance={}
for row in rows:
 item=provenance.setdefault(row['path'],dict(sha256=row['sha256'],detectors=[]))
 if row['name'] not in item['detectors']:item['detectors'].append(row['name'])
(ROOT/'vendor/openrgb-runtime/smbus-detector-provenance.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')

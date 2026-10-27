#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fetch hash-pinned upstream runtime and sources; stage CLI dependency closure.
No hardware access. This is a separate, explicit network-enabled build step.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import urllib.error
import time

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'vendor/openrgb-runtime/manifest.json'
CACHE=ROOT/'.build-cache/openrgb'
OUTPUT=CACHE/'prepared'

def verified_download(row):
    target=CACHE/row['name']
    def valid():return target.is_file() and target.stat().st_size==row['size'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']
    if not valid():
        temporary=target.with_suffix(target.suffix+'.partial')
        try:
            for attempt in range(3):
                print('Downloading '+row['name']+' (attempt '+str(attempt+1)+'/3)',flush=True)
                try:
                    request=urllib.request.Request(row['url'],headers={'User-Agent':'HackinFX-build/2.5'})
                    with urllib.request.urlopen(request,timeout=90) as response,temporary.open('wb') as out:shutil.copyfileobj(response,out)
                    break
                except (OSError,urllib.error.URLError):
                    if attempt==2:raise
                    temporary.unlink(missing_ok=True)
                    time.sleep(2**attempt)
            if temporary.stat().st_size!=row['size'] or hashlib.sha256(temporary.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Upstream download digest mismatch: '+row['name'])
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
    return target

def prepare():
    manifest=json.loads(MANIFEST.read_text());CACHE.mkdir(parents=True,exist_ok=True)
    archives={row['name']:verified_download(row) for row in manifest['downloads']}
    shutil.rmtree(OUTPUT,ignore_errors=True);OUTPUT.mkdir()
    engine=OUTPUT/'Engine/OpenRGB.app/Contents';engine.mkdir(parents=True)
    sources=OUTPUT/'Sources';sources.mkdir()
    notices=OUTPUT/'Notices';shutil.copytree(ROOT/'vendor/openrgb-runtime',notices)
    for row in manifest['downloads']:
        if row['kind']!='source':continue
        archive=archives[row['name']];shutil.copy2(archive,sources/archive.name)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                path=Path(member.name)
                if member.isfile() and not path.is_absolute() and '..' not in path.parts and any(word in path.name.upper() for word in ('LICENSE','LICENCE','COPYING','NOTICE')):
                    target=notices/row['name']/path;target.parent.mkdir(parents=True,exist_ok=True)
                    with tar.extractfile(member) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
    with tempfile.TemporaryDirectory(prefix='hackinfx-openrgb-') as temporary:
        subprocess.run(['/usr/bin/ditto','-x','-k',str(archives['openrgb-1.1-intel.zip']),temporary],check=True)
        upstream=Path(temporary)/'OpenRGB.app/Contents'
        (engine/'MacOS').mkdir();shutil.copy2(upstream/'MacOS/OpenRGB',engine/'MacOS/OpenRGB')
        shutil.copy2(upstream/'Info.plist',engine/'Info.plist')
        frameworks=engine/'Frameworks';frameworks.mkdir()
        for name in manifest['frameworks']:
            source=upstream/'Frameworks'/name
            if source.is_dir():shutil.copytree(source,frameworks/name,symlinks=True)
            else:shutil.copy2(source,frameworks/name)
        # CLI-only: no GUI plugins, platform plugins, profiles or app plugins.
        # Every device detector present in the official macOS binary is retained.
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(OUTPUT)

if __name__=='__main__':prepare()

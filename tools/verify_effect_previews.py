#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare native gallery math against the actual Python hardware renderer kernel."""
import itertools,json,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'app'))
import effects
cases=[]
for effect,reverse,scale,index,elapsed in itertools.product(effects.CATALOG['effects'],[False,True],[.25,1,4],[0,3,19],[0,1.37,7.8]):
    palette=[list(bytes.fromhex(v)) for v in effect['palette']];u=index/19;v=(index%4)/3
    args=dict(mode=effect['id'],palette=palette,index=index,u=u,v=v,coord=u,time=elapsed,speed=65,scale=scale,density=55,reverse=reverse)
    cases.append(dict(args,expected=list(effects.sample(**args))))
with tempfile.TemporaryDirectory(prefix='hackinfx-effects-') as folder:
    folder=Path(folder);fixture=folder/'cases.json';fixture.write_text(json.dumps(cases,allow_nan=False))
    subprocess.run(['swiftc','-swift-version','5','-target','x86_64-apple-macos15.0','-module-cache-path',str(Path(tempfile.gettempdir())/'aleopho-gpurgb-swift-cache'),str(root/'app/EffectLibrary.swift'),str(root/'app/tests/EffectKernelTests.swift'),'-o',str(folder/'effect-tests')],check=True)
    subprocess.run([str(folder/'effect-tests'),str(fixture)],check=True)

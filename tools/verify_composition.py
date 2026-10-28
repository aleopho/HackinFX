#!/usr/bin/env python3
"""Hardware-free Swift/Python composition equivalence."""
import sys,json,tempfile,subprocess,itertools
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'app'))
from center_core import scene_config
import effects
cases=[]
for mode,blend,brightness,t,index in itertools.product(['static','twinkle','plasma'],['normal','screen','multiply','add'],[0,45,100],[0,1.37],[0,9,19]):
 config=scene_config(dict(mode=mode,palette=['9bed4b','0055ff'],brightness=brightness,speed=65,mapping='canvas',layers=[dict(mode='twinkle',palette=['55ffcc'],opacity=65,blend=blend),dict(mode='wave',palette=['ff5500','0000ff'],opacity=25,blend='screen')]))
 points=[dict(x=i/19,y=(i%4)/3) for i in range(20)]
 expected=effects.frame(config,20,dict(x=.5,y=.5,width=1,height=1,led_positions=points),t)[index]
 cases.append(dict(mode=mode,palette=[list(bytes.fromhex(x)) for x in config['palette']],index=index,u=points[index]['x'],v=points[index]['y'],time=t,brightness=brightness,layers=config['layers'],expected=expected))
with tempfile.TemporaryDirectory(prefix='hackinfx-composition-') as folder:
 p=Path(folder);(p/'cases.json').write_text(json.dumps(cases));exe=p/'verify'
 subprocess.run(['swiftc','-swift-version','5','-target','x86_64-apple-macos15.0','-module-cache-path','/tmp/aleopho-gpurgb-swift-cache',str(root/'app/EffectLibrary.swift'),str(root/'app/tests/CompositionKernelTests.swift'),'-o',str(exe)],check=True)
 subprocess.run([str(exe),str(p/'cases.json')],check=True)

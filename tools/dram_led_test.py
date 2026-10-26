#!/usr/bin/env python3
"""Explicit bounded Corsair RGB check. No SPD/firmware/host reset operations."""
import argparse,json,os,select,subprocess,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--fps',type=int,default=20,choices=range(1,21),help='Bounded RAM test target, default 20 FPS');parser.add_argument('--effects',action='store_true',help='Test three LED regions, then bounded mint Twinkle on all four DIMMs');parser.add_argument('--seconds',type=float,default=8,help='Twinkle test duration, 1–15 seconds');parser.add_argument('--map-seconds',type=float,default=3,help='Hold the three-region LED map for 0–5 seconds');parser.add_argument('--remaining',action='store_true',help='Apply mint once to each of the other three DIMMs; stop on first error');parser.add_argument('--address',type=lambda v:int(v,0),default=0x18,choices=range(0x18,0x1c),help='Test one verified DIMM, default 0x18');parser.add_argument('--mint',action='store_true',help='Apply one dim mint color only after exact identity and CRC validation');args=parser.parse_args()
if not 1<=args.seconds<=15 or not 0<=args.map_seconds<=5:parser.error('Test duration outside bounds')
if args.effects and (args.mint or args.remaining):parser.error('--effects is a separate bounded test')
helper=Path(__file__).with_name('HackinFX-DRAM-Diagnostic')
process=subprocess.Popen([str(helper)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,bufsize=0)
def call(value,quiet=False):
 process.stdin.write((json.dumps(value)+'\n').encode());process.stdin.flush();out=bytearray();deadline=time.monotonic()+20
 while b'\n' not in out:
  remaining=deadline-time.monotonic()
  if remaining<=0 or not select.select([process.stdout],[],[],remaining)[0]:raise RuntimeError('Helper timed out; stopped without retry')
  chunk=os.read(process.stdout.fileno(),16384)
  if not chunk:raise RuntimeError('Helper closed')
  out.extend(chunk)
  if len(out)>32768:raise RuntimeError('Unexpected response size')
 r=json.loads(out)
 if not quiet or 'error' in r:print(json.dumps(r),flush=True)
 if 'error' in r:raise RuntimeError('command=%s address=%s: %s'%(value.get('command'),hex(value['address']) if 'address' in value else 'none',r['error']))
 return r
exit_code=0
try:
 status=call({'command':'status'})
 if not status.get('driver_loaded') or status.get('controllers')!=[{'vendor_id':'8086','device_id':'7f23'}]:raise RuntimeError('Exact loaded transport unavailable')
 host=call({'command':'diagnostics'})
 if host.get('helper_revision')!='titanium-block-v3-paced':raise RuntimeError('Wrong diagnostic helper revision; no colors sent')
 if host['status']&0x40:raise RuntimeError('SMBus semaphore already owned. No forced unlock. Close other RGB tools; restart with HackinFX auto-start disabled and retry before opening it.')
 result=call({'command':'probe'});devices=result.get('devices',[])
 if not devices:raise RuntimeError('No verified Corsair RGB controller; no color command sent')
 if args.effects:
  addresses=[0x18,0x19,0x1a,0x1b]
  targets=[d for address in addresses for d in devices if d['address']==address]
  if len(targets)!=4 or {d['address'] for d in targets}!=set(addresses):raise RuntimeError('All four DIMMs must be identified before the effect test')
  if any(d.get('product_id')!='0801' or d.get('protocol')!=4 or d.get('led_count')!=12 for d in targets):raise RuntimeError('Unexpected DIMM; no effect frames sent')
  import sys
  candidates=[Path(__file__).resolve().parents[1]/'app',Path(__file__).resolve().parent/'HackinFX-GitHub/app']
  source=next((v for v in candidates if (v/'center_core.py').is_file()),None)
  if source is None:raise RuntimeError('Matching HackinFX renderer source not found; no test frames sent')
  sys.path.insert(0,str(source))
  from center_core import frame,scene_config
  scene=scene_config(dict(mode='twinkle',palette=['a7f3d0'],brightness=40,speed=65,fps=args.fps,mapping='mirror',axis='y'))
  position=dict(led_positions=[dict(x=.5,y=i/11) for i in range(12)])
  print('LED MAP: four red, four green, four blue LEDs per DIMM. Then mint Twinkle at 65% speed / 40% brightness.',flush=True)
  pattern=[[64,0,0]]*4+[[0,64,0]]*4+[[0,0,64]]*4
  for d in targets:
   print('LED MAP address 0x%02X'%d['address'],flush=True)
   call(dict(command='frame',address=d['address'],colors=pattern),quiet=True)
  print('LED map sent to all four DIMMs; holding before Twinkle.',flush=True)
  time.sleep(args.map_seconds)
  print('TWINKLE starting; target %d FPS, no retries'%args.fps,flush=True)
  started=time.monotonic();groups=0;latencies=[];skews=[]
  while time.monotonic()-started<args.seconds:
   tick=time.monotonic();pixels=[list(c) for c in frame(scene,12,position,tick-started)];completed=[]
   for d in targets:
    before=time.monotonic();call(dict(command='frame',address=d['address'],colors=pixels),quiet=True)
    now=time.monotonic();completed.append(now);latencies.append(now-before)
   skews.append(completed[-1]-completed[0]);groups+=1
   delay=1/args.fps-(time.monotonic()-tick)
   if delay>0:time.sleep(delay)
  elapsed=time.monotonic()-started
  print(json.dumps(dict(test='mint-twinkle-65',target_fps=args.fps,duration_seconds=round(elapsed,3),complete_four_dimm_frames=groups,completed_fps_per_dimm=round(groups/elapsed,2),mean_command_ms=round(sum(latencies)/len(latencies)*1000,2),max_four_dimm_completion_skew_ms=round(max(skews)*1000,2),optically_confirmed=False)),flush=True)
  for d in targets:call(dict(command='static',address=d['address'],color=[32,64,48]),quiet=True)
  print('Test complete; all four DIMMs returned to fixed mint. Confirm distinct LED regions and visible Twinkle. No continuous background process remains.',flush=True)
 elif args.mint:
  addresses=[0x19,0x1a,0x1b] if args.remaining else [args.address]
  targets=[d for address in addresses for d in devices if d['address']==address]
  if len(targets)!=len(addresses) or {d['address'] for d in targets}!=set(addresses):raise RuntimeError('Requested DIMMs not all identified; no color sent')
  if any(d.get('product_id')!='0801' or d.get('protocol')!=4 or d.get('led_count')!=12 for d in targets):raise RuntimeError('Unexpected DIMM; no colors sent')
  for d in targets:
   if d.get('product_id')!='0801' or d.get('protocol')!=4 or d.get('led_count')!=12:raise RuntimeError('Direct test requires exact Titanium 0801 / protocol 4 / 12 LEDs')
   print('Testing RGB controller 0x%02X once'%d['address'],flush=True)
   call({'command':'static','address':d['address'],'color':[32,64,48]})
  print('Mint sent once to: '+', '.join('0x%02X'%d['address'] for d in targets)+'. Confirm each visible DIMM; transport success is not optical confirmation.')
 else:print('Identity check complete; no color commands sent.')
except Exception as exc:
 exit_code=1;print('STOP:',exc,flush=True)
finally:
 process.stdin.close()
 try:process.wait(timeout=2)
 except subprocess.TimeoutExpired:process.kill();process.wait()

raise SystemExit(exit_code)

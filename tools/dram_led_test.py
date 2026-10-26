#!/usr/bin/env python3
"""Explicit bounded Corsair RGB check. No SPD/firmware/host reset operations."""
import argparse,json,os,select,subprocess,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--mint',action='store_true',help='Apply one dim mint color only after exact identity and CRC validation');args=parser.parse_args()
helper=Path(__file__).with_name('HackinFX-DRAM-Diagnostic')
process=subprocess.Popen([str(helper)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,bufsize=0)
def call(value):
 process.stdin.write((json.dumps(value)+'\n').encode());process.stdin.flush();out=bytearray();deadline=time.monotonic()+20
 while b'\n' not in out:
  remaining=deadline-time.monotonic()
  if remaining<=0 or not select.select([process.stdout],[],[],remaining)[0]:raise RuntimeError('Helper timed out; stopped without retry')
  chunk=os.read(process.stdout.fileno(),16384)
  if not chunk:raise RuntimeError('Helper closed')
  out.extend(chunk)
  if len(out)>32768:raise RuntimeError('Unexpected response size')
 r=json.loads(out);print(json.dumps(r),flush=True)
 if 'error' in r:raise RuntimeError(r['error'])
 return r
try:
 status=call({'command':'status'})
 if not status.get('driver_loaded') or status.get('controllers')!=[{'vendor_id':'8086','device_id':'7f23'}]:raise RuntimeError('Exact loaded transport unavailable')
 host=call({'command':'diagnostics'})
 if host['status']&0x40:raise RuntimeError('SMBus semaphore already owned. No forced unlock. Close other RGB tools; restart with HackinFX auto-start disabled and retry before opening it.')
 result=call({'command':'probe'});devices=result.get('devices',[])
 if not devices:raise RuntimeError('No verified Corsair RGB controller; no color command sent')
 if args.mint:
  for d in devices:
   if d.get('product_id') not in ('0800','0801','0810','0811') or d.get('led_count')!=12:raise RuntimeError('Unexpected controller; no further colors sent')
   call({'command':'static','address':d['address'],'color':[32,64,48]})
  print('Dim mint commands accepted. Confirm visible RAM LEDs; transport success is not optical confirmation.')
 else:print('Identity check complete; no color commands sent.')
except Exception as exc:print('STOP:',exc,flush=True)
finally:
 process.stdin.close()
 try:process.wait(timeout=2)
 except subprocess.TimeoutExpired:process.kill();process.wait()

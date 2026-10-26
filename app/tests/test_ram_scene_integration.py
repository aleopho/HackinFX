import tempfile
import threading
import time
import unittest
from pathlib import Path
import center_core as core
from ram_control import RAMAdapter
from test_center import FakeSDK,FakeNative,device
from test_radius_ram_keyboard import RAMTransport

class MixedRAMSceneTests(unittest.TestCase):
    def test_slow_ram_receives_12_led_frames_without_stalling_fast_devices(self):
        class SlowRAM(RAMTransport):
            def call(self,request):
                if request['command']=='frame':time.sleep(.07)
                return super().call(request)
        class FastOutput:
            name='test-fast'
            def __init__(self):self.frames=[]
            def discover(self):
                row=device();row.update(id='fast',backend=self.name,direct=True,controllable=True,category='cooler',led_count=12)
                return [row]
            def activate(self,row):pass
            def write_frame(self,row,pixels,mode):self.frames.append((time.monotonic(),pixels))
            def close(self):pass
        transport=SlowRAM(True)
        ram=RAMAdapter(transport,lambda:[dict(manufacturer='Corsair',part_number='CMP32',size='16 GB')])
        ram.probe();fast=FastOutput()
        with tempfile.TemporaryDirectory() as folder:
            center=core.Center(Path(folder)/'scenes.json',folder,sdk=FakeSDK([]),native=FakeNative(),adapters=[ram,fast])
            try:
                center.refresh(inventory=False)
                ids=[d['id'] for d in center.devices]
                center.start(dict(devices=ids,config=dict(mode='twinkle',palette=['a7f3d0'],speed=65,brightness=40,fps=30,sync_policy='adaptive')))
                time.sleep(.35);center.stop()
                writes=[r for r in transport.calls if r['command']=='frame']
                self.assertGreaterEqual(len(writes),2)
                self.assertGreater(len(fast.frames),len(writes))
                self.assertTrue(all(len(r['colors'])==12 for r in writes))
                self.assertTrue(any(len({tuple(c) for c in r['colors']})>1 for r in writes))
                self.assertFalse(center.errors)
                self.assertEqual(center.status()['sync']['clock'],'shared-monotonic')
            finally:center.close()

# SPDX-License-Identifier: GPL-2.0-or-later
import tempfile,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
import center_core as core
from test_center import FakeSDK,FakeNative,device

class SyncTests(unittest.TestCase):
 def test_parallel_outputs_receive_same_frame_time_without_queued_backlog(self):
  class Adapter:
   name='fixture'
   def __init__(self):self.calls=[];self.guard=threading.Lock();self.slow_started=threading.Event();self.overlap=False
   def discover(self):return [dict(device(i),id=str(i),backend=self.name) for i in range(2)]
   def activate(self,d):pass
   def close(self):pass
   def write_frame(self,d,colors,mode):
    with self.guard:self.calls.append((d['id'],time.monotonic()))
    if d['id']=='0':self.slow_started.set();time.sleep(.12)
    else:self.overlap=self.slow_started.wait(.5);time.sleep(.001)
  with tempfile.TemporaryDirectory() as folder:
   a=Adapter();c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK(),native=FakeNative(),adapters=[a]);c.refresh(False)
   seen=[];real=core.frame
   def capture(scene,count,pos,elapsed):seen.append(elapsed);return real(scene,count,pos,elapsed)
   with patch.object(core,'frame',side_effect=capture):
    c.start(dict(devices=['0','1'],config=dict(mode='wave',synchronized=True)));time.sleep(.24);c.stop()
   self.assertAlmostEqual(seen[0],seen[1]);self.assertTrue(a.overlap)
   self.assertGreater(c.sync_stats['dropped'],0);self.assertGreater(len([v for v in a.calls if v[0]=='1']),len([v for v in a.calls if v[0]=='0']));c.close()
 def test_canvas_rejects_independent_hardware_clocks(self):
  with tempfile.TemporaryDirectory() as folder:
   d=device();d.update(direct=False,controllable=True,static_modes=['static','breathing'])
   c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK([d]),native=FakeNative());c.refresh(False)
   with self.assertRaisesRegex(ValueError,'Canvas sync'):c.start(dict(devices=[c.devices[0]['id']],config=dict(synchronized=True)))
   c.close()
 def test_scene_restart_preserves_shared_epoch(self):
  with tempfile.TemporaryDirectory() as folder:
   c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK([device()]),native=FakeNative());c.refresh(False);epoch=c.clock_started
   for _ in range(2):c.start(dict(devices=[c.devices[0]['id']],config=dict(mode='wave')));time.sleep(.02);c.stop()
   self.assertEqual(c.clock_started,epoch);c.close()
 def test_invalid_sync_setting_is_rejected(self):
  with self.assertRaises(ValueError):core.scene_config(dict(synchronized='yes'))
if __name__=='__main__':unittest.main()

class NativeStreamingTests(unittest.TestCase):
 def test_streamed_gpu_frames_use_validated_zone_rgb_path(self):
  driver=FakeNative();adapter=core.NativeGPUAdapter(driver);pixels=[(1,2,3)]*3
  adapter.write_frame(dict(id='gpu',host_stream=True),pixels,'wave')
  self.assertEqual(driver.writes,[('gpu',pixels,'gradient')])
 def test_static_only_gpu_keeps_its_original_mode(self):
  driver=FakeNative();core.NativeGPUAdapter(driver).write_frame(dict(id='gpu'),[(1,2,3)],'static')
  self.assertEqual(driver.writes[0][2],'static')

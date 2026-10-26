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
    c.start(dict(devices=['0','1'],config=dict(mode='wave',synchronized=False)));time.sleep(.24);c.stop()
   self.assertAlmostEqual(seen[0],seen[1]);self.assertTrue(a.overlap)
   self.assertGreater(c.sync_stats['dropped'],0);self.assertGreater(len([v for v in a.calls if v[0]=='1']),len([v for v in a.calls if v[0]=='0']));c.close()
 def test_canvas_rejects_independent_hardware_clocks(self):
  with tempfile.TemporaryDirectory() as folder:
   d=device();d.update(direct=False,controllable=True,static_modes=['static','breathing'])
   c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK([d]),native=FakeNative());c.refresh(False)
   with self.assertRaisesRegex(ValueError,'Canvas sync'):c.start(dict(devices=[c.devices[0]['id']],config=dict(mode='breathing',synchronized=True)))
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

class StaticRefreshTests(unittest.TestCase):
 def test_leased_static_output_is_refreshed_but_other_static_devices_are_not(self):
  class Adapter:
   name='fixture'
   def __init__(self):self.writes=[]
   def discover(self):return [dict(device(i),id=str(i),refresh_interval=.02 if i==0 else 0) for i in range(2)]
   def activate(self,d):pass
   def close(self):pass
   def write_frame(self,d,colors,mode):self.writes.append((d['id'],colors))
  with tempfile.TemporaryDirectory() as folder:
   a=Adapter();c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK(),native=FakeNative(),adapters=[a]);c.refresh(False)
   c.start(dict(devices=['0','1'],config=dict(mode='static',palette=['ffffff'],brightness=100)));time.sleep(.18);c.stop()
   self.assertGreaterEqual(len([w for w in a.writes if w[0]=='0']),2)
   self.assertEqual(len([w for w in a.writes if w[0]=='1']),1)
   self.assertTrue(all(color==(255,255,255) for _,colors in a.writes for color in colors));c.close()

class LeasePauseTests(unittest.TestCase):
 def test_pause_keeps_static_preview_lease_alive(self):
  class Adapter:
   name='fixture'
   def __init__(self):self.calls=[]
   def discover(self):return [dict(device(),id='r',refresh_interval=.02)]
   def activate(self,d):pass
   def close(self):pass
   def write_frame(self,d,pixels,mode):self.calls.append(pixels)
  with tempfile.TemporaryDirectory() as folder:
   a=Adapter();c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK(),native=FakeNative(),adapters=[a]);c.refresh(False)
   c.start(dict(devices=['r'],config=dict(mode='static',palette=['ffffff'])));time.sleep(.07);c.pause();count=len(a.calls);time.sleep(.6)
   self.assertGreater(len(a.calls),count);self.assertFalse(c.running);c.close()

class GroupBarrierTests(unittest.TestCase):
 def test_group_never_advances_before_slowest_output_finishes(self):
  class Adapter:
   name='fixture'
   def __init__(self):self.calls=[];self.started=threading.Event();self.release=threading.Event()
   def discover(self):return [dict(device(i),id=str(i)) for i in range(2)]
   def activate(self,d):pass
   def close(self):pass
   def write_frame(self,d,pixels,mode):
    self.calls.append((d['id'],pixels))
    if d['id']=='0' and not self.started.is_set():self.started.set();self.release.wait(2)
  with tempfile.TemporaryDirectory() as folder:
   a=Adapter();c=core.Center(Path(folder)/'s.json',folder,sdk=FakeSDK(),native=FakeNative(),adapters=[a]);c.refresh(False)
   try:
    c.start(dict(devices=['0','1'],config=dict(mode='wave')))
    self.assertTrue(a.started.wait(1));time.sleep(.1)
    self.assertEqual(len(a.calls),2);self.assertEqual(a.calls[0][1],a.calls[1][1])
    a.release.set();time.sleep(.12);c.stop()
    self.assertGreaterEqual(len(a.calls),4);self.assertEqual(c.sync_stats['dropped'],0)
   finally:a.release.set();c.close()
 def test_default_mirror_ignores_device_position(self):
  scene=core.scene_config(dict(mode='wave'))
  self.assertTrue(scene['synchronized']);self.assertEqual(scene['mapping'],'mirror')
  self.assertEqual(core.frame(scene,1,dict(x=0),1),core.frame(scene,1,dict(x=.5),1))

class PresentationDelayTests(unittest.TestCase):
 def test_fast_output_waits_until_predicted_completion_window(self):
  c=object.__new__(core.Center);c.output_latencies={'fast':.02};writes=[];c.write_output=lambda *args:writes.append(args)
  event=threading.Event()
  with patch.object(core.time,'monotonic',return_value=10),patch.object(event,'wait',return_value=False) as wait:
   c.timed_output({'id':'fast'},[(1,2,3)],'wave',10.1,event)
   self.assertAlmostEqual(wait.call_args.args[0],.08);self.assertEqual(len(writes),1)

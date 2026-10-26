# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import center_core as core
from openrgb_runtime import ManagedEngine,NATIVE_DETECTORS
from test_center import FakeSDK,FakeNative,device

class StartupTests(unittest.TestCase):
    def test_mint_twinkle_65_once_and_rediscovery_does_not_reset_colors(self):
        with tempfile.TemporaryDirectory() as folder:
            sdk=FakeSDK([device()]);c=core.Center(Path(folder)/'scenes.json',folder,sdk=sdk,native=FakeNative())
            c.initialize(inventory=False);worker=c.worker
            self.assertEqual(c.scene["mode"],"twinkle");self.assertEqual(c.scene["speed"],65);self.assertEqual(c.scene["palette"],["a7f3d0"])
            c.initialize(inventory=False);self.assertIs(c.worker,worker)
            c.refresh(inventory=False);count=len(sdk.calls);self.assertFalse(c.running);self.assertEqual(len(sdk.calls),count);c.close()
    def test_one_activation_failure_does_not_block_other_devices(self):
        class Partial(FakeSDK):
            def activate(self,index):
                if index==0:raise RuntimeError('fixture failure')
                super().activate(index)
        with tempfile.TemporaryDirectory() as folder:
            a=device(0);a['id']='a';b=device(1);b['id']='b';sdk=Partial([a,b])
            c=core.Center(Path(folder)/'scenes.json',folder,sdk=sdk,native=FakeNative())
            c.initialize(inventory=False);c.worker.join(2)
            self.assertTrue(any(call[0]=='colors' and call[1]==1 for call in sdk.calls))
            self.assertFalse(c.devices[0]['controllable']);self.assertIn('fixture failure',' '.join(c.errors));c.close()
    def test_inventory_and_unconfirmed_gpu_are_never_written(self):
        with tempfile.TemporaryDirectory() as folder:
            row=device();row.update(controllable=False,status='setup-required')
            sdk=FakeSDK([row]);native=FakeNative([dict(row,backend='native',id='n',owns_gpu=True)])
            c=core.Center(Path(folder)/'scenes.json',folder,sdk=sdk,native=native)
            c.initialize(inventory=False);self.assertEqual(sdk.calls,[]);self.assertEqual(native.writes,[]);c.close()
    def test_effects_are_bounded_deterministic_and_honor_blackout(self):
        for name in ['aurora','comet','twinkle','color shift']:
            scene=core.scene_config(dict(mode=name,palette=['ff0000','00ff00','0000ff'],brightness=93))
            args=(scene,128,dict(x=.4,y=.6,width=.3),12.5)
            pixels=core.frame(*args);self.assertEqual(pixels,core.frame(*args));self.assertTrue(all(0<=v<=255 for p in pixels for v in p))
            self.assertTrue(all(p==(0,0,0) for p in core.frame(dict(scene,brightness=0),128,{},12.5)))

class RuntimeTests(unittest.TestCase):
    def test_missing_bundle_never_falls_back_to_system_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=ManagedEngine(folder,Path(folder)/'missing')
            with self.assertRaisesRegex(RuntimeError,'Bundled OpenRGB'):engine.ensure_started()
            self.assertIsNone(engine.process)
    def test_private_config_exact_native_ownership_and_no_wildcards(self):
        with tempfile.TemporaryDirectory() as folder:
            executable=Path(folder)/'OpenRGB';executable.touch();engine=ManagedEngine(folder,executable)
            class Process:
                def poll(self):return None
                def terminate(self):pass
                def wait(self,timeout):return 0
            with patch('openrgb_runtime.subprocess.Popen',return_value=Process()) as launch,patch('openrgb_runtime.socket.create_connection'):
                engine.ensure_started();args=launch.call_args.args[0]
                self.assertIn('--noautoconnect',args);self.assertEqual(args[args.index('--server-host')+1],'127.0.0.1')
                cfg=json.loads((Path(folder)/'OpenRGB.json').read_text())['Detectors']['detectors']
                self.assertTrue(set(NATIVE_DETECTORS).issubset(cfg));self.assertIn("Corsair DRAM",cfg);self.assertTrue(all(v is False for v in cfg.values()))
                engine.ensure_started();self.assertEqual(launch.call_count,1)
                engine.claim_native_ram();engine.ensure_started()
                cfg=json.loads((Path(folder)/'OpenRGB.json').read_text())['Detectors']['detectors'];self.assertFalse(cfg['Corsair DRAM']);engine.close()
if __name__=='__main__':unittest.main()

class RAMStartupExclusionTests(unittest.TestCase):
 def test_even_ready_ram_is_never_activated_on_launch(self):
  with tempfile.TemporaryDirectory() as folder:
   ram=device();ram.update(category='dram',controllable=True,direct=True)
   sdk=FakeSDK([ram]);c=core.Center(Path(folder)/'s.json',folder,sdk=sdk,native=FakeNative())
   c.initialize(False);self.assertEqual(sdk.calls,[]);self.assertFalse(c.running);c.close()

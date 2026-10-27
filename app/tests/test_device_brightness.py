import tempfile,unittest,json
from pathlib import Path
from center_core import Center
class Adapter:
    name='fixture'
    def __init__(self):self.frames=[]
    def write_frame(self,d,colors,mode):self.frames.append((d['id'],colors))
    def activate(self,d):pass
    def close(self):pass
class BrightnessTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.adapter=Adapter();self.core=Center(Path(self.folder.name)/'state.json',self.folder.name,adapters=[self.adapter]);self.a=dict(id='a',fingerprint='fp-a',name='A',backend='fixture',controllable=True,direct=True,led_count=1,static_modes=['static']);self.b=dict(self.a,id='b',fingerprint='fp-b');self.core.devices=[self.a,self.b];self.core.layout={k:dict(x=.5,y=.5,width=.2) for k in ('a','b')};self.core.restore_device_brightness(self.core.devices)
    def tearDown(self):self.core.close();self.folder.cleanup()
    def test_independent_multiplication_and_zero_is_not_active(self):
        self.core.set_device_brightness({'a':25,'b':0});self.core.write_output(self.a,[(200,100,40)],'static');self.core.write_output(self.b,[(200,100,40)],'static');self.assertEqual(self.adapter.frames,[('a',[(50,25,10)]),('b',[(0,0,0)])]);self.assertEqual(self.core.status()['active_devices'],['a'])
    def test_stable_identity_restores_and_layout_save_does_not_erase_levels(self):
        self.core.set_device_brightness({'a':35});self.core.set_layout({'a':dict(x=.3,y=.4)});restored=Center(self.core.store,self.folder.name,adapters=[Adapter()]);rows=[dict(self.a,id='new-id')];restored.restore_device_brightness(rows);self.assertEqual(restored.device_brightness['new-id'],35)
    def test_bad_batch_is_atomic(self):
        for values in ({'a':-1},{'a':101},{'a':True},{'missing':50},{'a':float('nan')},{'a':50,'missing':20}):
            with self.assertRaises(ValueError):self.core.set_device_brightness(values)
        self.assertEqual(self.core.device_brightness,{'a':100,'b':100})
    def test_repeated_write_does_not_compound_saved_frame(self):
        self.core.set_device_brightness({'a':50});self.core.write_output(self.a,[(200,0,0)],'static');self.core.write_output(self.a,self.core.leased_frames['a'],'static');self.assertEqual(self.adapter.frames[-1][1],[(100,0,0)])

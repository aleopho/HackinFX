import unittest,tempfile,json,math
from pathlib import Path
from center_core import Center,scene_config,layout_config
import effects

class Adapter:
    name='fixture'
    def __init__(self):self.frames=[]
    def write_frame(self,d,colors,mode):self.frames.append((d['id'],colors))
    def activate(self,d):pass
    def close(self):pass

class CompositionTests(unittest.TestCase):
    def render(self,**value):return effects.frame(scene_config(value),3,dict(x=.5,y=.5,width=1,height=1),1.25)
    def test_layer_blends_and_master_zero(self):
        for blend,expected in [('normal',(0,255,0)),('add',(255,255,0)),('screen',(255,255,0)),('multiply',(0,0,0))]:
            value=dict(mode='static',palette=['ff0000'],brightness=100,layers=[dict(mode='static',palette=['00ff00'],brightness=100,opacity=100,blend=blend)])
            self.assertEqual(self.render(**value),[expected]*3)
            self.assertEqual(self.render(**dict(value,brightness=0)),[(0,0,0)]*3)
    def test_layer_order_and_round_trip(self):
        a=dict(mode='static',palette=['00ff00'],opacity=100,blend='normal');b=dict(a,palette=['0000ff'])
        self.assertNotEqual(self.render(layers=[a,b]),self.render(layers=[b,a]))
        c=scene_config(dict(layers=[a,b]));self.assertEqual(scene_config(json.loads(json.dumps(c))),c)
    def test_bounded_validated_layers(self):
        for value in [dict(layers=[{}]*5),dict(layers=[dict(layers=[{}])]),dict(layers=[dict(opacity=float('nan'))]),dict(layers=[dict(blend='bogus')])]:
            with self.assertRaises(ValueError):scene_config(value)
    def test_spatial_rotation_and_mirroring_change_gradient(self):
        c=scene_config(dict(mode='gradient',palette=['000000','ffffff'],brightness=100,mapping='canvas',axis='x'))
        p=dict(x=.5,y=.5,width=1,height=1)
        base=effects.frame(c,3,p,0)
        self.assertEqual(effects.frame(c,3,dict(p,mirror_x=True),0),list(reversed(base)))
        rotated=effects.frame(c,3,dict(p,rotation=90),0)
        self.assertTrue(all(all(abs(c-128)<=1 for c in rgb) for rgb in rotated))
    def test_rotation_input_guard(self):
        for v in [dict(rotation=math.nan),dict(mirror_x=1),dict(height=0)]:
            with self.assertRaises(ValueError):layout_config(dict(x=.5,y=.5,**v))

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.adapter=Adapter();self.core=Center(Path(self.tmp.name)/'state.json',self.tmp.name,adapters=[self.adapter]);self.row=dict(id='a',fingerprint='stable',name='A',backend='fixture',controllable=True,direct=True,led_count=1,static_modes=['static']);self.core.devices=[self.row];self.core.layout={'a':dict(x=.5,y=.5,width=.2)};self.core.restore_device_brightness(self.core.devices)
    def tearDown(self):self.core.close();self.tmp.cleanup()
    def test_calibration_brightness_and_no_compounding(self):
        self.core.set_calibration({'a':dict(red=.5,green=1,blue=0,gamma=2)})
        self.core.set_device_brightness({'a':50});self.core.write_output(self.row,[(128,128,128)],'static')
        self.assertEqual(self.adapter.frames[-1][1],[(16,32,0)])
        self.core.write_output(self.row,self.core.leased_frames['a'],'static');self.assertEqual(self.adapter.frames[-1][1],[(16,32,0)])
    def test_persistence_across_other_saves_and_identity_change(self):
        self.core.set_calibration({'a':dict(red=.7,gamma=1.4)});self.core.set_layout({'a':dict(x=.2,y=.4,rotation=45,mirror_x=True)});self.core.save_scene(dict(name='Layered',config=dict(layers=[dict(mode='twinkle')])));self.core.set_device_brightness({'a':45})
        restored=Center(self.core.store,self.tmp.name,adapters=[Adapter()]);restored.restore_device_brightness([dict(self.row,id='new')]);self.assertEqual(restored.calibration['new']['red'],.7);self.assertEqual(restored.saved_layout['stable']['rotation'],45);self.assertEqual(len(restored.scenes[0]['config']['layers']),1)
    def test_invalid_batch_is_atomic(self):
        for values in [{'a':{'red':1.1}},{'a':{'gamma':True}},{'a':{},'unknown':{}}]:
            with self.assertRaises(ValueError):self.core.set_calibration(values)
        self.assertEqual(self.core.calibration['a']['red'],1)
    def test_layout_edit_preserves_clock_and_running_flag(self):
        clock=self.core.clock_started;self.core.running=True
        self.core.set_layout({'a':dict(x=.7,y=.4,rotation=30)});self.assertTrue(self.core.running);self.assertEqual(self.core.clock_started,clock)
        self.core.running=False

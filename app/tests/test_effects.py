import json
from pathlib import Path
import time
import unittest
import effects
import center_core as core

class EffectLibraryTests(unittest.TestCase):
    def test_catalog_and_curated_looks_are_complete_and_executable(self):
        catalog=effects.CATALOG
        self.assertEqual(len(catalog['effects']),41);self.assertEqual(len(catalog['looks']),82)
        self.assertEqual(len(effects.MODES),41);self.assertEqual(len({v['id'] for v in catalog['looks']}),82)
        for look in catalog['looks']:
            self.assertIn(look['effect'],effects.MODES)
            scene=core.scene_config(dict(look,mode=look['effect']))
            self.assertEqual(len(core.frame(scene,12,{},3.7)),12)
    def test_all_effects_are_deterministic_bounded_and_honor_blackout(self):
        positions=dict(x=.2,y=.7,width=.8,led_positions=[dict(x=i%4/3,y=i//4/2) for i in range(12)])
        for mode in sorted(effects.MODES):
            for scale,density,reverse in [(.25,0,False),(1,55,False),(4,100,True)]:
                scene=core.scene_config(dict(mode=mode,palette=['000000','ffc040','ffffff'],scale=scale,density=density,reverse=reverse,mapping='canvas'))
                for elapsed in [0,3.7,1000000]:
                    first=core.frame(scene,12,positions,elapsed)
                    self.assertEqual(first,core.frame(scene,12,positions,elapsed),(mode,elapsed))
                    self.assertTrue(all(type(c)is int and 0<=c<=255 for rgb in first for c in rgb),mode)
                self.assertEqual(core.frame(dict(scene,brightness=0),12,positions,2),[(0,0,0)]*12,mode)
    def test_every_animated_effect_actually_changes_over_time(self):
        for e in effects.CATALOG['effects']:
            if e['id'] in ('static','gradient'):continue
            scene=core.scene_config(dict(e,mode=e['id'],brightness=100))
            snapshots=[core.frame(scene,40,{},t) for t in [0,.37,1.83,4.13]]
            self.assertTrue(any(v!=snapshots[0] for v in snapshots[1:]),e['id'])
    def test_effects_are_not_only_renamed_copies(self):
        signatures=[]
        for mode in effects.MODES:
            scene=core.scene_config(dict(mode=mode,palette=['ff3050','10d0a0','4070ff'],brightness=100))
            signatures.append(tuple(tuple(core.frame(scene,24,{},t)) for t in [.4,1.9,4.2]))
        self.assertEqual(len(set(signatures)),41)
    def test_spatial_mapping_and_reverse_are_real_controls(self):
        scene=core.scene_config(dict(mode='spiral',palette=['ff0000','00ff00','0000ff'],mapping='canvas'))
        a=core.frame(scene,12,dict(x=.2,y=.1,width=.3),1.1)
        b=core.frame(scene,12,dict(x=.8,y=.9,width=.3),1.1)
        self.assertNotEqual(a,b)
        self.assertNotEqual(a,core.frame(dict(scene,reverse=True),12,dict(x=.2,y=.1,width=.3),1.1))
    def test_control_validation_rejects_non_finite_and_unbounded_values(self):
        for change in [dict(scale=0),dict(scale=5),dict(scale=float('nan')),dict(density=-1),dict(density=101),dict(reverse=1),dict(mode='not an effect')]:
            with self.assertRaises(ValueError):core.scene_config(change)
    def test_old_saved_scene_gets_compatible_new_defaults(self):
        scene=core.scene_config(dict(mode='twinkle',palette=['a7f3d0'],speed=65))
        self.assertEqual((scene['scale'],scene['density'],scene['reverse']),(1,55,False))
        palette=[tuple(bytes.fromhex('a7f3d0'))]
        palette=[tuple(bytes.fromhex('a7f3d0'))]
        a=effects.sample('twinkle',palette,0,.2,.2,.2,1.5,65)
        b=effects.sample('twinkle',palette,99,.2,.2,.2,1.5,65)
        self.assertEqual(a,b) # device-local LED indexing must not alter canvas output

    def test_custom_effect_controls_survive_save_and_reload(self):
        import tempfile
        from test_center import FakeSDK,FakeNative
        with tempfile.TemporaryDirectory() as folder:
            store=Path(folder)/'scenes.json';first=core.Center(store,folder,sdk=FakeSDK([]),native=FakeNative())
            config=core.scene_config(dict(mode='plasma',scale=2.3,density=77,reverse=True))
            first.save_scene(dict(name='My plasma',config=config));first.close()
            second=core.Center(store,folder,sdk=FakeSDK([]),native=FakeNative())
            self.assertEqual(second.scenes[0]['config'],config);second.close()

    def test_all_effects_share_canvas_coordinates_independent_of_device_index(self):
        for e in effects.CATALOG['effects']:
            palette=[tuple(bytes.fromhex(c)) for c in e['palette']]
            for t in (0.0,1.37,12.9):
                a=effects.sample(e['id'],palette,0,.31,.72,.31,t,65)
                b=effects.sample(e['id'],palette,86,.31,.72,.31,t,65)
                self.assertEqual(a,b,e['id'])
    def test_fireplace_is_warm_and_temporally_smooth(self):
        palette=[(255,255,255)]
        for u,v in ((.1,.2),(.5,.5),(.9,.8)):
            frames=[effects.sample('fireplace',palette,0,u,v,u,i/60,65) for i in range(600)]
            self.assertTrue(all(r>g*2 and g>=b for r,g,b in frames))
            self.assertLess(max(abs(a-b) for x,y in zip(frames,frames[1:]) for a,b in zip(x,y)),6)
    def test_keyboard_topology_is_spatial_and_preserves_rgb_payload_offsets(self):
        import makr75
        positions={(k['x'],k['y']) for k in makr75.KEYS}
        self.assertEqual(len(positions),87)
        self.assertEqual(len({k['offset'] for k in makr75.KEYS}),87)
        scene=core.scene_config(dict(mode='twinkle',palette=['9bed4b'],brightness=100))
        pixels=core.frame(scene,87,dict(led_positions=[dict(x=k['x'],y=k['y']) for k in makr75.KEYS]),3.7)
        self.assertGreater(len(set(pixels)),20)

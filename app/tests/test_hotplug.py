import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock
from center_core import Center
from hotplug import HotplugMonitor
class Adapter:
    name='native-usb'
    def __init__(self,rows):self.rows=rows;self.calls=0
    def discover(self):self.calls+=1;return self.rows
    def close(self):pass
class HotplugTests(unittest.TestCase):
    def device(self,key):return dict(id=key,fingerprint=key,name=key,backend='native-usb',category='keyboard',controllable=True,direct=True,led_count=2)
    def test_new_device_joins_existing_scene_without_ram_or_gpu_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            usb=Adapter([self.device('a'),self.device('b')]);ram=Mock();ram.name='native-ram';core=Center(Path(folder)/'scenes.json',folder,adapters=[usb,ram]);core.devices=[self.device('a')];core.selected_devices=['a'];core.running=True;core.start=Mock(return_value={});clock=core.clock_started
            core.hotplug_refresh();self.assertEqual(core.start.call_args.args[0]['devices'],['a','b']);self.assertEqual(core.clock_started,clock);ram.discover.assert_not_called();ram.probe.assert_not_called()
    def test_removed_device_disappears_and_deselected_device_stays_deselected(self):
        with tempfile.TemporaryDirectory() as folder:
            usb=Adapter([self.device('b'),self.device('c')]);core=Center(Path(folder)/'scenes.json',folder,adapters=[usb]);core.devices=[self.device('a'),self.device('b')];core.selected_devices=['a'];core.running=True;core.start=Mock(return_value={});core.hotplug_refresh();self.assertEqual([d['id'] for d in core.devices],['b','c']);self.assertEqual(core.start.call_args.args[0]['devices'],['c'])
    def test_passive_inventory_does_not_accumulate(self):
        with tempfile.TemporaryDirectory() as folder:
            record=self.device('unknown');record.update(backend='inventory',controllable=False,direct=False,discovery_adapter='native-usb');usb=Adapter([record]);core=Center(Path(folder)/'scenes.json',folder,adapters=[usb]);core.devices=[record];core.hotplug_refresh();core.hotplug_refresh();self.assertEqual(len(core.devices),1)
    def test_topology_requires_two_stable_samples_and_does_not_refresh_before_init(self):
        core=Mock();core.initialized=False;core.operation=threading.RLock();monitor=HotplugMonitor.__new__(HotplugMonitor);monitor.core=core;monitor.last=None;monitor.pending=None;monitor.repeats=0;monitor.reader=Mock(side_effect=[('a',),('b',),('b',),('b',)])
        monitor.sample();monitor.sample();monitor.sample();core.hotplug_refresh.assert_not_called();core.initialized=True;monitor.sample();core.hotplug_refresh.assert_called_once()

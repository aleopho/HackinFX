# SPDX-License-Identifier: GPL-2.0-or-later
import json,struct,unittest
from pathlib import Path
from unittest.mock import patch
import radius_protocol as radius
import asus_keyboard as keyboard
from ram_control import RAMAdapter


def table(entries):
    raw=bytearray(64);raw[:5]=bytes([2,0xa4,8,0,len(entries)])
    for i,row in enumerate(entries):raw[5+i*3:8+i*3]=bytes(row)
    return bytes(raw)
class RadiusTransport:
    def __init__(self,entries=None):self.entries=entries or [(1,22,1),(0x11,16,1)];self.calls=[];self.bad_at=None
    def exchange(self,handle,packet):
        self.calls.append(packet)
        if len(self.calls)==self.bad_at:return bytes(64)
        if packet[2]==8:return table(self.entries)
        return packet[:3]+bytes(61)
class RadiusTests(unittest.TestCase):
    def test_dynamic_zones_and_exact_complete_batch(self):
        transport=RadiusTransport();driver=radius.Radius(transport,'test');zones=driver.discover();self.assertEqual([z['count'] for z in zones],[22,16]);self.assertEqual(len(transport.calls),1)
        colors=[(i,255-i,11) for i in range(38)];driver.write(colors);reports=transport.calls[1:];self.assertEqual(len(reports),11)
        for first,count,index in [(0,22,0),(6,16,22)]:
            header=reports[first+1];self.assertEqual(header[8],2);stream=b''.join(p[4:4+p[3]] for p in reports[first+2:first+(6 if count==22 else 5)])
            self.assertEqual(len(stream),3*(2+count*3));self.assertEqual(header[4],sum(stream)&255);self.assertEqual(int.from_bytes(header[5:7],'big'),len(stream))
            rgb=bytes(v for c in colors[index:index+count] for v in c)
            for j,timestamp in enumerate((0,562,1124)):
                block=stream[j*(2+count*3):(j+1)*(2+count*3)];self.assertEqual(block,timestamp.to_bytes(2,'big')+rgb)
        old=len(transport.calls);driver.write(colors);self.assertEqual(len(transport.calls),old)
        colors[-1]=(0,1,2);driver.write(colors);self.assertEqual(len(transport.calls),old+11)
    def test_invalid_topology_fails_before_colors(self):
        for rows in [[],[(1,21,1)],[(1,22,1),(1,2,1)],[(1,22,1),(0x21,16,1)],[(1,22,1),(0x11,16,8)],[(1,22,1),(0x11,16,1),(0x12,16,2)]]:
            with self.subTest(rows=rows),self.assertRaises(radius.RadiusError):radius.topology(table(rows))
    def test_ack_loss_latches_failure_without_retry(self):
        t=RadiusTransport();d=radius.Radius(t,'test');d.discover();t.bad_at=4
        with self.assertRaises(radius.RadiusError):d.write([(1,2,3)]*38)
        before=len(t.calls)
        with self.assertRaises(radius.RadiusError):d.write([(4,5,6)]*38)
        self.assertEqual(len(t.calls),before)
    def test_validate_all_colors_before_first_write(self):
        t=RadiusTransport();d=radius.Radius(t,'test');d.discover()
        for colors in [[(1,2,3)]*37,[(1,2,3)]*37+[(0,256,0)]]:
            with self.assertRaises(radius.RadiusError):d.write(colors)
            self.assertEqual(len(t.calls),1)
    def test_recorded_pump_fixture(self):
        path=Path(__file__).resolve().parents[2]/'vendor/radius/confirmed-packets.json'
        fixture=json.loads(path.read_text());reports=radius.packets([dict(id=1,count=22,type=1)],[(0,0,255)]*22)
        self.assertEqual([r.hex() for r in reports],[r['out_hex'] for r in fixture['reports'][:6]])
    def test_only_documented_lighting_commands(self):
        reports=radius.packets(radius.topology(table([(1,22,1),(0x11,16,1)])),[(0,0,0)]*38)
        self.assertTrue(all(len(p)==64 and p[:2]==bytes([2,0xa4]) and p[2] in (0x0a,0x11,0x12) for p in reports))
class KeyboardTests(unittest.TestCase):
    def test_descriptor_drives_output_report_size(self):
        descriptor=bytes.fromhex('0602ff0901a10185017508953f910285027508953f9102c0')
        self.assertEqual(keyboard.output_reports(descriptor),{1:64,2:64})
    def test_exact_scope_name_comes_from_paired_product_id(self):
        raw=bytearray(64);raw[:5]=bytes([1,0xa0,0,1,0]);raw[5:9]=struct.pack('<HBB',0x1ab0,2,4)
        self.assertIn('Scope II 96',keyboard.paired_keyboard(raw)['name'])
        raw[7]=3;self.assertIsNone(keyboard.paired_keyboard(raw))
    def test_no_guessed_model_from_unknown_product(self):
        raw=bytearray(64);raw[:5]=bytes([1,0xa0,0,1,0]);raw[5:9]=struct.pack('<HBB',0x7777,2,4);self.assertIsNone(keyboard.paired_keyboard(raw))
    def test_only_transient_asus_lighting_effects(self):
        for mode,value in [('static',0),('breathing',1),('spectrum',2)]:
            packet=keyboard.effect_packet(mode,(1,2,3));self.assertEqual(len(packet),64);self.assertEqual(packet[:7],bytes([2,0x51,0x2c,value,0,30,100]));self.assertEqual(packet[9:13],bytes([2,1,2,3]));self.assertNotEqual(packet[1],0x50)
        with self.assertRaises(ValueError):keyboard.effect_packet('wave',(1,2,3))
    def test_wired_keyboard_uses_report_zero_and_65_byte_hidapi_shape(self):
        packet=keyboard.effect_packet('static',(1,2,3),report_id=0,length=65)
        self.assertEqual(len(packet),65);self.assertEqual(packet[:3],bytes([0,0x51,0x2c]))
        descriptor=bytes.fromhex('0600ff0901a1010903750895409102c0')
        self.assertEqual(keyboard.output_reports(descriptor),{0:65})
    def test_asleep_keyboard_cannot_become_ready(self):
        class Fake:
            def exchange(self,*args):return bytes([2,0x12,0x12])+bytes(61)
        import base64
        row=dict(handle='test',product_id=0x1ace,descriptor=base64.b64encode(bytes.fromhex('85027508953f9102')).decode())
        with self.assertRaises(ValueError):keyboard.discover(Fake(),row)
class RAMTransport:
    def __init__(self,loaded=False,host='7f23'):self.calls=[];self.loaded=loaded;self.host=host;self.rows=[dict(address=0x18,name='Corsair Dominator Titanium RGB DDR5',led_count=12,protocol=4,product_id='0800')]
    def call(self,request):
        self.calls.append(request)
        if request['command']=='status':return dict(driver_loaded=self.loaded,controllers=[dict(vendor_id='8086',device_id=self.host)])
        if request['command']=='probe':return dict(devices=self.rows)
        return dict(sent=True)
    def close(self):pass
class RAMTests(unittest.TestCase):
    def make(self,t,part='CMP32GX5M2B6000Z30'):
        return RAMAdapter(t,lambda:[dict(manufacturer='Corsair',part_number=part,size='16 GB')])
    def test_discovery_never_opens_or_probes_bus(self):
        t=RAMTransport();rows=self.make(t).discover();self.assertEqual(t.calls,[dict(command='status')]);self.assertEqual(rows[0]['status'],'driver-required');self.assertFalse(rows[0]['controllable'])
    def test_driver_missing_fails_before_any_bus_request(self):
        t=RAMTransport()
        with self.assertRaises(ValueError):self.make(t).probe()
        self.assertTrue(all(c['command']=='status' for c in t.calls))
    def test_exact_host_and_family_gates(self):
        for t,part in [(RAMTransport(True,'1234'),'CMP32GX5M2B6000Z30'),(RAMTransport(True),'UNKNOWN')]:
            with self.assertRaises(ValueError):self.make(t,part).probe()
            self.assertFalse(any(c['command']=='probe' for c in t.calls))
    def test_helper_identity_must_match_before_static(self):
        t=RAMTransport(True);a=self.make(t);row=a.probe()[0];self.assertFalse(row['direct']);self.assertEqual(row['static_modes'],['static']);a.activate(row);a.write_frame(row,[(1,2,3)],'static');self.assertEqual(t.calls[-1],dict(command='static',address=0x18,color=[1,2,3]))
        with self.assertRaises(ValueError):a.write_frame(row,[(1,2,3)],'wave')
    def test_unexpected_controller_or_duplicate_rejected(self):
        for rows in [[dict(address=0x50,product_id='0800',led_count=12)],[dict(address=0x18,product_id='ffff',led_count=12)]]:
            t=RAMTransport(True);t.rows=rows
            with self.assertRaises(ValueError):self.make(t).probe()
    def test_driver_loss_invalidates_ready_targets(self):
        t=RAMTransport(True);a=self.make(t);a.probe();t.loaded=False
        self.assertFalse(a.discover()[0]['controllable']);self.assertFalse(a.allowed)
if __name__=='__main__':unittest.main()

class NativeIntegrationTests(unittest.TestCase):
    def test_radius_native_adapter_discovers_pump_and_fans_before_color(self):
        from usb_devices import NativeUSBAdapter
        class Transport(RadiusTransport):
            def inventory(self):return dict(devices=[dict(handle='radius',physical_id='usb-radius',vendor_id=0x36bc,product_id=0x1003,usage_page=0xff00,usage=1,interface=0,name='Radius',vendor='Fractal',transport='USB')],usb=[])
            def close(self):pass
        t=Transport();a=NativeUSBAdapter(t);row=a.discover()[0];self.assertEqual(row['name'],'Fractal Design Radius');self.assertEqual(row['led_count'],38);self.assertEqual([z['led_count'] for z in row['zones']],[22,16]);self.assertEqual(len(t.calls),1)
        a.activate(row);a.write_frame(row,[(3,2,1)]*38,'wave');self.assertEqual(len(t.calls),12)
    def test_wired_asus_replaces_its_lamparray_interface(self):
        import base64
        from usb_devices import NativeUSBAdapter
        class Transport:
            def __init__(self):self.calls=[]
            def inventory(self):
                row=dict(handle='kbd',physical_id='usb-kbd',vendor_id=0x0b05,product_id=0x1aae,usage_page=0xff00,usage=1,interface=1,name='ROG STRIX SCOPE II 96 WIRELESS',vendor='ASUS',descriptor=base64.b64encode(bytes.fromhex('0600ff0901a1010903750895409102c0')).decode())
                return dict(devices=[row,dict(row,handle='lamp',usage_page=0x59)],usb=[])
            def exchange(self,handle,packet):self.calls.append(packet);return bytes([0,0x12,0x12,1])+bytes(61)
            def send(self,handle,packet,feature=False):self.calls.append(packet)
            def close(self):pass
        t=Transport();a=NativeUSBAdapter(t);rows=a.discover();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['driver'],'asus-keyboard');self.assertIn('Scope II 96',rows[0]['name']);self.assertTrue(rows[0]['direct'])
        a.activate(rows[0]);a.write_frame(rows[0],[(1,2,3)],'static');self.assertEqual(t.calls[-1][0],0);self.assertEqual(len(t.calls[-1]),65)
    def test_radius_failure_cannot_hide_behind_previous_frame_dedup(self):
        t=RadiusTransport();d=radius.Radius(t,'test');d.discover();a=[(1,2,3)]*38;d.write(a);t.bad_at=len(t.calls)+1
        with self.assertRaises(radius.RadiusError):d.write([(4,5,6)]*38)
        with self.assertRaises(radius.RadiusError):d.write(a)

class RadiusLeaseTests(unittest.TestCase):
 def test_unchanged_white_is_renewed_after_lease_window(self):
  from unittest.mock import patch
  t=RadiusTransport();r=radius.Radius(t,'test');r.discover()
  with patch.object(radius.time,'monotonic',return_value=10):r.write([(255,255,255)]*38)
  count=len(t.calls)
  with patch.object(radius.time,'monotonic',return_value=10.1):r.write([(255,255,255)]*38)
  self.assertEqual(len(t.calls),count)
  with patch.object(radius.time,'monotonic',return_value=10.6):r.write([(255,255,255)]*38)
  self.assertGreater(len(t.calls),count)

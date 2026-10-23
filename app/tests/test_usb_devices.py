# SPDX-License-Identifier: GPL-2.0-or-later
import base64,copy,json,struct,unittest
from pathlib import Path
from unittest.mock import patch
import usb_devices as usb

# Public HID LampArray standard descriptor shape, as exposed by both tested host collections.
DESCRIPTOR=base64.b64decode('BVkJAaEBhQEJAqECCQMVACf//wAAdRCVAbEDCQQJBQkGCQcJCBUAJ////391IJUFsQPAhQIJIKECCSEVACf//wAAdRCVAbECwIUDCSKhAgkhFQAn//8AAHUQlQGxAgkjCSQJJQknCSYVACf///9/dSCVBbECCSgJKQkqCSsJLAktFQAm/wB1CJUGsQLAhQQJUKECCQMJVRUAJQh1CJUCsQIJIRUAJ///AAB1EJUIsQIJUQlSCVMJVAlRCVIJUwlUCVEJUglTCVQJUQlSCVMJVAlRCVIJUwlUCVEJUglTCVQJUQlSCVMJVAlRCVIJUwlUFQAm/wB1CJUgsQLAhQUJYKECCVUVACUIdQiVAbECCWEJYhUAJ///AAB1EJUCsQIJUQlSCVMJVBUAJv8AdQiVBLECwIUGCXChAglxFQAlAXUIlQGxAsDA')

def record(handle='1',physical='physical',vid=0x0b05,pid=0x1ace,page=0x59,usage=1,name='ROG OMNI RECEIVER'):
    return dict(handle=handle,physical_id=physical,vendor_id=vid,product_id=pid,usage_page=page,usage=usage,name=name,vendor='ASUS',transport='USB',descriptor=base64.b64encode(DESCRIPTOR).decode())
class Transport:
    def __init__(self,rows=None,count=9):self.rows=rows or [record()];self.sent=[];self.reads=[];self.index=0;self.count=count;self.denied=False;self.programmable=True
    def inventory(self):return dict(devices=copy.deepcopy(self.rows),usb=[])
    def get(self,handle,report):
        self.reads.append((handle,dict(report)))
        if self.denied:raise usb.HIDError('macOS denied HID lighting access')
        if report['id']==1:return struct.pack('<BH5I',1,self.count,100,100,10,1,100000)
        raw=bytearray(29);raw[0]=3;struct.pack_into('<H',raw,1,self.index);raw[23:27]=bytes([255]*4);raw[27]=int(self.programmable);return bytes(raw)
    def send(self,handle,packet,feature=False):
        self.sent.append((handle,packet,feature))
        if packet[0]==2:self.index=struct.unpack_from('<H',packet,1)[0]
    def check(self,handle):
        if self.denied:raise usb.HIDError('macOS denied HID lighting access')
    def close(self):pass
class USBTests(unittest.TestCase):
    def test_descriptor_maps_report_ids_and_sizes(self):
        reports=usb.lamp_descriptor(DESCRIPTOR)
        self.assertEqual(reports[2],dict(id=1,size=23));self.assertEqual(reports[0x50],dict(id=4,size=51))
    def test_malformed_or_unrecognized_layout_fails_closed(self):
        for raw in (b'',DESCRIPTOR[:-1],b'\xfe\0\0',DESCRIPTOR.replace(b'\x95\x08',b'\x95\x09')):
            with self.subTest(raw=raw[:4]):
                with self.assertRaises(usb.HIDError):usb.lamp_descriptor(raw)
    def test_discovery_reads_metadata_without_changing_lighting(self):
        transport=Transport();adapter=usb.NativeUSBAdapter(transport)
        rows=adapter.discover();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['category'],'keyboard');self.assertTrue(rows[0]['direct']);self.assertEqual(rows[0]['led_count'],9);self.assertEqual(transport.sent,[])
    def test_access_failure_preserves_visible_device_and_disables_control(self):
        transport=Transport([record(),record('2',page=1,usage=6)]);transport.denied=True
        rows=usb.NativeUSBAdapter(transport).discover();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'access-required');self.assertEqual(rows[0]['category'],'keyboard');self.assertFalse(rows[0]['controllable']);self.assertEqual(transport.sent,[])
    def test_multicollection_unknown_keyboard_is_inventoried_once(self):
        transport=Transport([record('1',pid=123,page=1,usage=6,name='Unknown keyboard'),record('2',pid=123,page=0xff00)])
        rows=usb.NativeUSBAdapter(transport).discover();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['category'],'keyboard');self.assertFalse(rows[0]['controllable'])
    def test_lamp_frames_include_exact_ids_chunk_counts_commit_and_rgb(self):
        transport=Transport();adapter=usb.NativeUSBAdapter(transport);device=adapter.discover()[0];adapter.activate(device);transport.sent=[]
        adapter.write_frame(device,[(1,2,3)]*9,'static');packets=[p for _,p,_ in transport.sent]
        self.assertEqual(len(packets),2);self.assertEqual(packets[0][:3],bytes([4,8,0]));self.assertEqual(packets[1][:3],bytes([4,1,1]));self.assertEqual(struct.unpack_from('<H',packets[1],3)[0],8);self.assertEqual(packets[0][19:23],bytes([1,2,3,255]));self.assertTrue(all(feature for _,_,feature in transport.sent))
    def test_lamp_respects_hardware_minimum_interval(self):
        transport=Transport();adapter=usb.NativeUSBAdapter(transport);device=adapter.discover()[0];adapter.activate(device);transport.sent=[]
        with patch.object(usb.time,'monotonic',side_effect=[1,1.05,1.11]):
            for _ in range(3):adapter.write_frame(device,[(1,2,3)]*9,'wave')
        self.assertEqual(len(transport.sent),4)
    def test_unprogrammable_metadata_never_claims_autonomous_control(self):
        transport=Transport();transport.programmable=False;adapter=usb.NativeUSBAdapter(transport);device=adapter.discover()[0]
        with self.assertRaises(usb.HIDError):adapter.activate(device)
        self.assertFalse(any(packet==bytes([6,0]) for _,packet,_ in transport.sent))
    def test_release_returns_lamp_autonomous_mode(self):
        transport=Transport();adapter=usb.NativeUSBAdapter(transport);device=adapter.discover()[0];adapter.activate(device);adapter.close()
        self.assertEqual(transport.sent[-1],('1',bytes([6,1]),True))
    def test_large_or_zero_lamp_count_cannot_become_controllable(self):
        for count in (0,513):
            rows=usb.NativeUSBAdapter(Transport(count=count)).discover();self.assertFalse(rows[0]['controllable'])
    def test_spatha_exact_transport_and_packets(self):
        transport=Transport([record(pid=0x1979,page=0xff01,name='ROG SPATHA X'),record('2',pid=0x1979,page=1,usage=2)])
        adapter=usb.NativeUSBAdapter(transport);device=adapter.discover()[0];self.assertEqual(device['driver'],'asus-spatha');self.assertEqual(device['category'],'mouse');self.assertFalse(device['direct']);self.assertEqual(transport.sent,[])
        adapter.activate(device);adapter.write_frame(device,[(10,20,30)]*3,'gradient')
        self.assertEqual(len(transport.sent),3)
        for zone,(_,packet,feature) in enumerate(transport.sent):
            self.assertFalse(feature);self.assertEqual(len(packet),65);self.assertEqual(packet[:10],bytes([0,0x51,0x28,zone,0,0,100,10,20,30]));self.assertNotEqual(packet[1],0x50)
    def test_wrong_asus_product_never_inherits_spatha_protocol(self):
        rows=usb.NativeUSBAdapter(Transport([record(pid=0x1234,page=0xff01)])).discover();self.assertTrue(all(not d['controllable'] for d in rows))
    def test_kraken_only_lighting_command_no_pump_or_fan_packets(self):
        packets=usb.kraken_packets([(10,20,30)]*9);self.assertEqual(len(packets),2)
        self.assertTrue(all(p[:2]==bytes([2,0x4c]) and len(p)==64 for p in packets));self.assertEqual(packets[0][5:8],bytes([20,10,30]));self.assertEqual(packets[1][5:8],bytes([10,20,30]))
    def test_catalog_contains_keyboard_mouse_cooling_and_mainboard_identities(self):
        catalog=usb.Catalog();self.assertGreater(len(catalog.entries),1000)
        self.assertTrue(any('Scope II 96' in r['name'] for r in catalog.match(0x0b05,0x1aae)))
        self.assertTrue(any('Spatha X' in r['name'] for r in catalog.match(0x0b05,0x1979)))
        self.assertTrue(catalog.match(0x1e71,0x170e));self.assertTrue(catalog.match(0x048d,0x5711))
    def test_catalog_match_alone_never_grants_write_capability(self):
        rows=usb.NativeUSBAdapter(Transport([record(vid=0x048d,pid=0x5711,page=0xff89,name='GIGABYTE Device')])).discover();self.assertEqual(rows[0]['status'],'catalog-match');self.assertFalse(rows[0]['controllable'])
if __name__=='__main__':unittest.main()

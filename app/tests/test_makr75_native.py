# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unittest.mock import patch
import makr75,usb_devices
class Transport:
    def __init__(self,version=(7,11,104),error=False):self.calls=[];self.version=version;self.error=error
    def inventory(self):
        return dict(devices=[dict(handle='lighting',physical_id='makr',vendor_id=0x1b1c,product_id=0x2b04,interface=1,usage_page=0xff42,usage=1,name='CORSAIR MAKR 75 RGB Gaming Keyboard',vendor='Corsair')],usb=[])
    def close(self):pass
    def exchange(self,handle,p):
        self.calls.append(p);reply=bytearray(512);reply[1]=p[2]
        if p[2:4]==bytes([2,0x13]):reply[3:7]=bytes([self.version[0],self.version[1],self.version[2]&255,self.version[2]>>8])
        if self.error and p[2]==6:reply[2]=1
        return bytes(reply)
class Makr75NativeTests(unittest.TestCase):
    def test_discovery_only_queries_firmware_and_exposes_individual_keys(self):
        t=Transport();a=usb_devices.NativeUSBAdapter(t);row=a.discover()[0]
        self.assertEqual([p[2:4] for p in t.calls],[bytes([2,0x13])]);self.assertTrue(row['direct']);self.assertEqual(row['led_count'],87);self.assertEqual(len(row['led_positions']),87)
        with patch('makr75.time.sleep'):a.activate(row)
        a.write_frame(row,[(i,0,255-i) for i in range(87)],'twinkle')
        p=t.calls[-1]
        for i,key in enumerate(makr75.KEYS):self.assertEqual(p[10+key['offset']:13+key['offset']],bytes([i,0,255-i]))
        a.release();self.assertEqual(t.calls[-1][:6],bytes([0,8,1,3,0,1]))
    def test_unknown_firmware_is_inventory_only_and_no_mode_write(self):
        t=Transport(version=(8,0,1));row=usb_devices.NativeUSBAdapter(t).discover()[0]
        self.assertFalse(row['controllable']);self.assertEqual(len(t.calls),1)
    def test_rgb_error_disables_session_and_never_retries_frame(self):
        t=Transport(error=True);c=makr75.Controller(t,'lighting');c.discover()
        with patch('makr75.time.sleep'):c.activate()
        with self.assertRaises(ValueError):c.write([(1,2,3)]*87)
        count=len(t.calls)
        with self.assertRaises(ValueError):c.write([(1,2,3)]*87)
        self.assertEqual(len(t.calls),count);c.release()
    def test_wrong_interface_never_receives_queries(self):
        t=Transport();inventory=t.inventory();inventory['devices'][0]['interface']=2
        t.inventory=lambda:inventory
        row=usb_devices.NativeUSBAdapter(t).discover()[0];self.assertFalse(row['controllable']);self.assertEqual(t.calls,[])

    def test_static_keyboard_renews_documented_software_mode_lease(self):
        t=Transport();c=makr75.Controller(t,'lighting');c.discover()
        with patch('makr75.time.sleep'):c.activate()
        c.last_keepalive=-100
        c.write([(10,20,30)]*87)
        self.assertEqual(t.calls[-2][:3],bytes([0,8,0x12]));self.assertEqual(t.calls[-1][2],6)
        c.release()

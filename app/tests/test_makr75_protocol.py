# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'tools/makr75_protocol.py'
s=importlib.util.spec_from_file_location('makr75_protocol',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Makr75Packets(unittest.TestCase):
    def test_read_only_query_has_no_configuration_payload(self):
        packet=m.firmware_query();self.assertEqual(len(packet),513);self.assertEqual(packet[:4],bytes([0,8,2,0x13]));self.assertEqual(set(packet[4:]),{0})
    def test_per_key_map_preserves_sparse_rgb_addresses(self):
        layout=m.key_layout();self.assertEqual(len(layout),81)
        colors=[(i,255-i,34) for i in range(len(layout))];packet=m.color_packet(colors)
        self.assertEqual(len(packet),513);self.assertEqual(packet[:10],bytes([0,8,6,1,0xb8,1,0,0,0x12,0]))
        for key,color in zip(layout,colors):self.assertEqual(packet[10+key['offset']:13+key['offset']],bytes(color))
        self.assertEqual(packet[10+420:10+440],bytes(20))
    def test_rejects_partial_or_invalid_frames(self):
        with self.assertRaises(ValueError):m.color_packet([(1,2,3)])
        with self.assertRaises(ValueError):m.color_packet([(256,0,0)]*81)

    def test_observed_firmware_and_negative_acknowledgements(self):
        reply=bytes.fromhex('000200070b6800')+bytes(505)
        self.assertEqual(m.firmware_version(reply),'7.11.104')
        for bad in [reply[:16],bytes([0,2,1])+bytes(509),bytes([0,6,0])+bytes(509)]:
            with self.assertRaises(ValueError):m.firmware_version(bad)

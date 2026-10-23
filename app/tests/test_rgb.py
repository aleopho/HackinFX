import ctypes as C
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_probe import Fake, p
sys.modules['probe'] = p
import rgb


class RGBFake(Fake):
    def __init__(self, flags=17, write_error=False, table_error=False):
        super().__init__()
        self.flags, self.write_error, self.table_error = flags, write_error, table_error
        self.writes = []

    def __call__(self, esc, data):
        if isinstance(data, p.Control) and data.cmd in (0x402c0104, 0x402c0102):
            self.calls.append((esc, data.cmd))
            data.status = 0
            if data.cmd == 0x402c0104:
                if self.table_error:
                    data.status = 0x56
                else:
                    table = rgb.Table.from_address(data.params)
                    table.count = 1
                    table.entries[0].address = 0x60
                    table.entries[0].port = 1
            else:
                req = rgb.Indexed.from_address(data.params)
                self.writes.append((bytes(req), C.string_at(req.message, req.length)))
                if self.write_error:
                    data.status = 0x56
            return 0, C.sizeof(data)
        result = super().__call__(esc, data)
        if isinstance(data, p.Control) and data.cmd == 0x402c0101:
            ports = (C.c_uint8 * 16).from_address(data.params)
            ports[1] = self.flags
        return result


class RGBTests(unittest.TestCase):
    def test_abi(self):
        rgb.check_abi()
        self.assertEqual(rgb.Indexed.address.offset, 2)
        self.assertEqual(rgb.Indexed.index_length.offset, 8)
        self.assertEqual(rgb.Indexed.length.offset, 16)

    def test_default_only_queries_metadata(self):
        fake, report = RGBFake(), {}
        rgb.RGB(fake, report).run()
        self.assertEqual(fake.writes, [])
        self.assertEqual(report['dcb_devices'][0]['address'], 0x60)
        self.assertEqual(fake.calls[-1][0], 0x29)

    def test_single_write_wire_format(self):
        import struct
        fake, report = RGBFake(), {}
        rgb.RGB(fake, report, port=1, apply=True).run()
        self.assertEqual(len(fake.writes), 1)
        wire, payload = fake.writes[0]
        self.assertEqual(wire[:20], struct.pack('<BBHII4sI', 1, 1, 0xc0, 0, 1, b'\x02\0\0\0', 7))
        self.assertEqual(payload, b'\x06\xff\0\0\x20\0\0')
        self.assertTrue(report['write_completed'])
        self.assertEqual(fake.calls[-1][0], 0x29)

    def test_unsafe_ports_rejected_without_write(self):
        for flags in (0, 1, 16, 23):
            fake = RGBFake(flags=flags)
            with self.assertRaises(p.ProbeError):
                rgb.RGB(fake, {}, port=1, apply=True).run()
            self.assertEqual(fake.writes, [])
            self.assertEqual(fake.calls[-1][0], 0x29)

    def test_write_failure_no_retry_and_cleanup(self):
        fake, report = RGBFake(write_error=True), {}
        with self.assertRaises(p.ProbeError):
            rgb.RGB(fake, report, port=1, apply=True).run()
        self.assertEqual(len(fake.writes), 1)
        self.assertNotIn('write_completed', report)
        self.assertEqual(fake.calls[-1][0], 0x29)

    def test_table_failure_prevents_write(self):
        fake = RGBFake(table_error=True)
        with self.assertRaises(p.ProbeError):
            rgb.RGB(fake, {}, port=1, apply=True).run()
        self.assertEqual(fake.writes, [])
        self.assertEqual(fake.calls[-1][0], 0x29)

    def test_bad_input_rejected(self):
        for kwargs in ({'port': 3}, {'led': 3}, {'color': (256, 0, 0)}):
            with self.assertRaises(p.ProbeError):
                rgb.RGB(RGBFake(), {}, **kwargs)

    def test_all_leds_bounded_to_three_packets(self):
        fake, report = RGBFake(), {}
        rgb.RGB(fake, report, port=1, led='all', apply=True).run()
        self.assertEqual([data[1][2] for data in fake.writes], [0, 1, 2])
        self.assertEqual(report['i2c_transactions_attempted'], 3)
        self.assertEqual(report['writes_completed'], 3)

    def test_all_leds_stop_on_first_failure(self):
        fake, report = RGBFake(write_error=True), {}
        with self.assertRaises(p.ProbeError):
            rgb.RGB(fake, report, port=1, led='all', apply=True).run()
        self.assertEqual(len(fake.writes), 1)
        self.assertEqual(report['writes_completed'], 0)
        self.assertEqual(fake.calls[-1][0], 0x29)

    def test_effect_wire_packets(self):
        self.assertEqual(rgb.effect_packets('cycle', (0, 0, 0), 'all', 0, 128), [(3,128,178,0,170,0,0)])
        self.assertEqual(rgb.effect_packets('wave', (0, 0, 0), 'all', 100, 255), [(4,255,0,0,170,0,0)])
        self.assertEqual(rgb.effect_packets('breath', (255,128,0), 'all', 100, 128), [(2,255,0,1,128,64,0)])
        self.assertEqual(rgb.effect_packets('off', (0,0,0), 'all'), [(0,)*7])

    def test_gradient_preserves_zone_order_and_scales(self):
        colors = ((255,0,0),(0,255,0),(0,0,255))
        self.assertEqual(rgb.effect_packets('gradient', (0,0,0), 'all', brightness=128, colors=colors),
                         [(6,255,0,0,128,0,0), (6,255,1,0,0,128,0), (6,255,2,0,0,0,128)])

    def test_hardware_effect_sends_one_packet(self):
        fake, report = RGBFake(), {}
        rgb.RGB(fake, report, port=1, apply=True, effect='wave').run()
        self.assertEqual(len(fake.writes), 1)
        self.assertEqual(fake.writes[0][1][0], 4)

    def test_invalid_effects_rejected_before_transport(self):
        for kwargs in ({'effect':'unknown'}, {'speed':101}, {'brightness':-1}, {'effect':'gradient'}):
            fake = RGBFake()
            with self.assertRaises(p.ProbeError):
                rgb.RGB(fake, {}, **kwargs)
            self.assertEqual(fake.calls, [])

    def test_profile_rejects_unverified_subsystems(self):
        import profiles
        device = dict(zip(('vendor-id','device-id','subsystem-vendor-id','subsystem-id'), (0x10de,0x2704,0x196e,0x13bc)))
        self.assertEqual(profiles.select([device]).port, 1)
        with self.assertRaises(ValueError):
            profiles.select([dict(device, **{'subsystem-id': 0})])
        with self.assertRaises(ValueError):
            profiles.select([device,device])

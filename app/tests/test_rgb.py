import ctypes as C
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_probe import Fake, p
sys.modules['probe'] = p
import rgb


class RGBFake(Fake):
    def __init__(self, flags=17, write_error=False, table_error=False, aura_magic=(0x15,0x89)):
        super().__init__()
        self.flags, self.write_error, self.table_error = flags, write_error, table_error
        self.writes = []
        self.aura_magic = aura_magic
        self.reads = []

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
                if not req.write:
                    self.reads.append(req.index[0])
                    if req.index_length == 0:
                        if self.write_error: data.status = 0x56
                        return 0, C.sizeof(data)
                    (rgb.U8 * 1).from_address(req.message)[0] = self.aura_magic[req.index[0]-0x20]
                    return 0, C.sizeof(data)
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


    def test_exact_pny_family_can_enter_test_without_claiming_user_verification(self):
        import profiles
        self.assertGreater(len(profiles.PROFILES), 1)
        device = dict(zip(('vendor-id','device-id','subsystem-vendor-id','subsystem-id'), (0x10de,0x2684,0x196e,0x13ae)))
        profile = profiles.select([device])
        self.assertEqual(profile.address, 0x60)
        self.assertEqual(profile.register, 2)
        self.assertEqual(profile.port, 1)
        self.assertIn('4090', profile.name)

    def test_other_nvidia_controller_does_not_inherit_pny_packets(self):
        import profiles
        device = dict(zip(('vendor-id','device-id','subsystem-vendor-id','subsystem-id'), (0x10de,0x1b80,0x3842,0x6286)))
        profile = profiles.select([device])
        self.assertEqual(profile.controller, 'EVGAPascalGPUController')
        self.assertEqual(rgb.controller_transactions(profile,'static',(255,128,0),'all',brightness=128),[(0x49,9,(128,)),(0x49,10,(64,)),(0x49,11,(0,)),(0x49,12,(1,))])
        with self.assertRaises(p.ProbeError):
            rgb.controller_transactions(profile,'wave',(255,0,0),'all')


    def test_evga_wire_uses_evga_address_and_stops_on_error(self):
        import profiles
        profile = next(profile for profile in profiles.PROFILES if profile.controller == 'EVGAPascalGPUController')
        fake, report = RGBFake(), {}
        rgb.RGB(fake,report,port=1,apply=True,color=(255,0,0),profile=profile).run()
        self.assertEqual(len(fake.writes),4)
        requests = [rgb.Indexed.from_buffer_copy(wire) for wire,payload in fake.writes]
        self.assertEqual([request.address for request in requests],[0x92]*4)
        self.assertEqual([request.index[0] for request in requests],[9,10,11,12])
        self.assertEqual([request.length for request in requests],[1]*4)
        fake = RGBFake(write_error=True)
        with self.assertRaises(p.ProbeError):
            rgb.RGB(fake,{},port=1,apply=True,profile=profile).run()
        self.assertEqual(len(fake.writes),1)

    def test_evga_hardware_modes_never_save_flash(self):
        import profiles
        profile = next(profile for profile in profiles.PROFILES if profile.controller == 'EVGAPascalGPUController')
        self.assertEqual(rgb.controller_transactions(profile,'cycle',(0,0,0),'all'),[(0x49,12,(2,))])
        self.assertEqual(rgb.controller_transactions(profile,'off',(0,0,0),'all'),[(0x49,12,(0,))])
        self.assertNotIn(0x23,[register for _,register,_ in rgb.controller_transactions(profile,'breath',(4,5,6),'all')])


    def test_asus_requires_signature_before_any_lighting_write(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'AsusAuraGPUController')
        fake, report = RGBFake(aura_magic=(0,0)), {}
        with self.assertRaisesRegex(p.ProbeError,'signature mismatch'):
            rgb.RGB(fake,report,port=1,apply=True,profile=profile).run()
        self.assertEqual(fake.reads,[0x20,0x21])
        self.assertEqual(fake.writes,[])
        self.assertEqual(report['i2c_transactions_attempted'],2)

    def test_asus_signature_then_volatile_rgb_and_mode(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'AsusAuraGPUController')
        fake, report = RGBFake(), {}
        rgb.RGB(fake,report,port=1,apply=True,profile=profile,effect='breath').run()
        self.assertEqual(fake.reads,[0x20,0x21])
        self.assertEqual([rgb.Indexed.from_buffer_copy(w).index[0] for w,p in fake.writes],[4,5,6,7])
        self.assertEqual(fake.writes[-1][1],b'\x02')
        self.assertEqual(report['i2c_transactions_attempted'],6)

    def test_asus_off_is_black_static_never_flash_save(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'AsusAuraGPUController')
        packets=rgb.controller_transactions(profile,'off',(255,255,255),'all')
        self.assertEqual(packets,[(0x29,4,(0,)),(0x29,5,(0,)),(0x29,6,(0,)),(0x29,7,(1,))])


    def test_turing_unlock_apply_and_relock_omit_flash_commands(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'EVGATuringGPUController')
        plans=rgb.controller_transactions(profile,'static',(255,128,0),'all',brightness=128)
        self.assertEqual([(r,p[0]) for _,r,p in plans[:4]],[(14,229),(14,233),(14,245),(14,249)])
        self.assertEqual([(r,p[0]) for _,r,p in plans[-3:]],[(8,1),(14,240),(14,224)])
        self.assertEqual([(r,p[0]) for _,r,p in plans[5:9]],[(108,255),(109,128),(110,0),(111,50)])
        self.assertFalse(any(r in (0x1f,0x23) for _,r,_ in plans))

    def test_turing_failure_still_attempts_bounded_relock(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'EVGATuringGPUController')
        fake,report=RGBFake(write_error=True),{}
        with self.assertRaises(p.ProbeError): rgb.RGB(fake,report,port=1,apply=True,profile=profile).run()
        self.assertEqual(len(fake.writes),4)
        self.assertTrue(report['controller_relock_attempted'])
        self.assertTrue(report['controller_relock_failed'])
        self.assertFalse(report.get('write_completed',False))

    def test_turing_speed_is_bounded_and_inputs_validated(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'EVGATuringGPUController')
        plan=rgb.controller_transactions(profile,'breath',(1,2,3),'all',speed=100)
        registers={r:p[0] for _,r,p in plan}
        self.assertEqual(registers[0x74],250)
        self.assertEqual(registers[0x75],0)
        with self.assertRaises(p.ProbeError): rgb.controller_transactions(profile,'static',(1,2,3),'all',brightness=999)

    def test_zotac_enables_controller_and_completes_required_readback(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'ZotacTuringGPUController')
        fake,report=RGBFake(),{}
        rgb.RGB(fake,report,port=1,apply=True,profile=profile,effect='wave').run()
        self.assertEqual(fake.writes[0][1],bytes([0xf1,1,0,0,0,0,0]))
        self.assertEqual(fake.writes[1][1][1],2)
        self.assertTrue(report['controller_readback_completed'])
        self.assertEqual(report['i2c_transactions_attempted'],3)

    def test_zotac_off_uses_black_static_and_unsupported_gradient_fails(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'ZotacTuringGPUController')
        plans=rgb.controller_transactions(profile,'off',(255,255,255),'all')
        self.assertEqual(plans[-1][2][1:5],(0,0,0,0))
        with self.assertRaises(p.ProbeError): rgb.controller_transactions(profile,'gradient',(1,2,3),'all')

    def test_zotac_readback_failure_cannot_be_reported_as_success(self):
        import profiles
        profile = next(p for p in profiles.PROFILES if p.controller == 'ZotacTuringGPUController')
        class ReadFailure(RGBFake):
            def __call__(self,esc,data):
                if isinstance(data,p.Control) and data.cmd == 0x402c0102:
                    request=rgb.Indexed.from_address(data.params)
                    if not request.write:
                        data.status=0x56
                        return 0,C.sizeof(data)
                return super().__call__(esc,data)
        fake,report=ReadFailure(),{}
        with self.assertRaises(p.ProbeError): rgb.RGB(fake,report,port=1,apply=True,profile=profile).run()
        self.assertFalse(report.get('write_completed',False))
        self.assertEqual(len(fake.writes),2)


    def test_native_write_lock_excludes_parallel_core_and_gpu_lab_requests(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            first=rgb.acquire_write_lock(temp)
            try:
                with self.assertRaises(p.ProbeError):rgb.acquire_write_lock(temp)
            finally:first.close()
            rgb.acquire_write_lock(temp).close()

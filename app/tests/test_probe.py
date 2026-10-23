import ctypes as C
import importlib.util
from pathlib import Path
import plistlib
import types
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('probe', Path(__file__).resolve().parents[1] / 'probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Fake:
    def __init__(self, fail_at=None, gpus=1, short_at=None):
        self.calls = []
        self.fail_at, self.gpus, self.short_at = fail_at, gpus, short_at

    def __call__(self, esc, data):
        self.calls.append((esc, getattr(data, 'cmd', getattr(data, 'cls', None))))
        index = len(self.calls)
        if index == self.fail_at:
            return 0xe00002bc, C.sizeof(data)
        if index == self.short_at:
            return 0, C.sizeof(data) - 1
        data.status = 0
        if isinstance(data, p.Alloc):
            if data.cls == 0x41:
                self.assert_root(data)
                data.new = 0xabc
        elif isinstance(data, p.Control):
            if data.cmd == 0x201:
                ids = (p.U32 * 32).from_address(data.params)
                for i in range(self.gpus):
                    ids[i] = 0x1234 + i
            elif data.cmd == 0x205:
                info = p.IdInfo.from_address(data.params)
                assert info.gpu == 0x1234
                info.device, info.subdevice = 3, 2
            elif data.cmd == 0x402c0101:
                flags = (C.c_uint8 * 16).from_address(data.params)
                flags[1] = 0x13
            else:
                raise AssertionError('Non-metadata command')
        return 0, C.sizeof(data)

    @staticmethod
    def assert_root(data):
        assert (data.root, data.parent, data.params, data.size) == (0, 0, 0, 0)


class Tests(unittest.TestCase):
    def test_existing_report_prevents_hardware_access(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            output.write_text('preserve me')
            with patch.object(p, 'run_diagnostic') as run:
                with self.assertRaises(SystemExit) as raised:
                    p.main(['--ports', '--output', str(output)])
                self.assertEqual(raised.exception.code, 2)
                run.assert_not_called()
            self.assertEqual(output.read_text(), 'preserve me')

    def test_missing_output_directory_prevents_hardware_access(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(p, 'run_diagnostic') as run:
                with self.assertRaises(SystemExit):
                    p.main(['--ports', '--output', str(Path(directory) / 'missing' / 'result.json')])
                run.assert_not_called()

    def test_native_bridge_selector_and_copyback(self):
        native = p.Native.__new__(p.Native)
        native.connections = [77, 88]
        def method(connection, selector, scalars, count, source, size,
                   output_scalars, output_count, target, length):
            self.assertEqual((connection, selector, count), (77, 1, 1))
            self.assertEqual(C.cast(scalars, C.POINTER(p.U64))[0], 0x2b)
            self.assertEqual(size, C.sizeof(p.Alloc))
            reply = C.cast(target, C.POINTER(p.Alloc)).contents
            reply.new, reply.status = 0xabc, 0
            return 0
        native.io = types.SimpleNamespace(IOConnectCallMethod=method)
        request = p.Alloc(status=0xffffffff)
        self.assertEqual(native(0x2b, request), (0, 32))
        self.assertEqual((request.new, request.status), (0xabc, 0))

    def test_native_short_response_is_not_copied(self):
        native = p.Native.__new__(p.Native)
        native.connections = [77]
        def method(*args):
            C.cast(args[-1], C.POINTER(C.c_size_t))[0] = 4
            return 0
        native.io = types.SimpleNamespace(IOConnectCallMethod=method)
        request = p.Alloc(status=0xffffffff)
        self.assertEqual(native(0x2b, request), (0, 4))
        self.assertEqual(request.status, 0xffffffff)

    def test_native_connections_close_in_reverse_order(self):
        native = p.Native.__new__(p.Native)
        native.connections = [77, 88]
        closed = []
        def close(connection):
            closed.append(connection)
            return 1 if connection == 88 else 0
        native.io = types.SimpleNamespace(IOServiceClose=close)
        self.assertEqual(native.close(), ['0x00000001'])
        self.assertEqual(closed, [88, 77])
        self.assertEqual(native.connections, [])

    def test_wire_abi(self):
        p.check_abi()
        import struct
        req = p.Alloc(1, 2, 3, 0x402c, 0x1122334455667788, 4, 0xffffffff)
        self.assertEqual(bytes(req), struct.pack('<IIIIQII', 1, 2, 3, 0x402c, 0x1122334455667788, 4, 0xffffffff))

    def test_complete_metadata_sequence(self):
        fake, report = Fake(), {}
        p.RM(fake, report).run()
        self.assertEqual(fake.calls, [(0x2b, 0x41), (0x2a, 0x201), (0x2a, 0x205),
                                     (0x2b, 0x80), (0x2b, 0x2080), (0x2b, 0x402c),
                                     (0x2a, 0x402c0101), (0x29, None)])
        self.assertTrue(report['port_metadata_ok'])
        self.assertTrue(report['ports'][1]['implemented'])
        self.assertFalse(report['ports'][1]['ddc'])
        self.assertEqual(report['rgb_controller_reachable'], 'not tested')

    def test_each_failure_stops_and_cleans_root(self):
        for i in range(1, 8):
            with self.subTest(i=i):
                fake, report = Fake(fail_at=i), {}
                with self.assertRaises(p.ProbeError):
                    p.RM(fake, report).run()
                self.assertNotIn('port_metadata_ok', report)
                self.assertEqual(len(fake.calls), i + (i > 1))
                if i > 1:
                    self.assertEqual(fake.calls[-1], (0x29, None))

    def test_short_reply_and_ambiguous_gpu(self):
        for fake in (Fake(short_at=3), Fake(gpus=0), Fake(gpus=2)):
            with self.assertRaises(p.ProbeError):
                p.RM(fake, {}).run()
            self.assertEqual(fake.calls[-1], (0x29, None))

    def test_rm_status_failure(self):
        def refused(esc, data):
            data.status = 0x56
            return 0, C.sizeof(data)
        with self.assertRaisesRegex(p.ProbeError, '00000056'):
            p.RM(refused, {}).run()

    def test_cleanup_failure_retained(self):
        fake, report = Fake(fail_at=8), {}
        p.RM(fake, report).run()
        self.assertIn('cleanup_error', report)

    def test_transaction_and_unrelated_allocations_blocked(self):
        fake = Fake()
        rm = p.RM(fake, {})
        for cmd in (0x402c0102, 0x402c0105, 0xdeadbeef):
            with self.assertRaises(p.ProbeError):
                rm.control(1, cmd, (C.c_uint8 * 16)())
        with self.assertRaises(p.ProbeError):
            rm.alloc(1, 2, 0xdead)
        self.assertEqual(fake.calls, [])

    def test_inventory_redaction(self):
        node = {'IORegistryEntryID': 123, 'vendor-id': bytes.fromhex('de100000'),
                'device-id': bytes.fromhex('04270000'), 'subsystem-vendor-id': bytes.fromhex('6e190000'),
                'private-serial': 'DO-NOT-EXPORT',
                'IORegistryEntryChildren': [{'IOObjectClass': 'NVRM'}]}
        with patch.object(p.subprocess, 'run', return_value=types.SimpleNamespace(stdout=plistlib.dumps([node]))):
            result = p.inventory()
        self.assertEqual(result[0]['device-id'], 0x2704)
        self.assertNotIn('DO-NOT-EXPORT', str(result))


if __name__ == '__main__':
    unittest.main()

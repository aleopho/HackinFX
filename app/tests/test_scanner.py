import json
import importlib.util
from pathlib import Path
import plistlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scanner


def gpu(vendor=0x10de, device=0x2704, ident=1):
    return {'class-code': (0x30000).to_bytes(4,'little'), 'vendor-id': vendor,
            'device-id': device, 'subsystem-vendor-id':0x196e,'subsystem-id':0x13bc,
            'IORegistryEntryID':ident, 'model':b'PNY RTX 4080\0',
            'IORegistryEntryName':'GFX0', 'serial-number':'PRIVATE-SERIAL',
            'IORegistryEntryChildren':[{'IOObjectClass':'NVRM','secret':'PRIVATE-CHILD'}]}


class ScannerTests(unittest.TestCase):
    def test_scan_unknown_vendors_and_redacts_private_data(self):
        items=scanner.adapters_from_tree([gpu(),gpu(0x1002,0x1234,2),gpu(0x8086,0x5678,3)])
        self.assertEqual(len(items),3)
        self.assertEqual(items[0]['rgb_support'],'verified-profile')
        self.assertEqual(items[0]['vendor_name'],'NVIDIA')
        self.assertEqual(items[0]['board_vendor'],'PNY')
        self.assertEqual(items[0]['gpu_name'],'GeForce RTX 4080')
        self.assertEqual(items[1]['rgb_support'],'not-verified')
        self.assertNotIn('PRIVATE',str(items))
        self.assertNotIn('IORegistryEntryID',str(items))

    def test_skips_audio_and_deduplicates(self):
        audio=gpu(ident=3);audio['class-code']=0x40300
        self.assertEqual(len(scanner.adapters_from_tree([gpu(),gpu(),audio])),1)

    def test_collect_only_two_read_only_commands_and_redacts_driver_output(self):
        calls=[]
        def run(command,**kwargs):
            calls.append(command)
            raw=json.dumps({'SPHardwareDataType':[{'_name':'CPU','cpu_type':'Intel','serial_number':'PRIVATE'}]}).encode() if command[0].endswith('system_profiler') else plistlib.dumps([gpu()]) if command[0].endswith('ioreg') else b'133 0 0xffffffabc 123 com.nullmoth.NVRM (2.5.2) PRIVATE-UUID\n other (1)'
            return types.SimpleNamespace(returncode=0,stdout=raw)
        report=scanner.collect(run)
        self.assertEqual(len(calls),3)
        self.assertEqual(report['rm_connections'],0)
        self.assertEqual(report['i2c_transactions'],0)
        self.assertEqual(report['driver_bundles'],[{'identifier':'com.nullmoth.NVRM','version':'2.5.2'}])
        self.assertNotIn('PRIVATE',str(report))
        self.assertNotIn('0xffffff',str(report))
        self.assertEqual(report['setup']['system_hardware'][0]['cpu_type'],'Intel')

    def test_failure_retains_other_query_result(self):
        def run(command,**kwargs):
            if command[0].endswith('ioreg'): raise TimeoutError('PRIVATE-USER-PATH')
            if command[0].endswith('system_profiler'):return types.SimpleNamespace(returncode=0,stdout=b'{}')
            return types.SimpleNamespace(returncode=0,stdout=b'com.nullmoth.NVRM (2.5.2)')
        report=scanner.collect(run)
        self.assertEqual(len(report['errors']),1)
        self.assertEqual(len(report['driver_bundles']),1)
        self.assertNotIn('PRIVATE',str(report))

    def test_existing_export_blocks_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'scan.json';output.write_text('keep')
            with patch.object(scanner,'collect') as collect:
                with self.assertRaises(SystemExit):scanner.main(['--output',str(output)])
                collect.assert_not_called()
            self.assertEqual(output.read_text(),'keep')

    def test_startup_routes_verified_and_unsupported_configurations(self):
        devices=scanner.adapters_from_tree([gpu()])
        self.assertEqual(scanner.lighting_configuration(devices,arch='x86_64')['status'],'supported')
        devices[0]['rgb_support']='not-verified'
        self.assertEqual(scanner.lighting_configuration(devices,arch='x86_64')['status'],'unsupported')

    def test_inventory_errors_are_unknown_not_unsupported(self):
        self.assertEqual(scanner.lighting_configuration([],inventory_failed=True,arch='x86_64')['status'],'unknown')

    def test_multi_bound_gpu_and_arm_cannot_enable_lighting(self):
        devices=scanner.adapters_from_tree([gpu(),gpu(ident=2)])
        self.assertEqual(scanner.lighting_configuration(devices,arch='x86_64')['status'],'unsupported')
        self.assertEqual(scanner.lighting_configuration(devices[:1],arch='arm64')['status'],'unsupported')

    def test_integrated_gpu_does_not_block_single_verified_nvrm_gpu(self):
        intel=gpu(0x8086,0x5678,2);intel['IORegistryEntryChildren']=[]
        devices=scanner.adapters_from_tree([gpu(),intel])
        self.assertEqual(scanner.lighting_configuration(devices,arch='x86_64')['status'],'supported')

    def test_fingerprint_stable_across_scans_but_changes_with_driver(self):
        def fake(version):
            return lambda command,**kwargs: types.SimpleNamespace(returncode=0,stdout=b'{}' if command[0].endswith('system_profiler') else plistlib.dumps([gpu()]) if command[0].endswith('ioreg') else ('com.nullmoth.NVRM (%s)'%version).encode())
        from unittest.mock import patch
        with patch.object(scanner.platform,"machine",return_value="x86_64"):
            first=scanner.collect(fake('2.5.2'))
            second=scanner.collect(fake('2.5.2'))
            changed=scanner.collect(fake('2.5.3'))
        self.assertEqual(first['configuration_fingerprint'],second['configuration_fingerprint'])
        self.assertNotEqual(first['configuration_fingerprint'],changed['configuration_fingerprint'])
        self.assertIn('visual test required',first['led_availability'])

    def test_failed_queries_do_not_produce_reusable_fingerprint(self):
        report=scanner.collect(lambda *args,**kwargs: types.SimpleNamespace(returncode=1,stdout=b''))
        self.assertIsNone(report['configuration_fingerprint'])

class HardwarePrivacyTests(unittest.TestCase):
 def test_recursive_inventory_excludes_serials_paths_and_private_fields(self):
  rows=scanner.hardware_inventory({'SPUSBDataType':[{'_name':'Hub','serial_num':'SECRET','_items':[{'_name':'Mouse','vendor_id':'0x1234','user':'SECRET','location_id':'SECRET'}]}],'SPStorageDataType':[{'_name':'PRIVATE VOLUME','size':1000,'mount_point':'SECRET'}]})
  self.assertIn('Mouse',str(rows));self.assertNotIn('SECRET',str(rows));self.assertNotIn('PRIVATE VOLUME',str(rows))

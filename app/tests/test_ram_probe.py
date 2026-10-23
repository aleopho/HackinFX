import json
import plistlib
import types
import unittest
import ram_probe


class RAMProbeTests(unittest.TestCase):
    def test_reports_only_public_module_fields_and_skips_empty_slots(self):
        rows=ram_probe.modules({'items':[{'_name':'slot','dimm_size':'16 GB','dimm_manufacturer':'Corsair','dimm_part_number':'CMP32','dimm_serial_number':'PRIVATE'},{'dimm_size':'empty'}]})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['part_number'],'CMP32')
        self.assertNotIn('PRIVATE',json.dumps(rows))

    def test_probe_never_opens_bus_or_reads_spd(self):
        calls=[]
        def run(command,**kwargs):
            calls.append(command)
            return types.SimpleNamespace(stdout=b'{"SPMemoryDataType":[]}' if command[0].endswith('system_profiler') else plistlib.dumps([]))
        report=ram_probe.collect(run)
        self.assertEqual(len(calls),2)
        self.assertEqual(report['hardware_writes'],0)
        self.assertEqual(report['spd_reads'],0)
        self.assertEqual(report['lighting_transport'],'not-implemented')

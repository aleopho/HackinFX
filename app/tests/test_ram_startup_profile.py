# SPDX-License-Identifier: GPL-2.0-or-later
import json,tempfile,unittest
from pathlib import Path
from ram_control import RAMAdapter
from test_radius_ram_keyboard import RAMTransport
DIMMS=[dict(manufacturer='Corsair',part_number='CMP32GX5M2B6000Z30',slot='DIMM_A1',size='16 GB')]
class RAMStartupProfileTests(unittest.TestCase):
    def test_no_profile_requires_explicit_probe_and_success_restores_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';t=RAMTransport(True);a=RAMAdapter(t,lambda:DIMMS,path)
            self.assertFalse(a.discover()[0]['controllable']);self.assertFalse(any(r['command']=='probe' for r in t.calls))
            a.probe();self.assertEqual(path.stat().st_mode&0o777,0o600)
            restored=RAMTransport(True);rows=RAMAdapter(restored,lambda:DIMMS,path).discover()
            self.assertTrue(rows[0]['controllable']);self.assertTrue(any(r['command']=='probe' for r in restored.calls));self.assertFalse(any(r['command']=='frame' for r in restored.calls))
    def test_inventory_change_revokes_profile_before_bus_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';RAMAdapter(RAMTransport(True),lambda:DIMMS,path).probe()
            t=RAMTransport(True);changed=[dict(DIMMS[0],size='32 GB')]
            self.assertFalse(RAMAdapter(t,lambda:changed,path).discover()[0]['controllable']);self.assertFalse(path.exists());self.assertFalse(any(r['command']=='probe' for r in t.calls))
    def test_changed_rgb_identity_revokes_profile_without_color_or_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';RAMAdapter(RAMTransport(True),lambda:DIMMS,path).probe()
            t=RAMTransport(True);t.rows[0]['address']=0x19;a=RAMAdapter(t,lambda:DIMMS,path)
            self.assertFalse(a.discover()[0]['controllable']);self.assertFalse(path.exists());a.discover();self.assertEqual(sum(r['command']=='probe' for r in t.calls),1)
    def test_frame_error_revokes_persistent_startup_authorization(self):
        class Broken(RAMTransport):
            def call(self,r):
                if r['command']=='frame':raise ValueError('fixture bus failure')
                return super().call(r)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';a=RAMAdapter(Broken(True),lambda:DIMMS,path);row=a.probe()[0]
            with self.assertRaises(ValueError):a.write_frame(row,[(1,2,3)]*12,'static')
            self.assertFalse(path.exists());self.assertFalse(row['controllable'])
    def test_verified_sku_migrates_once_and_speed_change_keeps_saved_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';t=RAMTransport(True);a=RAMAdapter(t,lambda:DIMMS,path,auto_known=True)
            self.assertTrue(a.discover()[0]['controllable']);self.assertTrue(path.exists());self.assertEqual(json.loads(path.read_text())['schema'],2)
            b=RAMAdapter(RAMTransport(True),lambda:[dict(DIMMS[0],speed='7200 MHz')],path)
            self.assertTrue(b.discover()[0]['controllable'])
    def test_previous_transport_failure_blocks_automatic_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';a=RAMAdapter(RAMTransport(True),lambda:DIMMS,path,auto_known=True);a.forget_profile('fixture transport failure')
            self.assertFalse(a.discover()[0]['controllable']);self.assertFalse(any(x['command']=='probe' for x in a.transport.calls))
    def test_unknown_sku_never_gets_automatic_identity_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            t=RAMTransport(True);a=RAMAdapter(t,lambda:[dict(DIMMS[0],part_number='CMP-UNKNOWN')],Path(folder)/'p.json',auto_known=True)
            self.assertFalse(a.discover()[0]['controllable']);self.assertFalse(any(x['command']=='probe' for x in t.calls))

    def test_helper_pipe_close_during_orderly_shutdown_preserves_profile(self):
        class Interrupted(RAMTransport):
            def call(self,r):
                if r['command']=='frame':raise BrokenPipeError('helper stopping')
                return super().call(r)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';a=RAMAdapter(Interrupted(True),lambda:DIMMS,path);row=a.probe()[0];a.begin_shutdown()
            with self.assertRaises(BrokenPipeError):a.write_frame(row,[(1,2,3)]*12,'static')
            self.assertTrue(path.exists());self.assertFalse(a.revocation_path.exists())
            self.assertTrue(RAMAdapter(RAMTransport(True),lambda:DIMMS,path).discover()[0]['controllable'])
    def test_real_bus_error_during_shutdown_still_revokes(self):
        class BusError(RAMTransport):
            def call(self,r):
                if r['command']=='frame':raise ValueError('SMBus NACK')
                return super().call(r)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';a=RAMAdapter(BusError(True),lambda:DIMMS,path);row=a.probe()[0];a.begin_shutdown()
            with self.assertRaises(ValueError):a.write_frame(row,[(1,2,3)]*12,'static')
            self.assertFalse(path.exists());self.assertTrue(a.revocation_path.exists())

    def test_validation_failure_records_actual_reason_for_manual_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            t=RAMTransport(True);t.rows[0]['protocol']=99
            a=RAMAdapter(t,lambda:DIMMS,Path(folder)/'p.json')
            with self.assertRaisesRegex(ValueError,'unexpected controller identity'):a.probe()
            reason=json.loads(a.revocation_path.read_text())['reason']
            self.assertIn('unexpected controller identity',reason)
            self.assertIn(reason,a.discover()[0]['detail'])
            self.assertFalse(any(x['command']=='frame' for x in t.calls))

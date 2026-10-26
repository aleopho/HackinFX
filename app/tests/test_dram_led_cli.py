import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

class RAMDiagnosticCLITests(unittest.TestCase):
    def run_script(self, *, failure=None, bad_identity=False, effects=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shutil.copy2(Path(__file__).resolve().parents[2]/'tools/dram_led_test.py',root/'test.py')
            (root/'HackinFX-GitHub').mkdir()
            (root/'HackinFX-GitHub/app').symlink_to(Path(__file__).resolve().parents[1],target_is_directory=True)
            rows=[dict(address=a,product_id='0801',protocol=4,led_count=12) for a in range(0x18,0x1c)]
            if bad_identity:rows[-1]['product_id']='ffff'
            responses=dict(status=dict(driver_loaded=True,controllers=[dict(vendor_id='8086',device_id='7f23')]),diagnostics=dict(helper_revision='titanium-block-v3-paced',status=0),probe=dict(devices=rows))
            helper=root/'HackinFX-DRAM-Diagnostic'
            helper.write_text('#!'+sys.executable+'\n'+'''import json,sys
from pathlib import Path
responses=REPLIES
for line in sys.stdin:
 r=json.loads(line)
 with Path(__file__).with_name('calls.jsonl').open('a') as out:out.write(json.dumps(r)+'\\n')
 reply=responses.get(r['command'],{'sent':True})
 if r['command'] in ('static','frame') and r['address']==FAILURE:reply={'error':'simulated bus error'}
 print(json.dumps(reply),flush=True)
'''.replace('REPLIES',repr(responses)).replace('FAILURE',repr(failure)))
            helper.chmod(0o700)
            result=subprocess.run([sys.executable,str(root/'test.py')]+(['--effects','--seconds','1','--map-seconds','0'] if effects else ['--mint','--remaining']),capture_output=True,text=True,timeout=10)
            calls=[json.loads(v) for v in (root/'calls.jsonl').read_text().splitlines()]
            return result,calls
    def test_remaining_colors_exactly_three_other_dimms_once(self):
        result,calls=self.run_script()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        writes=[r for r in calls if r['command']=='static']
        self.assertEqual([r['address'] for r in writes],[0x19,0x1a,0x1b])
        self.assertTrue(all(r['color']==[32,64,48] for r in writes))
    def test_failure_stops_before_next_dimm(self):
        result,calls=self.run_script(failure=0x19)
        self.assertEqual(result.returncode,1)
        self.assertEqual([r['address'] for r in calls if r['command']=='static'],[0x19])
    def test_all_requested_identities_checked_before_any_color(self):
        result,calls=self.run_script(bad_identity=True)
        self.assertEqual(result.returncode,1)
        self.assertFalse(any(r['command']=='static' for r in calls))

    def test_effect_test_uses_distinct_leds_and_restores_mint(self):
        result,calls=self.run_script(effects=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        frames=[r for r in calls if r['command']=='frame']
        self.assertEqual([r['address'] for r in frames[:4]],[24,25,26,27])
        self.assertEqual(frames[0]['colors'],[[64,0,0]]*4+[[0,64,0]]*4+[[0,0,64]]*4)
        self.assertTrue(any(len({tuple(c) for c in r['colors']})>1 for r in frames[4:]))
        self.assertEqual([r['address'] for r in calls if r['command']=='static'],[24,25,26,27])
        stats=next(json.loads(line) for line in result.stdout.splitlines() if 'completed_fps_per_dimm' in line)
        self.assertGreater(stats['complete_four_dimm_frames'],0)
        self.assertFalse(stats['optically_confirmed'])
    def test_effect_error_stops_without_cleanup_color_writes(self):
        result,calls=self.run_script(effects=True,failure=24)
        self.assertEqual(result.returncode,1,result.stdout)
        writes=[r for r in calls if r['command'] in ('frame','static')]
        self.assertEqual(len(writes),1)
        self.assertEqual(writes[0]['address'],24)

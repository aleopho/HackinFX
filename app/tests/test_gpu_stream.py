# SPDX-License-Identifier: GPL-2.0-or-later
import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from test_rgb import RGBFake,rgb
import gpu_stream as stream
import profiles

PNY=next(p for p in profiles.PROFILES if p.key=='pny-4080-196e-13bc')
class StreamTests(unittest.TestCase):
 def test_session_reuses_one_object_tree_for_many_frames_and_cleans_up(self):
  fake=RGBFake();colors=[[1,2,3],[4,5,6],[7,8,9]]
  source=io.StringIO(''.join(json.dumps(dict(sequence=i,pixels=colors))+'\n' for i in range(4)));sink=io.StringIO();check=Mock()
  worker=stream.Stream(fake,PNY,source,sink,check);worker.run()
  self.assertEqual(len(fake.writes),12);self.assertEqual(check.call_count,4)
  replies=[json.loads(line) for line in sink.getvalue().splitlines()];self.assertEqual(replies[0],{'ready':True});self.assertEqual(replies[-1],{'sequence':3,'ok':True})
  self.assertEqual(sum(esc==0x2b and value==0x41 for esc,value in fake.calls),1)
  self.assertEqual(fake.calls[-1][0],0x29);self.assertLessEqual(len(worker.report['calls']),24)
 def test_bad_frame_and_revoked_confirmation_never_write(self):
  for pixels in ([[1,2,3]],[[True,2,3]]*3):
   fake=RGBFake();worker=stream.Stream(fake,PNY,io.StringIO(json.dumps(dict(sequence=1,pixels=pixels))+'\n'),io.StringIO(),lambda:None)
   with self.assertRaises(ValueError):worker.run()
   self.assertEqual(fake.writes,[]);self.assertEqual(fake.calls[-1][0],0x29)
  fake=RGBFake();worker=stream.Stream(fake,PNY,io.StringIO(json.dumps(dict(sequence=1,pixels=[[1,2,3]]*3))+'\n'),io.StringIO(),Mock(side_effect=ValueError('revoked')))
  with self.assertRaises(ValueError):worker.run()
  self.assertEqual(fake.writes,[])
 def test_profile_requires_full_exact_confirmation(self):
  with tempfile.TemporaryDirectory() as folder:
   fp='a'*64;path=Path(folder)/('profile-'+fp+'.json');saved=dict(schema=1,fingerprint=fp,successfulSteps=3,userConfirmed=True,verifiedEffects=list(PNY.effects));path.write_text(json.dumps(saved))
   self.assertEqual(stream.confirmed_profile(folder,fp,PNY.key),PNY)
   saved['userConfirmed']=False;path.write_text(json.dumps(saved))
   with self.assertRaises(ValueError):stream.confirmed_profile(folder,fp,PNY.key)
   with self.assertRaises(ValueError):stream.confirmed_profile(folder,'../invalid',PNY.key)
 def test_client_launches_once_and_matches_every_acknowledgement(self):
  process=Mock();process.poll.return_value=None;process.stdin=io.BytesIO()
  client=stream.Client('/tmp','a'*64,PNY.key)
  with patch.object(stream,'confirmed_profile'),patch.object(stream.subprocess,'Popen',return_value=process) as launch,patch.object(client,'read',side_effect=[{'ready':True},{'sequence':1,'ok':True},{'sequence':2,'ok':True}]):
   client.write([[1,2,3]]*3);client.write([[4,5,6]]*3)
   self.assertEqual(launch.call_count,1);self.assertEqual(len(process.stdin.getvalue().splitlines()),2);client.close();process.wait.assert_called()
 def test_validation_before_worker_launch(self):
  client=stream.Client('/tmp','a'*64,PNY.key)
  with patch.object(stream.subprocess,'Popen') as launch:
   with self.assertRaises(ValueError):client.write([[256,0,0]]*3)
   launch.assert_not_called()

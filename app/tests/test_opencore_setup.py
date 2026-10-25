# SPDX-License-Identifier: GPL-2.0-or-later
import copy,importlib.util,plistlib,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('opencore_setup',Path(__file__).resolve().parents[2]/'installer/opencore_setup.py');oc=importlib.util.module_from_spec(spec);spec.loader.exec_module(oc)
def config():return dict(ACPI={},Booter={},Kernel=dict(Add=[dict(BundlePath='Lilu.kext',Enabled=True)]),Misc={},NVRAM={'keep':'unchanged'},PlatformInfo={},UEFI={})
class ConfigTests(unittest.TestCase):
 def test_add_preserves_others_and_is_idempotent(self):
  before=config();saved=copy.deepcopy(before);after=oc.edited_config(before);self.assertEqual(before,saved);self.assertEqual(oc.edited_config(after),after)
  entry=after['Kernel']['Add'].pop();self.assertEqual(after,before);self.assertTrue(entry['Enabled'])
 def test_existing_entry_is_enabled_without_losing_bounds(self):
  before=oc.edited_config(config());before['Kernel']['Add'][-1].update(Enabled=False,Comment='keep',MaxKernel='25.9.9')
  entry=oc.edited_config(before)['Kernel']['Add'][-1];self.assertTrue(entry['Enabled']);self.assertEqual(entry['Comment'],'keep');self.assertEqual(entry['MaxKernel'],'25.9.9')
 def test_invalid_duplicates_and_renamed_entries_rejected(self):
  bad=[{},dict(Kernel=dict(Add=[])),dict(config(),Kernel=dict(Add=[1]))]
  duplicate=oc.edited_config(config());duplicate['Kernel']['Add'].append(copy.deepcopy(duplicate['Kernel']['Add'][-1]));bad.append(duplicate)
  renamed=config();renamed['Kernel']['Add'].append(dict(BundlePath='macUSPCIO.kext'));bad.append(renamed)
  for value in bad:
   with self.assertRaises(oc.SetupError):oc.edited_config(value)
 def test_boot_guid_and_ambiguous_efi(self):
  guid=uuid.uuid4();node=bytes([4,1,42,0])+bytes(20)+guid.bytes_le+bytes([2,2])+bytes([127,255,4,0]);self.assertEqual(oc.boot_partition_guids(node),{str(guid)})
  a=dict(uuid=str(guid),path='a');b=dict(uuid=str(uuid.uuid4()),path='b');self.assertEqual(oc.choose_candidate([a,b],{str(guid)}),a)
  for candidates in ([a,b],[]):
   with self.assertRaises(oc.SetupError):oc.choose_candidate(candidates,set())
 def fixture(self,folder,binary=False):
  root=Path(folder);efi=root/'volume';p=efi/'EFI/OC/Kexts';p.mkdir(parents=True);(p.parent/'OpenCore.efi').write_bytes(b'fixture');cfg=p.parent/'config.plist';cfg.write_bytes(plistlib.dumps(config(),fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML))
  kext=root/oc.BUNDLE;(kext/'Contents/MacOS').mkdir(parents=True);(kext/'Contents/MacOS/macUSPCIO').write_bytes(b'fixture');(kext/'Contents/Info.plist').write_bytes(plistlib.dumps(dict(CFBundleIdentifier=oc.IDENTIFIER,CFBundleExecutable='macUSPCIO')))
  return root,efi,cfg,kext
 def test_transaction_full_backup_and_binary_plist(self):
  with tempfile.TemporaryDirectory() as folder:
   root,efi,cfg,kext=self.fixture(folder,True);before=cfg.read_bytes();backup=oc.install(efi,kext,root/'backups');self.assertEqual((backup/'EFI/OC/config.plist').read_bytes(),before);self.assertTrue(cfg.read_bytes().startswith(b'bplist'));self.assertTrue((efi/'EFI/OC/Kexts'/oc.BUNDLE).is_dir())
 def test_write_failure_restores_kext_and_keeps_config(self):
  with tempfile.TemporaryDirectory() as folder:
   root,efi,cfg,kext=self.fixture(folder);before=cfg.read_bytes()
   with patch.object(oc,'atomic_bytes',side_effect=OSError('disk full')):
    with self.assertRaises(OSError):oc.install(efi,kext,root/'backups')
   self.assertEqual(cfg.read_bytes(),before);self.assertFalse((efi/'EFI/OC/Kexts'/oc.BUNDLE).exists());self.assertEqual(len(list((root/'backups').iterdir())),1)
 def test_symlink_is_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   root,efi,cfg,kext=self.fixture(folder);original=cfg.read_bytes();cfg.unlink();other=root/'other';other.write_bytes(original);cfg.symlink_to(other)
   with self.assertRaises(oc.SetupError):oc.install(efi,kext,root/'backups')
   self.assertEqual(other.read_bytes(),original)
if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib,importlib.util,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('runtime_download',Path(__file__).resolve().parents[2]/'tools/prepare_openrgb_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
class RuntimeDownloadTests(unittest.TestCase):
    def row(self,data):return dict(name='fixture.zip',url='https://example.invalid/fixture.zip',size=len(data),sha256=hashlib.sha256(data).hexdigest())
    def test_transient_timeout_retries_and_only_caches_verified_bytes(self):
        data=b'verified fixture'
        with tempfile.TemporaryDirectory() as folder,patch.object(runtime,'CACHE',Path(folder)),patch.object(runtime.time,'sleep'),patch.object(runtime.urllib.request,'urlopen',side_effect=[TimeoutError('fixture timeout'),io.BytesIO(data)]) as download:
            path=runtime.verified_download(self.row(data));self.assertEqual(path.read_bytes(),data);self.assertEqual(download.call_count,2)
            runtime.verified_download(self.row(data));self.assertEqual(download.call_count,2)
    def test_invalid_payload_is_not_installed(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(runtime,'CACHE',Path(folder)),patch.object(runtime.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong')):
            with self.assertRaises(ValueError):runtime.verified_download(self.row(b'valid'))
            self.assertEqual(list(Path(folder).iterdir()),[])

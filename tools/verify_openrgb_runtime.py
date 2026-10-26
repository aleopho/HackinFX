#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise actual bundled OpenRGB SDK, explicitly WITHOUT hardware detection."""
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'app'))
from center_sdk import SDKClient
executable=root/'app/HackinFX.app/Contents/Resources/Engine/OpenRGB.app/Contents/MacOS/OpenRGB'
assert subprocess.check_output(['/usr/bin/lipo','-archs',str(executable)],text=True).strip()=='x86_64'
version=subprocess.check_output([str(executable),'--version'],text=True);assert '8e16de27858cf2be6af54a33ce003df74cb9fd3e' in version
with tempfile.TemporaryDirectory(prefix='hackinfx-engine-check-') as directory:
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    with open(Path(directory)/'engine.log','wb') as log:
        process=subprocess.Popen([str(executable),'--nodetect','--noautoconnect','--server','--server-host','127.0.0.1','--server-port',str(port),'--config',directory],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+20
            while True:
                assert process.poll() is None,'Engine exited; inspect dependency closure'
                try:
                    client=SDKClient(port);rows=client.discover();client.close();assert rows==[];break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.1)
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
print('Pinned x86-64 OpenRGB executable and real empty SDK negotiation verified without hardware detection')

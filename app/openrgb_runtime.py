# SPDX-License-Identifier: GPL-2.0-or-later
"""Process-owned, bundled OpenRGB CLI. No system install or external SDK required."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

# Native drivers own these exact controllers, including during detection.
NATIVE_DETECTORS=('HID LampArray Device','Asus ROG Spatha X USB',
                  'Asus ROG Spatha X 2.4GHz','NZXT Kraken X2','NZXT Kraken M2')

class ManagedEngine:
    def __init__(self,directory,executable=None,timeout=75):
        self.directory=Path(directory)
        self.executable=Path(executable) if executable else Path(__file__).parent/'Engine/OpenRGB.app/Contents/MacOS/OpenRGB'
        self.timeout=timeout;self.process=None;self.port=None;self.log=None
        self.lock=threading.RLock();self.reserve_ram=True
    def ensure_started(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:return self.port
            self.close()
            if not self.executable.is_file():raise RuntimeError('Bundled OpenRGB is missing. Reinstall the complete HackinFX package.')
            self.directory.mkdir(parents=True,exist_ok=True);os.chmod(self.directory,0o700)
            safety=json.loads(Path(__file__).with_name('openrgb_smbus_detectors.json').read_text())
            if safety.get('schema')!=1 or safety.get('unresolved') or not isinstance(safety.get('disabled'),list) or not 1<=len(safety['disabled'])<=2000 or any(not isinstance(n,str) or not 1<=len(n)<=160 for n in safety['disabled']):raise RuntimeError('SMBus detector safety catalog is missing or invalid')
            detectors={name:False for name in set(NATIVE_DETECTORS)|set(safety['disabled'])}
            if self.reserve_ram:detectors['Corsair DRAM']=False
            config={'Detectors':{'detectors':detectors}}
            # Only our private configuration is used; no external profiles/plugins.
            from center_core import atomic_json
            atomic_json(self.directory/'OpenRGB.json',config)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0));self.port=listener.getsockname()[1]
            fd=os.open(str(self.directory/'engine.log'),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            self.log=os.fdopen(fd,'wb')
            args=[str(self.executable),'--server','--server-host','127.0.0.1','--server-port',str(self.port),'--noautoconnect','--config',str(self.directory)]
            try:
                self.process=subprocess.Popen(args,stdout=self.log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
                deadline=time.monotonic()+self.timeout
                while time.monotonic()<deadline:
                    if self.process.poll() is not None:raise RuntimeError('OpenRGB stopped during detection. See the private engine.log.')
                    try:
                        with socket.create_connection(('127.0.0.1',self.port),timeout=.2):return self.port
                    except OSError:time.sleep(.1)
                raise RuntimeError('OpenRGB detection timed out. See the private engine.log.')
            except Exception:self.close();raise
    def claim_native_ram(self):
        with self.lock:self.close();self.reserve_ram=True
    def close(self):
        with self.lock:
            process=self.process;self.process=None
            try:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            finally:
                if self.log:self.log.close();self.log=None
                self.port=None

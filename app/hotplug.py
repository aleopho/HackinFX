# SPDX-License-Identifier: GPL-2.0-or-later
"""Debounced passive USB topology observation; never probes RAM or writes devices."""
import re,subprocess,threading

def topology():
    result=subprocess.run(['/usr/sbin/ioreg','-r','-c','IOUSBHostDevice','-d','1'],capture_output=True,text=True,timeout=5)
    if result.returncode:raise OSError('USB registry snapshot unavailable')
    return tuple(sorted(re.findall(r'\bid (0x[0-9a-fA-F]+),',result.stdout)))

class HotplugMonitor:
    def __init__(self,core,reader=topology,interval=2):
        self.core=core;self.reader=reader;self.interval=interval;self.event=threading.Event();self.last=None;self.pending=None;self.repeats=0
        self.thread=threading.Thread(target=self.run,daemon=True,name='usb-topology');self.thread.start()
    def sample(self):
        value=self.reader()
        if self.last is None:self.last=value;return
        if value==self.last:self.pending=None;self.repeats=0;return
        if self.pending!=value:self.pending=value;self.repeats=1;return
        self.repeats+=1
        if self.repeats<2 or not self.core.initialized:return
        if not self.core.operation.acquire(blocking=False):return
        try:
            self.core.hotplug_refresh();self.last=value;self.pending=None;self.repeats=0
        finally:self.core.operation.release()
    def run(self):
        while not self.event.wait(self.interval):
            try:self.sample()
            except Exception:
                # No repeated auto-probe after a failed refresh. Next physical change retries.
                if self.pending is not None:self.last=self.pending;self.pending=None;self.repeats=0
    def close(self):self.event.set();self.thread.join(timeout=8)

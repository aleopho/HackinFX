#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify signing after mounting the distributed image and copying the app."""
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

image = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='hackinfx-install-check-') as tmp:
    mount = Path(tmp)/'image'
    mount.mkdir()
    attached = False
    try:
        subprocess.run(['/usr/bin/hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mount),str(image)],check=True)
        attached = True
        source = mount/'HackinFX.app'
        destination = Path(tmp)/'installed/HackinFX.app'
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(source)],check=True)
        subprocess.run(['/usr/bin/ditto',str(source),str(destination)],check=True)
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(destination)],check=True)
        for bundle in [destination,destination/'Contents/PlugIns/HackinFXWidget.appex']:
            info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
            assert info['LSMinimumSystemVersion'] == '15.0'
            binary = bundle/'Contents/MacOS'/info['CFBundleExecutable']
            assert subprocess.check_output(['/usr/bin/lipo','-archs',str(binary)],text=True).strip() == 'x86_64'
        print('Mounted DMG and copied installation retain valid host/widget signatures; x86-64/macOS 15 verified.')
    finally:
        if attached:
            subprocess.run(['/usr/bin/hdiutil','detach',str(mount)],check=True)

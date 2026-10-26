#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Expand installer, verify target/payload/signature without installing it."""
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
with tempfile.TemporaryDirectory(prefix='hackinfx-pkg-check-') as temporary:
    target=Path(temporary)/'expanded'
    subprocess.run(['/usr/sbin/pkgutil','--expand-full',sys.argv[1],str(target)],check=True)
    distribution=ET.parse(target/'Distribution').getroot()
    assert distribution.find('options').get('hostArchitectures')=='x86_64'
    assert distribution.find('allowed-os-versions/os-version').get('min')=='15.0'
    apps=list(target.glob('**/Payload/Applications/HackinFX.app'));assert len(apps)==1
    scripts=list(target.glob('*.pkg/Scripts'))
    assert len(scripts)==1
    assert (scripts[0]/'postinstall').is_file()
    assert (scripts[0]/'opencore_setup.py').is_file()
    assert (scripts[0]/'macUSPCIO_Smbus.kext/Contents/Info.plist').is_file()
    assert (scripts[0]/'macUSPCIO_Smbus.kext/Contents/MacOS/macUSPCIO').stat().st_mode & 0o111
    option=distribution.find("choice[@id='opencore']");assert option is not None and option.get('start_selected')=='false'
    payload=apps[0].parent.parent
    assert [p.name for p in payload.iterdir()]==['Applications']
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(apps[0])],check=True)
print('Installer targets macOS 15+ x86-64, installs only Applications/HackinFX.app and retains signatures; separate opt-in OpenCore transaction script')

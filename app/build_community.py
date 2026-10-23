#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Rebuild the x86-64 Hackintosh app; no downloads or hardware calls."""
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent
app = root / 'HackinFX.app' / 'Contents'
resources = app / 'Resources'
# Recreate generated resources to exclude obsolete previews and bytecode.
shutil.rmtree(resources, ignore_errors=True)
resources.mkdir(parents=True, exist_ok=True)
(app / 'MacOS').mkdir(exist_ok=True)
cache = Path(tempfile.gettempdir()) / 'aleopho-gpurgb-swift-cache'
cache.mkdir(exist_ok=True)
subprocess.run(['/usr/bin/swiftc', '-swift-version', '5', '-target', 'x86_64-apple-macos13.0', '-module-cache-path', str(cache),
                str(root/'CommunityRGB.swift'), str(root/'SetupSupport.swift'), '-o', str(app/'MacOS'/'HackinFX'),
                '-framework', 'AppKit', '-framework', 'SwiftUI'], check=True)
for name in ('rgb.py','probe.py','profiles.py','scanner.py','compatibility.json','NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name, resources/name)
shutil.copy2(root/'report-endpoint.json', resources/'report-endpoint.json')
shutil.copy2(root/'assets'/'hackinfx-mark-v2.png', resources/'hackinfx-logo.png')
shutil.copy2(root/'assets'/'HackinFX.icns', resources/'HackinFX.icns')
source = resources/'Source'
source.mkdir(exist_ok=True)
for name in ('CommunityRGB.swift','SetupSupport.swift','render_icon.swift','package_dmg.py','compatibility.json','report-endpoint.json','rgb.py','probe.py','profiles.py','scanner.py','build_community.py'):
    shutil.copy2(root/name,source/name)
for name in ('NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name,source/name)
shutil.copytree(root/'assets', source/'assets', dirs_exist_ok=True)
shutil.copytree(root/'tests', source/'tests', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
(app/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleName='HackinFX',
    CFBundleDisplayName='HackinFX', CFBundleIdentifier='community.aleopho.hackinfx',
    CFBundleVersion='1.0.0', CFBundleShortVersionString='1.0.0', CFBundleExecutable='HackinFX',
    CFBundlePackageType='APPL', LSMinimumSystemVersion='13.0', NSHighResolutionCapable=True, CFBundleIconFile='HackinFX', CFBundleDevelopmentRegion='en', CFBundleLocalizations=['en'])))
subprocess.run(['/usr/bin/codesign','--force','--deep','--sign','-','--timestamp=none',str(app.parent)],check=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app.parent)],check=True)
print(app.parent)

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Rebuild the x86-64 Hackintosh app; no downloads or hardware calls."""
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import os

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
                '-framework', 'AppKit', '-framework', 'SwiftUI', '-framework', 'WidgetKit'], check=True)
for name in ('rgb.py','probe.py','profiles.py','scanner.py','gpu_catalog.py','openrgb_gpu_catalog.json','compatibility.json','NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name, resources/name)
shutil.copy2(root/'report-endpoint.json', resources/'report-endpoint.json')
shutil.copy2(root/'assets'/'hackinfx-mark-v2.png', resources/'hackinfx-logo.png')
shutil.copy2(root/'assets'/'HackinFX.icns', resources/'HackinFX.icns')
source = resources/'Source'
source.mkdir(exist_ok=True)
for name in ('CommunityRGB.swift','SetupSupport.swift','render_icon.swift','package_dmg.py','compatibility.json','report-endpoint.json','rgb.py','probe.py','profiles.py','scanner.py','gpu_catalog.py','openrgb_gpu_catalog.json','build_community.py'):
    shutil.copy2(root/name,source/name)
for name in ('NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name,source/name)
shutil.copytree(root/'assets', source/'assets', dirs_exist_ok=True)
shutil.copytree(root/'tests', source/'tests', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
(app/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleName='HackinFX',
    CFBundleDisplayName='HackinFX', CFBundleIdentifier='community.aleopho.hackinfx',
    CFBundleVersion='1.1.0b2', CFBundleShortVersionString='1.1.0', CFBundleExecutable='HackinFX',
    CFBundlePackageType='APPL', LSMinimumSystemVersion='13.0', NSHighResolutionCapable=True, CFBundleIconFile='HackinFX', CFBundleDevelopmentRegion='en', CFBundleLocalizations=['en'], CFBundleURLTypes=[dict(CFBundleURLName='HackinFX',CFBundleURLSchemes=['hackinfx'])])))
# Build a real WidgetKit app-extension with Xcode when available. No Apple account
# or App Group is needed for this read-only, narrowly scoped local snapshot mode.
widget_product = os.environ.get('HACKINFX_WIDGET_PATH')
developer = subprocess.run(['/usr/bin/xcode-select','-p'],capture_output=True,text=True).stdout.strip()
if not widget_product and (Path(developer)/'usr/bin/xcodebuild').is_file():
    widget_output = cache/'widget-product'
    subprocess.run([str(Path(developer)/'usr/bin/xcodebuild'),'-project',str(root/'Widget/HackinFXWidget.xcodeproj'),'-target','HackinFXWidget','-configuration','Release','-sdk','macosx','ARCHS=x86_64','ONLY_ACTIVE_ARCH=NO','CODE_SIGNING_ALLOWED=NO','CONFIGURATION_BUILD_DIR='+str(widget_output),'OBJROOT='+str(cache/'widget-intermediates')],cwd=root/'Widget',check=True,stdout=subprocess.DEVNULL)
    widget_product = str(widget_output/'HackinFXWidget.appex')
plugins=app/'PlugIns'
shutil.rmtree(plugins,ignore_errors=True)
if widget_product:
    plugins.mkdir()
    target=plugins/'HackinFXWidget.appex'
    shutil.copytree(widget_product,target)
    subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none','--entitlements',str(root/'Widget/Widget.entitlements'),str(target)],check=True)
else:
    print('WidgetKit source included; compiled extension requires Xcode or HACKINFX_WIDGET_PATH.')
shutil.copytree(root/'Widget',source/'Widget',dirs_exist_ok=True,ignore=shutil.ignore_patterns('build','DerivedData','xcuserdata','*.xcuserstate'))
repo=root.parent
for folder in ['tools','vendor']:
    if (repo/folder).is_dir():shutil.copytree(repo/folder,source/folder,ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(app.parent)],check=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app.parent)],check=True)
print(app.parent)

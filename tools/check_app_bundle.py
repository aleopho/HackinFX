#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify that the release really ships an entitled WidgetKit extension."""
import json
import plistlib
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
app=root/'app/HackinFX.app/Contents'
widget=app/'PlugIns/HackinFXWidget.appex/Contents'
host_info=plistlib.loads((app/'Info.plist').read_bytes())
info=plistlib.loads((widget/'Info.plist').read_bytes())
assert info['CFBundlePackageType']=='XPC!'
assert info['NSExtension']['NSExtensionPointIdentifier']=='com.apple.widgetkit-extension'
assert info['CFBundleIdentifier'].startswith(host_info['CFBundleIdentifier']+'.')
assert info['CFBundleVersion']==host_info['CFBundleVersion']
assert 'NSExtensionPrincipalClass' not in info['NSExtension']
assert 'hackinfx' in host_info['CFBundleURLTypes'][0]['CFBundleURLSchemes']
signature=subprocess.run(['/usr/bin/codesign','-d','--entitlements',':-',str(widget.parent)],check=True,capture_output=True)
entitlements=plistlib.loads(signature.stdout)
assert entitlements['com.apple.security.app-sandbox'] is True
assert entitlements['com.apple.security.temporary-exception.files.home-relative-path.read-only']==['Library/Application Support/HackinFX/Widget/']
assert 'com.apple.security.application-groups' not in entitlements
assert not (app/'Resources/Source/Widget/build').exists()
assert json.loads((app/'Resources/openrgb_gpu_catalog.json').read_text())['schema_version']==1
print('WidgetKit bundle identity, snapshot scope, preserved entitlements and host URL scheme verified')

helper=app/'Resources/HackinFXHID'
assert helper.is_file()
assert subprocess.check_output(['/usr/bin/lipo','-archs',str(helper)],text=True).strip()=='x86_64'
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(helper)],check=True)
assert (app/'Resources/Source/HIDBridge.swift').is_file()
usb=json.loads((app/'Resources/openrgb_usb_catalog.json').read_text())
assert usb['schema']==1 and len(usb['entries'])>1000
assert (app/'Resources/Source/vendor/openrgb/usb-sources.zip').is_file()
print('Signed x86-64 HID helper and reproducible OpenRGB USB catalog included')

ram_helper=app/'Resources/HackinFXSMBus'
assert ram_helper.is_file()
assert subprocess.check_output(['/usr/bin/lipo','-archs',str(ram_helper)],text=True).strip()=='x86_64'
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(ram_helper)],check=True)
assert (app/'Resources/Source/docs/RAM-SETUP.md').is_file()
assert (app/'Resources/Source/vendor/radius/LICENSE').is_file()
assert (app/'Resources/Source/vendor/rigstats/LICENSE').is_file()
print('Scoped RAM helper, setup guide and Radius/ASUS protocol notices included')

effects=json.loads((app/'Resources/effects_catalog.json').read_text())
assert effects['schema']==1 and len(effects['effects'])==40 and len(effects['looks'])==80
assert (app/'Resources/effects.py').is_file()
assert (app/'Resources/Source/EffectLibrary.swift').is_file()
assert (app/'Resources/Source/EffectGallery.swift').is_file()
print('Shared 40-effect catalog, 80 looks, native gallery and hardware renderer are bundled')

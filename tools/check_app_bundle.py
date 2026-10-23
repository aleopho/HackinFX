#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify that the beta really ships an entitled WidgetKit extension."""
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

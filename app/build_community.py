#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build x86-64 app from explicitly prepared inputs; no hardware calls."""
from pathlib import Path
import plistlib
import json
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
subprocess.run(['/usr/bin/swiftc', '-swift-version', '5', '-target', 'x86_64-apple-macos15.0', '-module-cache-path', str(cache),
                str(root/'BrandMark.swift'),str(root/'MAKRMedia.swift'),str(root/'Localization.swift'),str(root/'EffectLibrary.swift'),str(root/'EffectGallery.swift'),str(root/'ReleaseVersion.swift'), str(root/'CommunityRGB.swift'), str(root/'ControlCenter.swift'), str(root/'SetupSupport.swift'), '-o', str(app/'MacOS'/'HackinFX'),
                '-framework', 'AppKit', '-framework', 'SwiftUI', '-framework', 'WidgetKit', '-framework', 'ServiceManagement', '-framework', 'Carbon', '-framework', 'CoreImage', '-framework','IOKit','-framework','CoreAudio'], check=True)
subprocess.run(['/usr/bin/swiftc','-swift-version','5','-target','x86_64-apple-macos15.0','-module-cache-path',str(cache),str(root/'HIDBridge.swift'),'-o',str(resources/'HackinFXHID'),'-framework','IOKit'],check=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(resources/'HackinFXHID')],check=True)
subprocess.run(['/usr/bin/swiftc','-swift-version','5','-target','x86_64-apple-macos15.0','-module-cache-path',str(cache),str(root/'SMBusBridge.swift'),'-o',str(resources/'HackinFXSMBus'),'-framework','IOKit'],check=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(resources/'HackinFXSMBus')],check=True)
for name in ('gpu_stream.py','openrgb_runtime.py','openrgb_smbus_detectors.json','radius_protocol.py','asus_keyboard.py','asus_scope_layouts.json','ram_control.py','nanoleaf_control.py','usb_devices.py','makr75.py','makr75-layout.json','COPYING-GPL3','openrgb_usb_catalog.json','center_core.py','effects.py','effects_catalog.json','center_sdk.py','center_service.py','widget_bridge.py','remote_control.py','hotplug.py','ram_probe.py','rgb.py','probe.py','profiles.py','scanner.py','gpu_catalog.py','openrgb_gpu_catalog.json','compatibility.json','NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name, resources/name)
shutil.copy2(root/'report-endpoint.json', resources/'report-endpoint.json')
shutil.copy2(root/'assets'/'hackinfx-mark-v2.png', resources/'hackinfx-logo.png')
shutil.copy2(root/'assets'/'HackinFX.icns', resources/'HackinFX.icns')
shutil.copytree(root/'Localization',resources/'Localization',dirs_exist_ok=True)
source = resources/'Source'
source.mkdir(exist_ok=True)
shutil.copytree(root/'Localization',source/'Localization',dirs_exist_ok=True)
for name in ('gpu_stream.py','openrgb_runtime.py','openrgb_smbus_detectors.json','package_installer.py','ReleaseVersion.swift','SMBusBridge.swift','radius_protocol.py','asus_keyboard.py','asus_scope_layouts.json','ram_control.py','nanoleaf_control.py','HIDBridge.swift','usb_devices.py','makr75.py','makr75-layout.json','COPYING-GPL3','openrgb_usb_catalog.json','BrandMark.swift','MAKRMedia.swift','CommunityRGB.swift','ControlCenter.swift','EffectLibrary.swift','EffectGallery.swift','Localization.swift','SetupSupport.swift','render_icon.swift','package_dmg.py','compatibility.json','report-endpoint.json','center_core.py','effects.py','effects_catalog.json','center_sdk.py','center_service.py','widget_bridge.py','remote_control.py','hotplug.py','ram_probe.py','rgb.py','probe.py','profiles.py','scanner.py','gpu_catalog.py','openrgb_gpu_catalog.json','build_community.py'):
    shutil.copy2(root/name,source/name)
for name in ('NOTICE.txt','COPYING','LICENSE.md','SOURCES-RGB.md','SOURCES.md','HACKINFX.md','EFFECTS.md'):
    shutil.copy2(root/name,source/name)
shutil.copytree(root/'assets', source/'assets', dirs_exist_ok=True)
shutil.copytree(root/'tests', source/'tests', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
(app/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleName='HackinFX',
    CFBundleDisplayName='HackinFX', CFBundleIdentifier='community.aleopho.hackinfx',
    CFBundleVersion='3.0.1', CFBundleShortVersionString='3.0.1', CFBundleExecutable='HackinFX',
    CFBundlePackageType='APPL', NSLocalNetworkUsageDescription='Pair HackinFX Remote on your Android phone to control lighting over your local network.', LSMinimumSystemVersion='15.0', NSAppTransportSecurity={'NSAllowsLocalNetworking':True}, NSHighResolutionCapable=True, CFBundleIconFile='HackinFX', CFBundleDevelopmentRegion='en', CFBundleLocalizations=json.loads((root/'Localization/manifest.json').read_text())['languages'], CFBundleURLTypes=[dict(CFBundleURLName='HackinFX',CFBundleURLSchemes=['hackinfx'])])))
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
for folder in ['tools','vendor','docs','installer','android']:
    if (repo/folder).is_dir():shutil.copytree(repo/folder,source/folder,ignore=shutil.ignore_patterns('__pycache__','.gradle','build','local.properties','*.keystore'),dirs_exist_ok=True)
# Prepared, hash-verified full OpenRGB CLI and corresponding library sources.
prepared=root.parent/'.build-cache/openrgb/prepared'
if not (prepared/'manifest.json').is_file():
    raise SystemExit('Run python3 tools/prepare_openrgb_runtime.py before building.')
shutil.copytree(prepared/'Engine',resources/'Engine',symlinks=True)
shutil.copytree(prepared/'Notices',resources/'OpenRGB-Notices',symlinks=True)
shutil.copytree(prepared/'Sources',source/'ThirdPartySources',symlinks=True)
shutil.copy2(prepared/'manifest.json',resources/'Engine/manifest.json')
engine=resources/'Engine/OpenRGB.app'
# Sign dependencies inside out after relocating; preserve replaceable LGPL libraries.
for path in (engine/'Contents/Frameworks').iterdir():
    subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(path)],check=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(engine)],check=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(app.parent)],check=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app.parent)],check=True)
print(app.parent)

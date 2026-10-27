#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile and run an entitled WidgetKit reader against an ephemeral fake Core."""
import os,subprocess,sys,tempfile,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from widget_bridge import WidgetBridge
class Fixture:
    def status(self):return dict(scene=dict(mode='twinkle',palette=['9bed4b'],brightness=65),active_devices=['one','two'],running=True)
with tempfile.TemporaryDirectory(prefix='hackinfx-widget-') as folder:
    bundle=Path(folder)/'WidgetReader.app';contents=bundle/'Contents';(contents/'MacOS').mkdir(parents=True)
    (contents/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleIdentifier='community.aleopho.hackinfx.widget-reader-test',CFBundleExecutable='WidgetReader',CFBundleName='WidgetReader',CFBundlePackageType='APPL',NSAppTransportSecurity={'NSAllowsLocalNetworking':True})))
    binary=contents/'MacOS/WidgetReader'
    subprocess.run(['swiftc','-swift-version','5','-target','x86_64-apple-macos15.0','-module-cache-path',folder,str(ROOT/'app/Widget/WidgetStatus.swift'),str(ROOT/'app/tests/WidgetStatusTests.swift'),'-o',str(binary)],check=True)
    subprocess.run(['codesign','--force','--sign','-','--timestamp=none','--entitlements',str(ROOT/'app/Widget/Widget.entitlements'),str(bundle)],check=True)
    bridge=WidgetBridge(Fixture())
    try:subprocess.run([str(binary),'--fetch',str(bridge.server.server_port)],check=True,timeout=15)
    finally:bridge.close()

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""App installer with an explicit optional OpenCore SMBus transaction."""
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import zipfile
import hashlib
root=Path(__file__).resolve().parent
app=root/'HackinFX.app'
version=plistlib.loads((app/'Contents/Info.plist').read_bytes())['CFBundleShortVersionString']
output=root.parent/('HackinFX-'+version+'-Installer.pkg')
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
with tempfile.TemporaryDirectory(prefix='hackinfx-installer-') as temporary:
    work=Path(temporary);payload=work/'payload/Applications';payload.mkdir(parents=True)
    shutil.copytree(app,payload/app.name,symlinks=True)
    components=work/'components.plist'
    components.write_bytes(plistlib.dumps([dict(BundleHasStrictIdentifier=True,BundleIsRelocatable=False,BundleIsVersionChecked=True,BundleOverwriteAction='upgrade',RootRelativeBundlePath='Applications/HackinFX.app')]))
    subprocess.run(['/usr/bin/pkgbuild','--root',str(work/'payload'),'--component-plist',str(components),'--identifier','community.aleopho.hackinfx.application','--version',version,'--install-location','/','--ownership','recommended',str(work/'Application.pkg')],check=True)
    resources=work/'Resources';resources.mkdir()
    (resources/'Welcome.txt').write_text('HackinFX '+version+' — by aleopho\n\nRGB control for x86-64 Hackintoshes running macOS 15 or later.\nQuit HackinFX before installing. Installation target: Applications.\n\nOn launch, ready non-RAM devices receive mint Twinkle at 65% speed. RAM requires explicit probe and selection. Manage Launch at login in Settings and macOS Login Items.\n\nThe app and helpers are ad-hoc signed. The installer is not Developer ID signed or notarized; macOS may require approval.\n\nOptional OpenCore SMBus driver component: automatically detects the boot EFI, saves a complete backup, installs macUSPCIO and enables it in the existing config. Reboot required. Select Customize to enable this component. No SIP/security changes or immediate kext loading. EFI backups: /Library/Application Support/HackinFX/EFI Backups. Modern-OS driver behavior still needs physical validation.\n')
    shutil.copy2(root/'COPYING',resources/'License.txt')
    # Optional, explicit installer component. The app itself never edits EFI.
    driver=root.parent/'vendor/macUSPCIO'
    archive=driver/'macUSPCIO_Smbus_Release.kext.zip'
    hashes={line.split()[1]:line.split()[0] for line in (driver/'SHA256SUMS.txt').read_text().splitlines() if len(line.split())==2}
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==hashes[archive.name]
    scripts=work/'ram-scripts';scripts.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            path=Path(name)
            if path.parts and path.parts[0]=='macUSPCIO_Smbus.kext' and not path.is_absolute() and '..' not in path.parts:
                bundle.extract(name,scripts)
    (scripts/'macUSPCIO_Smbus.kext/Contents/MacOS/macUSPCIO').chmod(0o755)
    assert subprocess.check_output(['/usr/bin/lipo','-archs',str(scripts/'macUSPCIO_Smbus.kext/Contents/MacOS/macUSPCIO')],text=True).strip()=='x86_64'
    shutil.copy2(root.parent/'installer/opencore_setup.py',scripts/'opencore_setup.py')
    (scripts/'postinstall').write_text('#!/bin/sh\nset -eu\nif [ "${3:-/}" != "/" ]; then echo "EFI setup requires the current startup volume" >&2; exit 1; fi\nSCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec /usr/bin/python3 "$SCRIPT_DIR/opencore_setup.py" --kext "$SCRIPT_DIR/macUSPCIO_Smbus.kext" --backups "/Library/Application Support/HackinFX/EFI Backups"\n')
    (scripts/'postinstall').chmod(0o755)
    empty=work/'empty';empty.mkdir()
    subprocess.run(['/usr/bin/pkgbuild','--root',str(empty),'--scripts',str(scripts),'--identifier','community.aleopho.hackinfx.opencore','--version',version,'--install-location','/',str(work/'OpenCore.pkg')],check=True)
    distribution=work/'Distribution.xml'
    distribution.write_text('''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2"><title>HackinFX</title>
<welcome file="Welcome.txt"/><license file="License.txt"/>
<options customize="always" require-scripts="true" hostArchitectures="x86_64"/>
<domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
<allowed-os-versions><os-version min="15.0"/></allowed-os-versions>
<choices-outline><line choice="application"/><line choice="opencore"/></choices-outline>
<choice id="application" title="HackinFX" visible="false"><pkg-ref id="community.aleopho.hackinfx.application"/></choice>
<choice id="opencore" title="OpenCore SMBus driver (RAM RGB)" description="Automatically finds the boot OpenCore EFI, backs it up, copies macUSPCIO and enables its Kernel/Add entry. Reboot required. Skip if you do not need SMBus access. Installation stops if the EFI cannot be identified uniquely." start_selected="false"><pkg-ref id="community.aleopho.hackinfx.opencore"/></choice>
<pkg-ref id="community.aleopho.hackinfx.opencore" onConclusion="RequireRestart">OpenCore.pkg</pkg-ref>
<pkg-ref id="community.aleopho.hackinfx.application" version="'''+version+'''" onConclusion="none">Application.pkg</pkg-ref>
</installer-gui-script>''')
    subprocess.run(['/usr/bin/productbuild','--distribution',str(distribution),'--resources',str(resources),'--package-path',str(work),str(output)],check=True)
print(output)

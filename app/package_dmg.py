#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Package the built, locally signed app as a drag-and-drop UDZO disk image."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parent
app = root/'HackinFX.app'
output = root.parent/'HackinFX-aleopho-1.1.1.dmg'
if not (app/'Contents/MacOS/HackinFX').is_file():
    raise SystemExit('Build HackinFX.app first with build_community.py')
with tempfile.TemporaryDirectory(prefix='hackinfx-dmg-') as temporary:
    work = Path(temporary)
    stage = work/'stage';stage.mkdir()
    shutil.copytree(app, stage/'HackinFX.app', symlinks=True)
    (stage/'Applications').symlink_to('/Applications', target_is_directory=True)
    (stage/'Install HackinFX.txt').write_text('HackinFX — by aleopho\n\nDrag HackinFX.app onto Applications.\nEject this disk image and open HackinFX from Applications.\n\nThe app is locally ad-hoc signed, not Developer ID signed or notarized.\nThis does not guarantee that downloaded copies open without a macOS warning.\n\nAt launch: a brief intro, read-only hardware check, then setup or your saved profile.\nClosing the window keeps HackinFX running in the FX menu. Quit ends the app.\n')
    # makehybrid synthesizes FinderInfo on nested bundles, invalidating their
    # code signatures after installation. Create a native HFS+ image instead.
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(stage/'HackinFX.app')],check=True)
    subprocess.run(['/usr/bin/hdiutil','create','-srcfolder',str(stage),'-volname','HackinFX','-fs','HFS+','-format','UDZO','-ov',str(output)],check=True)
print(output)

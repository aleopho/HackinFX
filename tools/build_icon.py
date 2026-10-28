#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Render the code-owned RGB fan and pack PNG-backed ICNS without a GUI session."""
from pathlib import Path
import struct,subprocess,tempfile
root=Path(__file__).resolve().parents[1];assets=root/'app/assets'
with tempfile.TemporaryDirectory() as folder:
 folder=Path(folder);renderer=folder/'render-fan'
 subprocess.run(['/usr/bin/swiftc','-module-cache-path',str(Path(tempfile.gettempdir())/'aleopho-gpurgb-swift-cache'),str(root/'app/BrandMark.swift'),str(root/'app/render_icon.swift'),'-o',str(renderer),'-framework','CoreGraphics','-framework','ImageIO','-framework','CoreText'],check=True)
 subprocess.run([str(renderer),str(assets/'hackinfx-mark-v2.png')],check=True)
 chunks=[]
 for size,kind in [(16,b'icp4'),(32,b'icp5'),(64,b'icp6'),(128,b'ic07'),(256,b'ic08'),(512,b'ic09'),(1024,b'ic10')]:
  png=folder/(str(size)+'.png');subprocess.run(['/usr/bin/sips','-z',str(size),str(size),str(assets/'hackinfx-mark-v2.png'),'--out',str(png)],check=True,stdout=subprocess.DEVNULL)
  data=png.read_bytes();chunks.append(kind+struct.pack('>I',8+len(data))+data)
 content=b''.join(chunks);(assets/'HackinFX.icns').write_bytes(b'icns'+struct.pack('>I',8+len(content))+content)
 print('RGB fan PNG and ICNS generated')

# HackinFX — by aleopho

The new application and Python lighting implementation in this project are
licensed under GPL-2.0-or-later. See COPYING for the GPL version 2 text.
This program comes without warranty. You may redistribute and modify it under
the GNU General Public License, version 2 or (at your option) any later version.

PNY lighting effect packet construction follows the OpenRGB PNY Lovelace
controller by yufan (2023) and OpenRGB contributors, GPL-2.0-or-later:
https://gitlab.com/CalcProgrammer1/OpenRGB/-/tree/master/Controllers/PNYLovelaceGPUController
The Python adaptation and native macOS UI were developed on 2026-10-23.
Source files and build script accompany the release application.
The upstream LICENSE copy in COPYING is preserved verbatim, including its
historical OpenAuraSDK example notice. It does not name this app's author.

NVIDIA public RM SDK definitions: MIT; retain NOTICE.txt.

NullMoth NVRM is a separate installed dependency. No NullMoth driver binary,
Mesa patch or NullMoth source is included in this application. The examined
NVRM.cpp v2.5.3 identifies PolyForm-Noncommercial-1.0.0:
https://github.com/nullmoth/nvidia-macos-driver/blob/v2.5.3/kexts/NVRM/NVRM.cpp
Its terms are distinct from this application's GPL license. Attribution does
not relicense that driver. Consult the upstream project for its full terms.

This is an independent community project. No endorsement or affiliation with
PNY, NVIDIA, Apple, NullMoth or OpenRGB is claimed.

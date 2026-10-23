# OpenRGB GPU detector source snapshot

Pinned upstream commit: 817834cfab034c97927451e31c4a2deb60a44725.
Source: https://gitlab.com/CalcProgrammer1/OpenRGB
License: GPL-2.0-or-later. Full GPL text: ../../LICENSE.

These source files preserve their original author/copyright/license headers. They are inputs to tools/import_openrgb_catalog.py, not compiled or executed by HackinFX. manifest.json records original paths and SHA-256 hashes.

Scope: GPU-named controller families (including nested MSI/ASRock GPU detectors), Intel Arc A770 LE HID and NVIDIA Illumination. Motherboard, keyboard, mouse and other non-GPU detectors are excluded. This is a GPU identity snapshot, not a promise that upstream platform-dependent transports are available on macOS. PCI reuse/alias ambiguity is preserved. USB identities remain separate and are not guessed from a PCI ID.

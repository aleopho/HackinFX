# Bundled OpenRGB CLI runtime

HackinFX includes the official **OpenRGB 1.1 Intel macOS executable**, commit
`8e16de27858cf2be6af54a33ce003df74cb9fd3e`. No controller code is removed or
modified. Only the executable's transitive dylib/framework dependency closure
is redistributed; OpenRGB's GUI, GUI plugins and application plugins are not.
The executable is invoked as a separate local CLI/SDK process, not linked into
HackinFX's Swift executable. Local ad-hoc signatures are renewed after bundling.

`manifest.json` pins every binary/source download by URL, size and SHA-256.
Run `python3 tools/prepare_openrgb_runtime.py` before the normal app build.
This explicit preparation step needs network access; the app itself never
fetches executables or plugins. Build cache is excluded from Git.

## Source and license delivery

The installed app includes `Contents/Resources/Source/ThirdPartySources/`:

- Complete OpenRGB release source archive, including its bundled dependencies.
- Qt base 6.11.0 source: QtCore, QtGui, QtWidgets and QtDBus frameworks.
- GLib 2.88.0 source: libglib and libgthread.
- GNU gettext 1.0 source: libintl.
- libusb 1.0.29 source.

These are the upstream release sources for the versions identified in the
runtime. The official upstream package is used as the binary input; this does
not claim a bit-for-bit reproducible rebuild of its Homebrew/Qt environment.
All license/COPYING/NOTICE files from those archives are also extracted under
`Contents/Resources/OpenRGB-Notices/`. The archives preserve the complete source,
build instructions, third-party notices and license alternatives.

Other dynamic dependency notices are retained in this directory:
BLAKE2 libb2; D-Bus (AFL/GPL alternatives); double-conversion; FreeType (FTL);
Graphite2; HarfBuzz; ICU/Unicode; Mbed TLS (Apache-2.0 alternatives);
MD4C; PCRE2; libpng; Zstandard; hidapi/hidapi-hotplug (BSD alternative).
Original OpenRGB, NullMoth/NVRM, Radius MIT and native protocol credits remain
in the project's existing THIRD-PARTY-NOTICES and vendor directories.

Qt/GLib/gettext/libusb libraries remain separate, replaceable dynamic files.
There is no technical restriction on modification or replacement: developers
may rebuild/replace them and reapply an ad-hoc signature (`codesign --force
--sign -`) inside out. No Developer ID, online activation or vendor signing
key is required. Preserve the upstream license obligations when redistributing.

## Runtime ownership

OpenRGB binds to **127.0.0.1 on a dynamically selected local port**. Its SDK has
no authentication; it is not exposed on a LAN. HackinFX's separate UI/Core HTTP
API requires a session bearer token and rejects browser origins.
A private configuration directory prevents loading another OpenRGB install's
profiles or plugins. `--noautoconnect` prevents attaching to an unrelated server.
The app stops only its own child engine, never other OpenRGB processes.

Native LampArray, ASUS Spatha X USB/wireless and Kraken X2/M2 detectors are
reserved for HackinFX's native adapters before detection. Native Corsair RAM
probing stops the engine and reserves Corsair DRAM before restarting it.
Other detector defaults, including upstream disabled detectors, are preserved.
Catalog entries do not grant write access: an actual working controller with
Direct/custom mode is required for shared per-LED effects. Hardware-only-mode
controllers remain visible but are not misrepresented as scene-ready devices.
This includes the official **macOS** OpenRGB driver set, not Windows-only APIs.

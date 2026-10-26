# HackinFX 2.0.3

RGB Control Center for x86-64 Hackintoshes, macOS 15 or later. By aleopho.

## Changes

- Bundled, version-pinned OpenRGB 1.1 CLI and macOS drivers, managed by HackinFX.
  No separate OpenRGB install or manually configured SDK server is needed.
- Lighting changes are live, with a short debounce and serialized requests.
  Changes made during another update are coalesced; there is no Apply step.
- On each app/Core session, successfully discovered scene-capable devices are
  set to static white at 100%. A failed device does not block other devices.
  Rediscovery within that session does not force white again. Unconfirmed
  native GPUs and inventory-only devices are never written automatically.
- Launch at login via macOS ServiceManagement, enabled by default after the
  app is installed in Applications and launched. macOS may require approval
  in Login Items. This runs **after sign-in**, not before the login screen.
- Settings: check the latest public GitHub release, then open its download page.
  No automatic installation, unsigned executable fetch or credentials required.
- Lighting-first navigation, collapsed advanced tools, responsive effect grid,
  live color visualization, hover/press/navigation animations, Reduce Motion.
- Nine shared effects: Static, Gradient, Spectrum, Breathing, Wave, Aurora,
  Comet, Twinkle and Color shift. Native hardware-only paths expose their
  smaller supported subset; incompatible targets keep their last color.
- Radius HID callback context and report buffer retained for the helper session,
  fixing the observed use-after-free crash. Actual lighting still needs a
  physical device test; no claim of confirmed Radius support is made.
- PKG installer for /Applications with an optional OpenCore SMBus component.
  It identifies the boot EFI, saves a complete backup, copies macUSPCIO and
  activates its Kernel/Add entry. Ambiguous EFIs stop without modification;
  failed writes roll back. Reboot is required. No SIP changes or live kext load.
- OpenRGB and dynamic dependency licenses, notices and source archives included.

## Practical limits

- The macOS drivers in OpenRGB determine device access; a catalog match alone
  is not proof of control. Windows-specific drivers are not macOS support.
- Native NVIDIA access and SMBus DRAM access depend on available drivers,
  chipset/module support and physical verification. No universal RAM support.
- Real WidgetKit extension is included in Xcode builds. The reported blank
  desktop widget is still an open issue; this release does not claim to fix it.
- App/helpers are ad-hoc signed. No Developer ID or notarization is supplied;
  Gatekeeper may ask for approval for a downloaded package or app.
- Profiles/scenes: ~/Documents/HackinFX. Private engine state and logs:
  ~/Library/Application Support/HackinFX/Core. No reports are sent by startup
  white or discovery. Existing explicit report submission remains available.

## Build and checks

1. `python3 tools/prepare_openrgb_runtime.py` (hash-pinned network inputs).
2. `python3 app/build_community.py` (Xcode required to compile WidgetKit).
3. `python3 tools/verify_openrgb_runtime.py` (real SDK, --nodetect, no hardware).
4. `python3 app/package_installer.py` and `python3 tools/verify_installer.py HackinFX-2.0.3-Installer.pkg`.
5. Python unit suite in app/, native version/profile tests, Radius port check,
   bundle signature/extension checks, installer and DMG verification in CI.

Physical RGB, login launch and desktop widget behavior require real macOS
sessions; successful compilation does not establish those hardware results.

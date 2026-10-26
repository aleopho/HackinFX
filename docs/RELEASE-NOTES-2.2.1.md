# HackinFX 2.2.1 — Lighting Studio

Native RAM RGB joins the Lighting Studio: four Corsair Dominator Titanium DDR5
DIMMs have passed visible Static mint, separate LED-region and paced Twinkle tests
on Intel 8086:7f23 with macUSPCIO. Each DIMM exposes twelve independently addressed
LEDs. The eight-second test measured **16.65 completed FPS per DIMM**. GPU and AIO
streaming benefit from persistent native output and adaptive scheduling.

## Included

- Direct 32+6-byte RAM LED block transfer, identity/CRC guards, bounded frames,
  conservative timing, no SPD/bootloader/firmware writes and no forced bus reset.
- Explicit RAM probe and selection in the app; normal status polling now preserves
  selected DIMMs. RAM remains excluded from automatic startup lighting.
- Mint Twinkle startup at 65% speed for ready non-RAM devices.
- Shared-clock adaptive rendering with per-output FPS/latency metrics, so slower
  devices do not stall faster ones. Optional lockstep remains available.
- Permanent Feedback access and exact-layout keyboard topology for recognized
  OpenRGB layout replies. Unknown Scope layouts keep whole-keyboard output.
- Real WidgetKit extension, macOS 15+ / x86-64 app, PKG installer and drag/drop DMG.

## Install / enable RAM

Quit HackinFX using its menu-bar Quit action, then install the PKG. On an already
prepared system with macUSPCIO loaded, leave the optional OpenCore driver component
unselected. In Devices, open Memory details and choose **Probe RAM RGB**, then
select the four DIMMs in Lighting. Start with mint `#A7F3D0`, Twinkle, speed 65%,
brightness 40%, matching the confirmed test. The application uses the existing driver.

## Validation and limits

171 Python tests and Linux/backend checks passed. The macOS build validates native
helpers, WidgetKit packaging, nested code signatures and installer/DMG integrity.
The scoped RAM test is short-duration evidence, not universal compatibility or
long-duration stability. Exact physical synchronization is not guaranteed. Radius
may still show occasional frame jitter; performance/synchronization improvements
remain ongoing. The user's wired Scope II 96 layout still needs per-key validation.
Nanoleaf Shapes Triangles integration is planned, not included in this release.
Automatic generic OpenRGB SMBus detection is disabled pending transport review;
USB/HID and reviewed native paths remain available.

App and helpers are ad-hoc signed, not Developer ID notarized. Intel and AMD CPU
Hackintosh systems are in scope; Apple Silicon is excluded. Native RAM is currently
restricted to the exact Intel controller and Corsair protocol described above.

Credits and licenses: [aleopho](https://github.com/aleopho),
[OpenRGB and its contributors](https://openrgb.org/),
[NullMoth NVRM](https://github.com/nullmoth/nvidia-macos-driver),
[macUSPCIO](https://github.com/ShadyNawara/macUSPCIO), plus all bundled
[third-party notices](THIRD-PARTY-NOTICES.md). GPL source is included with the app
and as a release archive. NullMoth's driver is installed separately, not bundled.

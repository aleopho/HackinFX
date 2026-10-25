# HackinFX 2.1.0 — Canvas

- Canvas: 560-point spatial workspace, Direct-device selection and shared-clock mode.
- Effect Studio: reusable look library, separated from Lighting's live controls.
- Output rendering uses a persistent monotonic epoch across edits/restarts,
  precomputes a tick from one timestamp and dispatches independent outputs in
  parallel. Only one write per device may be outstanding; slow outputs drop
  stale frames rather than queueing them. Actual HID/USB delivery latency is
  not zero, and no claim of physical frame-perfect synchronization is made.
- Strict Canvas mode excludes onboard-only modes because their clocks cannot
  be controlled by the host. The native ASUS Spatha can now stream RGB directly.
- Confirmed three-zone PNY Lovelace profiles can stream their RGB zones from
  the host timeline, using the existing fingerprint-checked NVRM gradient path.
  Native transaction latency limits the real rate; successful frame reports are
  removed and failed reports are bounded. Other native GPU families retain
  their existing static/onboard limits.
- Software Update settings include automatic public-release checks at launch.
- OpenCore installer uses the documented vendor NVRAM boot-path rather than
  confusing the OS volume's chosen device path with the bootloader EFI. If
  needed, an explicit EFI picker resolves ambiguity; cancellation changes nothing.
  Original full-EFI backup, constrained config edit and rollback remain in place.
- Radius discovery and lighting are now user-confirmed on aleopho's system.
- Native GPU test candidates: 68 exact profiles across PNY Lovelace (12), ASUS
  Aura (21), EVGA Pascal (5), EVGA Turing (26), Zotac Turing (4). Candidate does
  not mean physically verified. Fresh supported cards enter the existing RGB/
  effect test; matching confirmed profiles restore locally. Unknown protocols
  remain inventory-only rather than receiving guessed writes.

Nanoleaf is a follow-up integration, not implemented in this version. Its
local OpenAPI pairing and UDP external-control protocol suit the shared Canvas;
exact device family/firmware support needs capability negotiation and testing.

Validation includes regression tests for shared timestamps, bounded slow-output
behavior, independent hardware-clock rejection, persistent epoch, OpenCore
vendor boot-path parsing and interactive selection/cancellation. Physical boot
and visible inter-device timing still require user validation. Widget desktop
blank-display issue remains open. macOS 15+, x86-64, ad-hoc signed.

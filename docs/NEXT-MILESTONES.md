# Next milestones

## Current focus: effect library and workspace

40 real effect algorithms, 80 curated looks, searchable category gallery, favorites,
live previews, custom saved looks, larger responsive startup window. Validate all
patterns against the renderer and test the actual macOS gallery layout before
handing over the installer. Preserve device pacing and existing driver boundaries.

## Next phase requested by aleopho: Android Remote Control

Begin after the effect-gallery update is validated. Design an opt-in local remote
service, explicit pairing, revocable per-client credentials, connection status and
Android controls for devices, groups, effects, brightness and saved looks. Keep a
single Mac-side renderer so remote commands cannot create competing hardware
writers. Network discovery, mobile UI, reconnects and background behavior need
separate design and validation. No Android app or LAN listener is shipped yet.

## Continue hardware quality work

Track achieved FPS, frame gaps and visible synchronization across Radius, keyboard,
GPU, RAM and Shapes. Per-key Scope output needs physical confirmation on the
actual keyboard. Shapes pairing is user-confirmed; no universal hardware claim.
Native RAM remains limited to the exact validated Intel/Corsair path. EFI/USB boot
configuration review was explicitly deferred in favor of HackinFX improvements.

Long-term scope: broad Corsair/iCUE and Razer families, reviewed per transport and
validated on real macOS hardware. Catalog detection is not proof of working control.

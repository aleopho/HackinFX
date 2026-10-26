# Next milestones

HackinFX 2.4.0 is published. aleopho confirmed the installed Effect Gallery update
runs well. The next requested priorities, before Android Remote Control, are below.

## 1. Clean up the application

Remove the old V1-era GPU Lab and legacy navigation/UI. Preserve exact hardware
identity guards, profile reuse and required visual tests by integrating GPU setup
into the normal device workflow. Removing a legacy page must not remove the only
setup route for an unconfirmed supported GPU. Keep Credits accessible normally.

## 2. Broad multilingual UI

The user explicitly requested broad language coverage, not only German/English.
Plan around 20 languages, with locale variants where needed: English, German,
French, Spanish, Italian, Portuguese (Brazil/Portugal), Dutch, Polish, Czech,
Swedish, Turkish, Ukrainian, Russian, Arabic, Hindi, Indonesian, Vietnamese,
Japanese, Korean and Chinese (Simplified/Traditional).

Cover navigation, effect names/descriptions, gallery filters, setup, errors and
settings. Preserve stable internal effect/profile IDs and actual hardware names.
Support system-language detection, a manual preference and a clean English
fallback. Check translation completeness, longer strings, non-Latin scripts and
right-to-left layouts. Physical Canvas geometry must remain consistent rather
than silently mirroring hardware coordinates in RTL. Keep saved profiles and
network protocol values language-independent. Language names alone in a menu do
not constitute translated UI; complete and review actual message coverage.

## 3. Live Canvas background

Show the running effect behind the device arrangement, using the same effect
kernel, spatial coordinates and shared scene time. Keep devices/labels readable
and retain dragging, scaling and selection. Respect Reduce Motion and limit UI
preview refresh so the background cannot slow device output. It is an effect
visualization, not optical LED readback or guaranteed physical synchronization.

## 4. Corsair MAKR 75 practical test

aleopho expects to connect a Corsair MAKR 75. First identify its exact USB/HID
identity, connection mode, firmware and any existing OpenRGB implementation.
Validate discovery, exact LED mapping, colors, per-key animation and pacing on
that physical unit. If unsupported, implement only documented/reviewed lighting
commands and test them before claiming support; no firmware/profile flashing.
The keyboard is not yet claimed as supported or physically verified.

## Following phase: Android Remote Control

Design an opt-in local remote service, explicit pairing, revocable per-client
credentials, connection status and Android controls for devices, groups, effects,
brightness and saved looks. Keep a single Mac-side renderer so remote commands
cannot create competing hardware writers. Network discovery, reconnects and
background behavior need separate validation. No Android app or LAN listener is
shipped in 2.4.0.

## Continue hardware quality work

Track achieved FPS, frame gaps and visible synchronization across Radius,
keyboard, GPU, RAM and Shapes. Shapes pairing is user-confirmed; no universal
hardware claim. Native RAM remains limited to the exact validated Intel/Corsair
path. EFI/USB boot configuration review was explicitly deferred in favor of
HackinFX improvements. Long-term scope includes broad Corsair/iCUE and Razer
families, reviewed per transport and validated on real macOS hardware.

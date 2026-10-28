# HackinFX 3.0 — composition workspace

## Lighting

The live composition panel shows the current effect, additional layer count, selected LED count, active outputs and mapping. Its animation illustrates the host renderer; it is not optical LED readback. Device hardware and network buffering can still affect visible synchronization.

## Layer Studio

A base effect plus up to four additional layers share the Core monotonic clock. Choose effect, color, speed, opacity and Screen/Add/Multiply/Normal blending; move layers upward to change composition order. All layers inherit the scene mapping. Each layer has its own effect parameters. Save the composition using the existing saved-look controls in Effects. Saved compositions preserve their layer stack. The master brightness scales the complete composition, including every additional layer.

Layers require host-streamed Direct devices. Unsupported onboard-only outputs are excluded by the desktop target selection and rejected by the Core if sent directly. No firmware effects or device clocks are used to simulate layered playback.

## Canvas

Positions now include width, height, rotation and horizontal/vertical mirroring. The effect renderer transforms individual mapped LED coordinates before sampling. Devices without known topology use their existing linear zone order. Select a device below the canvas to adjust its transform. Transform changes are debounced and do not restart the running scene clock. Static and gradient outputs are resent after a placement edit.

## Color calibration

Open a controllable device's inspector and expand Color calibration. RGB gains (0–1) and gamma (0.5–3) are applied to outgoing RGB frames along with existing device brightness. Defaults preserve existing RGB output exactly. This changes lighting frames, not device firmware, SPD, fan control or electrical settings.

Calibration and canvas transforms persist alongside existing scenes and brightness in the local workspace store. Unique hardware fingerprints restore them across device ID changes. Identical ambiguous fingerprints remain session-specific. Keep a copy of the local workspace store before downgrading to older versions, which may not preserve new metadata when saving.

## Verification

- 238 Python regression tests, including composition bounds, blend order, master blackout, calibration persistence and canvas clock continuity.
- 216 Swift/Python layer composition samples, plus the existing 2,160 base-effect equivalence cases.
- Synthetic CPU-only sample: base plus four layers across 293 LEDs, around 6.4 ms median on the development machine. This is not a hardware FPS measurement.
- Native x86-64 macOS build and signatures must be checked for the final assembled app. Visual hardware validation remains necessary before public release.

New workspace controls currently use English fallback; existing translated areas retain their language support. Audio-reactive capture, screen ambient lighting, per-zone layer masks and a guided calibration wizard are outside this implementation.

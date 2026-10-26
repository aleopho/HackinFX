# HackinFX 2.2.0 — performance and device topology

## Implemented for validation

- Target output is 30 FPS by default, selectable 20 / 30 / 60 in Lighting and
  Canvas. This is a requested rate, not a promise that every transport achieves it.
- Adaptive output keeps at most one frame per device in flight. Slow outputs no
  longer stall fast outputs; a shared timeline uses measured command latency.
  Explicit Lockstep preserves whole-group barriers when desired.
- Each device exposes completed frames, achieved command FPS, command duration,
  last-output age and busy ticks. Feedback includes these bounded measurements.
- Confirmed native PNY streaming uses one persistent worker and RM object tree
  instead of launching/re-inventorying for every frame. Exact PCI/profile checks,
  per-frame confirmation checks, cross-process locking, bounded IPC, failure
  termination and cleanup remain. GPU Lab explicitly pauses Core ownership.
- Native HID lighting handles stay open across frames. Wired Scope II 96 gains
  OpenRGB-derived 101/102 LED ANSI/ISO topology, real key IDs and matrix positions;
  per-key RGB packets are batched within the exact lighting-only allowlist.
  OMNI and unknown layout variants retain explicitly labeled whole-device color.
- Device details show mapped LED positions and distinguish LED count from zones.
- Feedback is a permanent main-navigation workspace with a focused description,
  fresh scan, report review, explicit Send/receipt and export.
- RAM probe failures remain visible on DIMMs. Host diagnostics and precise
  transaction errors distinguish driver presence from working RGB identity.
  No reset, configuration bypass, SPD or firmware writes are introduced.

## Evidence and remaining physical checks

The installed 2.1.1 Twinkle group was observed at approximately 5.5 completed
frames/s over a short sample on the development system. The new worker and
adaptive scheduler still need normal-app physical FPS measurement; fixture
throughput is not hardware performance.

macUSPCIO is now loaded and the exact 8086:7f23 host is detected. The installed
RAM helper's limited identity probe failed with its generic host/bus timeout
message. No RAM color effect has worked. New diagnostics retain precise error
information; RAM is not advertised as fixed or verified.

The agent execution sandbox denies direct PCI/driver inventory and new SMBus
user-client access. It cannot safely verify the new persistent native session
or RAM colors there. The original Twinkle look was restored after the bounded
old-helper probe. No live EFI modifications were made.

Validate on the normal installed app: all selected device FPS and frame pacing,
Twinkle/Wave visual smoothness, key-by-key Scope mapping and LED count, disconnect,
GPU Lab ownership, Radius color retention, Feedback scan/receipt/export and
WidgetKit state. Exact optical synchronization still depends on firmware and
wireless buffering. Low-rate transport limits must remain visible.

macOS 15+, x86-64; ad-hoc signed, not notarized. Original OpenRGB / NullMoth /
Radius / RIGStats notices remain, with Mola19 per-key source attribution added.
Corsair/iCUE and Razer breadth are longer-term priorities, not universal support.

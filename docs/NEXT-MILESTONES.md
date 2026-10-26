# Next release priorities

Requested by aleopho after release 2.1.1. These are planned work and acceptance
criteria, not features already shipped or guarantees for every device.

## 1. High-FPS shared effects

Observed in 2.1.1: Twinkle and other animations visibly have low frame rates.
Source inspection identifies a 20 Hz renderer ceiling (`center_core.py`), a new
Python GPU process per frame, and a synchronized group barrier whose throughput
follows the slowest output. No physical output-rate measurement is claimed yet.

- Measure achieved FPS, frame intervals, command latency and dropped/late frames
  per adapter and for the group; include bounded summaries in feedback.
- Replace per-frame native GPU process/setup with a persistent, guarded lighting
  session. Preserve exact identity checks, disconnect handling and cleanup.
- Separate rendering from transport pacing. Use a shared timeline and bounded
  output queues, with explicit latency/capability limits rather than a hidden
  slow-device bottleneck. Preserve a clear synchronization policy.
- Target smooth 60 FPS where the actual transport supports it; report slower
  device limits honestly. Raising a setting alone is not a performance fix.
- Physically compare Twinkle, Wave, Spectrum and transitions with all development
  devices active; record achieved rates and visible timing, not only mock FPS.

## 2. Real keyboard LED topology / per-key control

The current native ASUS adapter intentionally exposes one whole-keyboard zone
and sends a single RGB value through the volatile Static packet path. This is
not a complete physical-LED scan. Increasing led_count cannot add per-key control.

- Research an exact Scope II 96 per-key transport/layout, including USB and OMNI
  differences, using licensed references and bounded read-only discovery first.
- Model physical LEDs, controllable zones, key IDs and matrix positions
  separately. Use actual reported/documented topology; never invent 100 LEDs.
- Render per-key effects only when the device protocol supports them. Keep a
  clearly labeled whole-keyboard fallback for devices lacking that path.
- Validate mapping visually on the real keyboard: single keys, rows, edges and
  all-key animation, without firmware or persistent profile writes.

## 3. DRAM detection and lighting

RAM remains non-working on the development system. Diagnose loaded macUSPCIO,
OpenCore boot volume/config, service matching, SMBus access and module identity
as separate stages. Installed files are not proof of a loaded driver.

Expose the precise failing stage; distinguish DIMM inventory from an accessible
RGB controller. Extend only documented compatible hosts/modules, and retain
backups, exact matching, CRC checks and bounded transactions. Physical reboot
and color tests are required before claiming working DRAM lighting.

## 4. Visible feedback and diagnostics

Move Feedback into the permanent primary navigation, outside Advanced. Provide a
single clear form for problem description, fresh allowlisted hardware scan,
preview, explicit Send, receipt and offline JSON export. Include per-device
performance/capability data once implemented. Never silently publish private
reports as public tickets or promise next-release support from a submission.

## 5. Design overhaul around the expanded studio

Refine Lighting, device topology, Canvas and Effects as distinct workflows.
Display real LED/zone capabilities and output limits clearly. Keep controls
reachable, reduce panel noise, preserve accessibility/Reduce Motion and retain
menu-bar behavior. Hardware performance work takes precedence over decorative
animation. UI previews must not be confused with physical-device validation.

## Long-term device families

Corsair/iCUE and Razer are priority families across keyboards, mice, lighting
controllers, coolers, fans and DRAM where appropriate. Coverage requires actual
macOS transports, exact device identities/topology, licensed protocol references
and physical tests. This is roadmap scope, not a claim that all products work.

# HackinFX 2.1.1 — regression repair

- Installer recognizes GPT EFI and FAT/MBR OpenCore boot partitions. OpenCore's
  printable MBR boot signature and partition number are matched against the disk
  MBR, in addition to GPT UUIDs. The development system boots OpenCore from the
  MBR USB volume named 1401; the old GPT-only scan missed it. No live EFI was
  changed during development. A correct installation still requires reboot and
  checking that macUSPCIO is actually loaded. Backup/rollback and explicit
  selection on ambiguity remain in place.
- Lighting is the default launch/deep-link destination; setup sheets no longer
  force navigation. Confirming a GPU returns to Lighting and refreshes targets.
- Ready devices are selected on startup and rediscovery. Startup white remains
  100%, while rediscovery reuses the current selected look.
- Canvas target filtering now excludes independent-clock devices before sending
  the request, matching the Core validation. Polls cannot apply stale device
  state while a live mutation is in progress. Errors report their actual cause.
- Radius unchanged colors are periodically refreshed through the acknowledged
  preview protocol, including Static/Gradient and paused effects. No commit,
  cooling, PWM, firmware, or flash commands are added. A failed transaction stops
  rather than being retried. Steady white requires validation on real firmware.
- Effect Studio adds editable palettes (up to eight stops), animation selection,
  preview, tempo, brightness, direction, palette inspirations and save/load.
- Window and menu title: HackinFX. Author attribution remains in Credits.
- Widget rebuilt as one WidgetKit type, with Core lighting snapshots instead of
  only legacy GPU Lab events: current mode, palette, brightness, ready-device
  count, GPU model and attention state. Snapshot writes are atomic and semantic-
  change driven, refresh requests are throttled, fallback is informative. Bad
  brightness data cannot cause an integer-conversion crash. WidgetKit controls
  refresh scheduling; this does not claim live LED feedback or guarantee instant
  updates. If old diagnostic widgets remain, remove them and add HackinFX again.

Physical checks still needed: actual macUSPCIO load after installing into the
booted MBR volume and rebooting; sustained Radius white; visible output timing;
real desktop widget registration/rendering. Automated checks are not substitutes
for those observations. macOS 15+, x86-64, locally ad-hoc signed.

Group synchronization now defaults to mirrored output. Each group receives the
same frame and waits for all output commands before advancing. Measured command
durations delay faster outputs toward a common presentation time. Throughput is
limited by the slowest device; command completion is not optical LED timing.
Canvas mapping remains an explicit option. Supported ASUS keyboards receive
host-rendered whole-keyboard colors instead of independent onboard animations.

Feedback & compatibility adds a fresh automatic read-only system scan before
report review. CPU, memory, USB, PCI and storage specification fields are
allowlisted, with serials, raw trees, volume labels and mount paths excluded.
The existing configured HTTPS report inbox stores these under setup.system_hardware
alongside the user's description and Core device/errors. SourceForge issue
submission is not wired up: no credentials are embedded and no private reports
are published as public tickets. Reports are evidence for triage, not a promise
of next-release support.

Native LampArray / Kraken output rate limits now wait instead of silently dropping
a group frame. Optional system-inventory failures cannot invalidate a valid GPU
profile fingerprint; incomplete inventory is included as a scan error.

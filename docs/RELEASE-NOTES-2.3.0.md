# HackinFX 2.3.0 — device integration candidate

This source branch adds native Nanoleaf Shapes pairing and per-panel extControl v2,
a wired Scope II 96 report-zero layout correction, and atomic acknowledged Radius
frames. It has not yet been published as a release.

- Shapes NL42: private local pairing, actual panel IDs/positions, UDP v2 capped at
  10 Hz with 100ms panel interpolation. Only Shapes light types 7/8/9 are mapped;
  controller type 12 is excluded. UDP send success is not hardware confirmation.
  No cloud, scene upload, scene deletion, reset or firmware operation.
- Scope II 96 wired 0B05:1AAE: actual report 0012120000020300 yields ISO layout 203.
  Our canonical input includes report zero, so layout bytes are 5/6 rather than the
  unprefixed OpenRGB read's 4/5. Existing GPL OpenRGB map supplies 102 LED addresses.
  Physical per-key output remains pending the new app test.
- Radius: one complete validated Still-preview frame is sent as a native ACKed
  batch. Every packet still requires its ACK; other HID requests cannot interleave
  between packets of a frame. This removes Python round trips/interleaving, not
  proof that hardware jitter is eliminated. No cooling/fan/firmware writes.
- Per-output frame interval, jitter and maximum gap metrics accompany completed FPS.
  Shared clocks/latency compensation remain estimates, not optical synchrony.

Nanoleaf pairing and streaming await physical validation. This is a build candidate,
not a broad compatibility claim. Existing confirmed GPU/RAM behavior is retained.
References: Nanoleaf OpenAPI documentation and OpenRGB NanoleafController.cpp/.h
(GPL-2.0-or-later, Nikita Rushmanov), existing ASUS/Radius source notices retained.

Shapes discovery is automatic through bounded Bonjour queries. Pairing stores a
stable controller identity and a private serial hash so a changed DHCP address
can be re-resolved without a fixed-IP setup. The shared renderer includes the
100ms Shapes interpolation window in its estimated presentation timing. This
is latency compensation, not a claim of measured optical synchronization.

User follow-up: Shapes pairing and visible lighting were confirmed after installing
the integration build. This does not verify other Nanoleaf models.

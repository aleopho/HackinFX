# Next milestones

1. **Measured synchronization:** per-device frame-rate/latency metrics and a
   visual calibration wizard. Command-ack timing is not physical LED-onset timing;
   compensation should use observations rather than claim perfect synchronization.
2. **Nanoleaf Canvas extension:** discover locally, physical-button pairing,
   protect tokens, import panel coordinates, capability-check device/firmware,
   drive supported panels over local UDP external control. Do not label every
   Essentials/Matter product compatible by association.
   Official API: https://support.nanoleaf.me/hc/en-us/articles/41105798500628-API-Quick-Start-Guide
3. **Device capability matrix:** distinguish catalog identity, executable driver,
   successful command, user-confirmed lighting and host-streaming capability.
   Publish exact tested hardware/firmware rather than inflate support counts.
4. **Effect graph and groups:** layer palettes/masks, per-group brightness,
   named setup profiles and import/export portable looks without hardware IDs.
5. **Reliability:** hotplug recovery, a single-writer device arbiter across GPU
   Lab and Core, bounded diagnostic bundles, stable WidgetKit delivery and
   fault-isolated adapters. Finish these before audio/screen capture or Android.
6. **Local remote control:** authenticated, explicitly paired LAN API; Android
   controls the same daemon and scene state. Never expose unauthenticated OpenRGB
   SDK ports beyond loopback.

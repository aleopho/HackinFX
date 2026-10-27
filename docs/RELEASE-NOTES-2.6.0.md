# HackinFX 2.6.0

- Adds an opt-in Android Remote service, encrypted local-network connections, short-lived QR pairing, per-phone credentials and revocation. Android cannot access setup/probe, driver, firmware, report or shutdown endpoints. Existing loopback Core authorization remains separate.
- Adds native Android Remote 1.0.0 sources, matching dark/lime interface, live scene controls, device selection and effect/looks gallery. Tokens use Android Keystore. The Mac owns the hardware clock and updates both clients from versioned scene state.
- Rebuilds the WidgetKit data path: a read-only loopback feed replaces sandbox home-directory file access. Widget now displays HackinFX, current effect and successfully applied device count. Offline and last-applied states are explicit. Widget updates remain scheduled by macOS.
- Retains the physically confirmed MAKR 75 adapter, persisted identity-bound RAM startup and #9BED4B Twinkle at 65% speed from 2.5.1. Unknown firmware and unsupported hardware remain gated.

The Remote service stays disabled until enabled in Settings. It requires the same private IPv4 network and may need a local-network/firewall approval from macOS.

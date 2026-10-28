# HackinFX Remote for Android

Version 1.1.0: dedicated camera permission flow, pairing-details paste, visible connection errors, private crash diagnostics and animated effect gallery illustrations.

Native Android companion for HackinFX on the same Wi-Fi network. Android 8+ (API 26). Dark charcoal panels, lime controls, animated preview, device selection, 41 effects, 82 looks and saved scenes. QR pairing and manual pairing are available.

## Pair

On the Mac, install HackinFX 2.6.0 and open Settings → Android Remote. Enable local-network control, allow incoming connections when macOS asks, choose the correct private IPv4 address and click Pair a phone. In Android, scan the displayed QR directly from the Mac. Manual pairing requires the address, port, six-digit code and complete SHA-256 certificate fingerprint shown by the Mac. Pairing expires after two minutes and five failures.

TLS is mandatory and the certificate is pinned to the fingerprint received directly from the Mac. No cleartext fallback or cloud relay. Phone tokens are encrypted using Android Keystore; no backups, logging or external storage. Revoke individual phones from the Mac. The Android app cannot perform hardware probes, firmware operations, driver/EFI installation or shutdown. Stop and scene controls use the same validated Core as the macOS app.

## Build

JDK 17, Gradle 8.9, Android SDK platform 35 / build tools 35.0.0. Run `gradle -p android testDebugUnitTest lintDebug assembleRelease`. Release APKs are unsigned until signed by the project owner. Signing keys and local.properties must never be committed. CI also produces an independently signed debug APK for development.

The Mac must remain running; macOS owns lighting rendering and device transport. Effects shown in the phone preview are illustrations. Local IPv4 networks only in this first version. Pairing/firewall isolation and physical Android behavior require testing on the target network.

GPL-3.0-or-later, aleopho and contributors. ZXing Android Embedded (JourneyApps) and ZXing are Apache-2.0; retain their upstream notices in redistribution. OpenRGB, NullMoth and the macOS hardware adapters retain the credits documented by the main project.

Remote 2.0.1 adds Layer Studio, a native color wheel, the orbital FX identity and centered bottom navigation labels. The Mac remains the effect renderer and hardware owner.

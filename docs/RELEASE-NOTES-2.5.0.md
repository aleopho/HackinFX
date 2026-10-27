# HackinFX 2.5.0

## Workspace and languages

- Simplified navigation: Lighting, Devices, Canvas, Effects and Feedback. Credits and Settings remain directly accessible. Legacy GPU Lab and duplicate first-generation studio views have been removed.
- Native GPU visual setup now opens from the matching device. Existing controller identity checks, confirmation requirements and contribution preferences are preserved.
- Offline language selection: 22 locale variants covering English, German, French, Spanish, Italian, Brazilian and European Portuguese, Dutch, Polish, Czech, Swedish, Turkish, Ukrainian, Russian, Arabic, Hindi, Indonesian, Vietnamese, Japanese, Korean, Simplified and Traditional Chinese. System language or manual selection.
- Translation resources are generated at build time and require community linguistic review. Untranslated text falls back to English. Hardware identifiers, user preset names and diagnostic JSON remain unchanged. No translation service is contacted by the app.
- Canvas renders the currently applied effect behind the devices using the engine clock. Device positioning stays physically consistent in right-to-left languages. Reduce Motion disables the animated background.

No new device driver or EFI change is required for this update. MAKR 75 hardware testing and Android remote control are separate follow-up work.

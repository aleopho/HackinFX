# HackinFX 2.5.1

- Adds native per-key Corsair MAKR 75 RGB support for the physically tested wired 1B1C:2B04, firmware 7.11.104. 81 mapped key LEDs from the US reference layout; other layouts/firmwares need separate verification. No input remapping, polling-rate, firmware or profile-storage commands. Acknowledged lighting frames follow the shared effect clock; session errors stop writes until rediscovery.
- Includes all ready devices at startup, including paired Nanoleaf panels and RAM after one successful saved probe. RAM authorization persists under Documents/HackinFX/ram-rgb-profile.json. Exact inventory and RGB identities are revalidated, and bus failures revoke authorization. Users coming from versions without this profile need one successful probe in this version.
- Startup color is #9BED4B (sRGB sampled from the supplied screenshot), Twinkle at 65% speed.
- Preserves the workspace cleanup, offline languages and live Canvas from 2.5.0. Corrects several German gallery labels.
- Adds OpenLinkHub/Nikola Jurkovic credits, original source and GPL-3.0-or-later text for the MAKR adapter. The combined distribution is provided under GPL-3.0-or-later; existing per-file notices and separate engine licenses are retained.

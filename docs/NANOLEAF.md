# Nanoleaf Shapes

In Settings, choose Find Nanoleaf and select a discovered Shapes controller. Discovery uses bounded Bonjour queries, not a subnet scan. Hold its power button for
5–7 seconds until flashing, then choose Pair Shapes within 30 seconds. Pairing
obtains a token and reads the real panel layout; it does not send lighting.
After pairing, select Shapes in Lighting. Canvas uses the actual panel coordinates.
Activation enables temporary extControl v2, turns the controller on and sets its
master brightness to 100%; HackinFX then controls brightness through RGB values.
No saved scenes are added/deleted. Quitting leaves the last requested output;
select a saved scene in the Nanoleaf app to return control there.

Only Shapes model NL42, light types 7/8/9, is enabled. Controller type 12 is omitted.
Streams are capped at 10Hz with 100ms panel interpolation per the official guidance.
Tokens stay in a 0600 local file under Application Support/HackinFX/Core and are
never put in device records/feedback. No cloud account or inbound LAN API is used.
Shapes are not automatically selected at startup. If its DHCP address changes, the adapter can rediscover the same Bonjour controller identity and validate its stored serial hash before updating the local address. No fixed IP is required.

Sources:
- https://support.nanoleaf.me/hc/en-us/articles/41105798500628-API-Quick-Start-Guide
- https://nanoleaf.atlassian.net/wiki/spaces/nlapid/pages/2789310530/
- OpenRGB NanoleafController.cpp/.h, GPL-2.0-or-later, Nikita Rushmanov (2022).

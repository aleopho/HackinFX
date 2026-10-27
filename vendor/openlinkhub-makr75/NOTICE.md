# MAKR 75 protocol reference

OpenLinkHub by Nikola Jurkovic, GPL-3.0-or-later.
Source: https://github.com/jurkovic-nikola/OpenLinkHub
Reference tree: 575fec6b1b483539a9507a507a88acfc991727ed

`makr75WU.go` and `makr75.json` preserve the original protocol and US-layout reference. The derived adapter and compact layout are in `app/makr75.py` and `app/makr75-layout.json`. The packet-construction utility is in `tools/makr75_protocol.py`.

The implementation is limited to firmware inquiry, acknowledged volatile RGB commands, software-mode keepalive and restoration of hardware lighting mode. It does not implement input remapping, macros, polling-rate changes, firmware updates, wireless configuration or onboard profile storage. Supported product identifiers, interface matching and firmware gates are defined in the adapter source. Other layouts and firmware revisions require separate compatibility verification.

No personal device reports, probe transcripts or access-permission logs are included in this reference notice. The complete GPL-3.0 text is preserved in COPYING; the original sources retain their notices.

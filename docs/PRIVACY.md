# Reports, privacy and community data

HackinFX can be used locally. Hardware inventory and lighting reports are saved under `~/Library/Application Support/HackinFX`. Reusable profile and sharing preferences use macOS application preferences.

## Minimal compatibility confirmations

After the visual test, the user confirms visible success and chooses whether to share. Sharing defaults to enabled and is visible in the confirmation dialog/settings. The local profile is useful even with sharing disabled.

The confirmation includes PCI/subsystem IDs, GPU and board names, local profile identifier, tested effect names, OS/architecture/driver/app versions, timestamps, success assertions and a randomly generated installation ID. Manual name corrections carry a `user-supplied` origin and the original detected model as additional private metadata. The installation ID is for deduplication, not a hardware serial number.

`POST /verifications` upserts one row per installation/card. Retries and retests from that installation do not inflate its count. The server validates format and claimed test completeness; it cannot remotely observe LEDs or establish that every claim is true. An attacker can forge a self-report or invent installation IDs. Rate limits mitigate volume, not authenticity.

`GET /compatibility` returns a public aggregate of hardware identity, module, confirmed functions, confirmation count, source and latest date. It does not expose installation IDs, private runtime details, manual-detection metadata or troubleshooting notes. Structured compatibility rows do not expire automatically.

## Private troubleshooting reports

The user writes a description, reviews the exact JSON and explicitly presses Send. The report includes allowlisted PCI/model/driver/OS inventory, query status/timings, bounded command results, setup outcome, session events and the notes as entered. Free text can contain personal information if the user types it; review it before sending. The scanner does not intentionally collect serial numbers, hostnames, complete IORegistry trees or kernel addresses.

`POST /reports` enforces a 128 KiB body limit, format/key restrictions, prepared database statements and rate limits. A successful storage receipt contains a report ID; the app does not claim receipt when that acknowledgement is missing. Repeated submission IDs return the same stored receipt. There is no unauthenticated public read endpoint for private reports. The account owner can read them in the authenticated Cloudflare D1 console.

A daily retention task removes private troubleshooting reports older than 90 days. This retention does not remove local exports or structured community confirmations. No email alerts are configured in version 1.0.

## Service and local data

The official app uses `https://hackinfx-reports.hackinfx-report-inbox.workers.dev`. Cloudflare processes network requests, including network-level IP metadata under its applicable policies. The Worker does not place IP addresses in report or confirmation database rows. Rate limiting uses network-derived keys. No report body logging is enabled by the Worker code; platform behavior is separate from the application payload.

The shared catalog is fetched and cached even when sending new compatibility confirmations is disabled. It is informational and never downloads executable code. The app does not require an account or contain a Cloudflare token. Contributors deploying their own service use their own credentials privately and configure their own database binding.

Local folders: `Reports`, `Scans`, `Troubleshooting`, `VerificationQueue` and `compatibility.json`. Local exports persist until the user deletes them. Quitting/reinstalling the app does not automatically erase Application Support data or preferences.

For sensitive material, do not post raw reports publicly on GitHub. Use in-app review/send or describe the issue with personal information removed.

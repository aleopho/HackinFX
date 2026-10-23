# Contributing

Issues and pull requests are welcome. Read [architecture](docs/ARCHITECTURE.md), [compatibility](docs/COMPATIBILITY.md) and [development](docs/DEVELOPMENT.md) first.

Include relevant offline tests and a concise explanation of behavior changes. Preserve unknown-device rejection, bounded transactions, error cleanup and separation of public catalog/private reports. Do not enable a broad family of cards based only on a matching marketing name.

Hardware profiles need exact PCI/subsystem identity, documented protocol and transport evidence, source/license attribution and visible per-effect test results on the actual board. Mocked successful commands are not hardware verification. Note untested behavior honestly.

Contributions to HackinFX must be available under GPL-2.0-or-later and retain applicable third-party notices. Do not submit proprietary driver code, credentials, private reports or unrelated raw system data. NullMoth is a separate dependency; this repository does not redistribute its driver or change its terms.

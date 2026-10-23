# Building and validation

## Native app

Use macOS with Xcode command line tools and Python 3. No third-party Python packages are required.

```sh
python3 app/build_community.py
python3 app/package_dmg.py
```

The compiler targets `x86_64-apple-macos13.0` and links AppKit/SwiftUI. The build copies runtime sources/assets/licenses into `app/HackinFX.app`, embeds the corresponding source and applies a local ad-hoc codesign. Packaging creates a compressed drag-and-drop DMG in the repository root. It does not notarize the app or mount a temporary disk image while building.

Runtime dependencies are the installed NVRM service and `/usr/bin/python3`. Building does not access GPU hardware. Tests use fake transports and fixture inventories. Do not add real hardware operations to CI.

## Offline tests

```sh
(cd app && python3 -m unittest discover -s tests -v)
swiftc app/SetupSupport.swift app/tests/SetupSupportTests.swift -o /tmp/hackinfx-profile-tests
/tmp/hackinfx-profile-tests
(cd report-inbox && node --test *.test.mjs)
(cd report-inbox && python3 -m unittest test_schema.py)
```

Validated for 1.0.0: 38 Python transport/scanner tests, 18 Swift profile/queue assertions, 11 backend tests and one SQLite schema/upsert test. They cover ABI/layout, metadata-only operation, packet construction, bounded writes, guard rejection, first-failure behavior/cleanup, scanner redaction, driver fingerprint changes, exact profile matching, legacy-profile rejection, queue persistence/supersession, payload validation, receipts/deduplication and private/public separation.

Live synthetic tests against the deployed Worker/D1 verified report receipts/retries, confirmation upsert, public aggregation and rejection of unauthenticated private report reads. A native Foundation URLSession client using the app's Codable models uploaded, retried and decoded the live catalog. Manual identity metadata was checked in D1. Synthetic records were then removed. No real private hardware report was published for these tests.

## Validation limits

Automated checks do not establish visible LED operation. The development card's effects were visually confirmed by aleopho separately. New native first-run/dialog behavior and real DMG installation still need a normal desktop run; the development sandbox prevented native AppKit rendering. Sequoia/Tahoe appearance and sleep/wake/restart behavior are not claimed as fully validated. Release notes retain these limits.

The `--render-preview` and `--render-setup-preview` native app options render UI with sample hardware data when run in a normal graphical session. Such output must be captioned as a sample-data UI preview, not a live hardware screenshot.

## Release checks

- Run the tests and build. Check `codesign --verify --deep --strict app/HackinFX.app` and `hdiutil verify HackinFX-aleopho-1.0.0.dmg`.
- Check version, embedded source, license notices and endpoint configuration.
- Test the native first-run/saved-profile/failure/offline flows on real supported hardware.
- Make SHA-256 checksums for distributable assets. Attach DMG/source/checksums to the release, with corresponding source available at the tag.
- Publish only selected source/docs/assets, never Application Support reports, device trees, credentials, local auth folders or node_modules.

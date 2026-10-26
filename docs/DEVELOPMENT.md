# Build, tests and release validation

## Build

Use macOS with Python 3 and full Xcode for the real WidgetKit extension. The
application and packaged helpers target **x86_64 macOS 15+**. Command-line-tools-
only builds omit the compiled widget and are not the complete release bundle.

```sh
python3 tools/prepare_openrgb_runtime.py
python3 app/build_community.py
python3 tools/check_app_bundle.py
python3 tools/verify_openrgb_runtime.py
python3 app/package_installer.py
python3 tools/verify_installer.py HackinFX-2.1.1-Installer.pkg
python3 app/package_dmg.py
python3 tools/verify_dmg.py HackinFX-aleopho-2.1.1.dmg
```

Runtime preparation is a separate network-enabled step. It verifies pinned
OpenRGB binary/source hashes and stages the dependency closure, corresponding
source archives and notices. Build output embeds app source and notices and
ad-hoc signs nested code. No Developer ID or notarization is performed.

## Tests

```sh
PYTHONPATH=app python3 -m unittest discover -s app/tests -v
node app/tests/verify-radius-port.mjs
(cd report-inbox && node --test *.test.mjs)
(cd report-inbox && python3 -m unittest test_schema.py)
swiftc app/SetupSupport.swift app/tests/SetupSupportTests.swift -o /tmp/hackinfx-profile-tests
/tmp/hackinfx-profile-tests
swiftc app/ReleaseVersion.swift app/tests/ReleaseVersionTests.swift -o /tmp/hackinfx-version-tests
/tmp/hackinfx-version-tests
```

2.1.1 has **150 Python regression tests**, plus native profile/version, backend,
protocol, catalog, bundle/signature and packaging checks. The runtime helpers
provide offline `--self-test` modes. Tests use fixtures/simulated transports;
never add real bus scans or lighting writes to CI.

The tested application-source commit is
`7d5dbfe576d74371bb553c2d2cb32407a4e7eab0`:
[successful complete build](https://github.com/aleopho/HackinFX/actions/runs/40248507390).
The release tag additionally includes refreshed documentation, the user-supplied
screenshot and release automation. Tagged source is the release reference.

## Release process

The release workflow runs on Intel macOS, prepares the pinned engine, executes
checks, builds the real widget and validates PKG/DMG signatures and payloads.
It publishes a regular GitHub release with PKG, DMG, tagged source ZIP and
SHA-256 checksums. GPL source and bundled dependency notices remain available.
Do not commit generated packages, personal reports, Application Support state,
credentials or dependency caches to the source tree.

Actual LED behavior, RAM driver load after reboot, optical group timing and
WidgetKit desktop registration require physical testing. RAM is currently not
working on the development machine. Automated success must never be represented
as universal device support. Sample-data UI renders must be captioned; the 2.1.1
README screenshot is a genuine user-provided desktop capture.

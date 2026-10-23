# HackinFX report inbox

Cloudflare Worker + D1 backend. Source: GPL-2.0-or-later; full license in COPYING. Official service: https://hackinfx-reports.hackinfx-report-inbox.workers.dev. This repository includes no credentials or owner database ID.

## API

- GET /health: service health.
- POST /reports: reviewed private troubleshooting JSON; maximum 128 KiB, validation, prepared storage and per-network rate limit. A 201 receipt contains report_id only after stored-row confirmation. Duplicate submission_id returns the existing receipt. There is no public report-read API.
- POST /verifications: minimal complete visual-test confirmation. User/transport/basic-RGB success and consistent effect/test count are required. One upsert per random installation ID/card prevents repeat submissions from inflating that installation's count; newer observations supersede older ones.
- GET /compatibility: safe public aggregate of card/vendor/subsystem identity, module, effects/count/source/date. No installation IDs, private notes, original detection metadata or environment details. Claims are self-reported, not independently audited.

The daily scheduled task deletes private reports older than 90 days. Structured compatibility confirmations remain until the account owner removes them. The code does not log report bodies or store network IPs in report rows. Cloudflare still handles network metadata. No email alerts or admin web UI are included. Read private rows only through an authenticated D1 console. See ../docs/PRIVACY.md.

## Deploy your own service

1. Install dependencies from package.json (current compatible Node.js and npm). Run npx wrangler login, handling OAuth in your browser. Keep tokens outside the repository.
2. Run npx wrangler d1 create hackinfx-reports. Put its database_id in your local wrangler.toml. Preserve binding name DB.
3. For a NEW database, run npx wrangler d1 execute hackinfx-reports --remote --file=schema.sql.
4. For an existing pre-identity-metadata database, apply migrations/0002-identity.sql once instead of assuming CREATE TABLE IF NOT EXISTS upgrades existing columns. Do not apply the ALTER migration to a fresh schema that already contains those columns.
5. Run npx wrangler deploy. It publishes to your workers.dev address and configures the daily trigger. No custom domain is required.
6. Use synthetic disposable data to test receipts, retries, real persistence, catalog aggregation and private/public separation. Remove synthetic rows afterwards.
7. Change app/report-endpoint.json to your HTTPS /reports URL before building a fork. /verifications and /compatibility are derived as sibling endpoints. Never embed a Cloudflare token in the app.

The official 1.0 deployment passed synthetic real D1/HTTP/native-URLSession checks; this does not automatically validate a fork's deployment.

## Test

node --test *.test.mjs
python3 -m unittest test_schema.py

The rate limiter is approximate, not authentication. Public self-reporting can be forged. A catalog entry never enables a local RGB module.

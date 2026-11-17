# Battery Timeline · Tek-Qubit concept

A working local dealership application: service capture → pack-aware evidence Timeline → appraised offer → dealer-issued buyer report. Independent hackathon concept; no Tekion endorsement, certification, or private-system integration.

## Setup and start

Python 3.13 and Node 22 are the tested versions.

```sh
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.lock
npm ci
./scripts/start.sh
```

Open **http://localhost:5173** and choose a seeded manager, technician or sales session. The backend validates the selected role. API documentation: http://localhost:8000/docs.

SQLite records persist in `data/battery.db`; server-managed images persist in `data/uploads`. Migrations preserve existing records. The 26-vehicle synthetic inventory is deterministic, with two additive warranty examples. No destructive reset occurs on startup.

Configuration is read from environment variables. To load the shell-compatible example:

```sh
cp .env.example .env
set -a
. ./.env
set +a
./scripts/start.sh
```

The demo clock defaults to Nov 16, 2026. Change `ASSESSMENT_DATE` before creating fresh demo records. Normal mode uses the actual date. `DEMO_MODE=false` disables the local demo login; production authentication is outside this hackathon build.

## Photo capture

Manual entry always works. To enable real local OCR on macOS:

```sh
./scripts/build-ocr.sh
```

This compiles the included Apple Vision adapter using the installed Swift toolchain. On other systems, install Tesseract and set `TESSERACT_BIN=/absolute/path/to/tesseract`. No API key is required. The browser explicitly requests extraction and a human must confirm the result. Unsupported/unavailable OCR preserves the image for manual review.

Labeled synthetic examples: `data/seed/sample-health.png` and `data/seed/sample-charge.png`. These are sample diagnostic screens, not OEM certificates. The health example extracts 92%; the charge example stays ambiguous. Actual macOS OCR execution and both cases were verified in browser tests.

## Verification

```sh
.venv/bin/pip install -r apps/api/requirements-dev.txt
.venv/bin/ruff check apps/api scripts
npm run format:check
npm run typecheck
.venv/bin/python -m pytest apps/api/tests -q
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests start their own backend and frontend on ports 8001/5175 with a disposable database. They do not mutate the working demo. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` only to use an existing Chromium binary. The OCR test requires one configured local OCR provider. Screenshots and a sample PDF are saved in `docs/`. The suite includes axe WCAG A/AA checks at desktop/mobile widths; automated scans do not establish full accessibility conformance. See `docs/accessibility-results.json` for violations and checks requiring manual inspection.

On macOS, after browser tests:

```sh
.venv/bin/python scripts/verify_pdf.py
```

This renders every PDF page, compares displayed values with the captured public snapshot, and decodes the exact-version QR. Generated QA QR URLs use the disposable test server; create a report in the working app for an ongoing demonstration.

Explicit development reset (stop the working backend first):

```sh
.venv/bin/python -m scripts.reset --confirm-demo-reset
```

This deletes demo records/tokens and reseeds 26 vehicles. Image files are retained.

## Public data and reports

`DATA_MODE=fixture` makes no external calls and is labeled explicitly. `DATA_MODE=live` enables server-side vPIC identity, model-level recall and EPA variant lookups from each vehicle's Sources tab. Timeouts, bounded retries, persistent cache fallback, response validation and retrieval timestamps are implemented. Live reads now pass for all three providers. The smoke check found eight EPA variants, checked a full record against its menu, and verified cache fallback using a simulated outage against the real retrieved payloads. The vPIC documentation example is partial and explicitly requires review; synthetic inventory VINs are not verified. Run `.venv/bin/python -m scripts.smoke_public` to repeat in a temporary database; results are saved in `docs/public-smoke.json`.

Managers explicitly resolve identity or select an EPA trim/drive/battery option. Original EPA-rated range never changes health. Active warranty rules cover **US 2023 Ford Mustang Mach-E and Chevrolet Bolt EV/EUV**. The reviewed Hyundai Ioniq 5 document remains provisional because capacity/transfer language needs clarification. Unsupported years remain unknown. See [source review](docs/warranty-source-review.md).

`PUBLIC_BASE_URL` determines QR links. A localhost URL works only on the host computer, not another phone. LAN/reverse-proxy access requires deliberate binding/origin configuration. No external deployment or messaging is performed.

Reports use immutable sanitized snapshots, opaque tokens, expiry and revocation. Sales responses exclude internal offer data and private evidence. Report snapshots exclude customer records, technician identities, notes, attachments and internal pricing. New readings do not rewrite accepted offers or published versions.

## Optional PostgreSQL

Both SQLite and PostgreSQL were exercised against the API/domain/concurrency suite. Optional local service:

```sh
.venv/bin/pip install -r apps/api/requirements-postgres.txt
docker compose up -d db
DATABASE_URL='postgresql+psycopg://battery:local-demo-only@localhost:5432/battery_timeline' ./scripts/start.sh
```

PostgreSQL mutation transactions use an application advisory lock; SQLite uses BEGIN IMMEDIATE. Idempotency, decision versions and multiprocess public counters are tested on both. The database suite creates a unique schema and drops only that test schema:

```sh
TEST_DATABASE_URL='postgresql+psycopg://battery:local-demo-only@localhost:5432/battery_timeline' .venv/bin/python -m pytest apps/api/tests -q
```

The database role needs CREATE SCHEMA permission. Tests never use the working DATABASE_URL implicitly. Verification here used an isolated PostgreSQL 18.6 binary because Docker was unavailable; the supplied PostgreSQL 17 Compose image has not been started here.

## Handoff

See [build status](docs/build-status.md), [acceptance follow-up](docs/remaining-5-percent.md), [four-minute demo](docs/demo-script.md), [methodology](docs/methodology.md), and [integration boundaries](docs/integration-boundaries.md). Persistence uses explicitly migrated SQLAlchemy JSON aggregates plus typed contracts and indexed token/rate-limit tables; it is not a fully normalized relational domain model. The interface uses scoped CSS rather than Tailwind. The build is a hackathon concept, not a production certification claim.

## Additional acceptance checks

A clean dependency install can be reproduced without touching working records:

```sh
.venv/bin/python scripts/verify_clean_install.py
```

This copies source into a temporary directory, creates a new Python environment, installs both lockfiles, runs backend tests/lint and builds the frontend. It needs download access. The completed same-machine result is in `docs/clean-install.json`; it is not a second-machine test.

The touch capture-to-report journey also runs in WebKit:

```sh
npx playwright install webkit
PLAYWRIGHT_BROWSER=webkit npm run test:e2e -- tests/mobile-browser.spec.ts
```

This is mobile browser emulation, not a physical phone/keyboard test.

For an actual phone on the same trusted LAN, stop the local preview first and replace the placeholder with the computer's LAN address:

```sh
WEB_HOST=0.0.0.0 PUBLIC_BASE_URL=http://YOUR_LAN_IP:5173 ./scripts/start.sh
```

The API remains on loopback and Vite proxies its requests. Open the same URL on the phone; publish a new report so its QR uses the reachable base URL. This exposes the explicitly labeled demo role login to that LAN. Defaults remain loopback-only. Do not reuse test-server QR artifacts for the demonstration.

# Battery Timeline — resumed build, approximately 99% complete

Updated Nov 17, 2026. This is an engineering progress estimate, not a validation or certification score. The user lifted the earlier 95% stop after their usage reset. The core capture → Timeline → appraisal → buyer report workflow is implemented and persistent.

## Latest build — reference-led frontend refresh

The requested interface refresh is implemented. Overall completion remains approximately **99%**, with the human/environment acceptance work below comprising the remaining approximately **1%**. The three user-supplied desktop/mobile banking screenshots guided spacing, navigation and visual hierarchy; no banking content or third-party logos were added.

- Replaced the charcoal sidebar with a white workspace shell, emerald active navigation, subtle neutral surfaces and quieter rounded cards. Desktop queue filters and rows use the same theme.
- Added prominent teal health cards to the vehicle workspace and buyer web report, with observed readings and evidence limitations still distinct from estimates. Appraisal calculations and persisted records are unchanged.
- Added labeled fixed bottom navigation on phones, active states for nested routes, separate vehicle cards, visible field labels and full-width search above two useful filters. Capture confirmation clears the bottom navigation and safe area.
- Manual capture opens directly to review fields. A visible Upload photo option reveals the existing real upload/OCR flow; attached evidence survives navigation and stays visible for review. Increased mobile input text to 16 px to avoid focus zoom on common mobile browsers.
- Verified this revision with **10 Chromium browser tests passed**, **1 WebKit touch journey passed**, TypeScript/production build and Prettier. Seven-screen axe scans have zero enabled-rule violations. The first pass caught summary-card text contrast below 4.5:1; that was corrected and the full suite rerun successfully. Chart/occluded-content contrast remains inconclusive to automation, not a conformance claim.
- Inspected actual rendered screenshots at 1440, 768 and 390 px, including Chromium and WebKit phone capture. Fixed narrow mobile filters found in the screenshot review. Added browser checks for bottom-navigation routing, nested active state, default manual input and confirmation/nav non-overlap.

Review artifacts: `queue-desktop.png`, `detail-desktop.png`, `detail-tablet.png`, `queue-mobile.png`, `capture-viewport-chromium.png`, `capture-viewport-webkit.png`, `detail-viewport-chromium.png`, `report-mobile.png`. Earlier verification below describes preceding builds. No backend/domain code or PDF layout changed in this refresh; the browser journey still verifies the report/PDF handoff.

## Completed this build

- Added successful live-source verification, provider-specific recall spelling, EPA family/variant discovery and full-record matching. Partial vPIC decodes are shown for review rather than mislabeled as outage or verified identity. EPA subrequest source history is retained and visible. `docs/public-smoke.json` records live results, eight options and truthful cache fallback against those payloads.
- Added serialized PostgreSQL mutation transactions, isolated PostgreSQL test schemas, atomic multiprocess public rate counters and sanitized retryable database errors. Fixed the reserved `window` SQL column usage. No working records were reset.
- Added exact-year 2023 Chevrolet Bolt EV/EUV rules from a manufacturer-hosted booklet, with its 60% capacity threshold. Hyundai remains explicitly provisional. Known mileage/time headroom survives a missing input for the other limit. Unsupported jurisdictions/eligibility remain unknown.
- Added expiry recovery preserving capture drafts; retry after a lost confirmation response reuses the existing draft instead of submitting another observation. Upload/extraction/save operation labels now reflect the actual action. Legacy sessions without expiry fail closed.
- Added defensive date/value filtering to the plain-Python engine for malformed imported observations. Existing valid input behavior and immutable saved snapshots are preserved.
- Added axe accessibility scans across seven desktop/mobile screens. Fixed secondary-text contrast, supporting text smaller than 12 px, loading status semantics and navigation labels. Improved source/coverage explanations and refreshed final scope/methodology/integration documentation.

## Verification

- **37 tests passed on SQLite** and **37 on PostgreSQL 18.6**. Includes eight competing requests for confirmation/acceptance/publication, unique report versions, two drafts for the same observation, four-process rate counters, transaction rollback, expiry, partial warranty inputs and malformed imported readings.
- **Nine browser journeys passed** in the last complete run: real OCR/SOC, draft recovery, corrections, role privacy, policy/warranty edits, session recovery, keyboard source access, lost-response retry, full report/PDF handoff and automated accessibility scans. The final complete run passed all nine; the two affected browser checks (workflow and accessibility) passed again after the final PDF/tablet-link polish.
- Axe found zero violations among enabled WCAG A/AA checks on seven screens. Chart contrast checks remain inconclusive to the automated scanner; that is not full accessibility conformance. Desktop/mobile screenshots inspected. Final screenshot capture waits for loaded records. Loaded layouts at 390/768/1440 px were inspected; a direct appraisal shortcut now follows the battery summary on smaller screens.
- Ruff lint and format, Prettier format, TypeScript and production build passed. The final rebuild after loading labels and the tablet shortcut passed. One upstream Starlette/anyio TestClient deprecation warning remains; no large bundle warning.
- PDF verification passed for two rendered pages, matching snapshot values, exact-version QR and absent internal valuation labels. A final visual check found and fixed an orphaned warranty heading; verification now also checks that its text stays on the same page.
- Live public smoke passed: partial documentation VIN (review required), six model-level recall records, eight EPA variants, matching full-record probe and simulated outage cache fallback. Synthetic inventory VINs were not claimed as verified.

## Run

`./scripts/start.sh` → http://localhost:5173; API docs http://localhost:8000/docs. See README for first install, pinned dependencies, native OCR and optional PostgreSQL. Browser tests use disposable database/ports 8001/5175. PostgreSQL tests use a fresh schema through TEST_DATABASE_URL. All staff data and uploads remain durable in the working database.

No paid API credentials are required for the implemented path. macOS OCR uses the included compiled Apple Vision adapter; other platforms can configure Tesseract. Voice/assistant/test booking remain deferred. No external deployment or messaging occurred. The temporary PostgreSQL acceptance server was stopped after final checks; the working preview remains on ports 8000/5173.

## Remaining approximately 1%

See [acceptance follow-up](remaining-5-percent.md): actual-phone camera/keyboard, real screen-reader operation, second-machine setup and the optional Docker/Tesseract execution. Hyundai manufacturer clarification and broader OEM comparability remain honest unsupported areas, not silently filled with assumptions. The reviewed Ford/Chevrolet paths work. No Tekion/APC integration, production authentication or certification is claimed.

The source checkpoint is prepared for the configured GitHub repository, `sneharc16/tekion`, on `main`. Runtime databases, uploaded attachments, environment secrets, installed dependencies and compiled local OCR binaries are excluded from Git. The full original master brief is in the user conversation, not a repository file.

## Final artifact pass

- Full browser suite: 9 passed in 22.1 seconds on this machine with isolated local servers; this is test-run duration, not a product performance claim. Final targeted workflow/accessibility checks: 2 passed after PDF pagination and tablet action changes.
- Production build and TypeScript passed; Ruff and Prettier checks passed.
- Final PDF check includes snapshot values, exact QR URL, no internal valuation labels and warranty heading/body pagination. Both pages inspected.
- The previous 95% snapshot is preserved in build-history.md. Remaining human/environment acceptance is documented in remaining-5-percent.md.

## Continued acceptance pass

- Fresh installation succeeded in a disposable source copy on this macOS machine: new Python environment, pinned Python/dev packages, npm ci, lint, all 37 backend tests and production build. See clean-install.json and clean-install.log. This does not substitute for a different machine/OS.
- WebKit 27.2 touch emulation at 390×844 passed the manual capture → appraisal → report/QR journey and verified two separate pack-series curves. Source screenshots: report-touch-webkit.png and pack-touch-webkit.png. Real mobile keyboard/camera and screen-reader acceptance remain pending.
- Startup now supports optional WEB_HOST/WEB_PORT for deliberate trusted-LAN phone testing; default binding remains loopback. README documents matching PUBLIC_BASE_URL and explains demo-login visibility.

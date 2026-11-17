# Build checkpoint — Nov 16, 2026

## Overall

Working local end-to-end demonstration; approximately 60% of the full brief implemented (engineering estimate, not an acceptance score). Full master-brief completion is not claimed. Repository was empty; no AGENTS.md or named master-prompt file existed. The complete supplied chat brief governed implementation.

## Completed and verified

- React/TypeScript/Vite shell, charcoal/teal design, 24 synthetic vehicles, real queue counts and URL filters, desktop/mobile layouts.
- FastAPI, SQLAlchemy, explicit migration, persistent SQLite and uploads, explicit reset, server-validated demo sessions and role/tenant checks.
- Source-aware deterministic health intervals, independent-date evidence rubric, pack split, guarded robust trend and conditional scenarios.
- Manual draft/confirmation flow, SOC guard, dates/ranges/units/odometer checks, duplicate test check, backend recalculation, local unfinished-form persistence.
- Immutable appraisal and override snapshots, required review reasons, battery-inclusive base protection, newer-evidence indication, audit log.
- Report drafts/publication/revocation, sanitized immutable snapshot, opaque public token, QR and downloadable PDF, noindex API headers and simple process-local rate limiting.
- Public VIN/recall/EPA adapter code with fixture/live modes, bounded timeout/retry and cached/unavailable states; mocked transport tests.
- Reviewed Ford 2023 Mustang Mach-E warranty rule and domain boundary tests. Vehicle application remains unknown without verified eligibility inputs.
- Optional local Tesseract adapter and review UI; no OCR binary installed, so actual OCR execution is unverified.

## Actual checks

- `npm run build`: TypeScript and production build passed. Bundle warning remains (~709 kB before gzip).
- `.venv/bin/python -m pytest apps/api/tests -q`: seven tests passed before final PDF/security changes; rerun recorded below when complete.
- Playwright critical journey passed: login, SOC negative case, manual capture, updated workspace, accepted offer, published report, public page and PDF download; 390/768/1440 px overflow checks.
- Screenshots generated in docs. Desktop queue, tablet detail, mobile capture and report inspected. Found/fixed oversized search field and chart resize overflow. Mobile select fields changed to one column after inspection.
- PDF first version inspected visually; replaced with paginated ReportLab layout including chart and all rows. Final PDF validation pending below.
- `npm audit` after compatible package upgrades: zero vulnerabilities reported by installation audit. Initial build had five advisories; affected packages were upgraded.
- No separate lint command. No live external-provider smoke test or configured OCR execution. Python TestClient emits one dependency deprecation warning.

## Milestones

1. Foundation/design/persistence: substantially complete.
2. Signature workflow: working; method compatibility, exclusions, amendments and richer metadata still incomplete.
3. Decisions/integrations: partial; acceptance works, but policy editing, editable base value/inclusion UI, warranty eligibility/editor and live adapter resolution UI remain.
4. Buyer handoff: working; expiry and broader publication edge cases remain.
5. Extraction/polish/verification: partial; local optional OCR path, no provider execution, incomplete full acceptance matrix.

## Exact next steps

1. Implement normalized typed PackSegment/Source/Warranty/Policy records and versioned policy/base provenance editing, then wire authoritative preview recomputation.
2. Wire reviewed warranty rule into eligibility editor and cards; verify additional exact Ford/Chevrolet/Hyundai model years. Seed actual near-expiry and known-eligibility cases without treating demo evidence as manufacturer verification.
3. Add reading amendment/supersession/exclusion review and explicit method/reference capacity compatibility. Add durable uniqueness constraints, concurrent-decision versioning and idempotent report creation.
4. Complete source UI for VIN manual resolution, EPA option selection and recall source cards. Smoke-test live providers with real public test VINs, never demo VINs.
5. Exercise installed OCR against labeled sample SOH/SOC images; preserve attachment draft across navigation, show transcript and ambiguity/confidence flags. Voice remains stretch.
6. Complete response schemas, production auth/config separation, durable/public-scoped token lookup, rate-limit storage, report expiration, broader permission UX and full negative test matrix. PostgreSQL is not verified.

## Run

`./scripts/start.sh` after README setup. Frontend http://localhost:5173, API http://localhost:8000/docs. Fixed demo clock Nov 16, 2026. Existing database is preserved. Localhost QR does not work on another phone.

## Final regression result for this checkpoint

- Eight backend tests passed after the final PDF, SQLite write-serialization, session-expiry and observed-reading fixes.
- Final browser journey passed in 8.7 seconds on local Chromium, including 390/768/1440 px overflow assertions and PDF download. This is test-run duration, not an application performance benchmark.
- Final production build passed; bundle-size warning remains.
- Revised PDF first page visually inspected. Multipage flow is implemented, but every generated page/QR decode was not visually or independently verified.
- Latest source and all handoff documents are saved. No deployment or Git commit was performed. Local preview was started for QA.

# Continuation checkpoint — Build 4

This section supersedes the earlier progress estimates and next-step list above. Approximately **75% implemented / 25% remaining** against the master brief, an engineering estimate rather than an acceptance score.

## Implemented in this continuation

- Migration 002 safely changes record identity to `(kind, id, dealer)`, preserving existing data and preventing same-ID cross-dealer overwrite.
- Manager-editable starting appraisal amount, provenance, effective date and explicit battery-included/unknown state. Backend recomputes preview after save.
- Immutable dealer policy versions with configurable reference health, per-point amount, cap and limited-evidence reserve. Accepted decisions retain their original policy snapshot. Battery-inclusive bases receive neither a second adjustment nor a reserve.
- Appraisal decision revision and policy-version guards; changed inputs/policy/decision reject stale submissions. Idempotency verifies the decision request payload.
- Warranty evidence editor and authoritative coverage cards with separate remaining days/miles, manufacturer source, capacity condition and unknown eligibility states. Only the previously reviewed 2023 US Ford rule is activated. California exceptions stay pending review.
- Two additive synthetic Ford examples, EV-2425 near mileage limit and EV-2426 with missing warranty inputs. Existing records preserved; inventory now 26 vehicles.
- Audited reading exclusion preserves original observations/amendment record and recalculates health. Published snapshots remain fixed. Correction/supersession UI is still pending.
- Health engine partitions BMS capacity estimates and measured usable-energy methods; invalid physical values are excluded with reasons. Repeated same-date sources use the largest uncertainty allowance. Legacy readings retain an explicitly documented BMS method assumption.
- Capture retains uploaded-image reference across navigation; OCR transcript is reviewable and ambiguous new uploads clear prior candidate values. Actual OCR executable remains untested.
- Report creation operation IDs prevent duplicate retry versions. New snapshots have a 90-day validity period. Expiry blocks public web payload, QR and PDF; errors also get noindex/no-store headers. Existing legacy snapshots retain their original payloads and lack expiry.
- Preview startup fails on occupied frontend port instead of silently moving URLs. Backend-start failure is reported explicitly.

## Verification

- 15 backend/domain/API tests passed after the final uncertainty/idempotency changes.
- Production build and TypeScript checks passed. Existing large-bundle warning remains (~718 kB before gzip); no lint check configured.
- Two browser journeys passed: capture → acceptance → publication → public PDF; policy versioning → edited base/inclusion → warranty evidence → reading exclusion.
- Desktop/mobile warranty screenshots inspected. Screenshot capture now scrolls to the top first so fixed navigation is represented correctly. Existing 390/768/1440 px overflow checks retained.
- Initial browser failures came from the stale previous backend and a test navigating before login completed; these were corrected and rerun. A new exclusion-schema test initially failed and was fixed before the passing suite.

## Next concrete work

1. Complete per-vehicle public-source UI, manual VIN resolution, EPA selection and exact-variant persistence; smoke-test actual live transports. Existing adapters are still server-only and mock-transport tested.
2. Complete amendment/supersession, pack/source typed records, reference-capacity compatibility and additional seed edge cases. Legacy method defaults need explicit migration provenance in the UI.
3. Harden permission presentation and staff read schemas (especially sales summaries), public token lookup beyond the demo tenant, durable rate limiting, report version freshness markers and remaining concurrency paths.
4. Verify additional exact OEM warranty combinations; do not generalize the Ford rule to other years or Chevrolet/Hyundai. Warranty UI currently displays days rather than calendar years/months.
5. Exercise installed Tesseract on labeled SOH/SOC sample images, expand extraction metadata and review. Voice/assistant/test-task stretch remains deferred.
6. Complete PDF all-page visual/QR verification and remaining acceptance tests, improve bundle splitting and source formatting. PostgreSQL remains unverified. Production authentication/deployment is outside the verified local demo.

Run remains `./scripts/start.sh` after README setup. Browser tests mutate demo records; reset explicitly when a fresh demonstration is required. No destructive reset or external deployment was performed in this continuation.


---

# Battery Timeline — 95% implementation checkpoint

**Target:** stop with approximately 5% remaining at the user's explicit request, then resume after their limit is restored. Percentages are engineering estimates; no certification or statistical validation is claimed.

## Working product

- React/TypeScript/Vite application with responsive charcoal/teal shell, 26 synthetic vehicles, actual queue counts, URL search/filters, scenario selector, and desktop/mobile evidence workspaces.
- FastAPI/Pydantic/SQLAlchemy backend, durable SQLite, three explicit migrations, dealer-scoped record identities, local simulated DMS adapter, file-storage boundary, typed pack/source/public-report contracts and explicit reset.
- Server-validated demo roles and expiring HttpOnly sessions; sales/technician summaries exclude private appraisal fields; private attachment access and mutations are permission checked. Logout clears the session. Public routes are noindex/no-store and rate-limited in the database.
- Persistent service visits, actual photo upload/OCR and full manual capture, draft/confirmation boundary, preserved local drafts and attachments, reference/method/unit/date/value/odometer checks, duplicate checks, pack-date validation, and detected-VIN mismatch guard.
- Actual local Apple Vision OCR exercised on labeled synthetic health and SOC examples. Tesseract adapter is configurable on other platforms; its executable was not exercised here. No paid credential required.
- Deterministic source-, reference-, method- and pack-aware assessment, robust gated trend, cautious conditional scenarios, independent-date rubric, stale/conflict warnings, visible old/new pack boundaries, event markers and accessible evidence list.
- Audited exclusions and corrections with retained original observations; new assessments update without rewriting accepted decisions or published reports.
- Dealer-editable starting value/provenance/battery inclusion, immutable policy versions, explicit adjustments/reserves/caps, no double counting, manager acceptance/override, stale-decision guards and retry-safe operations.
- Reviewed US 2023 Ford Mustang Mach-E warranty rule, evidence editor, separate days/miles remaining and source/threshold display. Unsupported model years and missing eligibility remain unknown. Synthetic known/missing warranty examples included.
- Public-source UI with explicit live/cache/fixture/unavailable labels, manual identity resolution, model-level recall context, explicit EPA selection and variant checks. Live services returned unavailable here; mock transports cover successful and ambiguous results.
- Report preview/publish/revoke/expire, sanitized immutable snapshots, indexed opaque tokens across dealers, new-evidence flags, QR and paginated PDF from the same snapshot. Customer note templates are saved with accepted decisions; nothing is sent externally.

## Verification at this checkpoint

- Latest complete browser suite: five journeys passed on an isolated disposable database. Covers real OCR/SOC ambiguity, draft recovery, corrections, read-only roles, policy/base/warranty editing, exclusions, capture-to-report publication and PDF download.
- Backend test suite expanded beyond 23 tests with final pack/service/model checks; final result recorded below after regression.
- Ruff and Prettier are installed with repeatable commands; TypeScript and production builds run. Source formatted into readable files.
- Bundle split into application/charts/icons; prior >500 kB chunk warning removed.
- Actual desktop/mobile screenshots inspected, including OCR capture and warranty forms; automated overflow checks cover 390, 768 and 1440 px.
- Both PDF pages visually inspected. Native PDF/QR verification confirmed displayed values against the public snapshot and decoded the exact published-version URL. `docs/pdf-verification.json` records the result.
- Live network smoke results are in `docs/public-smoke.json`: all three services unavailable. This is not represented as successful live integration.

## Run / resume

See README for exact setup. `./scripts/start.sh` serves http://localhost:5173 and API docs on port 8000. Optional `./scripts/build-ocr.sh` enables native macOS OCR. No destructive reset or external deployment performed. Browser tests now start their own servers on 8001/5175 and preserve the working database.

The exact reserved work is in **[remaining-5-percent.md](remaining-5-percent.md)**. Earlier build logs are retained in **[build-history.md](build-history.md)**. Do not restart the project or overwrite existing records on resume.

## Final recorded results

- **27 backend/domain/API tests passed.** Coverage includes SOC/draft guards, duplicates/correlation, stale/conflicting readings, pack/method/reference boundaries, corrections, unit conversion, model mismatch, warranty boundaries, policy/decision immutability, idempotency, tenant isolation, staff privacy, upload validation, EPA selection, public expiry/revocation and rate limits.
- **Five isolated browser journeys passed**, including actual local OCR; none skipped in this environment. Screenshots and snapshot/PDF artifacts were regenerated.
- **Ruff lint, Prettier format check, TypeScript and production build passed.** No large-chunk warning after splitting charts/icons. One upstream TestClient deprecation warning remains in pytest output.
- **PDF verification passed:** two pages, snapshot values matched, printed QR decoded to the exact-version URL, internal valuation labels absent. Both rendered pages visually inspected. See `pdf-verification.json`.
- **External availability limitation:** live vPIC/recall/EPA attempts returned unavailable, saved in `public-smoke.json`. Successful response/ambiguity paths use mock-transport tests, not a claimed live result.
- Final pack-start context was added to the sanitized web/PDF snapshot. Date-only chart points use a stable dealership date so tooltips do not shift to the previous day.

Source and documentation are saved in the workspace. No Git commit or external deployment was performed. Stop here per the requested approximately 95% boundary; resume from the five explicit tasks in remaining-5-percent.md.

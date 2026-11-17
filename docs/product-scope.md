# Battery Timeline — implemented scope

Independent Tek-Qubit hackathon concept: a battery history that service writes and appraisal reads. The working loop is capture → explicit confirmation → updated pack-aware Timeline → accepted/overridden appraisal → immutable dealer-issued buyer report.

## Delivered

- Responsive light/teal staff workspace with 26 synthetic vehicles, actionable filters/search, evidence context, role-specific screens and desktop/mobile capture. The supplied UI references informed the white desktop sidebar, focused health cards, mobile bottom navigation and manual/photo input selector.
- Python/FastAPI backend, SQLAlchemy persistence, explicit migrations, durable uploads, deterministic seed/reset and optional PostgreSQL. Backend calculations are authoritative.
- Server-validated local demo sessions, dealer-scoped authorization, private attachments, expiring sessions and capture recovery after sign-in. No production identity provider is implied.
- Manual capture and actual local macOS Vision OCR; configured Tesseract alternative. Extracted proposals remain editable drafts. SOC, dates, units, odometer, VIN mismatch, duplicate evidence, pack identity and method/reference are checked.
- Deterministic intervals, independent-date evidence rubric, gated trend/scenarios, pack boundaries, service context and preserved corrections/exclusions. Numerical results do not depend on an LLM.
- Versioned dealer adjustment policy, editable starting value and provenance, battery-inclusion guard, reasoned manager overrides, immutable decisions, audit history and concurrent retry protection.
- Exact US 2023 Ford Mustang Mach-E and Chevrolet Bolt EV/EUV warranty rules. Hyundai Ioniq 5 source reviewed but provisional. Other years stay unknown. See warranty-source-review.md.
- Live vPIC, model-level NHTSA recall and EPA model/variant adapters. Explicit fixture mode, persistent cache fallback, source times, manual identity resolution and confirmed EPA variant selection. Actual live calls and fallback against their saved payloads were verified.
- Draft/published/revoked/expired reports, allowlisted immutable snapshots, opaque token, exact-version QR and matching PDF. Staff pricing, identities, notes and attachments are excluded. New evidence never rewrites an accepted decision or published report.
- Tests run against isolated SQLite and PostgreSQL records. Browser journeys, automated accessibility scans, responsive screenshots and native PDF/QR verification support acceptance; see build-status.md for exact final results.

## Limits and deferred scope

Real-phone camera/keyboard behavior, real screen-reader operation, another-machine installation and formal accessibility review need human/device acceptance. Broad OEM diagnostic comparability is not certified. Hyundai capacity/transfer ambiguity needs manufacturer clarification. Tesseract execution has not been tested here.

Voice, contextual assistant and simulated independent-test tasks remain deferred stretch features. Production authentication, public hosting and approved Tekion/APC integration are future scopes. No outbound communication occurs.

Excluded: lease forecasts, general pricing engine, connected-car accounts, hardware diagnostics, F&I, cross-dealer sharing, marketplaces, battery-passport claims, autonomous disposition and paid partner orders.

## Architecture choices

Records use explicitly migrated dealer-scoped JSON aggregates and typed contracts, with dedicated token/rate-limit tables. PostgreSQL mutations use one transaction advisory lock to preserve the same serialized-write semantics as SQLite; this is a modest local workflow architecture, not a high-throughput system. The UI uses scoped CSS rather than Tailwind. No private Tekion design system, proprietary font, endpoint or certification is claimed.

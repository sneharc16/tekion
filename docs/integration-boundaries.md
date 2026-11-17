# Integration boundaries

`apps/api/app/adapters/local_dms.py` simulates vehicle, visit, event and appraisal access using dealer-scoped records. `adapters/files.py` owns controlled image paths. No Tekion credentials, private schemas, endpoint URLs or compatibility are claimed. A future APC adapter requires approved documentation, credentials, tenant identity, field mapping, reconciliation and idempotency agreements.

## Public reads

- [vPIC documentation](https://vpic.nhtsa.dot.gov/api/): DecodeVinValuesExtended, with API error inspection. Partial/error-bearing identity is marked for manual review. Live retrieval is distinct from verified vehicle identity.
- [NHTSA datasets/APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis): model-level recalls only. The provider spelling “MUSTANG MACH E” is mapped explicitly from the dealer model name. Neither recall applicability nor completion is inferred for a VIN.
- [EPA service documentation](https://www.fueleconomy.gov/feg/ws/): model menu → candidate family options → full selected record. AWD/RWD/battery options remain explicit. The selected record must match the menu's exact model and year/make/ID. Original EPA-rated range is never an SOH input.

Adapters use per-request timeouts, two bounded attempts, validated JSON, closed HTTP clients, persistent cache fallback and retrieval provenance. Multi-request EPA results retain each source and timestamp. Partial variant retrieval blocks selection. Fixture mode performs no external verification and is labeled accordingly. Model-family grouping suggests candidates; the dealer still verifies trim/drive/battery.

`python -m scripts.smoke_public` runs in a temporary database. `docs/public-smoke.json` records actual successful reads, eight EPA options, a full-record consistency probe, and simulated outage fallback preserving those live payloads. Its partial documentation VIN is not an inventory verification. No application vehicle is modified by this probe.

## Extraction

Apple Vision is compiled from `scripts/native/vision.swift`, invoked locally only on explicit extraction, and tested against labeled synthetic health/SOC screens. Tesseract is an optional alternative and was not executed in this session. Both use fixed subprocess argument arrays and a bounded timeout. Images/text are untrusted data. Explicit health labels produce editable candidates; ambiguous values stay unconfirmed. Detected-VIN mismatch prevents association. No image is sent to an external AI provider and no paid credential is needed.

## Access and publication

Demo role sessions are server validated, expire after eight hours, and fail closed when expiry is absent. Staff and public schemas differ. Tenant identities are scoped in every record lookup; public tokens resolve a dealer internally without exposing internal IDs. Public routes are read-only, noindex, no-store, and rate-limited with atomic database counters shared across processes. Reverse-proxy IP trust is not configured; proxy deployments need a deliberate trusted-client-IP policy.

QR and PDF use PUBLIC_BASE_URL. Loopback links cannot be opened by another phone. Revocation/expiry stops active web/QR/PDF serving; already downloaded files cannot be recalled. PDF and web share one immutable snapshot. No partner appointment, email, SMS, paid order or autonomous publication exists.

## Public design references

Tekion's [home](https://www.tekion.com/), [DSE](https://www.tekion.com/products/arc/dse) and [about](https://www.tekion.com/about-us) informed the original charcoal/teal workflow design. The products index and specified 2026 blog were unavailable in the initial research pass. No proprietary wordmark or font is bundled.

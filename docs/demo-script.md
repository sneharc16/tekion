# Four-minute demo

Start the app and sign in as manager. All inventory is synthetic; assessment clock is Nov 16, 2026.

0:00–0:40 — Queue: show actionable filters, stock search and evidence labels. Open EV-2401 through All vehicles or `/vehicles/1`. Explain health versus charge.

0:40–1:35 — Add reading. Select battery health, enter 91%, Nov 16, 2026, 28,500 mi and OEM diagnostic tool. Confirm. Open updated appraisal; see the new reading and recalculated interval. For a repeated demo, use an isolated demo database or the documented reset after preserving needed records. Do not alter a value merely to bypass duplicate prevention.

1:35–2:20 — Inspect Why this estimate and policy assumptions. Accept appraisal. The saved decision is immutable. An override requires a reason and manager permission.

2:20–2:50 — Show cold start `/vehicles/2` and conflict `/vehicles/3`. No readings means no estimate. A conflicting high value requires evidence review, not an automatic premium. `/vehicles/4` separates old and replacement packs.

2:50–4:00 — Return to vehicle 1. Preview and publish report. Open public page, inspect masked VIN and absent internal prices. Download PDF. Explain that QR points to this exact immutable version. Revoke through Reports to demonstrate the unavailable status. Localhost QR is not accessible from another phone.

Optional negative case: select State of charge with 80%; confirmation rejects it. Upload a real test image for manual review; OCR operates when the native macOS adapter is built or TESSERACT_BIN is configured.

## Additional verified paths

- Technician sign-in → upload `data/seed/sample-charge.png` → Extract → ambiguous charge rejected as health. Upload `sample-health.png` → actual local OCR proposes health/date/odometer → review before confirmation. Enable native OCR with `./scripts/build-ocr.sh` on macOS or configure Tesseract first.
- Manager → Sources & settings → save new policy version. Existing accepted decisions retain the old version.
- EV-2425 → Warranty shows documented demo headroom of 500 miles and a separate day count; EV-2426 shows missing eligibility. Manufacturer terms are reviewed; VIN-specific eligibility remains synthetic demo evidence.
- Manager → an evidence record → Correct → original remains superseded. Publish a new report version to include the change; prior reports stay fixed.
- Sales sign-in → summaries/reports only. Private prices, override reasons and attachment access are unavailable on the server.
- Browser QA uses disposable ports 8001/5175. Its generated PDF/QR artifacts are test artifacts; create a report in the working app for the jury demonstration.

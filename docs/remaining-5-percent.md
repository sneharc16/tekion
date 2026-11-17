# Acceptance follow-up — approximately 1% remains

The earlier “5%” stop was lifted by the user after their usage reset. The implementation is now approximately 99% complete as an engineering estimate, not a measured certification score. Required local workflows run. This file retains its original name so existing handoff links work.

## Completed in the resumed build

- Successful live vPIC/recall/EPA reads; real EPA ambiguity and full-record probe; cache fallback against those actual fetched payloads. Corrected provider-specific model names. Partial VIN decodes remain explicitly unverified.
- PostgreSQL migration and workflow checks on a disposable PostgreSQL 18.6 cluster. Fixed a reserved SQL column; added cross-worker transaction locking. Independent schemas keep tests out of working records.
- 2023 Chevrolet Bolt EV/EUV manufacturer rules activated with the documented 60% threshold. Hyundai handbook reviewed and intentionally left provisional. No inferred recall reset.
- Competing confirmations, duplicate drafts, offer races, report retries/version allocation, rollback on database failure and counters across four processes tested on both databases.
- Session expiry and lost-confirmation response recovery preserve local drafts without duplicating evidence.
- Automated WCAG A/AA scans across seven desktop/mobile screens; corrected low-contrast support text, tiny labels and loading status semantics. Screenshot and PDF review performed; exact results are in build-status.md.

## Remaining human/environment checks

1. On an actual phone, use camera capture and the software keyboard with long forms. Check screen magnification, reduced motion, touch targets and capture recovery in the phone browser. Localhost QR links cannot reach another device; configure a reachable PUBLIC_BASE_URL before phone testing.
2. Exercise the complete workflow with VoiceOver/NVDA and keyboard-only use. Automated scans cannot certify accessibility; chart contrast checks marked inconclusive still require manual review.
3. A clean dependency install from both lockfiles passed in a disposable copy on this machine (clean-install.json). WebKit touch emulation passed the full workflow. Still install using the lockfiles on a second machine. SQLite and PostgreSQL 18.6 were tested here; Docker was absent, so the supplied PostgreSQL 17 Compose service was not executed. Test Tesseract separately if selecting that provider.
4. Obtain manufacturer clarification before activating the provisional Hyundai rule or any replacement-pack program. Add exact-year rules only with reviewed documents. Dealer/OEM measurement comparability remains an explicit review responsibility.

Next concrete step: run the four-minute demo on the target presentation machine, then the phone and assistive-technology checks above. Record observed issues before expanding features. Voice, assistant, paid test booking, production authentication, hosting and private Tekion/APC integration remain out of this build's required scope.

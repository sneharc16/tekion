# Interface direction

Updated Nov 17, 2026 from the user's three supplied screenshots. These references supersede the earlier charcoal-sidebar direction for the frontend.

The desktop banking reference supplies the visual structure: white sidebar, emerald selection, pale neutral canvas, generous spacing, quiet cards and thin line icons. The two mobile references supply a clear primary value, rounded content sections, compact actions and labeled bottom navigation. Battery Timeline keeps one coherent teal palette across screen sizes rather than switching the product's accent by device.

The vehicle's estimated health is the prominent summary value. Its evidence quality, last measured value, limitations and next action remain visible. The work queue stays operational; the reference does not introduce finance widgets, invented battery metrics or decorative chart data. The report retains dealer-issued wording and the public privacy boundary.

On phones, Work queue, Vehicles, Reports and Sources remain available in the fixed bottom navigation. The capture confirmation bar sits above it and accounts for safe-area insets. Manual entry is the initial input view; Upload photo exposes the real attachment and configured OCR workflow. An attached image remains visible for review even when switching the input selector.

Implementation lives in `apps/web/src/main.tsx` and `apps/web/src/style.css`. No external fonts, template runtime or new package dependencies were introduced. Existing API calculations, immutable appraisals/reports, roles and persistence remain authoritative.

Verification for this change: 10 Chromium browser tests, one WebKit touch journey, seven automated accessibility scans, TypeScript production build and formatting. Actual screenshots were inspected at 390, 768 and 1440 px. Real-device camera/keyboard and screen-reader acceptance remain outstanding as documented in `build-status.md`.

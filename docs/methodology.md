# Methodology — interval-v1

Battery health means remaining usable capacity relative to the source's original/reference capacity, according to its measurement method. It is distinct from state of charge, charge limit, dashboard range and a warranty threshold. Drafts never affect calculations. Original percentages and units are retained; kilometers convert with 0.621371192237334 miles/km.

## Eligibility and comparability

Only confirmed current-pack health readings with a usable-capacity basis are eligible. Invalid physical values, malformed/future dates and unknown methods/reference categories are excluded. Pack replacement creates a separate segment; old-pack readings remain visible but never join the current trend. The latest eligible method/reference category is the primary group; incompatible observations stay in history with exclusion reasons.

BMS capacity estimates and measured usable energy are separate groups. Original usable capacity and documented replacement reference are separate categories. Legacy records without method/reference metadata default to BMS/original capacity for backward compatibility; their provenance remains demo or dealer-entered, not independently verified. Within a category, cross-OEM/tool comparability still requires dealer review. The application does not claim that identical labels from every diagnostic tool are equivalent.

Same-date values use a median, contributing at most one independent observation. The largest source allowance on that date is used. Exact duplicate test/image confirmation is rejected. Corrections preserve original raw evidence, supersede its eligibility and append an audit/amendment record. Exclusions retain the original and a manager reason. Neither amendments nor new readings rewrite accepted decisions or published reports.

## Deterministic estimate and trend

The interval centers on the latest date's median. Illustrative source allowances are ±1.5 percentage points for independent tests, ±2 for OEM diagnostics, ±3 for dashboard readings and ±4 for transcription. Age adds 2 points/year up to 8. Conflicts add 4 points. Intervals round outward and clamp to 0–100. These are product assumptions, not calibrated statistical coverage.

An adjacent increase above 4 points, absolute difference above 10 points, or same-day spread above 5 points requires review. Software events provide context but cannot clear a conflict. A high BMS value is not evidence of fraud. Readings older than 365 days are stale.

- Limited: fewer than two independent dates or any warning.
- Strong: at least four dates spanning a year, latest within 180 days, source allowances no greater than 2 points and no warnings.
- Moderate: otherwise, with at least two independent dates and no warnings.

Evidence quality is not independent verification. No readings means insufficient vehicle evidence. One reading gives an observation/interval with limited quality and no trend.

Trend requires at least three dates spanning 183 days without warnings. It uses the median pairwise slope for pairs at least 60 days apart, in percentage points/year. Conditional 12/24-month intervals continue that slope and add one uncertainty point/year. They do not estimate failure time or treat warranty expiry as end of life.

## Appraisal policy

The initial demo policy uses 90% reference health, $125/point, a ±$1,500 cap and zero reserve. Managers can create immutable new policy versions with explicit coefficients/caps/reserve. These are dealer demo assumptions, not market-calibrated prices. The starting valuation and its effective date/provenance are separately saved.

Battery-inclusive starting values receive no further battery adjustment or reserve. Unknown inclusion blocks application. No usable evidence blocks a recommendation; limited/conflicting evidence recommends more evidence and requires a manager review reason to proceed with an available interval. Overrides require an amount and reason while retaining the original recommendation. Warranty headroom adds no dollar premium. Accepted decisions preserve the assessment, policy, inputs, actor and timestamp. Optimistic versions plus serialized transactions protect concurrent decisions.

## Warranty

Exact model/year/market rules are versioned in `app/warranty.py`; [source review](warranty-source-review.md) records the manufacturer documents and unresolved terms. Active rules cover US 2023 Ford Mustang Mach-E and Chevrolet Bolt EV/EUV. Hyundai Ioniq 5 is provisional; unsupported years stay unknown.

Time uses the documented original first-use/delivery basis. Mileage uses the original absolute odometer limit. Each limit is shown independently, whichever comes first; when only one input is missing, the affected limit stays unknown. Missing jurisdiction/transfer eligibility prevents applying both. A replacement does not restart coverage. Manufacturer claim determination and exclusions still apply; an estimated SOH interval is not a warranty test.

## Publication and exclusions

Reports are sanitized, immutable dealer-issued summaries, normally expiring 90 days after the assessment clock date. Web and PDF share the same snapshot. An integrity hash identifies that snapshot; it proves neither OEM verification nor scientific accuracy. Revocation cannot recall downloaded copies.

No fleet curve, NASA/CALCE training, inferred fast charging, lifetime climate history, universal resale premium, universal 70% failure point or exact remaining lifetime is claimed. EPA range is original rated range only. NHTSA recalls are model context only.

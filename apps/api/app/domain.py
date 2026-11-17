"""Deterministic illustrative engine v1. No calibrated statistical coverage."""

from datetime import date
from statistics import median
import math

METHOD = "interval-v1"
ALLOWANCE = {
    "OEM diagnostic tool": 2,
    "Independent test": 1.5,
    "OEM dashboard": 3,
    "Manual transcription": 4,
}
POLICY = {
    "version": "demo-v1",
    "reference_health": 90,
    "dollars_per_point": 125,
    "cap": 1500,
    "reserve": 0,
    "label": "Illustrative dealer assumptions; not market calibrated",
}


def assess(readings, pack, today):
    def valid_date(r):
        try:
            return date(2000, 1, 1) <= date.fromisoformat(r.get("date", "")) <= today
        except (TypeError, ValueError):
            return False

    usable = [
        r
        for r in readings
        if r["pack"] == pack
        and r["state"] == "confirmed"
        and r["measurement"] == "health"
        and r["basis"] == "usable capacity"
    ]
    invalid = [
        r
        for r in usable
        if isinstance(r.get("value"), bool)
        or not isinstance(r.get("value"), (int, float))
        or not math.isfinite(r["value"])
        or not 0 <= r["value"] <= 100
    ]
    invalid_dates = [r for r in usable if not valid_date(r)]
    usable = [
        r
        for r in usable
        if r not in invalid
        and r not in invalid_dates
        and r.get("method", "BMS capacity estimate") != "unknown"
        and r.get("reference_basis", "Original usable capacity") != "unknown"
    ]
    usable.sort(key=lambda r: (r["date"], r.get("created_at", ""), r["id"]))
    method = usable[-1].get("method", "BMS capacity estimate") if usable else None
    reference = usable[-1].get("reference_basis", "Original usable capacity") if usable else None
    incompatible = [
        r
        for r in usable
        if r.get("method", "BMS capacity estimate") != method
        or r.get("reference_basis", "Original usable capacity") != reference
    ]
    usable = [r for r in usable if r not in incompatible]
    exclusions = (
        [{"id": r["id"], "reason": "Invalid physical percentage"} for r in invalid]
        + [{"id": r["id"], "reason": "Invalid or future reading date"} for r in invalid_dates]
        + [{"id": r["id"], "reason": "Incompatible measurement method"} for r in incompatible]
    )

    # Same-day observations do not increase independent evidence count.
    grouped = {}
    for r in usable:
        grouped.setdefault(r["date"], []).append(r)
    points = [
        dict(
            max(rs, key=lambda r: ALLOWANCE.get(r["source"], 4)),
            value=median(r["value"] for r in rs),
        )
        for rs in grouped.values()
    ]
    warnings = []
    if any(
        max(r["value"] for r in rs) - min(r["value"] for r in rs) > 5 for rs in grouped.values()
    ):
        warnings.append("Same-day readings disagree materially")
    for a, b in zip(points, points[1:]):
        if b["value"] - a["value"] > 4 or abs(b["value"] - a["value"]) > 10:
            warnings.append("Unexplained change needs review")
    base = {
        "version": METHOD,
        "count": len(points),
        "input_ids": [r["id"] for r in usable],
        "pack": pack,
        "interval": None,
        "quality": "limited",
        "warnings": warnings,
        "slope": None,
        "scenarios": [],
        "as_of": str(today),
        "method": method,
        "reference_basis": reference,
        "exclusions": exclusions,
        "last": usable[-1] if usable else None,
    }
    if not points:
        return dict(base, reason="Insufficient vehicle evidence", action="Capture reading")
    latest = points[-1]
    age = (today - date.fromisoformat(latest["date"])).days
    allowance = ALLOWANCE.get(latest["source"], 4) + min(8, max(0, age) / 365 * 2)
    if age > 365:
        warnings.append("Evidence is stale; obtain a current reading")
    if warnings:
        allowance += 4
    center = latest["value"]
    lo = max(0, math.floor(center - allowance))
    hi = min(100, math.ceil(center + allowance))
    span = (date.fromisoformat(points[-1]["date"]) - date.fromisoformat(points[0]["date"])).days
    quality = (
        "limited"
        if warnings or len(points) < 2
        else "strong"
        if len(points) >= 4
        and span >= 365
        and age <= 180
        and all(ALLOWANCE.get(r["source"], 4) <= 2 for r in points)
        else "moderate"
    )
    if len(points) >= 3 and span >= 183 and not warnings:
        slopes = [
            (b["value"] - a["value"])
            / ((date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days / 365.25)
            for i, a in enumerate(points)
            for b in points[i + 1 :]
            if (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days >= 60
        ]
        if slopes:
            base["slope"] = round(median(slopes), 2)
            base["scenarios"] = [
                {
                    "months": m,
                    "interval": [
                        max(0, min(100, math.floor(lo + base["slope"] * m / 12 - m / 12))),
                        max(0, min(100, math.ceil(hi + base["slope"] * m / 12 + m / 12))),
                    ],
                }
                for m in [12, 24]
            ]
    return dict(
        base,
        interval=[lo, hi],
        quality=quality,
        reason=f"Based on {len(points)} independent reading dates over {span} days",
        action="Obtain more evidence" if quality == "limited" else "Open appraisal",
        age_days=age,
    )


def appraisal(assessment, base, included, policy=None):
    policy = policy or POLICY
    if included == "unknown":
        return {
            "interval": None,
            "adjustment": None,
            "reserve": 0,
            "reason": "Resolve whether starting value includes battery health",
        }
    if not assessment["interval"]:
        return {
            "interval": None,
            "adjustment": None,
            "reserve": 0,
            "reason": "Obtain more evidence",
        }
    adj = (
        [0, 0]
        if included == "yes"
        else [
            round(
                max(
                    -policy["cap"],
                    min(
                        policy["cap"],
                        (x - policy["reference_health"]) * policy["dollars_per_point"],
                    ),
                )
            )
            for x in assessment["interval"]
        ]
    )
    reserve = (
        0 if included == "yes" else policy["reserve"] if assessment["quality"] == "limited" else 0
    )
    return {
        "interval": [max(0, round(base + x - reserve)) for x in adj],
        "adjustment": adj,
        "reserve": reserve,
        "reason": "Battery already included; no additional adjustment or reserve"
        if included == "yes"
        else policy["label"],
    }

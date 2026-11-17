from datetime import date
import math

FORD_RULE = {
    "version": "ford-us-2023-v1",
    "manufacturer": "Ford",
    "model": "Mustang Mach-E",
    "years": [2023],
    "market": "US",
    "duration_years": 8,
    "mileage_limit": 100000,
    "mileage_basis": "absolute",
    "capacity_threshold": 70,
    "start_basis": "Earlier of delivery or first service; California retail-sales exception requires review",
    "transfer": "Remaining coverage available to subsequent owners; jurisdiction and exclusions apply",
    "source": "https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/23MYUS_Ford_MachE_WTY_V5.pdf",
    "locator": "Printed pages 6–7, 10, 18–20",
    "verified_date": "2026-11-16",
    "status": "verified",
    "notes": "EV-certified Ford dealer determines excessive capacity loss. Not automatic claim approval. No replacement reset.",
}

CHEVROLET_SOURCE = "https://contentdelivery.ext.gm.com/bypass/gma-content-api/resources/sites/GMA/content/staging/MANUALS/5000/MA5698/en_US/5.0/23_CHEV_WM_en_US_U_16451727B_2022AUG29_Rvsd1.pdf"
HYUNDAI_SOURCE = "https://sweb-owners.hyundaiusa.com/content/dam/hyundai/us/myhyundai/manuals/factory-warranty/2023/2023-Hyundai-Owners-Warranty-Information-Handbook.pdf"
RULES = [
    FORD_RULE,
    *[
        {
            "version": f"chevrolet-us-2023-{suffix}-v1",
            "manufacturer": "Chevrolet",
            "model": model,
            "years": [2023],
            "market": "US",
            "duration_years": 8,
            "mileage_limit": 100000,
            "mileage_basis": "absolute",
            "capacity_threshold": 60,
            "start_basis": "Original delivery or first use; no automatic replacement reset",
            "transfer": "Remaining electric-vehicle coverage transfers to subsequent owners within the original term",
            "source": CHEVROLET_SOURCE,
            "locator": "2023 booklet, printed pages 5, 7 and 12",
            "verified_date": "2026-11-17",
            "status": "verified",
            "notes": "Certified dealer determines capacity below 60%. US registration and normal operation required; salvage/total-loss exclusions apply. Original vehicle term only; recall replacement programs require separate evidence.",
        }
        for model, suffix in [("Bolt EV", "bolt-ev"), ("Bolt EUV", "bolt-euv")]
    ],
    {
        "version": "hyundai-us-2023-ioniq5-provisional-v1",
        "manufacturer": "Hyundai",
        "model": "Ioniq 5",
        "years": [2023],
        "market": "US",
        "duration_years": 10,
        "mileage_limit": 100000,
        "mileage_basis": "absolute",
        "capacity_threshold": None,
        "start_basis": "Original retail delivery or first use",
        "transfer": "EV-system transfer applicability requires manufacturer clarification; do not substitute powertrain terms",
        "source": HYUNDAI_SOURCE,
        "locator": "2023 handbook, printed pages 18, 23–24",
        "verified_date": "2026-11-17",
        "status": "provisional",
        "notes": "EV-system term is documented, but capacity coverage/exclusion wording is inconsistent and transfer applicability is unresolved. Rule is not activated; obtain manufacturer verification.",
    },
]
US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
)


def coverage(v, today):
    result = {
        "status": "Needs warranty verification",
        "time_remaining": None,
        "miles_remaining": None,
        "reason": "No verified rule for this exact model year.",
        "rule": None,
    }
    rule = next(
        (
            r
            for r in RULES
            if (v.get("make"), v.get("model")) == (r["manufacturer"], r["model"])
            and v.get("year") in r["years"]
        ),
        None,
    )
    if not rule:
        return result
    result["rule"] = rule
    if rule["status"] != "verified":
        return dict(result, reason=rule["notes"])
    missing = []
    if v.get("market") != "US":
        missing.append("US warranty market")
    if v.get("sale_state") not in US_STATES:
        missing.append("sale jurisdiction")
    if rule["manufacturer"] == "Ford" and v.get("sale_state") == "CA":
        missing.append("California start-basis review")
    if not v.get("transfer_verified"):
        missing.append("ownership and transfer eligibility")
    # Unresolved applicability prevents both terms from being applied.
    if missing:
        return dict(result, reason="Verify: " + ", ".join(missing), missing_inputs=missing)

    mileage = v.get("miles")
    miles = None
    if (
        isinstance(mileage, (int, float))
        and not isinstance(mileage, bool)
        and math.isfinite(mileage)
        and mileage >= 0
    ):
        miles = max(0, rule["mileage_limit"] - mileage)
    else:
        missing.append("current odometer")
    days = None
    expiry = None
    if not v.get("in_service") or not v.get("warranty_start_verified"):
        missing.append("verified delivery or first-use date")
    else:
        try:
            start = date.fromisoformat(v["in_service"])
            if start > today or start.year < v["year"] - 1:
                raise ValueError("Implausible warranty start date")
            try:
                expiry = start.replace(year=start.year + rule["duration_years"])
            except ValueError:
                expiry = start.replace(year=start.year + rule["duration_years"], day=28)
            days = max(0, (expiry - today).days)
        except (TypeError, ValueError):
            missing.append("valid documented warranty start date")
    expired = days == 0 or miles == 0
    return dict(
        result,
        status="Expired"
        if expired
        else "Needs warranty verification"
        if missing
        else "Coverage headroom",
        time_remaining=days,
        miles_remaining=miles,
        expiry=str(expiry) if expiry else None,
        missing_inputs=missing,
        reason=("Verify: " + ", ".join(missing) + ". " if missing else "")
        + "Whichever comes first. Subject to manufacturer eligibility and exclusions.",
    )

"""Allowlisted staff summaries. Public snapshots have a separate contract."""

SUMMARY_FIELDS = {
    "id",
    "stock",
    "year",
    "make",
    "model",
    "vin",
    "miles",
    "pack",
    "scenario",
    "revision",
    "provenance",
    "identification_status",
    "epa_match",
    "assessment",
    "warranty",
    "packs",
}
READING_FIELDS = {
    "id",
    "vehicle",
    "pack",
    "date",
    "value",
    "miles",
    "source",
    "state",
    "basis",
    "method",
    "reference_basis",
    "provenance",
}


def staff_summary(payload, role):
    if role == "manager":
        return payload
    out = {k: v for k, v in payload.items() if k in SUMMARY_FIELDS}
    out["assessment"] = dict(out["assessment"])
    if out["assessment"].get("last"):
        out["assessment"]["last"] = {
            k: v for k, v in out["assessment"]["last"].items() if k in READING_FIELDS
        }
    if role == "technician":
        out["readings"] = payload.get("readings", [])
        out["events"] = payload.get("events", [])
        out["activity"] = payload.get("activity", [])
    else:
        out["vin"] = "•••••••••••" + out["vin"][-6:]
        out["readings"] = [
            {k: v for k, v in r.items() if k in READING_FIELDS} for r in payload.get("readings", [])
        ]
        out["events"] = [
            {k: v for k, v in e.items() if k in ("id", "date", "type")}
            for e in payload.get("events", [])
        ]
        out["activity"] = []
    out["decisions"] = []
    return out

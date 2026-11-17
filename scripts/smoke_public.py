"""Read-only live provider probes, isolated from dealer inventory and cache."""

import os
import json
import tempfile
from unittest.mock import patch
import httpx

os.environ["DATA_MODE"] = "live"
_directory = tempfile.TemporaryDirectory(prefix="battery-public-smoke-")
os.environ["DATABASE_URL"] = "sqlite:///" + _directory.name + "/smoke.db"
from sqlalchemy.orm import Session  # noqa: E402
from apps.api.app.store import engine, migrate  # noqa: E402
from apps.api.app.adapters import public_data  # noqa: E402


def summary(r):
    return {
        "status": r["status"],
        "source": r["source"],
        "retrieved_at": r["retrieved_at"],
        "data_fields": list(r["data"]) if r.get("data") else [],
        **({"sources": r["sources"]} if "sources" in r else {}),
    }


migrate()
results = {
    "note": "Public documentation VIN example is partial, not a verified inventory VIN. EPA record probe does not select a variant for a dealer vehicle."
}
probes = [
    ("vin", lambda s: public_data.vin(s, "5UXWX7C5*BA", 2011)),
    ("recalls", lambda s: public_data.recalls(s, "Ford", "Mustang Mach-E", 2023)),
    ("epa", lambda s: public_data.epa(s, "Ford", "Mustang Mach-E", 2023)),
]
original = httpx.Client
with Session(engine) as s:
    for name, fn in probes:
        r = fn(s)
        results[name] = summary(r)
        if r.get("data"):
            if name == "vin":
                results[name]["review_required"] = r["data"]["review_required"]
                results[name]["provider_error_code"] = r["data"]["ErrorCode"]
            elif name == "recalls":
                results[name]["model_level_count"] = len(r["data"]["items"])
            else:
                results[name]["option_count"] = len(r["data"]["options"])
                results[name]["match_status"] = r["data"]["match_status"]
                # Probe full-record consistency without changing any vehicle match.
                if r["data"]["options"]:
                    option = r["data"]["options"][0]
                    record = public_data.epa_record(s, option["value"])
                    results["epa_record_probe"] = summary(record)
                    if record.get("data"):
                        d = record["data"]
                        results["epa_record_probe"]["identity_matches_menu"] = (
                            str(d["id"]) == str(option["value"])
                            and d["model"] == option["epa_model"]
                            and str(d["year"]) == "2023"
                            and d["make"] == "Ford"
                        )
        s.commit()
        # Deliberate simulated outage against the actual fetched/cache payload.
        with patch.object(
            public_data.httpx,
            "Client",
            lambda **kw: original(
                transport=httpx.MockTransport(lambda request: httpx.Response(503))
            ),
        ):
            fallback = fn(s)
        results[name]["simulated_outage_status"] = fallback["status"]
        results[name]["cache_preserves_payload"] = (
            r.get("data") == fallback.get("data") and r["retrieved_at"] == fallback["retrieved_at"]
            if r.get("data")
            else None
        )
        print(name, results[name]["status"], results[name]["simulated_outage_status"], flush=True)
with open("docs/public-smoke.json", "w") as output:
    json.dump(results, output, indent=2)
engine.dispose()
_directory.cleanup()

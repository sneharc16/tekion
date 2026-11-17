"""Public API reads only; never interprets identity/range/recalls as SOH."""

import os
import hashlib
import time
import re
import httpx
from ..store import get, put, now


def fetch(s, url, params, validate, client=None):
    # Close owned connections even on cache fallback or schema failure.
    if client is None:
        with httpx.Client(
            timeout=6, headers={"Accept": "application/json"}, follow_redirects=False
        ) as owned:
            return fetch(s, url, params, validate, owned)
    key = hashlib.sha256((url + str(sorted(params.items()))).encode()).hexdigest()
    cached = get(s, "external_cache", key)
    if os.getenv("DATA_MODE", "fixture") != "live":
        return {
            "status": "demo fixture",
            "source": url,
            "retrieved_at": None,
            "data": None,
            "message": "Fixture mode: no external verification performed.",
        }
    for attempt in range(2):
        try:
            r = client.get(url, params=params)
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(0.2)
                continue
            r.raise_for_status()
            raw = r.json()
            if not isinstance(raw, dict):
                raise ValueError("Unexpected public API response")
            data = validate(raw)
            result = {"status": "live", "source": str(r.url), "retrieved_at": now(), "data": data}
            put(s, "external_cache", key, result)
            return result
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
            if attempt == 0:
                continue
    if cached:
        return dict(
            cached,
            status="cached",
            message="Live fetch unavailable; previously retrieved result shown.",
        )
    return {
        "status": "unavailable",
        "source": url,
        "retrieved_at": None,
        "data": None,
        "message": "Public service unavailable. Saved vehicle evidence is unaffected.",
    }


def vin(s, vin, year):
    def valid(d):
        r = d["Results"][0]
        if not all(r.get(k) for k in ["Make", "Model", "ModelYear", "ErrorCode"]):
            raise ValueError("No usable identity returned")
        result = {
            k: r.get(k) for k in ["Make", "Model", "ModelYear", "Trim", "ErrorCode", "ErrorText"]
        }
        result["review_required"] = (
            r["ErrorCode"] != "0" or str(r["ModelYear"]) != str(year) or len(vin) != 17
        )
        result["identification_status"] = (
            "Partial identity; manual review required"
            if result["review_required"]
            else "Decoded identity; verify against vehicle"
        )
        return result

    return fetch(
        s,
        "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/" + vin,
        {"format": "json", "modelyear": year},
        valid,
    )


def recalls(s, make, model, year):
    def valid(d):
        if not isinstance(d["results"], list):
            raise ValueError()
        return {
            "label": "Model-level recall information; not VIN applicability or completion",
            "items": [
                {
                    k: r.get(k)
                    for k in ["NHTSACampaignNumber", "Component", "Summary", "ReportReceivedDate"]
                }
                for r in d["results"]
            ],
        }

    # Reviewed provider spelling, not a change to the dealer vehicle identity.
    provider_model = (
        "MUSTANG MACH E"
        if (make.casefold(), model.casefold()) == ("ford", "mustang mach-e")
        else model
    )
    return fetch(
        s,
        "https://api.nhtsa.gov/recalls/recallsByVehicle",
        {"make": make, "model": provider_model, "modelYear": year},
        valid,
    )


def epa(s, make, model, year):
    """Resolve provider model families before presenting every matching variant.

    EPA separates AWD/RWD/battery variants into model names. No variant is chosen.
    Every subrequest retains its provenance; incomplete results cannot look live.
    """

    def normalize(value):
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    wanted = normalize(model)

    def models(d):
        items = d.get("menuItem", [])
        items = [items] if isinstance(items, dict) else items
        if not isinstance(items, list) or any(
            not isinstance(x, dict) or not isinstance(x.get("value"), str) for x in items
        ):
            raise ValueError("Malformed EPA model menu")
        return {"models": [x["value"] for x in items]}

    menu = fetch(
        s,
        "https://www.fueleconomy.gov/ws/rest/vehicle/menu/model",
        {"make": make, "year": year},
        models,
    )
    if menu.get("data") is None:
        return menu
    candidates = [
        m
        for m in menu["data"]["models"]
        if normalize(m) == wanted or normalize(m).startswith(wanted + " ")
    ]
    if len(candidates) > 12:
        return dict(
            menu,
            status="partial",
            data={"options": [], "match_status": "incomplete"},
            message="Too many candidates. Refine the vehicle model before matching.",
        )
    results = [menu]
    options = []
    for provider_model in candidates:
        result = epa_options(s, make, provider_model, year)
        results.append(result)
        for option in (result.get("data") or {}).get("options", []):
            options.append(
                dict(option, text=provider_model + " · " + option["text"], epa_model=provider_model)
            )
    incomplete = any(r.get("data") is None for r in results)
    cached = any(r["status"] == "cached" for r in results)
    return dict(
        menu,
        status="partial" if incomplete else "cached" if cached else "live",
        retrieved_at=min(r["retrieved_at"] for r in results if r["retrieved_at"]),
        sources=[{k: r[k] for k in ["source", "retrieved_at", "status"]} for r in results],
        message="Some EPA variants could not be retrieved. Retry before choosing."
        if incomplete
        else "Review all candidates; verify trim, drive and battery. No automatic match.",
        data={
            "options": options,
            "match_status": "incomplete"
            if incomplete
            else "selection required"
            if options
            else "no matching models",
        },
    )


def epa_options(s, make, model, year):
    def valid(d):
        items = d.get("menuItem", [])
        items = [items] if isinstance(items, dict) else items
        if not isinstance(items, list) or any(
            not isinstance(item, dict)
            or not str(item.get("value", "")).isdigit()
            or not isinstance(item.get("text"), str)
            for item in items
        ):
            raise ValueError("Malformed EPA options")
        return {
            "options": items,
            "match_status": "selection required" if len(items) > 1 else "unconfirmed",
            "message": "Select and verify trim/drive/battery variant. No automatic first-option match.",
        }

    return fetch(
        s,
        "https://www.fueleconomy.gov/ws/rest/vehicle/menu/options",
        {"make": make, "model": model, "year": year},
        valid,
    )


def epa_record(s, id):
    def valid(d):
        if not all(d.get(k) for k in ["id", "year", "make", "model"]):
            raise ValueError("Incomplete EPA identity")
        return {
            k: d.get(k)
            for k in [
                "id",
                "year",
                "make",
                "model",
                "drive",
                "fuelType",
                "range",
                "trany",
                "cylinders",
                "displ",
            ]
        }

    return fetch(s, "https://www.fueleconomy.gov/ws/rest/vehicle/" + id, {}, valid)

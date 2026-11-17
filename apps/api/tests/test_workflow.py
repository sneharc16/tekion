import time
from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.domain import assess, appraisal
from datetime import date

client = TestClient(app)


def login(role="manager"):
    client.post("/api/session", json={"role": role})


def draft(**kw):
    b = dict(
        value=91,
        measurement="health",
        date="2026-11-16",
        odometer=28500,
        unit="mi",
        source="OEM diagnostic tool",
        basis="usable capacity",
        pack="original",
    )
    b.update(kw)
    return client.post("/api/service-visits/1/capture-drafts", json=b)


def test_full_workflow_and_privacy():
    login()
    old = client.get("/api/vehicles/1").json()
    d = draft().json()
    assert client.get("/api/vehicles/1").json()["assessment"] == old["assessment"]
    r = client.post("/api/capture-drafts/" + d["id"] + "/confirm")
    assert r.status_code == 200
    assert client.post("/api/capture-drafts/" + d["id"] + "/confirm").status_code == 200
    v = client.get("/api/vehicles/1").json()
    assert v["assessment"]["count"] == 5
    body = dict(revision=v["revision"], base=v["base"], included="no", operation_id="decision-test")
    dec = client.post("/api/vehicles/1/appraisals", json=body)
    assert dec.status_code == 200
    report = client.post("/api/vehicles/1/reports").json()
    assert client.get("/api/public/reports/" + report["token"]).status_code == 404
    client.post("/api/reports/" + report["id"] + "/publish")
    public = client.get("/api/public/reports/" + report["token"])
    assert public.status_code == 200
    assert not any(
        key in public.json() for key in ["base", "actor", "notes", "accepted", "vehicle_id"]
    )
    assert client.get("/api/public/reports/" + report["token"] + "/pdf").content.startswith(b"%PDF")
    original = public.json()
    d2 = draft(value=90.5, odometer=28510).json()
    assert client.post("/api/capture-drafts/" + d2["id"] + "/confirm").status_code == 200
    assert client.get("/api/public/reports/" + report["token"]).json() == original
    assert client.get("/api/vehicles/1").json()["decisions"][0]["newer_evidence"]
    client.post("/api/reports/" + report["id"] + "/revoke")
    assert client.get("/api/public/reports/" + report["token"]).status_code == 410


def test_soc_validation_permissions():
    login()
    d = draft(measurement="charge", value=80).json()
    assert client.post("/api/capture-drafts/" + d["id"] + "/confirm").status_code == 422
    assert draft(value=101).status_code == 422
    assert draft(date="2030-01-01").status_code == 422
    assert draft(unit="").status_code == 422
    login("sales")
    assert draft().status_code == 403
    login("technician")
    assert client.post("/api/vehicles/1/reports").status_code == 403


def test_no_trend_pack_and_correlated_evidence():
    r = dict(
        id="a",
        pack="new",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-11-01",
        value=90,
        source="OEM diagnostic tool",
    )
    h = assess([r, dict(r, id="b")], "new", date(2026, 11, 16))
    assert h["count"] == 1 and h["slope"] is None and h["quality"] == "limited"
    assert assess([r], "old", date(2026, 11, 16))["interval"] is None
    h["interval"] = [88, 92]
    assert appraisal(h, 25000, "yes")["adjustment"] == [0, 0]
    assert appraisal(h, 25000, "unknown")["interval"] is None


def test_conflicts_staleness_and_odometer():
    login()
    d = draft(value=88, odometer=1).json()
    assert client.post("/api/capture-drafts/" + d["id"] + "/confirm").status_code == 422
    assert client.get("/api/vehicles/3").json()["assessment"]["warnings"]
    assert client.get("/api/vehicles/7").json()["assessment"]["quality"] == "limited"


def test_warranty_boundaries_and_unknowns():
    from apps.api.app.warranty import coverage

    v = dict(
        make="Ford",
        model="Mustang Mach-E",
        year=2023,
        in_service="2023-02-28",
        market="US",
        sale_state="IL",
        transfer_verified=True,
        warranty_start_verified=True,
        miles=99999,
    )
    assert coverage(v, date(2031, 2, 27))["time_remaining"] == 1
    assert coverage(v, date(2031, 2, 28))["status"] == "Expired"
    assert coverage(dict(v, miles=100000), date(2026, 11, 16))["status"] == "Expired"
    assert (
        coverage(dict(v, market=None), date(2026, 11, 16))["status"]
        == "Needs warranty verification"
    )
    assert coverage(dict(v, pack="replacement"), date(2026, 11, 16))["expiry"] == "2031-02-28"


def test_public_adapter_cache_and_epa_ambiguity(monkeypatch):
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine
    from apps.api.app.adapters.public_data import fetch, epa
    import httpx

    monkeypatch.setenv("DATA_MODE", "live")
    good = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"x": 1})))
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with Session(engine) as s:
        assert fetch(s, "https://example.com", {}, lambda d: d, good)["status"] == "live"
        assert fetch(s, "https://example.com", {}, lambda d: d, bad)["status"] == "cached"
        assert (
            fetch(s, "https://example.com/empty", {}, lambda d: d, bad)["status"] == "unavailable"
        )
    monkeypatch.setenv("DATA_MODE", "fixture")
    with Session(engine) as s:
        assert epa(s, "Ford", "Mustang Mach-E", 2023)["status"] == "demo fixture"


def test_tenant_scope():
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, put

    with Session(engine) as s:
        put(
            s,
            "session",
            "other-token",
            {"dealer": "other", "role": "manager", "expires_at": time.time() + 3600},
        )
        s.commit()
    other = TestClient(app)
    other.cookies.set("bt_session", "other-token")
    assert other.get("/api/vehicles/1").status_code == 404
    assert other.post("/api/vehicles/1/reports").status_code == 404


def test_last_recorded_is_an_observation_not_same_day_median():
    r = dict(
        id="a",
        pack="p",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-11-01",
        value=90,
        source="OEM diagnostic tool",
    )
    h = assess([r, dict(r, id="b", value=92)], "p", date(2026, 11, 16))
    assert h["count"] == 1
    assert h["last"]["value"] == 92


def test_versioned_policy_valuation_and_concurrent_decision():
    login()
    v = client.get("/api/vehicles/5").json()
    # Unresolved double-counting state blocks acceptance even with usable evidence.
    body = {
        "revision": v["revision"],
        "base": 25000,
        "included": "unknown",
        "source": "Dealer entered demo value",
        "effective_date": "2026-11-16",
    }
    assert client.post("/api/vehicles/5/valuation", json=body).status_code == 200
    v = client.get("/api/vehicles/5").json()
    assert v["recommendation"]["interval"] is None
    body.update(revision=v["revision"], included="no")
    client.post("/api/vehicles/5/valuation", json=body)
    v = client.get("/api/vehicles/5").json()
    old_policy = v["policy"]
    d = {
        "revision": v["revision"],
        "base": 25000,
        "included": "no",
        "operation_id": "governance-first",
        "policy_version": old_policy["version"],
        "decision_revision": 0,
    }
    accepted = client.post("/api/vehicles/5/appraisals", json=d)
    assert accepted.status_code == 200
    assert (
        client.post(
            "/api/vehicles/5/appraisals", json=dict(d, operation_id="governance-second")
        ).status_code
        == 409
    )
    assert client.post("/api/vehicles/5/appraisals", json=d).json() == accepted.json()
    p = {k: old_policy[k] for k in ["reference_health", "dollars_per_point", "cap", "reserve"]}
    p.update(previous_version=old_policy["version"], dollars_per_point=200, reserve=250)
    new = client.post("/api/settings/appraisal-policy", json=p)
    assert new.status_code == 200
    assert client.post("/api/settings/appraisal-policy", json=p).status_code == 409
    v = client.get("/api/vehicles/5").json()
    assert v["decisions"][0]["policy"] == old_policy
    assert v["policy"]["version"] != old_policy["version"]
    assert (
        client.post(
            "/api/vehicles/5/appraisals",
            json=dict(d, operation_id="stale-policy-test", decision_revision=1),
        ).status_code
        == 409
    )
    # Existing battery adjustment also suppresses a separate reserve.
    assert (
        appraisal({"interval": [88, 92], "quality": "limited"}, 25000, "yes", new.json())["reserve"]
        == 0
    )


def test_exclusion_keeps_observation_and_published_report():
    login()
    v = client.get("/api/vehicles/3").json()
    before = [r for r in v["readings"] if r["value"] == 99][0]
    report = client.post("/api/vehicles/3/reports").json()
    client.post("/api/reports/" + report["id"] + "/publish")
    original = client.get("/api/public/reports/" + report["token"]).json()
    result = client.post(
        "/api/readings/" + before["id"] + "/exclude",
        json={"revision": v["revision"], "reason": "Conflicting test pending independent review"},
    )
    assert result.status_code == 200 and before["id"] not in result.json()["input_ids"]
    after = next(
        r for r in client.get("/api/vehicles/3").json()["readings"] if r["id"] == before["id"]
    )
    assert after["raw_value"] == before["raw_value"] and after["state"] == "excluded"
    assert client.get("/api/public/reports/" + report["token"]).json() == original
    login("technician")
    assert (
        client.post(
            "/api/readings/" + before["id"] + "/exclude",
            json={"revision": v["revision"], "reason": "Not authorized to exclude evidence"},
        ).status_code
        == 403
    )


def test_same_id_tenant_storage_and_policy_permissions():
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, put, get

    with Session(engine) as s:
        put(s, "test_scope", "same", {"value": "first"}, "dealer-a")
        put(s, "test_scope", "same", {"value": "second"}, "dealer-b")
        assert get(s, "test_scope", "same", "dealer-a")["value"] == "first"
        assert get(s, "test_scope", "same", "dealer-b")["value"] == "second"
    login()
    p = client.get("/api/sources").json()["policy"]
    login("sales")
    assert client.get("/api/sources").json()["policy"] is None
    assert (
        client.post(
            "/api/settings/appraisal-policy",
            json={
                **{k: p[k] for k in ["reference_health", "dollars_per_point", "cap", "reserve"]},
                "previous_version": p["version"],
            },
        ).status_code
        == 403
    )


def test_warranty_application_snapshot_and_unknown_state():
    login()
    v = client.get("/api/vehicles/warranty-25").json()
    assert v["warranty"]["miles_remaining"] == 500
    assert (
        client.get("/api/vehicles/warranty-26").json()["warranty"]["status"]
        == "Needs warranty verification"
    )
    payload = {
        "revision": v["revision"],
        "in_service": "2023-04-18",
        "market": "US",
        "sale_state": "CA",
        "transfer_verified": True,
        "warranty_start_verified": True,
        "warranty_evidence": "Synthetic California eligibility document pending review",
    }
    result = client.post("/api/vehicles/warranty-25/warranty", json=payload)
    assert result.status_code == 200 and result.json()["status"] == "Needs warranty verification"
    payload.update(revision=v["revision"] + 1, sale_state="IL")
    assert (
        client.post("/api/vehicles/warranty-25/warranty", json=payload).json()["miles_remaining"]
        == 500
    )
    r = client.post("/api/vehicles/warranty-25/reports").json()
    assert "500 mi" in r["payload"]["warranty"]
    assert "warranty_evidence" not in r["payload"]["coverage"]


def test_incompatible_methods_and_invalid_values_do_not_enter_estimate():
    r = dict(
        id="a",
        pack="p",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-10-01",
        value=90,
        source="OEM diagnostic tool",
        method="BMS capacity estimate",
    )
    newer = dict(r, id="b", date="2026-11-01", value=88, method="Measured usable energy")
    h = assess([r, newer, dict(r, id="bad", value=float("nan"))], "p", date(2026, 11, 16))
    assert h["count"] == 1 and h["input_ids"] == ["b"] and h["slope"] is None
    assert {e["id"] for e in h["exclusions"]} == {"a", "bad"}


def test_report_creation_idempotency_expiry_and_error_headers(monkeypatch):
    login()
    options = {"operation_id": "report-retry-expiry", "valid_days": 1}
    r = client.post("/api/vehicles/1/reports", json=options).json()
    assert client.post("/api/vehicles/1/reports", json=options).json()["id"] == r["id"]
    assert client.post("/api/vehicles/2/reports", json=options).status_code == 409
    assert client.post("/api/reports/" + r["id"] + "/publish").status_code == 200
    monkeypatch.setattr("apps.api.app.main.today", lambda: date(2026, 11, 17))
    for suffix in ["", "/pdf", "/qr"]:
        response = client.get("/api/public/reports/" + r["token"] + suffix)
        assert response.status_code == 410
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
        assert response.headers["Cache-Control"] == "no-store"


def test_same_day_sources_use_conservative_allowance():
    r = dict(
        id="a",
        pack="p",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-11-16",
        value=90,
        source="Manual transcription",
    )
    h = assess([r, dict(r, id="z", source="Independent test")], "p", date(2026, 11, 16))
    assert h["count"] == 1 and h["interval"] == [86, 94] and h["quality"] == "limited"


def test_readonly_responses_and_private_attachments():
    login()
    v = client.get("/api/vehicles/1").json()
    assert "base" in v
    login("sales")
    summary = client.get("/api/vehicles/1").json()
    assert not any(
        k in summary
        for k in ["base", "policy", "recommendation", "warranty_evidence", "base_source"]
    )
    assert "••" in summary["vin"]
    assert not any("notes" in r or "actor" in r or "attachment" in r for r in summary["readings"])
    assert client.get("/api/attachments/anything").status_code == 403
    login("technician")
    assert "base" not in client.get("/api/vehicles/1").json()
    assert client.post("/api/session/logout").status_code == 200
    assert client.get("/api/session").status_code == 401


def test_correction_preserves_raw_observation_and_is_idempotent():
    login()
    v = client.get("/api/vehicles/9").json()
    old = sorted(v["readings"], key=lambda r: r["date"])[-1]
    b = {
        "revision": v["revision"],
        "reason": "Corrected transcription against original source image",
        "operation_id": "correction-test-9",
        "reading": {
            "value": old["value"] - 0.2,
            "measurement": "health",
            "basis": old["basis"],
            "date": old["date"],
            "odometer": old["miles"],
            "unit": "mi",
            "source": old["source"],
            "pack": old["pack"],
        },
    }
    r = client.post("/api/readings/" + old["id"] + "/supersede", json=b)
    assert r.status_code == 200, r.text
    assert (
        client.post("/api/readings/" + old["id"] + "/supersede", json=b).json()["id"]
        == r.json()["id"]
    )
    after = client.get("/api/vehicles/9").json()
    original = next(x for x in after["readings"] if x["id"] == old["id"])
    assert original["raw_value"] == old["raw_value"] and original["state"] == "superseded"
    assert (
        old["id"] not in after["assessment"]["input_ids"]
        and r.json()["id"] in after["assessment"]["input_ids"]
    )


def test_epa_ambiguity_selection_and_identity_validation(monkeypatch):
    from apps.api.app.adapters import public_data

    login()
    v = client.get("/api/vehicles/2").json()
    options = {
        "status": "live",
        "source": "https://www.fueleconomy.gov/ws/rest/vehicle/menu/options",
        "retrieved_at": "2026-11-16T00:00:00Z",
        "data": {
            "options": [
                {"value": "111", "text": "AWD extended battery"},
                {"value": "222", "text": "RWD standard battery"},
            ]
        },
    }
    monkeypatch.setattr(public_data, "epa", lambda *args: options)
    assert len(client.get("/api/vehicles/2/external/epa").json()["data"]["options"]) == 2
    monkeypatch.setattr(
        public_data,
        "epa_record",
        lambda *args: {
            "status": "live",
            "source": "https://www.fueleconomy.gov/ws/rest/vehicle/111",
            "retrieved_at": "2026-11-16T00:00:00Z",
            "data": {
                "id": "111",
                "year": v["year"],
                "make": v["make"],
                "model": v["model"],
                "range": 300,
                "drive": "AWD",
            },
        },
    )
    b = {"revision": v["revision"], "record_id": "111", "confirmation": False}
    assert client.post("/api/vehicles/2/epa-match", json=b).status_code == 422
    assert (
        client.post(
            "/api/vehicles/2/epa-match", json=dict(b, record_id="999", confirmation=True)
        ).status_code
        == 422
    )
    assert (
        client.post("/api/vehicles/2/epa-match", json=dict(b, confirmation=True)).status_code == 200
    )
    assert client.get("/api/vehicles/2").json()["epa_match"]["id"] == "111"


def test_public_token_other_dealer_and_rate_limit():
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from apps.api.app.store import engine, put, all_records

    with Session(engine) as s:
        report = all_records(s, "report")[0]
        r = dict(report, id="tenant-public", token="opaque-other-dealer-token", status="published")
        put(s, "report", r["id"], r, "other")
        s.execute(
            text("INSERT INTO public_tokens VALUES (:t,:d,:r)"),
            {"t": r["token"], "d": "other", "r": r["id"]},
        )
        s.commit()
    assert client.get("/api/public/reports/opaque-other-dealer-token").status_code == 200
    with Session(engine) as s:
        import hashlib
        import time

        s.execute(
            text(
                'INSERT INTO rate_limits(client,"window",count) VALUES (:k,:w,90) ON CONFLICT(client,"window") DO UPDATE SET count=90'
            ),
            {"k": hashlib.sha256(b"testclient").hexdigest(), "w": int(time.time()) // 60},
        )
        s.commit()
    assert client.get("/api/public/reports/opaque-other-dealer-token").status_code == 429
    with Session(engine) as s:
        s.execute(text("DELETE FROM rate_limits"))
        s.commit()


def test_ocr_candidates_and_reference_partition():
    from apps.api.app.adapters.extraction import candidates

    assert candidates("Battery 80% Charge limit 90%")["measurement"] == "ambiguous"
    r = candidates("SAMPLE\nBattery health: 92%\nDate: 2026-11-16\nOdometer: 30000 km")
    assert (r["value"], r["unit"], r["odometer"]) == (92, "km", 30000)
    assert candidates("SOH: 92%\nSOH: 88%")["value"] is None
    assert candidates("SOH: 120%")["measurement"] == "ambiguous"
    base = dict(
        id="a",
        pack="p",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-10-01",
        value=90,
        source="OEM diagnostic tool",
    )
    h = assess(
        [
            base,
            dict(
                base, id="b", date="2026-11-01", reference_basis="Documented replacement reference"
            ),
        ],
        "p",
        date(2026, 11, 16),
    )
    assert h["count"] == 1 and h["input_ids"] == ["b"]


def test_null_public_response_is_unavailable(monkeypatch):
    import httpx
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine
    from apps.api.app.adapters.public_data import fetch

    monkeypatch.setenv("DATA_MODE", "live")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=None)))
    with Session(engine) as s:
        assert (
            fetch(s, "https://example.com/null", {}, lambda d: d, client)["status"] == "unavailable"
        )


def test_upload_validation_and_cross_dealer_attachment():
    from io import BytesIO
    from PIL import Image
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, put

    login("technician")
    assert (
        client.post(
            "/api/uploads", files={"file": ("fake.png", b"<script>bad</script>", "image/png")}
        ).status_code
        == 422
    )
    b = BytesIO()
    Image.new("RGB", (20, 20), "white").save(b, format="PNG")
    r = client.post("/api/uploads", files={"file": ("safe.png", b.getvalue(), "image/png")})
    assert r.status_code == 200
    with Session(engine) as s:
        put(
            s,
            "session",
            "attachment-other",
            {"dealer": "other", "role": "technician", "expires_at": time.time() + 3600},
        )
        s.commit()
    other = TestClient(app)
    other.cookies.set("bt_session", "attachment-other")
    assert other.get(r.json()["url"]).status_code == 404


def test_kilometer_original_and_duplicate_photo():
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, put

    login()
    with Session(engine) as s:
        put(s, "attachment", "duplicate-photo", {"id": "duplicate-photo"})
        s.commit()
    body = {
        "value": 91,
        "measurement": "health",
        "date": "2026-11-16",
        "odometer": 100000,
        "unit": "km",
        "source": "OEM diagnostic tool",
        "basis": "usable capacity",
        "pack": "original",
        "attachment": "duplicate-photo",
    }
    d = client.post("/api/service-visits/17/capture-drafts", json=body).json()
    r = client.post("/api/capture-drafts/" + d["id"] + "/confirm")
    assert r.status_code == 200
    assert r.json()["reading"]["original_odometer"] == 100000
    assert abs(r.json()["reading"]["miles"] - 62137.1192237) < 0.001
    body["value"] = 92
    d2 = client.post("/api/service-visits/17/capture-drafts", json=body).json()
    assert client.post("/api/capture-drafts/" + d2["id"] + "/confirm").status_code == 409


def test_service_visit_and_pack_date_guards():
    login("technician")
    visit = client.get("/api/service-visits/1")
    assert visit.status_code == 200
    body = dict(
        value=92,
        measurement="health",
        date="2001-01-01",
        odometer=25000,
        unit="mi",
        source="OEM diagnostic tool",
        pack="replacement",
    )
    assert client.post("/api/service-visits/4/capture-drafts", json=body).status_code == 422
    assert client.get("/api/service-visits/missing").status_code == 404
    login("sales")
    assert client.get("/api/service-visits/1").status_code == 403


def test_software_event_does_not_explain_conflict():
    # Service-event context is deliberately not an input to the numeric engine.
    base = dict(
        pack="original",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        source="OEM diagnostic tool",
    )
    rs = [
        dict(base, id="1", date="2026-01-01", value=89),
        dict(base, id="2", date="2026-05-01", value=88),
        dict(base, id="3", date="2026-11-01", value=99, nearby_software_event=True),
    ]
    h = assess(rs, "original", date(2026, 11, 16))
    assert h["quality"] == "limited" and h["slope"] is None and h["warnings"]


def test_extracted_vehicle_mismatch_blocks_confirmation_draft():
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, put

    login()
    attachment = "a" * 64
    with Session(engine) as s:
        put(
            s,
            "attachment",
            attachment,
            {"id": attachment, "extraction": {"detected_vin": "1G1FY6S08L4100001"}},
        )
        s.commit()
    result = draft(attachment=attachment)
    assert result.status_code == 422 and result.json()["detail"]["code"] == "vehicle_mismatch"


def test_pack_change_after_draft_requires_review():
    from sqlalchemy.orm import Session
    from apps.api.app.store import engine, get, put

    login()
    b = dict(
        value=91,
        measurement="health",
        date="2026-11-16",
        odometer=65000,
        unit="mi",
        source="OEM diagnostic tool",
        pack="original",
    )
    d = client.post("/api/service-visits/18/capture-drafts", json=b).json()
    with Session(engine) as s:
        v = get(s, "vehicle", "18")
        v["pack"] = "replacement"
        put(s, "vehicle", "18", v)
        s.commit()
    r = client.post("/api/capture-drafts/" + d["id"] + "/confirm")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_pack"

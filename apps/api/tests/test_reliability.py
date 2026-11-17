"""Exercise real competing requests and domain boundary failures."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import time

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from apps.api.app.main import app
from apps.api.app.store import engine, get, put, all_records
from apps.api.app.warranty import coverage
from apps.api.app.adapters import public_data


def manager():
    c = TestClient(app)
    assert c.post("/api/session", json={"role": "manager"}).status_code == 200
    return c


def compete(c, path, bodies):
    token = c.cookies.get("bt_session")

    def send(body):
        with TestClient(app) as worker:
            worker.cookies.set("bt_session", token)
            return worker.post(path, json=body)

    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(send, bodies))


def test_concurrent_confirmation_decision_and_report_retries():
    c = manager()
    v = c.get("/api/vehicles/21").json()
    body = dict(
        value=90.1,
        measurement="health",
        date="2026-11-16",
        odometer=v["miles"],
        unit="mi",
        source="OEM diagnostic tool",
        basis="usable capacity",
        pack=v["pack"],
    )
    draft = c.post("/api/service-visits/21/capture-drafts", json=body).json()
    results = compete(c, "/api/capture-drafts/" + draft["id"] + "/confirm", [{}] * 8)
    assert all(r.status_code == 200 for r in results)
    updated = c.get("/api/vehicles/21").json()
    assert updated["revision"] == v["revision"] + 1
    assert sum(r["id"] == draft["id"] for r in updated["readings"]) == 1
    assert (
        sum(a["action"] == "Reading confirmed; assessment completed" for a in updated["activity"])
        == 1
    )

    decision = dict(
        revision=updated["revision"],
        base=updated["base"],
        included=updated["included"],
        policy_version=updated["policy"]["version"],
        reason="Reviewed competing demo requests and battery evidence.",
        operation_id="concurrency-decision-21",
    )
    results = compete(c, "/api/vehicles/21/appraisals", [decision] * 8)
    assert all(r.status_code == 200 for r in results)
    assert len({r.json()["id"] for r in results}) == 1
    v = c.get("/api/vehicles/21").json()
    assert len(v["decisions"]) == 1
    # Two different decisions from the same screen cannot both be accepted.
    decision.update(decision_revision=v["decision_revision"])
    results = compete(
        c,
        "/api/vehicles/21/appraisals",
        [dict(decision, operation_id="race-offer-" + str(i)) for i in range(8)],
    )
    assert sorted(r.status_code for r in results) == [200] + [409] * 7

    results = compete(c, "/api/vehicles/21/reports", [{"operation_id": "race-report-21"}] * 8)
    assert all(r.status_code == 200 for r in results)
    assert len({r.json()["id"] for r in results}) == 1
    report = results[0].json()
    results = compete(c, "/api/reports/" + report["id"] + "/publish", [{}] * 8)
    assert all(r.status_code == 200 for r in results)
    with Session(engine) as s:
        assert (
            sum(
                a["entity"] == "21" and a["action"] == "Report published"
                for a in all_records(s, "audit")
            )
            == 1
        )
    # Different report creations receive unique version numbers.
    results = compete(
        c,
        "/api/vehicles/21/reports",
        [{"operation_id": "race-new-report-" + str(i)} for i in range(8)],
    )
    assert all(r.status_code == 200 for r in results)
    assert len({r.json()["payload"]["version"] for r in results}) == 8


def test_different_drafts_of_same_observation_are_deduplicated_under_race():
    c = manager()
    v = c.get("/api/vehicles/22").json()
    body = dict(
        value=91.2,
        measurement="health",
        date="2026-11-16",
        odometer=v["miles"],
        unit="mi",
        source="OEM diagnostic tool",
        basis="usable capacity",
        pack=v["pack"],
    )
    drafts = [c.post("/api/service-visits/22/capture-drafts", json=body).json() for _ in range(2)]
    token = c.cookies.get("bt_session")

    def send(d):
        with TestClient(app) as worker:
            worker.cookies.set("bt_session", token)
            return worker.post("/api/capture-drafts/" + d["id"] + "/confirm")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, drafts))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert c.get("/api/vehicles/22").json()["revision"] == v["revision"] + 1


def test_expired_and_legacy_sessions_fail_closed_without_mutation():
    c = manager()
    token = c.cookies.get("bt_session")
    for expiry in [time.time() - 1, None]:
        with Session(engine) as s:
            a = get(s, "session", token)
            a.pop("expires_at", None)
            if expiry is not None:
                a["expires_at"] = expiry
            put(s, "session", token, a)
            before = len(all_records(s, "report"))
            s.commit()
        assert c.post("/api/vehicles/23/reports").status_code == 401
        with Session(engine) as s:
            assert len(all_records(s, "report")) == before


def test_exact_warranty_rules_and_invalid_evidence():
    v = dict(
        make="Chevrolet",
        model="Bolt EV",
        year=2023,
        market="US",
        sale_state="CA",
        in_service="2023-11-16",
        transfer_verified=True,
        warranty_start_verified=True,
        miles=99999,
    )
    c = coverage(v, date(2031, 11, 15))
    assert (c["time_remaining"], c["miles_remaining"], c["rule"]["capacity_threshold"]) == (
        1,
        1,
        60,
    )
    assert coverage(v, date(2031, 11, 16))["status"] == "Expired"
    for change in [
        dict(miles=None),
        dict(miles=float("nan")),
        dict(sale_state="ZZ"),
        dict(in_service="bad"),
        dict(in_service="2032-01-01"),
        dict(transfer_verified=False),
        dict(year=2024),
    ]:
        assert (
            coverage(dict(v, **change), date(2026, 11, 16))["status"]
            == "Needs warranty verification"
        )
    assert coverage(dict(v, pack="replacement"), date(2026, 11, 16))["expiry"] == "2031-11-16"
    h = coverage(dict(v, make="Hyundai", model="Ioniq 5"), date(2026, 11, 16))
    assert h["rule"]["status"] == "provisional" and h["time_remaining"] is None
    assert h["rule"]["capacity_threshold"] is None


def test_epa_family_resolution_and_truthful_mixed_cache(monkeypatch):
    original = httpx.Client
    offline = False

    def transport(request):
        if offline:
            return httpx.Response(503)
        if request.url.path.endswith("/model"):
            return httpx.Response(
                200,
                json={
                    "menuItem": [
                        {"text": m, "value": m}
                        for m in ["Mustang Mach-E AWD", "Mustang Mach-E RWD", "Mustang"]
                    ]
                },
            )
        model = request.url.params["model"]
        return httpx.Response(
            200,
            json={
                "menuItem": {
                    "text": "electric drive",
                    "value": "111" if model.endswith("AWD") else "222",
                }
            },
        )

    monkeypatch.setattr(
        public_data.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(transport)),
    )
    monkeypatch.setenv("DATA_MODE", "live")
    with Session(engine) as s:
        result = public_data.epa(s, "Ford", "Mustang Mach-E", 2023)
        assert result["status"] == "live"
        assert len(result["data"]["options"]) == 2
        assert result["data"]["match_status"] == "selection required"
        offline = True
        cached = public_data.epa(s, "Ford", "Mustang Mach-E", 2023)
        assert cached["status"] == "cached"
        assert cached["data"] == result["data"]
        assert cached["retrieved_at"] == result["retrieved_at"]
        # Cached model menu must not contain a previously filtered vehicle family.
        other = public_data.epa(s, "Ford", "Mustang", 2023)
        assert other["data"]["match_status"] == "incomplete"
        assert other["status"] == "partial"


def test_partial_vpic_identity_is_not_verification(monkeypatch):
    original = httpx.Client
    monkeypatch.setenv("DATA_MODE", "live")

    def transport(request):
        return httpx.Response(
            200,
            json={
                "Results": [
                    dict(
                        Make="BMW",
                        Model="X3",
                        ModelYear="2011",
                        ErrorCode="6",
                        ErrorText="Incomplete VIN",
                    )
                ]
            },
        )

    monkeypatch.setattr(
        public_data.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(transport)),
    )
    with Session(engine) as s:
        result = public_data.vin(s, "5UXWX7C5*BA", 2011)
        assert result["status"] == "live"
        assert result["data"]["review_required"] is True
        assert result["data"]["ErrorCode"] == "6"


def test_public_counter_is_atomic_across_processes():
    import subprocess
    import sys
    import json
    import uuid
    from apps.api.app.store import consume_public_request

    key = "process-test-" + uuid.uuid4().hex
    window = int(time.time()) // 60
    code = (
        "import json,sys; from apps.api.app.store import consume_public_request; "
        "print(json.dumps([consume_public_request(sys.argv[1], int(sys.argv[2])) for _ in range(25)]))"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, key, str(window)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    counts = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        counts.extend(json.loads(stdout))
    assert sorted(counts) == list(range(1, 101))
    assert sum(count <= 90 for count in counts) == 90
    assert consume_public_request(key, window + 1) == 1


def test_retryable_database_failure_is_sanitized_and_rolls_back():
    from sqlalchemy.exc import OperationalError
    from unittest.mock import patch

    c = manager()
    with Session(engine) as s:
        before = len(all_records(s, "report"))
    with patch(
        "apps.api.app.main.audit",
        side_effect=OperationalError(
            "secret-db-password", {}, RuntimeError("private connection details")
        ),
    ):
        response = c.post("/api/vehicles/23/reports")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_busy"
    assert "secret" not in response.text and "private" not in response.text
    with Session(engine) as s:
        assert len(all_records(s, "report")) == before


def test_domain_quarantines_future_and_malformed_imports():
    from apps.api.app.domain import assess

    base = dict(
        id="valid",
        pack="original",
        state="confirmed",
        measurement="health",
        basis="usable capacity",
        date="2026-11-01",
        value=90,
        source="OEM diagnostic tool",
    )
    imported = [
        dict(base, id="future", date="2027-01-01"),
        dict(base, id="bad-date", date="yesterday"),
        dict(base, id="missing-date", date=None),
        dict(base, id="bad-value", value=True),
    ]
    h = assess([base] + imported, "original", date(2026, 11, 16))
    assert h["input_ids"] == ["valid"]
    assert h["last"]["id"] == "valid" and h["slope"] is None
    assert {r["id"] for r in h["exclusions"]} == {"future", "bad-date", "missing-date", "bad-value"}


def test_warranty_retains_known_headroom_when_one_input_is_missing():
    v = dict(
        make="Chevrolet",
        model="Bolt EUV",
        year=2023,
        market="US",
        sale_state="IL",
        in_service=None,
        transfer_verified=True,
        warranty_start_verified=False,
        miles=99500,
    )
    c = coverage(v, date(2026, 11, 16))
    assert c["status"] == "Needs warranty verification"
    assert c["miles_remaining"] == 500 and c["time_remaining"] is None
    c = coverage(
        dict(v, in_service="2023-11-16", warranty_start_verified=True, miles=None),
        date(2026, 11, 16),
    )
    assert c["status"] == "Needs warranty verification"
    assert c["expiry"] == "2031-11-16" and c["miles_remaining"] is None
    c = coverage(dict(v, miles=100000), date(2026, 11, 16))
    assert c["status"] == "Expired"

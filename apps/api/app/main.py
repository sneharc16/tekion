import os
import uuid
import secrets
import hashlib
import json
import io
from datetime import date, timedelta
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Response, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from PIL import Image
import qrcode
from .store import engine, migrate, seed, put, get, all_records, now, today
from .domain import assess, appraisal, POLICY
from .warranty import coverage, RULES, US_STATES
from .store import seed_warranty_examples, seed_metadata
from .store import serialize_write, consume_public_request
from sqlalchemy.exc import OperationalError
from .security import staff_summary
from .adapters.local_dms import LocalDMSAdapter
from .adapters.files import images
from .contracts import PublicReport, SourceRecord
from sqlalchemy import text

migrate()
seed()
seed_warranty_examples()
seed_metadata()
app = FastAPI(title="Battery Timeline", version="0.1.0")


@app.exception_handler(OperationalError)
async def database_unavailable(request, error):
    # Do not expose connection strings or database exception details to clients.
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "database_busy",
                "message": "The save could not complete. Your entries are preserved; retry shortly.",
            }
        },
        headers={"Retry-After": "2"},
    )


def uid():
    return uuid.uuid4().hex


def db(request: Request):
    with Session(engine) as s:
        if request.method not in ("GET", "HEAD") and not request.url.path.endswith("/extract"):
            serialize_write(s)
        yield s
        s.commit()


def fail(code, msg, status=422):
    raise HTTPException(status, detail={"code": code, "message": msg})


def actor(request: Request, s=Depends(db)):
    a = get(s, "session", request.cookies.get("bt_session", ""))
    if not a or a.get("expires_at", 0) <= __import__("time").time():
        fail("session_required", "Choose a demo role to continue", 401)
    if (
        request.method not in ("GET", "HEAD")
        and request.headers.get("origin")
        and request.headers["origin"]
        not in (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            os.getenv("PUBLIC_BASE_URL", "http://localhost:5173"),
        )
    ):
        fail("origin", "Untrusted request origin", 403)
    return a


def permit(a, roles):
    if a["role"] not in roles:
        fail("permission", "This role cannot perform this action", 403)


def vehicle(s, id, a):
    v = LocalDMSAdapter(s, a["dealer"]).vehicle(id)
    if not v:
        fail("not_found", "Vehicle not found", 404)
    return v


def readings(s, id, a):
    return [r for r in all_records(s, "reading", a["dealer"]) if r["vehicle"] == id]


def assessment(s, v, a):
    return assess(readings(s, v["id"], a), v["pack"], today())


def audit(s, a, entity, action):
    id = uid()
    put(
        s,
        "audit",
        id,
        {"id": id, "entity": entity, "action": action, "actor": a["role"], "at": now()},
        a["dealer"],
    )


def current_policy(s, a):
    config = get(s, "configuration", "policy", a["dealer"])
    return get(s, "policy", config["version"], a["dealer"]) if config else POLICY


def detail(s, v, a):
    h = assessment(s, v, a)
    return dict(
        v,
        assessment=h,
        warranty=coverage(v, today()),
        recommendation=appraisal(h, v["base"], v["included"], current_policy(s, a)),
        policy=current_policy(s, a),
    )


class Login(BaseModel):
    role: Literal["manager", "technician", "sales"]


@app.post("/api/session")
def login(body: Login, response: Response, s=Depends(db)):
    if os.getenv("DEMO_MODE", "true") != "true":
        fail("demo_disabled", "Demo sessions are disabled", 403)
    token = secrets.token_urlsafe(32)
    a = {"role": body.role, "dealer": "demo", "expires_at": __import__("time").time() + 28800}
    put(s, "session", token, a)
    response.set_cookie(
        "bt_session",
        token,
        httponly=True,
        samesite="strict",
        max_age=28800,
        secure=os.getenv("COOKIE_SECURE") == "true",
    )
    return a


@app.get("/api/session")
def session(a=Depends(actor)):
    return dict(a, as_of=str(today()), dealer_name="Northline Motors", timezone="America/Chicago")


@app.get("/api/health")
def health():
    return {"status": "ok", "as_of": str(today()), "demo": os.getenv("DEMO_MODE", "true") == "true"}


@app.get("/api/vehicles")
def vehicles(a=Depends(actor), s=Depends(db), offset: int = 0, limit: int = 50):
    if offset < 0 or not 1 <= limit <= 100:
        fail("pagination", "Invalid page range")
    vs = sorted(all_records(s, "vehicle", a["dealer"]), key=lambda v: v["stock"])
    return {
        "items": [staff_summary(detail(s, v, a), a["role"]) for v in vs[offset : offset + limit]],
        "total": len(vs),
    }


@app.get("/api/vehicles/{id}")
def one(id: str, a=Depends(actor), s=Depends(db)):
    v = vehicle(s, id, a)
    result = dict(
        detail(s, v, a),
        packs=[p for p in all_records(s, "pack", a["dealer"]) if p["vehicle"] == id],
        readings=readings(s, id, a),
        events=[e for e in all_records(s, "event", a["dealer"]) if e["vehicle"] == id],
        decisions=[
            dict(d, newer_evidence=d["revision"] != v["revision"])
            for d in all_records(s, "decision", a["dealer"])
            if d["vehicle"] == id
        ],
        activity=[e for e in all_records(s, "audit", a["dealer"]) if e["entity"] == id],
    )
    return staff_summary(result, a["role"])


class Reading(BaseModel):
    value: float = Field(ge=0, le=100, allow_inf_nan=False)
    measurement: Literal["health", "charge", "ambiguous"]
    date: date
    odometer: float = Field(ge=0, le=2000000, allow_inf_nan=False)
    unit: Literal["mi", "km"]
    source: Literal[
        "OEM diagnostic tool", "OEM dashboard", "Independent test", "Manual transcription"
    ]
    basis: Literal["usable capacity", "unknown"] = "usable capacity"
    pack: str
    method: Literal["BMS capacity estimate", "Measured usable energy", "unknown"] = (
        "BMS capacity estimate"
    )
    reference_basis: Literal[
        "Original usable capacity", "Documented replacement reference", "unknown"
    ] = "Original usable capacity"
    temperature_c: float | None = Field(default=None, ge=-50, le=100, allow_inf_nan=False)
    soc_at_measurement: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    notes: str = Field(default="", max_length=2000)
    attachment: str | None = None


@app.post("/api/service-visits/{id}/capture-drafts")
def draft(id: str, b: Reading, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager", "technician"])
    visit = LocalDMSAdapter(s, a["dealer"]).service_visit(id)
    if not visit:
        fail("not_found", "Service visit not found", 404)
    v = vehicle(s, visit["vehicle"], a)
    pack = get(s, "pack", v["id"] + ":" + b.pack, a["dealer"])
    if pack and pack.get("start_date") and b.date < date.fromisoformat(pack["start_date"]):
        fail("pack_date", "Reading predates the documented pack segment")
    if b.date > today() or b.date < date(2000, 1, 1):
        fail("reading_date", "Reading date must be between Jan 1, 2000 and the assessment date")
    if b.pack != v["pack"]:
        fail("pack", "Select the current verified pack segment")
    if b.attachment:
        attachment = get(s, "attachment", b.attachment, a["dealer"])
        if not attachment:
            fail("attachment", "Attachment not found", 404)
        extracted_vin = attachment.get("extraction", {}).get("detected_vin")
        if extracted_vin and extracted_vin != v["vin"]:
            fail(
                "vehicle_mismatch",
                "The image identifies another VIN. Review the source before confirming.",
            )
    d = dict(b.model_dump(mode="json"), id=uid(), vehicle=v["id"], visit=id, state="draft")
    put(s, "draft", d["id"], d, a["dealer"])
    return d


@app.post("/api/capture-drafts/{id}/confirm")
def confirm(id: str, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager", "technician"])
    d = get(s, "draft", id, a["dealer"])
    if not d:
        fail("not_found", "Draft not found", 404)
    if d["state"] == "confirmed":
        return {"reading": get(s, "reading", id, a["dealer"]), "status": "already confirmed"}
    if d["measurement"] != "health":
        fail(
            "not_health",
            "We could not confirm this is battery health. Charge percentage cannot be used as health.",
        )
    if d.get("reference_basis") == "unknown":
        fail("reference", "Confirm the reference capacity basis before adding this reading")
    if d.get("method") == "unknown":
        fail("method", "Confirm the measurement method before adding to the assessment")
    if d["basis"] != "usable capacity":
        fail("basis", "Confirm the measurement basis before adding to the assessment")
    v = vehicle(s, d["vehicle"], a)
    if d["pack"] != v["pack"]:
        fail("stale_pack", "The active pack changed. Review this draft before confirming.", 409)
    miles = d["odometer"] * (0.621371192237334 if d["unit"] == "km" else 1)
    rs = readings(s, v["id"], a)
    for r in rs:
        if r["state"] == "superseded":
            continue
        if (r["date"] == d["date"] and r["pack"] == d["pack"] and r["value"] == d["value"]) or (
            d["attachment"] and r.get("attachment") == d["attachment"]
        ):
            fail("duplicate", "This test is already recorded", 409)
        if (r["date"] < d["date"] and r["miles"] > miles) or (
            r["date"] > d["date"] and r["miles"] < miles
        ):
            fail(
                "odometer", "Odometer conflicts with recorded history. Review the original reading."
            )
    r = dict(
        d,
        state="confirmed",
        miles=miles,
        original_odometer=d["odometer"],
        raw_value=d["value"],
        actor=a["role"],
        created_at=now(),
        provenance="Dealer-entered observation",
    )
    source = SourceRecord(
        id=id,
        vehicle=v["id"],
        title="Confirmed capacity observation",
        provider=r["source"],
        provenance="dealer entered",
        retrieved_at=now(),
        attachment=r.get("attachment"),
    )
    put(s, "source", id, source.model_dump(), a["dealer"])
    put(s, "reading", id, r, a["dealer"])
    visit = get(s, "visit", d.get("visit", v["id"]), a["dealer"])
    if visit:
        visit.update(state="Battery evidence confirmed", latest_reading=id)
        put(s, "visit", visit["id"], visit, a["dealer"])
    d["state"] = "confirmed"
    put(s, "draft", id, d, a["dealer"])
    v["miles"] = max(v["miles"], miles)
    v["revision"] += 1
    put(s, "vehicle", v["id"], v, a["dealer"])
    h = assessment(s, v, a)
    put(s, "assessment", uid(), h, a["dealer"])
    audit(s, a, v["id"], "Reading confirmed; assessment completed")
    return {"reading": r, "assessment": h, "status": "completed"}


@app.post("/api/uploads")
async def upload(file: UploadFile = File(...), a=Depends(actor), s=Depends(db)):
    permit(a, ["manager", "technician"])
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        fail("size", "Image must be under 8 MB")
    try:
        im = Image.open(io.BytesIO(content))
        im.verify()
        im = Image.open(io.BytesIO(content))
        if im.format not in ("PNG", "JPEG", "WEBP") or im.width * im.height > 20000000:
            raise ValueError()
        im = im.convert("RGB")
    except Exception:
        fail("image", "Upload a readable PNG, JPEG or WebP image")
    id = hashlib.sha256(content).hexdigest()
    images.save(id, im)
    from .adapters.extraction import configured

    put(s, "attachment", id, {"id": id, "created_at": now()}, a["dealer"])
    return {
        "id": id,
        "url": f"/api/attachments/{id}",
        "extraction": "available" if configured() else "unavailable",
        "message": "Image stored. Extract candidate fields or enter the reading manually."
        if configured()
        else "Image stored. Automatic extraction is not configured. Review the image and enter confirmed fields manually.",
    }


@app.get("/api/attachments/{id}")
def attachment(id: str, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager", "technician"])
    if not get(s, "attachment", id, a["dealer"]):
        fail("not_found", "Attachment not found", 404)
    return FileResponse(images.path(id), media_type="image/jpeg")


class Decision(BaseModel):
    revision: int
    base: float = Field(ge=0, le=1000000, allow_inf_nan=False)
    included: Literal["yes", "no", "unknown"]
    amount: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    reason: str = Field(default="", max_length=2000)
    operation_id: str = Field(min_length=8, max_length=100)
    decision_revision: int = Field(default=0, ge=0)
    policy_version: str = "demo-v1"


@app.post("/api/vehicles/{id}/appraisals")
def decide(id: str, b: Decision, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    v = vehicle(s, id, a)
    prior = get(s, "decision", b.operation_id, a["dealer"])
    if prior:
        if (
            prior.get("request_hash")
            and prior["request_hash"] != hashlib.sha256(b.model_dump_json().encode()).hexdigest()
        ):
            fail(
                "operation_conflict",
                "This decision request identifier was already used with different inputs",
                409,
            )
        if prior["vehicle"] != id:
            fail("operation_conflict", "This operation identifier belongs to another vehicle", 409)
        return prior
    if b.revision != v["revision"]:
        fail("stale", "New evidence arrived. Refresh before deciding.", 409)
    policy = current_policy(s, a)
    if b.policy_version != policy["version"] or b.decision_revision != v.get(
        "decision_revision", 0
    ):
        fail("stale", "The policy or appraisal decision changed. Refresh before deciding.", 409)
    if b.base != v["base"] or b.included != v["included"]:
        fail("inputs", "Save the starting appraisal inputs before accepting", 409)
    h = assessment(s, v, a)
    rec = appraisal(h, b.base, b.included, policy)
    if not rec["interval"]:
        fail("evidence", rec["reason"])
    if (h["quality"] == "limited" or b.amount is not None) and len(b.reason.strip()) < 10:
        fail("reason", "A review or override requires a reason of at least 10 characters")
    d = {
        "id": b.operation_id,
        "request_hash": hashlib.sha256(b.model_dump_json().encode()).hexdigest(),
        "vehicle": id,
        "revision": v["revision"],
        "assessment": h,
        "policy": policy,
        "base": b.base,
        "base_source": v.get("base_source", "Synthetic dealer appraisal"),
        "base_effective_date": v.get("base_effective_date", str(today())),
        "included": b.included,
        "recommendation": rec,
        "customer_note": "Your offer uses the available battery readings and warranty verification status. Ask us to walk through the evidence considered.",
        "accepted": b.amount if b.amount is not None else round(sum(rec["interval"]) / 2),
        "reason": b.reason,
        "actor": a["role"],
        "at": now(),
    }
    v["decision_revision"] = v.get("decision_revision", 0) + 1
    put(s, "vehicle", id, v, a["dealer"])
    put(s, "decision", d["id"], d, a["dealer"])
    audit(s, a, id, "Appraisal accepted" if b.amount is None else "Appraisal overridden")
    return d


@app.get("/api/reports")
def reports(a=Depends(actor), s=Depends(db)):
    return [
        dict(
            r,
            newer_evidence=r.get("vehicle_revision") is not None
            and r["vehicle_revision"] != get(s, "vehicle", r["vehicle"], a["dealer"])["revision"],
            status="expired" if report_expired(r) and r["status"] != "revoked" else r["status"],
        )
        for r in all_records(s, "report", a["dealer"])
        if a["role"] == "manager" or r["status"] != "draft"
    ]


class ReportOptions(BaseModel):
    operation_id: str | None = Field(default=None, min_length=8, max_length=100)
    valid_days: int = Field(default=90, ge=1, le=365)


@app.post("/api/vehicles/{id}/reports")
def report(id: str, b: ReportOptions | None = None, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    v = vehicle(s, id, a)
    b = b or ReportOptions()
    if b.operation_id:
        prior = get(s, "report_operation", b.operation_id, a["dealer"])
        if prior:
            if prior["vehicle"] != id or prior["valid_days"] != b.valid_days:
                fail(
                    "operation_conflict",
                    "Report request identifier was already used for another request",
                    409,
                )
            return get(s, "report", prior["report_id"], a["dealer"])
    h = assessment(s, v, a)
    segment = get(s, "pack", id + ":" + v["pack"], a["dealer"])
    token = secrets.token_urlsafe(32)
    rs = [
        {"date": r["date"], "value": r["value"], "source": r["source"], "miles": r["miles"]}
        for r in readings(s, id, a)
        if r["id"] in h["input_ids"]
    ]
    payload = {
        "title": "Battery Health Report",
        "subtitle": "Dealer-issued evidence summary",
        "vehicle": f"{v['year']} {v['make']} {v['model']}",
        "vin": "•••••••••••" + v["vin"][-6:],
        "miles": v["miles"],
        "interval": h["interval"],
        "last": {"date": h["last"]["date"], "value": h["last"]["value"]} if h["last"] else None,
        "quality": h["quality"],
        "reason": h["reason"],
        "warnings": h["warnings"],
        "readings": rs,
        "pack": v["pack"],
        "pack_context": {k: segment.get(k) for k in ["start_date", "verification"]}
        if segment
        else None,
        "warranty": warranty_summary(coverage(v, today())),
        "coverage": coverage(v, today()),
        "dealer": "Northline Motors · Demo data",
        "as_of": str(today()),
        "expires_on": str(today() + timedelta(days=b.valid_days)),
        "generated_at": now(),
        "limitations": "Illustrative estimate from available capacity readings. Not independent certification or a guarantee of future performance. Current pack only.",
    }
    rid = uid()
    version = 1 + sum(r["vehicle"] == id for r in all_records(s, "report", a["dealer"]))
    payload["version"] = version
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    r = {
        "id": rid,
        "vehicle": id,
        "token": token,
        "status": "draft",
        "payload": payload,
        "integrity": digest,
        "vehicle_revision": v["revision"],
    }
    put(s, "report", rid, r, a["dealer"])
    s.execute(
        text("INSERT INTO public_tokens VALUES (:t,:d,:r)"),
        {"t": token, "d": a["dealer"], "r": rid},
    )
    audit(s, a, id, "Report preview created")
    if b.operation_id:
        put(
            s,
            "report_operation",
            b.operation_id,
            {"vehicle": id, "report_id": rid, "valid_days": b.valid_days},
            a["dealer"],
        )
    return r


@app.post("/api/reports/{id}/{action}")
def report_action(id: str, action: Literal["publish", "revoke"], a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    r = get(s, "report", id, a["dealer"])
    if not r:
        fail("not_found", "Report not found", 404)
    if r["status"] == "revoked":
        if action == "revoke":
            return r
        fail("revoked", "Revoked versions cannot be republished", 409)
    if action == "publish" and report_expired(r):
        fail("expired", "Create a new report version; this snapshot has expired", 410)
    if action == "publish" and r["status"] == "published":
        return r
    r["status"] = "published" if action == "publish" else "revoked"
    put(s, "report", id, r, a["dealer"])
    audit(s, a, r["vehicle"], f"Report {r['status']}")
    return r


def report_expired(r):
    expires = r["payload"].get("expires_on")
    return bool(expires and date.fromisoformat(expires) <= today())


@app.middleware("http")
async def public_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/public/"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Cache-Control"] = "no-store"
    return response


def public_report(token, request, s):
    import time

    key = hashlib.sha256(request.client.host.encode()).hexdigest()
    window = int(time.time()) // 60
    # Separate transaction persists the limit even when the requested token is invalid.
    count = consume_public_request(key, window)
    if count > 90:
        fail("rate_limit", "Try again shortly", 429)
    ref = s.execute(
        text("SELECT dealer,report_id FROM public_tokens WHERE token=:t"), {"t": token}
    ).first()
    r = get(s, "report", ref[1], ref[0]) if ref else None
    if not r or r["status"] == "draft":
        fail("not_found", "Report not found", 404)
    if report_expired(r):
        fail("expired", "This report has expired. Ask the dealer for a current version.", 410)
    if r["status"] == "revoked":
        fail("revoked", "This report has been revoked. Ask the dealer for an updated version.", 410)
    return r


@app.get(
    "/api/public/reports/{token}", response_model=PublicReport, response_model_exclude_none=True
)
def public(token: str, request: Request, response: Response, s=Depends(db)):
    r = public_report(token, request, s)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-store"
    return dict(r["payload"], status=r["status"], integrity=r["integrity"])


def link(token):
    return os.getenv("PUBLIC_BASE_URL", "http://localhost:5173").rstrip("/") + "/r/" + token


@app.get("/api/public/reports/{token}/qr")
def qr(token: str, request: Request, s=Depends(db)):
    public_report(token, request, s)
    b = io.BytesIO()
    qrcode.make(link(token)).save(b, format="PNG")
    return Response(b.getvalue(), media_type="image/png", headers={"X-Robots-Tag": "noindex"})


@app.get("/api/public/reports/{token}/pdf")
def pdf(token: str, request: Request, s=Depends(db)):
    from .report_pdf import render

    r = public_report(token, request, s)
    return Response(
        render(r["payload"], link(token), r["integrity"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="battery-report-v{r["payload"]["version"]}.pdf"',
            "X-Robots-Tag": "noindex",
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/sources")
def sources(a=Depends(actor), s=Depends(db)):
    return {
        "mode": os.getenv("DATA_MODE", "fixture"),
        "as_of": str(today()),
        "vehicle_count": len(all_records(s, "vehicle", a["dealer"])),
        "policy": current_policy(s, a) if a["role"] == "manager" else None,
        "sources": [
            {
                "title": "NHTSA vPIC",
                "url": "https://vpic.nhtsa.dot.gov/api/",
                "status": "Server adapter available; explicit DATA_MODE=live required",
            },
            {
                "title": "Manufacturer warranty documents",
                "url": RULES[0]["source"],
                "status": "2023 US Ford Mustang Mach-E and Chevrolet Bolt EV/EUV rules reviewed; Hyundai provisional",
            },
        ],
        "warranty_rules": RULES,
    }


@app.get("/api/vehicles/{id}/external/{provider}")
def external(id: str, provider: Literal["vin", "recalls", "epa"], a=Depends(actor), s=Depends(db)):
    from .adapters import public_data

    v = vehicle(s, id, a)
    permit(a, ["manager", "technician"])
    result = (
        public_data.vin(s, v["vin"], v["year"])
        if provider == "vin"
        else getattr(public_data, provider)(s, v["make"], v["model"], v["year"])
    )
    result["identity"] = [v["year"], v["make"], v["model"]]
    put(s, "external_result", id + ":" + provider, result, a["dealer"])
    return result


@app.post("/api/attachments/{id}/extract")
def extract_attachment(id: str, a=Depends(actor), s=Depends(db)):
    from .adapters.extraction import extract

    permit(a, ["manager", "technician"])
    if not get(s, "attachment", id, a["dealer"]):
        fail("not_found", "Attachment not found", 404)
    result = extract(images.path(id))
    source = get(s, "attachment", id, a["dealer"])
    source["extraction"] = result
    put(s, "attachment", id, source, a["dealer"])
    audit(s, a, id, "OCR review requested; no reading confirmed")
    return result


class PolicyInput(BaseModel):
    previous_version: str
    reference_health: float = Field(ge=0, le=100, allow_inf_nan=False)
    dollars_per_point: float = Field(ge=0, le=10000, allow_inf_nan=False)
    cap: float = Field(ge=0, le=50000, allow_inf_nan=False)
    reserve: float = Field(ge=0, le=50000, allow_inf_nan=False)


@app.post("/api/settings/appraisal-policy")
def save_policy(b: PolicyInput, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    old = current_policy(s, a)
    if b.previous_version != old["version"]:
        fail("stale", "Policy changed. Reload before saving.", 409)
    p = dict(
        b.model_dump(exclude={"previous_version"}),
        version="dealer-" + uid()[:12],
        label=POLICY["label"],
        effective_date=str(today()),
        created_at=now(),
        actor=a["role"],
    )
    if not get(s, "policy", old["version"], a["dealer"]):
        put(s, "policy", old["version"], old, a["dealer"])
    put(s, "policy", p["version"], p, a["dealer"])
    put(s, "configuration", "policy", {"version": p["version"]}, a["dealer"])
    audit(s, a, "policy", "New appraisal policy version saved: " + p["version"])
    return p


class ValuationInput(BaseModel):
    revision: int
    base: float = Field(ge=0, le=1000000, allow_inf_nan=False)
    included: Literal["yes", "no", "unknown"]
    source: str = Field(min_length=3, max_length=200)
    effective_date: date


@app.post("/api/vehicles/{id}/valuation")
def save_valuation(id: str, b: ValuationInput, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    v = vehicle(s, id, a)
    if v["revision"] != b.revision:
        fail("stale", "Vehicle changed. Reload before saving.", 409)
    if b.effective_date > today():
        fail("date", "Effective date cannot be in the future")
    v.update(
        base=b.base,
        included=b.included,
        base_source=b.source,
        base_effective_date=str(b.effective_date),
        revision=v["revision"] + 1,
    )
    put(s, "vehicle", id, v, a["dealer"])
    audit(s, a, id, "Starting appraisal inputs saved")
    return detail(s, v, a)


class WarrantyInput(BaseModel):
    revision: int
    in_service: date | None = None
    market: Literal["US", "unknown"] = "unknown"
    sale_state: str = Field(default="", max_length=2)
    transfer_verified: bool = False
    warranty_start_verified: bool = False
    warranty_evidence: str = Field(min_length=10, max_length=1000)


@app.post("/api/vehicles/{id}/warranty")
def save_warranty(id: str, b: WarrantyInput, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    v = vehicle(s, id, a)
    if v["revision"] != b.revision:
        fail("stale", "Vehicle changed. Reload before saving.", 409)
    if b.in_service and (b.in_service > today() or b.in_service.year < v["year"] - 1):
        fail("date", "Check the actual in-service date against model year and assessment date")
    if b.warranty_start_verified and not b.in_service:
        fail("date", "Supply the documented warranty start date")
    if b.sale_state and b.sale_state not in US_STATES:
        fail("jurisdiction", "Enter a valid US state or DC code, or leave it unknown")
    v.update(b.model_dump(mode="json", exclude={"revision"}))
    v["revision"] += 1
    put(s, "vehicle", id, v, a["dealer"])
    audit(s, a, id, "Warranty application evidence saved")
    return coverage(v, today())


def warranty_summary(c):
    if c["status"] == "Needs warranty verification":
        known = []
        if c["time_remaining"] is not None:
            known.append(f"{c['time_remaining']} days to time limit")
        if c["miles_remaining"] is not None:
            known.append(f"{c['miles_remaining']:,.0f} mi to mileage limit")
        return c["status"] + ". " + ("; ".join(known) + ". " if known else "") + c["reason"]
    days = "Unknown time" if c["time_remaining"] is None else f"{c['time_remaining']} days"
    miles = "unknown mileage" if c["miles_remaining"] is None else f"{c['miles_remaining']:,.0f} mi"
    return f"{c['status']}: {days} and {miles} remaining, whichever comes first. Capacity threshold {c['rule']['capacity_threshold']}%; manufacturer determination required."


class EvidenceReview(BaseModel):
    revision: int
    reason: str = Field(min_length=10, max_length=1000)


@app.post("/api/readings/{id}/exclude")
def exclude_reading(id: str, b: EvidenceReview, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    r = get(s, "reading", id, a["dealer"])
    if not r:
        fail("not_found", "Reading not found", 404)
    v = vehicle(s, r["vehicle"], a)
    if b.revision != v["revision"]:
        fail("stale", "Evidence changed. Reload before reviewing.", 409)
    if r["state"] != "confirmed":
        fail("state", "Only confirmed readings can be excluded", 409)
    original = dict(r)
    r.update(state="excluded", exclusion_reason=b.reason, excluded_at=now(), excluded_by=a["role"])
    put(
        s,
        "reading_amendment",
        uid(),
        {"original": original, "reason": b.reason, "actor": a["role"], "at": now()},
        a["dealer"],
    )
    put(s, "reading", id, r, a["dealer"])
    v["revision"] += 1
    put(s, "vehicle", v["id"], v, a["dealer"])
    audit(s, a, v["id"], "Reading excluded from assessment: " + id)
    return assessment(s, v, a)


@app.post("/api/session/logout")
def logout(response: Response, request: Request, a=Depends(actor), s=Depends(db)):
    s.execute(
        text("DELETE FROM records WHERE kind='session' AND id=:id"),
        {"id": request.cookies.get("bt_session")},
    )
    response.delete_cookie("bt_session")
    return {"status": "signed out"}


class ReadingCorrection(BaseModel):
    revision: int
    reason: str = Field(min_length=10, max_length=1000)
    operation_id: str = Field(min_length=8, max_length=100)
    reading: Reading


@app.post("/api/readings/{id}/supersede")
def supersede(id: str, b: ReadingCorrection, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    r = get(s, "reading", id, a["dealer"])
    if not r:
        fail("not_found", "Reading not found", 404)
    fingerprint = hashlib.sha256(b.model_dump_json().encode()).hexdigest()
    prior = get(s, "correction_operation", b.operation_id, a["dealer"])
    if prior:
        if prior["fingerprint"] != fingerprint or prior["original"] != id:
            fail("operation_conflict", "Correction request identifier has different inputs", 409)
        return get(s, "reading", prior["replacement"], a["dealer"])
    v = vehicle(s, r["vehicle"], a)
    if b.revision != v["revision"] or r["state"] == "superseded":
        fail("stale", "Reading changed. Reload before correcting.", 409)
    if b.reading.pack != r["pack"]:
        fail("pack", "A correction cannot move evidence between battery packs")
    original = dict(r)
    d = draft(v["id"], b.reading, a, s)
    r.update(state="superseded", superseded_by=d["id"], amendment_reason=b.reason)
    put(s, "reading", id, r, a["dealer"])
    result = confirm(d["id"], a, s)["reading"]
    result["supersedes"] = id
    put(s, "reading", result["id"], result, a["dealer"])
    put(
        s,
        "reading_amendment",
        uid(),
        {
            "original": original,
            "replacement": result["id"],
            "reason": b.reason,
            "actor": a["role"],
            "at": now(),
        },
        a["dealer"],
    )
    put(
        s,
        "correction_operation",
        b.operation_id,
        {"fingerprint": fingerprint, "original": id, "replacement": result["id"]},
        a["dealer"],
    )
    audit(s, a, v["id"], "Reading corrected; original retained: " + id)
    return result


class IdentityInput(BaseModel):
    revision: int
    vin: str = Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")
    make: str = Field(min_length=2, max_length=50)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1996, le=2030)
    trim: str = Field(default="", max_length=80)
    reason: str = Field(min_length=10, max_length=1000)


@app.post("/api/vehicles/{id}/identity")
def resolve_identity(id: str, b: IdentityInput, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager"])
    v = vehicle(s, id, a)
    if b.revision != v["revision"]:
        fail("stale", "Vehicle changed. Reload before resolving identity.", 409)
    before = {k: v.get(k) for k in ["vin", "make", "model", "year", "trim"]}
    v.update(b.model_dump(exclude={"revision", "reason"}))
    v.update(
        identification_status="Dealer-entered; not externally verified",
        identity_reason=b.reason,
        epa_match=None,
        warranty_start_verified=False,
        transfer_verified=False,
        revision=v["revision"] + 1,
    )
    put(s, "vehicle", id, v, a["dealer"])
    put(
        s,
        "identity_amendment",
        uid(),
        {"vehicle": id, "before": before, "reason": b.reason, "actor": a["role"], "at": now()},
        a["dealer"],
    )
    audit(
        s,
        a,
        id,
        "Vehicle identity manually resolved; external matching and warranty require review",
    )
    return detail(s, v, a)


class EPAMatch(BaseModel):
    revision: int
    record_id: str = Field(pattern=r"^\d{1,8}$")
    confirmation: bool


@app.post("/api/vehicles/{id}/epa-match")
def match_epa(id: str, b: EPAMatch, a=Depends(actor), s=Depends(db)):
    from .adapters import public_data

    permit(a, ["manager"])
    v = vehicle(s, id, a)
    if v["revision"] != b.revision:
        fail("stale", "Vehicle changed. Reload matching options.", 409)
    if not b.confirmation:
        fail("confirmation", "Confirm trim, drive and battery variant against the record")
    options = get(s, "external_result", id + ":epa", a["dealer"])
    identity = [v["year"], v["make"], v["model"]]
    if not options or options.get("identity") != identity or not options.get("data"):
        fail("options", "Load the current EPA options before selecting a record")
    if options["data"].get("match_status") == "incomplete":
        fail("options", "Retry EPA lookup; not all variant options were retrieved", 503)
    if b.record_id not in [str(x["value"]) for x in options["data"]["options"]]:
        fail("option", "Select a record from the supplied options")
    record = public_data.epa_record(s, b.record_id)
    if not record.get("data"):
        fail("unavailable", "EPA record unavailable; saved match remains unchanged", 503)
    data = record["data"]
    selected = next(x for x in options["data"]["options"] if str(x["value"]) == b.record_id)
    if (
        str(data.get("year")) != str(v["year"])
        or data.get("make", "").casefold() != v["make"].casefold()
        or data.get("model", "").casefold() != selected.get("epa_model", v["model"]).casefold()
        or str(data.get("id")) != b.record_id
    ):
        fail("identity", "EPA vehicle identity does not match. Review the vehicle and options.")
    v["epa_match"] = {
        "id": b.record_id,
        "status": "Dealer confirmed variant",
        "description": data,
        "source": record["source"],
        "retrieved_at": record["retrieved_at"],
        "provenance": record["status"],
    }
    v["revision"] += 1
    put(s, "vehicle", id, v, a["dealer"])
    audit(s, a, id, "EPA variant explicitly selected; range is not an SOH input")
    return v["epa_match"]


@app.get("/api/service-visits/{id}")
def service_visit(id: str, a=Depends(actor), s=Depends(db)):
    permit(a, ["manager", "technician"])
    visit = LocalDMSAdapter(s, a["dealer"]).service_visit(id)
    if not visit:
        fail("not_found", "Service visit not found", 404)
    vehicle(s, visit["vehicle"], a)
    return visit

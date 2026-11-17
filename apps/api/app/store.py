import os
import json
from datetime import date, timedelta, datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from pathlib import Path

Path("data").mkdir(exist_ok=True)
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./data/battery.db"))


def serialize_write(connection):
    """Serialize aggregate mutations across workers; released on commit/rollback.

    A single application lock deliberately mirrors SQLite's write serialization.
    This keeps cross-record checks atomic, including new record/idempotency keys.
    PostgreSQL reads and public rate-limit upserts remain independent.
    """
    dialect = (
        connection.get_bind().dialect if isinstance(connection, Session) else connection.dialect
    )
    if dialect.name == "sqlite":
        connection.execute(text("BEGIN IMMEDIATE"))
    else:
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(724619302)"))


def now():
    return datetime.now(timezone.utc).isoformat()


def today():
    return (
        date.fromisoformat(os.getenv("ASSESSMENT_DATE", "2026-11-16"))
        if os.getenv("DEMO_MODE", "true") == "true"
        else date.today()
    )


def migrate():
    with engine.begin() as c:
        serialize_write(c)
        c.execute(
            text(
                "CREATE TABLE IF NOT EXISTS records (kind VARCHAR(40) NOT NULL, id VARCHAR(100) NOT NULL, dealer VARCHAR(40) NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id))"
            )
        )
        c.execute(
            text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
        )
        c.execute(
            text(
                "INSERT INTO schema_migrations(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version=1)"
            )
        )
        if not c.execute(text("SELECT version FROM schema_migrations WHERE version=2")).scalar():
            c.execute(
                text(
                    "CREATE TABLE records_v2 (kind VARCHAR(40) NOT NULL, id VARCHAR(100) NOT NULL, dealer VARCHAR(40) NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id,dealer))"
                )
            )
            c.execute(text("INSERT INTO records_v2 SELECT kind,id,dealer,payload FROM records"))
            c.execute(text("DROP TABLE records"))
            c.execute(text("ALTER TABLE records_v2 RENAME TO records"))
            c.execute(text("INSERT INTO schema_migrations(version) VALUES (2)"))
        c.execute(
            text(
                "CREATE TABLE IF NOT EXISTS public_tokens (token VARCHAR(100) PRIMARY KEY, dealer VARCHAR(40) NOT NULL, report_id VARCHAR(100) NOT NULL)"
            )
        )
        c.execute(
            text(
                'CREATE TABLE IF NOT EXISTS rate_limits (client VARCHAR(100) NOT NULL, "window" BIGINT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(client,"window"))'
            )
        )
        for row in c.execute(
            text("SELECT id,dealer,payload FROM records WHERE kind='report'")
        ).all():
            payload = json.loads(row[2])
            c.execute(
                text("INSERT INTO public_tokens VALUES (:t,:d,:r) ON CONFLICT(token) DO NOTHING"),
                {"t": payload["token"], "d": row[1], "r": row[0]},
            )
        c.execute(
            text(
                "INSERT INTO schema_migrations(version) SELECT 3 WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version=3)"
            )
        )


def put(s, kind, id, data, dealer="demo"):
    s.execute(
        text(
            "INSERT INTO records(kind,id,dealer,payload) VALUES (:k,:i,:d,:p) ON CONFLICT(kind,id,dealer) DO UPDATE SET payload=excluded.payload"
        ),
        {"k": kind, "i": id, "d": dealer, "p": json.dumps(data)},
    )


def get(s, kind, id, dealer="demo"):
    r = s.execute(
        text("SELECT payload FROM records WHERE kind=:k AND id=:i AND dealer=:d"),
        {"k": kind, "i": id, "d": dealer},
    ).scalar()
    return json.loads(r) if r else None


def all_records(s, kind, dealer="demo"):
    return [
        json.loads(r)
        for r in s.execute(
            text("SELECT payload FROM records WHERE kind=:k AND dealer=:d"),
            {"k": kind, "d": dealer},
        ).scalars()
    ]


def consume_public_request(client_key, window):
    """Atomic database counter, shared by every worker and persisted on 404/410."""
    with engine.begin() as c:
        c.execute(text('DELETE FROM rate_limits WHERE "window" < :w'), {"w": window - 2})
        return c.execute(
            text(
                'INSERT INTO rate_limits(client,"window",count) VALUES (:k,:w,1) ON CONFLICT(client,"window") DO UPDATE SET count=rate_limits.count+1 RETURNING count'
            ),
            {"k": client_key, "w": window},
        ).scalar_one()


def seed():
    with Session(engine) as s:
        serialize_write(s)
        if all_records(s, "vehicle"):
            return
        models = [
            ("Chevrolet", "Bolt EV"),
            ("Ford", "Mustang Mach-E"),
            ("Hyundai", "Ioniq 5"),
            ("Chevrolet", "Bolt EUV"),
        ]
        scenarios = [
            "Stable history",
            "Cold start",
            "Conflicting reading",
            "Pack replacement",
            "Warranty verification",
            "Unknown in-service date",
            "Stale evidence",
            "Battery included in base",
        ]
        for i in range(24):
            make, model = models[i % 4]
            scenario = scenarios[i % 8]
            vid = str(i + 1)
            miles = 28450 + i * 1327
            v = {
                "id": vid,
                "stock": f"EV-{2401 + i}",
                "vin": f"DEMO000000{i + 1:07d}",
                "make": make,
                "model": model,
                "year": 2023 + i % 2,
                "miles": miles,
                "in_service": None if i % 8 == 5 else "2023-04-18",
                "pack": "replacement" if i % 8 == 3 else "original",
                "scenario": scenario,
                "base": 23800 + i * 325,
                "included": "yes" if i % 8 == 7 else "no",
                "revision": 1,
                "provenance": "Demo fixture",
            }
            put(s, "vehicle", vid, v)
            put(
                s,
                "visit",
                vid,
                {"id": vid, "vehicle": vid, "ro": f"RO-{8100 + i}", "state": "Inspection open"},
            )
            if i % 8 != 1:
                for j, days in enumerate([650, 430, 210, 25]):
                    if i % 8 == 6:
                        days += 440
                    value = 95 - j * 1.2 - i % 3
                    if i % 8 == 2 and j == 3:
                        value = 99
                    rid = f"{vid}-{j}"
                    pack = "original" if i % 8 != 3 or j < 2 else "replacement"
                    if i % 8 == 3 and j >= 2:
                        value = 99 - (j - 2)
                    put(
                        s,
                        "reading",
                        rid,
                        {
                            "id": rid,
                            "vehicle": vid,
                            "pack": pack,
                            "date": str(today() - timedelta(days=days)),
                            "value": value,
                            "raw_value": value,
                            "miles": miles - (3 - j) * 6500 - 300,
                            "original_odometer": miles - (3 - j) * 6500 - 300,
                            "unit": "mi",
                            "source": "OEM diagnostic tool",
                            "basis": "usable capacity",
                            "measurement": "health",
                            "state": "confirmed",
                            "actor": "Demo technician",
                            "provenance": "Demo fixture",
                            "created_at": now(),
                        },
                    )
            if i % 8 == 3:
                put(
                    s,
                    "event",
                    vid,
                    {
                        "id": vid,
                        "vehicle": vid,
                        "date": str(today() - timedelta(days=230)),
                        "type": "Pack replacement",
                        "notes": "Synthetic installation record. Replacement warranty basis pending verification.",
                    },
                )
        s.commit()


def seed_warranty_examples():
    """Additive demo examples; existing vehicle IDs are never overwritten."""
    if os.getenv("DEMO_MODE", "true") != "true":
        return
    with Session(engine) as s:
        serialize_write(s)
        for id, known in [("warranty-25", True), ("warranty-26", False)]:
            if get(s, "vehicle", id):
                continue
            v = {
                "id": id,
                "stock": "EV-2425" if known else "EV-2426",
                "vin": "DEMO00000000242" + ("5" if known else "6"),
                "make": "Ford",
                "model": "Mustang Mach-E",
                "year": 2023,
                "miles": 99500 if known else 38000,
                "pack": "original",
                "in_service": "2023-04-18" if known else None,
                "market": "US",
                "sale_state": "IL",
                "transfer_verified": known,
                "warranty_start_verified": known,
                "warranty_evidence": "Synthetic demo delivery record and ownership eligibility, reviewed for this example.",
                "scenario": "Warranty near mileage limit" if known else "Warranty inputs missing",
                "base": 25000,
                "included": "no",
                "revision": 1,
                "provenance": "Demo fixture",
            }
            put(s, "vehicle", id, v)
            put(
                s,
                "visit",
                id,
                {"id": id, "vehicle": id, "ro": "RO-DEMO-" + id, "state": "Inspection open"},
            )
            for j, days in enumerate([650, 430, 210, 25]):
                rid = id + "-" + str(j)
                miles = v["miles"] - (3 - j) * 6000 - 300
                put(
                    s,
                    "reading",
                    rid,
                    {
                        "id": rid,
                        "vehicle": id,
                        "pack": "original",
                        "date": str(today() - timedelta(days=days)),
                        "value": 95 - j,
                        "raw_value": 95 - j,
                        "miles": miles,
                        "original_odometer": miles,
                        "unit": "mi",
                        "source": "OEM diagnostic tool",
                        "basis": "usable capacity",
                        "measurement": "health",
                        "state": "confirmed",
                        "actor": "Demo technician",
                        "provenance": "Demo fixture",
                        "created_at": now(),
                    },
                )
        s.commit()


def seed_metadata():
    from .contracts import PackSegment, SourceRecord, DealerRecord

    with Session(engine) as s:
        serialize_write(s)
        if not get(s, "dealer", "demo"):
            put(s, "dealer", "demo", DealerRecord(id="demo", name="Northline Motors").model_dump())
        for v in all_records(s, "vehicle"):
            rs = [r for r in all_records(s, "reading") if r["vehicle"] == v["id"]]
            for pack in {r["pack"] for r in rs} | {v["pack"]}:
                key = v["id"] + ":" + pack
                if get(s, "pack", key):
                    continue
                events = [
                    e
                    for e in all_records(s, "event")
                    if e["vehicle"] == v["id"] and e["type"] == "Pack replacement"
                ]
                segment = PackSegment(
                    id=key,
                    vehicle=v["id"],
                    identifier=pack,
                    start_date=events[0]["date"]
                    if pack == "replacement" and events
                    else v.get("in_service")
                    if pack == "original"
                    else None,
                    preceding_segment="original" if pack == "replacement" else None,
                    replacement_evidence=events[0]["id"]
                    if pack == "replacement" and events
                    else None,
                    verification="demo fixture",
                )
                put(s, "pack", key, segment.model_dump())
            for r in rs:
                if not get(s, "source", r["id"]):
                    source = SourceRecord(
                        id=r["id"],
                        vehicle=v["id"],
                        title="Battery capacity reading",
                        provider=r["source"],
                        provenance="demo fixture"
                        if r["provenance"] == "Demo fixture"
                        else "dealer entered",
                        retrieved_at=r.get("created_at"),
                        attachment=r.get("attachment"),
                    )
                    put(s, "source", r["id"], source.model_dump())
        s.commit()

"""Validated persisted aggregates; identifiers remain dealer-scoped in storage."""

from typing import Literal
from pydantic import BaseModel, Field


class PackSegment(BaseModel):
    id: str
    vehicle: str
    identifier: str
    start_date: str | None = None
    start_odometer: float | None = None
    preceding_segment: str | None = None
    replacement_evidence: str | None = None
    verification: Literal["demo fixture", "dealer confirmed", "pending"] = "pending"


class SourceRecord(BaseModel):
    id: str
    vehicle: str | None = None
    title: str
    provider: str
    provenance: Literal["demo fixture", "dealer entered", "live", "cached", "curated"]
    retrieved_at: str | None = None
    url: str | None = None
    attachment: str | None = None
    locator: str | None = None


class DealerRecord(BaseModel):
    id: str
    name: str
    timezone: str = "America/Chicago"
    units: str = "mi"
    currency: str = "USD"


class PublicReading(BaseModel):
    date: str
    value: float = Field(ge=0, le=100)
    source: str
    miles: float


class PublicReport(BaseModel):
    title: str
    subtitle: str
    vehicle: str
    vin: str
    miles: float
    interval: list[int] | None
    last: dict | None
    quality: str
    reason: str
    warnings: list[str]
    readings: list[PublicReading]
    pack: str
    pack_context: dict | None = None
    warranty: str
    coverage: dict | None = None
    dealer: str
    as_of: str
    expires_on: str | None = None
    generated_at: str
    limitations: str
    version: int
    status: str
    integrity: str

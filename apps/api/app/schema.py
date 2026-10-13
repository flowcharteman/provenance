from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class CompanySummary(BaseModel):
    id: str
    name: str | None = None
    ticker: str | None = None
    cik: str | None = None
    sector: str | None = None
    industry: str | None = None


class FactRecord(BaseModel):
    metric: str
    value: float | int | None = None
    currency: str | None = None
    period: str | None = None
    period_type: str | None = None
    source: str | None = None


class CompanyDetail(BaseModel):
    id: str
    name: str | None = None
    ticker: str | None = None
    cik: str | None = None
    sector: str | None = None
    industry: str | None = None
    facts: list[FactRecord] = []
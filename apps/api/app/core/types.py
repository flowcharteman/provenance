"""Small set of types shared across application boundaries."""

from __future__ import annotations

from enum import Enum
from typing import NewType
from uuid import UUID

CompanyId = NewType("CompanyId", UUID)
SourceSystemId = NewType("SourceSystemId", UUID)
SourceObservationId = NewType("SourceObservationId", UUID)
NormalizationRunId = NewType("NormalizationRunId", UUID)
FinancialFactId = NewType("FinancialFactId", UUID)
ValuationRunId = NewType("ValuationRunId", UUID)


class IdentifierType(str, Enum):
    TICKER = "TICKER"
    ISIN = "ISIN"
    CIK = "CIK"
    LEI = "LEI"
    REGISTRY_ID = "REGISTRY_ID"
    SEDAR_ID = "SEDAR_ID"
    OTHER = "OTHER"


class FactDataType(str, Enum):
    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    ASSUMPTION = "ASSUMPTION"
    ESTIMATE = "ESTIMATE"

"""Provider-neutral values exchanged at source and normalization boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Mapping, Union
from uuid import UUID

from app.core.types import FactDataType

JsonScalar = Union[str, int, float, bool, None]
JsonValue = Union[JsonScalar, List["JsonValue"], Dict[str, "JsonValue"]]


class SourceCapability(str, Enum):
    COMPANY_SEARCH = "COMPANY_SEARCH"
    IDENTIFIER_LOOKUP = "IDENTIFIER_LOOKUP"
    FILINGS = "FILINGS"
    FINANCIAL_FACTS = "FINANCIAL_FACTS"
    MARKET_DATA = "MARKET_DATA"
    MACRO_DATA = "MACRO_DATA"
    DOCUMENTS = "DOCUMENTS"


class ObservationKind(str, Enum):
    COMPANY_CANDIDATE = "COMPANY_CANDIDATE"
    IDENTIFIER_MATCH = "IDENTIFIER_MATCH"
    FILING = "FILING"
    FINANCIAL = "FINANCIAL"
    MARKET = "MARKET"
    MACRO = "MACRO"
    DOCUMENT = "DOCUMENT"


@dataclass(frozen=True)
class SourceMetadata:
    """Non-secret provider identity and operational metadata."""

    key: str
    name: str
    category: str
    base_url: str | None = None
    documentation_url: str | None = None
    license_terms_url: str | None = None
    supported_capabilities: frozenset[SourceCapability] = field(
        default_factory=frozenset
    )
    public_metadata: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class Provenance:
    """Trace back to a provider record/document and a specific retrieval."""

    source_system_key: str
    retrieved_at: datetime
    retrieval_batch_id: UUID
    source_record_id: str | None = None
    source_record_hash: str | None = None
    source_document_reference: str | None = None
    published_at: datetime | None = None
    effective_at: datetime | None = None
    filing_reference: str | None = None

    def __post_init__(self) -> None:
        timestamps = (
            self.retrieved_at,
            self.published_at,
            self.effective_at,
        )
        if any(value is not None and value.utcoffset() is None for value in timestamps):
            raise ValueError("provenance timestamps must be timezone-aware")


@dataclass(frozen=True)
class SourceObservation:
    """Provider-originated observation; payload shape remains source-specific."""

    kind: ObservationKind
    provenance: Provenance
    provider_payload: Mapping[str, JsonValue]
    subject_reference: str | None = None


@dataclass(frozen=True)
class PersistedSourceObservation:
    """Observation plus its database identity, assigned by ingestion."""

    id: UUID
    observation: SourceObservation


@dataclass(frozen=True)
class CompanyCandidate:
    provider_reference: str
    display_name: str
    provenance: Provenance
    legal_name: str | None = None
    jurisdiction: str | None = None
    identifiers: tuple[tuple[str, str], ...] = ()
    source_observations: tuple[SourceObservation, ...] = ()


@dataclass(frozen=True)
class FilingReference:
    provider_reference: str
    filing_type: str
    provenance: Provenance
    period_start: date | None = None
    period_end: date | None = None
    source_observation: SourceObservation | None = None


@dataclass(frozen=True)
class ObservationQuery:
    """Minimal common query envelope; provider-specific filters stay local."""

    subject_reference: str
    since: datetime | None = None
    until: datetime | None = None
    filters: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedFactCandidate:
    """Canonical candidate emitted by a normalizer, not a provider parser."""

    metric_key: str
    value: Decimal
    unit_code: str
    data_type: FactDataType
    source_observation_ids: tuple[UUID, ...]
    normalization_version: str
    company_id: UUID
    period_type: str
    currency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    effective_at: datetime | None = None
    published_at: datetime | None = None
    confidence: Decimal | None = None
    context: Mapping[str, JsonValue] = field(default_factory=dict)

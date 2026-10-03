"""Structural adapter contracts split by independently supported capability."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.adapters.types import (
    CompanyCandidate,
    FilingReference,
    ObservationQuery,
    SourceMetadata,
    SourceObservation,
)


@runtime_checkable
class SourceAdapter(Protocol):
    @property
    def metadata(self) -> SourceMetadata: ...

    async def aclose(self) -> None: ...


@runtime_checkable
class CompanySearchAdapter(SourceAdapter, Protocol):
    async def search_companies(
        self, query: str
    ) -> Sequence[CompanyCandidate]: ...


@runtime_checkable
class IdentifierAdapter(SourceAdapter, Protocol):
    async def lookup_identifier(
        self, identifier_type: str, identifier_value: str
    ) -> Sequence[CompanyCandidate]: ...


@runtime_checkable
class FilingAdapter(SourceAdapter, Protocol):
    async def list_filings(
        self,
        subject_reference: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Sequence[FilingReference]: ...


@runtime_checkable
class FinancialFactsAdapter(SourceAdapter, Protocol):
    async def fetch_financial_observations(
        self, query: ObservationQuery
    ) -> Sequence[SourceObservation]: ...


@runtime_checkable
class MarketDataAdapter(SourceAdapter, Protocol):
    async def fetch_market_observations(
        self, query: ObservationQuery
    ) -> Sequence[SourceObservation]: ...


@runtime_checkable
class MacroDataAdapter(SourceAdapter, Protocol):
    async def fetch_macro_observations(
        self, query: ObservationQuery
    ) -> Sequence[SourceObservation]: ...


@runtime_checkable
class DocumentAdapter(SourceAdapter, Protocol):
    async def fetch_document_observations(
        self, query: ObservationQuery
    ) -> Sequence[SourceObservation]: ...

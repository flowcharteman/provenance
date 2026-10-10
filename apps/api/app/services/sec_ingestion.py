"""Company-to-facts SEC ingestion orchestration."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, Mapping, Sequence, TypeVar
from uuid import UUID

from app.adapters.contracts import (
    CompanySearchAdapter,
    FinancialFactsAdapter,
    FilingAdapter,
    IdentifierAdapter,
)
from app.adapters.errors import AdapterError
from app.adapters.sec.catalog import sec_tags_for_ingestion
from app.adapters.sec.normalizer import (
    SecFactNormalizer,
    unsupported_fact_reasons,
)
from app.adapters.types import (
    CompanyCandidate,
    ObservationKind,
    ObservationQuery,
    SourceMetadata,
)
from app.db.sec_repository import CompanyResolutionError, SecPostgresRepository

_T = TypeVar("_T")


class SecIngestionExecutor:
    """Shared request pacing/retry layer, outside source adapters."""

    def __init__(
        self,
        *,
        requests_per_second: float,
        max_retries: int,
        initial_backoff_seconds: float,
        max_backoff_seconds: float,
    ) -> None:
        self._minimum_interval = 1.0 / requests_per_second
        self._max_retries = max_retries
        self._initial_backoff = initial_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def request(
        self,
        operation: Callable[..., Awaitable[_T]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        attempt = 0
        while True:
            await self._wait_for_request_slot()
            try:
                return await operation(*args, **kwargs)
            except AdapterError as error:
                if not error.retryable or attempt >= self._max_retries:
                    raise
                backoff = min(
                    self._max_backoff,
                    self._initial_backoff * (2**attempt),
                )
                delay = (
                    error.retry_after_seconds
                    if error.retry_after_seconds is not None
                    else backoff
                )
                await asyncio.sleep(delay)
                attempt += 1

    async def _wait_for_request_slot(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            if delay:
                await asyncio.sleep(delay)
            self._next_request_at = time.monotonic() + self._minimum_interval


@dataclass(frozen=True)
class SecIngestionReport:
    company_id: UUID
    cik: str
    company_name: str
    created_identifiers: int
    created_identity_observations: int
    created_filings: int
    created_filing_observations: int
    created_financial_observations: int
    duplicate_financial_observations: int
    normalization_run_id: UUID | None
    created_financial_facts: int
    unsupported_counts: Mapping[str, int]


class SecIngestionService:
    def __init__(
        self,
        *,
        company_search: CompanySearchAdapter,
        identifier_lookup: IdentifierAdapter,
        filings: FilingAdapter,
        financial_facts: FinancialFactsAdapter,
        repository: SecPostgresRepository,
        executor: SecIngestionExecutor,
        normalizer: SecFactNormalizer | None = None,
        metadata: SourceMetadata,
    ) -> None:
        self._company_search = company_search
        self._identifier_lookup = identifier_lookup
        self._filings = filings
        self._financial_facts = financial_facts
        self._repository = repository
        self._executor = executor
        self._normalizer = normalizer or SecFactNormalizer()
        self._metadata = metadata

    async def ingest(
        self,
        *,
        name: str | None = None,
        ticker: str | None = None,
        cik: str | None = None,
    ) -> SecIngestionReport:
        identity_candidates = await self._find_identity_candidates(
            name=name,
            ticker=ticker,
            cik=cik,
        )
        if not identity_candidates:
            raise CompanyResolutionError("No SEC company matched the supplied identity.")
        if len(identity_candidates) > 1:
            await self._repository.persist_unresolved_candidates(
                identity_candidates, self._metadata
            )
            raise CompanyResolutionError(
                "SEC company resolution is ambiguous. Refine the name/ticker or provide a CIK.",
                identity_candidates,
            )

        company = identity_candidates[0]
        company_id, normalized_cik, identifiers_added, identity_observations_added = (
            await self._repository.persist_company(company, self._metadata)
        )

        filing_references = await self._executor.request(
            self._filings.list_filings,
            normalized_cik,
        )
        filings_added, filing_observations_added = await self._repository.persist_filings(
            company_id,
            filing_references,
            self._metadata,
        )

        metric_tags = sec_tags_for_ingestion()
        financial_observations = await self._executor.request(
            self._financial_facts.fetch_financial_observations,
            ObservationQuery(
                subject_reference=normalized_cik,
                filters={
                    "taxonomies": ["us-gaap"],
                    "tags": metric_tags,
                    "forms": ["10-K", "10-Q", "8-K"],
                },
            ),
        )
        document_observation = next(
            (
                observation
                for observation in financial_observations
                if observation.kind is ObservationKind.DOCUMENT
            ),
            None,
        )
        unsupported = (
            unsupported_fact_reasons(document_observation.provider_payload)
            if document_observation
            else {}
        )
        persisted_observations, duplicates = (
            await self._repository.persist_financial_observations(
                company_id,
                financial_observations,
                self._metadata,
            )
        )
        if not persisted_observations:
            return SecIngestionReport(
                company_id=company_id,
                cik=normalized_cik,
                company_name=company.display_name,
                created_identifiers=identifiers_added,
                created_identity_observations=identity_observations_added,
                created_filings=filings_added,
                created_filing_observations=filing_observations_added,
                created_financial_observations=0,
                duplicate_financial_observations=duplicates,
                normalization_run_id=None,
                created_financial_facts=0,
                unsupported_counts=unsupported,
            )

        candidates = await self._normalizer.normalize(
            persisted_observations,
            company_id=company_id,
        )
        run_id, facts_added = await self._repository.persist_normalization(
            company_id=company_id,
            observations=persisted_observations,
            candidates=candidates,
            unsupported_counts=unsupported,
            normalizer_version=self._normalizer.version,
            metadata=self._metadata,
        )
        return SecIngestionReport(
            company_id=company_id,
            cik=normalized_cik,
            company_name=company.display_name,
            created_identifiers=identifiers_added,
            created_identity_observations=identity_observations_added,
            created_filings=filings_added,
            created_filing_observations=filing_observations_added,
            created_financial_observations=sum(
                observation.observation.kind
                in {ObservationKind.DOCUMENT, ObservationKind.FINANCIAL}
                for observation in persisted_observations
            ),
            duplicate_financial_observations=duplicates,
            normalization_run_id=run_id,
            created_financial_facts=facts_added,
            unsupported_counts=unsupported,
        )

    async def _find_identity_candidates(
        self, *, name: str | None, ticker: str | None, cik: str | None
    ) -> Sequence[CompanyCandidate]:
        candidate_sets = []
        if name:
            candidate_sets.append(
                await self._executor.request(
                    self._company_search.search_companies, name
                )
            )
        if ticker:
            candidate_sets.append(
                await self._executor.request(
                    self._identifier_lookup.lookup_identifier, "TICKER", ticker
                )
            )
        if cik:
            candidate_sets.append(
                await self._executor.request(
                    self._identifier_lookup.lookup_identifier, "CIK", cik
                )
            )
        if not candidate_sets:
            raise ValueError("Provide at least one of company name, ticker, or CIK")

        per_set = [
            {candidate.provider_reference: candidate for candidate in candidates}
            for candidates in candidate_sets
        ]
        common_ciks = set(per_set[0])
        for candidate_set in per_set[1:]:
            common_ciks.intersection_update(candidate_set)
        merged = []
        for key in sorted(common_ciks):
            matches = [candidate_set[key] for candidate_set in per_set]
            identifiers = tuple(
                sorted({item for candidate in matches for item in candidate.identifiers})
            )
            source_observations = tuple(
                {
                    item.provenance.source_record_id: item
                    for candidate in matches
                    for item in candidate.source_observations
                }.values()
            )
            merged.append(
                replace(
                    matches[0],
                    identifiers=identifiers,
                    source_observations=source_observations,
                )
            )
        return tuple(merged)

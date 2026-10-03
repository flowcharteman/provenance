"""SEC EDGAR company, filing, and company-facts capability implementation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from app.adapters.errors import AdapterError, AdapterErrorStatus
from app.adapters.sec.client import SecHttpClient
from app.adapters.sec.parsing import (
    normalize_cik,
    parse_company_tickers,
    parse_companyfacts_observations,
    parse_filings,
    parse_submission_candidate,
)
from app.adapters.types import (
    CompanyCandidate,
    FilingReference,
    ObservationQuery,
    SourceCapability,
    SourceMetadata,
    SourceObservation,
)
from app.config.settings import Settings


COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SecEdgarAdapter:
    """Implements only company search, identifier, filing, and facts access."""

    def __init__(self, settings: Settings, client: SecHttpClient | None = None) -> None:
        self._settings = settings
        self._client = client or SecHttpClient(
            user_agent=settings.sec_user_agent,
            timeout_seconds=settings.sec_request_timeout_seconds,
            cache_dir=settings.sec_http_cache_dir,
        )
        self._metadata = SourceMetadata(
            key="sec-edgar",
            name="SEC EDGAR",
            category="REGULATORY_FILING_DATA",
            base_url="https://www.sec.gov/edgar",
            documentation_url="https://www.sec.gov/edgar/sec-api-documentation",
            license_terms_url="https://www.sec.gov/about/developer-resources",
            supported_capabilities=frozenset(
                {
                    SourceCapability.COMPANY_SEARCH,
                    SourceCapability.IDENTIFIER_LOOKUP,
                    SourceCapability.FILINGS,
                    SourceCapability.FINANCIAL_FACTS,
                }
            ),
            public_metadata={
                "submissions_endpoint": "https://data.sec.gov/submissions/",
                "company_facts_endpoint": "https://data.sec.gov/api/xbrl/companyfacts/",
            },
        )

    @property
    def metadata(self) -> SourceMetadata:
        return self._metadata

    async def aclose(self) -> None:
        return None

    async def search_companies(self, query: str) -> Sequence[CompanyCandidate]:
        if not query.strip():
            raise ValueError("Company search query must not be blank")
        response = await self._client.get_json(COMPANY_TICKERS_URL)
        retrieved_at = datetime.now(timezone.utc)
        candidates = parse_company_tickers(
            response.payload,
            query=query,
            retrieved_at=retrieved_at,
            retrieval_batch_id=uuid4(),
            url=response.url,
        )
        return candidates

    async def lookup_identifier(
        self, identifier_type: str, identifier_value: str
    ) -> Sequence[CompanyCandidate]:
        kind = identifier_type.strip().upper()
        if kind == "TICKER":
            return await self.search_companies(identifier_value)
        if kind != "CIK":
            raise AdapterError(
                AdapterErrorStatus.DATA_UNAVAILABLE,
                f"SEC identifier lookup does not support {identifier_type!r}",
                retryable=False,
                source_system_key=self.metadata.key,
            )
        cik = normalize_cik(identifier_value)
        url = SUBMISSIONS_URL.format(cik=cik)
        response = await self._client.get_json(url)
        candidate = parse_submission_candidate(
            response.payload,
            cik=cik,
            retrieved_at=datetime.now(timezone.utc),
            url=response.url,
            response_hash=hashlib.sha256(response.body).hexdigest(),
        )
        return (candidate,)

    async def list_filings(
        self,
        subject_reference: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Sequence[FilingReference]:
        cik = normalize_cik(subject_reference)
        url = SUBMISSIONS_URL.format(cik=cik)
        response = await self._client.get_json(url)
        return parse_filings(
            response.payload,
            cik=cik,
            retrieved_at=datetime.now(timezone.utc),
            url=response.url,
            since=since,
            until=until,
        )

    async def fetch_financial_observations(
        self, query: ObservationQuery
    ) -> Sequence[SourceObservation]:
        cik = normalize_cik(query.subject_reference)
        url = COMPANY_FACTS_URL.format(cik=cik)
        response = await self._client.get_json(url)
        return parse_companyfacts_observations(
            response.payload,
            cik=cik,
            retrieved_at=datetime.now(timezone.utc),
            url=response.url,
            response_hash=hashlib.sha256(response.body).hexdigest(),
        )

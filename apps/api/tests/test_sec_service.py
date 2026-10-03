import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.types import (
    CompanyCandidate,
    ObservationKind,
    Provenance,
    SourceMetadata,
    SourceObservation,
)
from app.adapters.errors import AdapterError, AdapterErrorStatus
from app.db.sec_repository import CompanyResolutionError
from app.services.sec_ingestion import SecIngestionExecutor, SecIngestionService


class CandidateAdapter:
    def __init__(self, candidates):
        self.candidates = candidates

    async def search_companies(self, query):
        return self.candidates

    async def lookup_identifier(self, identifier_type, identifier_value):
        return self.candidates


class CandidateRepository:
    def __init__(self):
        self.unresolved = []

    async def persist_unresolved_candidates(self, candidates, metadata):
        self.unresolved.extend(candidates)
        return 0


def _candidate(cik, name):
    provenance = Provenance(
        source_system_key="sec-edgar",
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        retrieval_batch_id=uuid4(),
        source_record_id=f"company-ticker:{cik}",
        source_record_hash="0123456789abcdef" * 4,
        source_document_reference="https://www.sec.gov/files/company_tickers.json",
    )
    observation = SourceObservation(
        kind=ObservationKind.COMPANY_CANDIDATE,
        provenance=provenance,
        provider_payload={"ticker": "SHARED", "title": name},
    )
    return CompanyCandidate(
        provider_reference=cik,
        display_name=name,
        legal_name=name,
        provenance=provenance,
        identifiers=(("CIK", cik), ("TICKER", "SHARED")),
        source_observations=(observation,),
    )


class SecServiceResolutionTests(unittest.IsolatedAsyncioTestCase):
    def service(self, candidates):
        adapter = CandidateAdapter(candidates)
        return SecIngestionService(
            company_search=adapter,
            identifier_lookup=adapter,
            filings=adapter,
            financial_facts=adapter,
            repository=CandidateRepository(),
            executor=SecIngestionExecutor(
                requests_per_second=10,
                max_retries=0,
                initial_backoff_seconds=1,
                max_backoff_seconds=1,
            ),
            metadata=SourceMetadata(
                key="sec-edgar",
                name="SEC EDGAR",
                category="REGULATORY_FILING_DATA",
            ),
        )

    async def test_ambiguous_ticker_is_not_guessed(self):
        service = self.service(
            [
                _candidate("0000100001", "First Company"),
                _candidate("0000100002", "Second Company"),
            ]
        )

        with self.assertRaises(CompanyResolutionError) as captured:
            await service.ingest(ticker="SHARED")
        self.assertEqual(len(captured.exception.candidates), 2)
        self.assertEqual(len(service._repository.unresolved), 2)

    async def test_missing_company_is_explicit(self):
        service = self.service([])
        with self.assertRaises(CompanyResolutionError):
            await service.ingest(name="No SEC match")

    async def test_retries_are_orchestrated_outside_adapter(self):
        executor = SecIngestionExecutor(
            requests_per_second=10,
            max_retries=1,
            initial_backoff_seconds=0.01,
            max_backoff_seconds=0.01,
        )
        attempts = 0

        async def operation():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise AdapterError(
                    AdapterErrorStatus.RATE_LIMITED,
                    "Rate limited",
                    retryable=True,
                    retry_after_seconds=0,
                    http_status=429,
                )
            return "success"

        self.assertEqual(await executor.request(operation), "success")
        self.assertEqual(attempts, 2)

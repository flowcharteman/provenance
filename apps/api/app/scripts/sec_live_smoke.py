"""Opt-in live SEC-to-PostgreSQL smoke test; never part of unit discovery."""

from __future__ import annotations

import asyncio
import os

from app.adapters.sec.adapter import SecEdgarAdapter
from app.config.settings import Settings
from app.db.sec_repository import SecPostgresRepository
from app.services.sec_ingestion import SecIngestionExecutor, SecIngestionService


async def run_smoke_test() -> None:
    if os.environ.get("SEC_LIVE_TESTS") != "1":
        raise RuntimeError(
            "Set SEC_LIVE_TESTS=1 explicitly to enable this live SEC smoke test"
        )
    settings = Settings.from_env()
    adapter = SecEdgarAdapter(settings)
    repository = await SecPostgresRepository.connect(settings.database_url)
    executor = SecIngestionExecutor(
        requests_per_second=settings.sec_requests_per_second,
        max_retries=settings.sec_max_retries,
        initial_backoff_seconds=settings.sec_initial_backoff_seconds,
        max_backoff_seconds=settings.sec_max_backoff_seconds,
    )
    service = SecIngestionService(
        company_search=adapter,
        identifier_lookup=adapter,
        filings=adapter,
        financial_facts=adapter,
        repository=repository,
        executor=executor,
        metadata=adapter.metadata,
    )
    try:
        report = await service.ingest(ticker="AAPL")
        persisted_cik = await repository.company_cik(report.company_id)
        pipeline = await repository.verify_pipeline(report.company_id)
        if persisted_cik != report.cik:
            raise AssertionError("Persisted SEC CIK does not match resolved identity")
        if pipeline["sec_cik_count"] != 1:
            raise AssertionError("Expected exactly one persisted SEC CIK identifier")
        if pipeline["filing_count"] < 1:
            raise AssertionError("No SEC filings were persisted")
        if pipeline["fact_count"] < 1:
            raise AssertionError("No normalized SEC financial facts were persisted")
        if pipeline["traceable_fact_count"] != pipeline["fact_count"]:
            raise AssertionError("One or more financial facts lack complete SEC provenance")
        print(
            "SEC live smoke test passed: "
            f"CIK={persisted_cik}, filings={pipeline['filing_count']}, "
            f"observations={pipeline['observation_count']}, "
            f"traceable_facts={pipeline['traceable_fact_count']}"
        )
    finally:
        await adapter.aclose()
        await repository.close()


def main() -> None:
    asyncio.run(run_smoke_test())


if __name__ == "__main__":
    main()

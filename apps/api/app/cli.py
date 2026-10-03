"""Command-line entry point for the SEC company-to-facts ingestion flow."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.adapters.errors import AdapterError
from app.adapters.sec.adapter import SecEdgarAdapter
from app.config.settings import Settings
from app.db.sec_repository import CompanyResolutionError, SecPostgresRepository
from app.services.sec_ingestion import SecIngestionExecutor, SecIngestionService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve a US public company and ingest SEC filings/XBRL facts."
    )
    parser.add_argument("--name", help="SEC company name to search")
    parser.add_argument("--ticker", help="SEC company ticker to resolve")
    parser.add_argument("--cik", help="SEC Central Index Key")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if not any((args.name, args.ticker, args.cik)):
        raise ValueError("Provide at least one of --name, --ticker, or --cik")
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
        report = await service.ingest(
            name=args.name,
            ticker=args.ticker,
            cik=args.cik,
        )
        print(f"Company: {report.company_name} (CIK {report.cik})")
        print(f"Company ID: {report.company_id}")
        print(f"New identifiers: {report.created_identifiers}")
        print(f"New filings: {report.created_filings}")
        print(
            "New source observations: "
            f"{report.created_identity_observations + report.created_filing_observations + report.created_financial_observations}"
        )
        print(f"Duplicate financial observations skipped: {report.duplicate_financial_observations}")
        print(f"New normalized financial facts: {report.created_financial_facts}")
        print(f"Normalization run: {report.normalization_run_id or 'not needed (no new observations)'}")
        if report.unsupported_counts:
            print(f"Unmapped/unsupported SEC facts: {dict(report.unsupported_counts)}")
        return 0
    finally:
        await adapter.aclose()
        await repository.close()


def main() -> None:
    args = _parser().parse_args()
    try:
        exit_code = asyncio.run(_run(args))
    except (ValueError, CompanyResolutionError, AdapterError) as error:
        print(f"SEC ingestion failed: {error}", file=sys.stderr)
        if isinstance(error, CompanyResolutionError) and error.candidates:
            print("Candidate CIKs:", file=sys.stderr)
            for candidate in error.candidates[:20]:
                print(
                    f"  {candidate.provider_reference}: {candidate.display_name}",
                    file=sys.stderr,
                )
        raise SystemExit(2) from error
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

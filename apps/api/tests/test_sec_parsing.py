import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.adapters.sec.normalizer import SecFactNormalizer, unsupported_fact_reasons
from app.adapters.sec.parsing import (
    canonical_hash,
    normalize_cik,
    parse_company_tickers,
    parse_companyfacts_observations,
    parse_filings,
    parse_period,
)
from app.adapters.sec.normalizer import is_currency_unit
from app.adapters.types import ObservationKind, PersistedSourceObservation

FIXTURES = Path(__file__).parent / "fixtures" / "sec"


def _load(name):
    with (FIXTURES / name).open(encoding="utf-8") as stream:
        return json.load(stream)


class SecParsingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.retrieved_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_ticker_resolution_preserves_cik_and_source_record(self):
        candidates = parse_company_tickers(
            _load("company_tickers.json"),
            query="AAPL",
            retrieved_at=self.retrieved_at,
            url="https://www.sec.gov/files/company_tickers.json",
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].provider_reference, "0000320193")
        self.assertIn(("CIK", "0000320193"), candidates[0].identifiers)
        self.assertIn(("TICKER", "AAPL"), candidates[0].identifiers)
        self.assertEqual(
            candidates[0].source_observations[0].provider_payload["title"],
            "Apple Inc.",
        )

    def test_same_ticker_for_distinct_ciks_remains_ambiguous(self):
        payload = {
            "0": {"cik_str": 100001, "ticker": "SHARED", "title": "First Public Company"},
            "1": {"cik_str": 100002, "ticker": "SHARED", "title": "Second Public Company"},
        }
        candidates = parse_company_tickers(
            payload,
            query="SHARED",
            retrieved_at=self.retrieved_at,
            url="https://www.sec.gov/files/company_tickers.json",
        )

        self.assertEqual(
            {candidate.provider_reference for candidate in candidates},
            {"0000100001", "0000100002"},
        )

    def test_cik_normalization_rejects_invalid_values(self):
        self.assertEqual(normalize_cik("320193"), "0000320193")
        with self.assertRaises(ValueError):
            normalize_cik("not-a-cik")

    def test_filing_parsing_keeps_form_dates_accession_and_source_record(self):
        references = parse_filings(
            _load("submissions.json"),
            cik="320193",
            retrieved_at=self.retrieved_at,
            url="https://data.sec.gov/submissions/CIK0000320193.json",
        )

        self.assertEqual(len(references), 1)
        filing = references[0]
        self.assertEqual(filing.filing_type, "10-K")
        self.assertEqual(filing.provider_reference, "0000320193-23-000106")
        self.assertEqual(filing.period_end.isoformat(), "2023-09-30")
        self.assertTrue(filing.provenance.filing_reference.endswith("-index.html"))
        self.assertEqual(filing.source_observation.kind, ObservationKind.FILING)
        self.assertEqual(filing.source_observation.provider_payload["filing"]["form"], "10-K")

    async def test_xbrl_fact_normalization_preserves_period_unit_and_lineage(self):
        payload = _load("companyfacts_excerpt.json")
        observations = parse_companyfacts_observations(
            payload,
            cik="320193",
            retrieved_at=self.retrieved_at,
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
        )
        persisted = tuple(
            PersistedSourceObservation(uuid4(), observation)
            for observation in observations
        )
        normalized = await SecFactNormalizer().normalize(
            persisted,
            company_id=uuid4(),
        )

        source_rows = [
            row
            for row in payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
        ]
        revenue = next(item for item in normalized if item.metric_key == "revenue")
        revenue_observation = next(
            item for item in persisted
            if item.id in revenue.source_observation_ids
            and item.observation.kind is ObservationKind.FINANCIAL
        )
        self.assertEqual(revenue.value, Decimal(str(source_rows[0]["val"])))
        self.assertEqual(revenue.currency, "USD")
        self.assertEqual(revenue.unit_code, "USD")
        self.assertEqual(revenue.period_type, "ANNUAL")
        self.assertEqual(revenue.period_start.isoformat(), source_rows[0]["start"])
        self.assertEqual(revenue.period_end.isoformat(), source_rows[0]["end"])
        self.assertEqual(revenue.context["taxonomy"], "us-gaap")
        self.assertEqual(
            revenue.context["tag"],
            "RevenueFromContractWithCustomerExcludingAssessedTax",
        )
        self.assertIn(
            revenue_observation.id,
            revenue.source_observation_ids,
        )
        self.assertTrue(
            any(
                item.observation.kind is ObservationKind.DOCUMENT
                and item.id in revenue.source_observation_ids
                for item in persisted
            )
        )

        assets = next(item for item in normalized if item.metric_key == "total_assets")
        self.assertEqual(assets.period_type, "INSTANT")
        self.assertIsNone(assets.period_start)
        self.assertEqual(assets.period_end.isoformat(), "2023-09-30")

    def test_unsupported_ytd_and_currency_units_are_not_guessed(self):
        ytd_context = {
            "form": "10-Q",
            "start": "2023-01-01",
            "end": "2023-06-30",
        }
        period_type, _, _, reason = parse_period(ytd_context)
        self.assertEqual(period_type, "UNSUPPORTED")
        self.assertEqual(reason, "unsupported_duration_or_form")
        self.assertTrue(is_currency_unit("USD"))
        self.assertFalse(is_currency_unit("shares"))

    def test_source_document_keeps_original_payload_and_hash(self):
        payload = _load("companyfacts_excerpt.json")
        observations = parse_companyfacts_observations(
            payload,
            cik="320193",
            retrieved_at=self.retrieved_at,
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
            response_hash=canonical_hash(payload),
        )

        document = observations[0]
        self.assertEqual(document.kind, ObservationKind.DOCUMENT)
        self.assertEqual(document.provider_payload, payload)
        self.assertEqual(
            document.provenance.source_record_hash,
            canonical_hash(payload),
        )
        self.assertGreater(len(observations), 1)

    def test_unknown_tags_are_reported_without_discarding_source_document(self):
        payload = _load("companyfacts_excerpt.json")
        payload["facts"]["custom-taxonomy"] = {
            "UnmappedConcept": {
                "label": "Unmapped concept",
                "units": {"USD": [{"form": "10-K", "end": "2023-09-30"}]},
            }
        }
        reasons = unsupported_fact_reasons(payload)
        self.assertEqual(reasons["unmapped_tag"], 1)

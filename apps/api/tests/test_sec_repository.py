import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.types import ObservationKind, Provenance, SourceObservation
from app.db.sec_repository import SecPostgresRepository


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    async def fetchone(self):
        return self.row


class FakeReadCursor:
    def __init__(self, rows=()):
        self.rows = list(rows)

    async def fetchone(self):
        return self.rows[0] if self.rows else None

    async def fetchall(self):
        return self.rows


class FakeReadConnection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.executed = []

    async def execute(self, statement, parameters):
        self.executed.append((statement, parameters))
        return FakeReadCursor(self.rows)


class FakeObservationConnection:
    def __init__(self):
        self.records = {}

    async def execute(self, statement, parameters):
        if statement.lstrip().startswith("SELECT id FROM source_observations"):
            source_id, record_id, record_hash, company_id, filing_id = parameters
            key = (source_id, record_id, record_hash, company_id, filing_id)
            existing = self.records.get(key)
            return FakeCursor({"id": existing} if existing else None)
        if statement.lstrip().startswith("INSERT INTO source_observations"):
            source_id, company_id, filing_id = parameters[0:3]
            record_id, record_hash = parameters[5:7]
            key = (source_id, record_id, record_hash, company_id, filing_id)
            observation_id = uuid4()
            self.records[key] = observation_id
            return FakeCursor({"id": observation_id})
        return FakeCursor()


class SecRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_identical_source_record_is_deduplicated(self):
        connection = FakeObservationConnection()
        repository = SecPostgresRepository(connection)
        source_id = uuid4()
        company_id = uuid4()
        observation = SourceObservation(
            kind=ObservationKind.FINANCIAL,
            provenance=Provenance(
                source_system_key="sec-edgar",
                retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                retrieval_batch_id=uuid4(),
                source_record_id="xbrl:fixture:record",
                source_record_hash="0123456789abcdef" * 4,
                source_document_reference=(
                    "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
                ),
            ),
            provider_payload={"taxonomy": "us-gaap", "tag": "Assets"},
            subject_reference="0000320193",
        )

        first_id, first_inserted = await repository._persist_observation(
            observation,
            source_id=source_id,
            company_id=company_id,
            filing_id=None,
        )
        second_id, second_inserted = await repository._persist_observation(
            observation,
            source_id=source_id,
            company_id=company_id,
            filing_id=None,
        )

        self.assertTrue(first_inserted)
        self.assertFalse(second_inserted)
        self.assertEqual(first_id, second_id)

    async def test_find_company_by_ticker_uses_sec_company_identifiers(self):
        company = {
            "id": uuid4(),
            "name": "Apple Inc.",
            "display_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "cik": "0000320193",
            "ticker": "AAPL",
        }
        connection = FakeReadConnection([company])
        repository = SecPostgresRepository(connection)

        result = await repository.find_company_by_ticker(" aapl ")

        self.assertEqual(result, company)
        statement, parameters = connection.executed[0]
        self.assertEqual(parameters, ("AAPL",))
        self.assertIn("sec_cik.namespace = 'SEC'", statement)
        self.assertIn("ticker_identifier.identifier_type = 'TICKER'", statement)
        self.assertTrue(statement.lstrip().startswith("SELECT"))

    async def test_get_company_returns_details_or_none(self):
        company_id = uuid4()
        company = {
            "id": company_id,
            "name": "Apple Inc.",
            "display_name": "Apple Inc.",
            "legal_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "cik": "0000320193",
            "ticker": "AAPL",
        }
        connection = FakeReadConnection([company])
        repository = SecPostgresRepository(connection)

        result = await repository.get_company(str(company_id))

        self.assertEqual(result, company)
        statement, parameters = connection.executed[0]
        self.assertEqual(parameters, (company_id,))
        self.assertIn("left(identifier.namespace, 8) = 'SEC:CIK:'", statement)
        self.assertTrue(statement.lstrip().startswith("SELECT"))

        missing_connection = FakeReadConnection()
        missing_repository = SecPostgresRepository(missing_connection)
        self.assertIsNone(await missing_repository.get_company(company_id))

    async def test_get_financial_facts_returns_latest_annual_facts_with_provenance(self):
        company_id = uuid4()
        facts = [
            {
                "metric_key": "revenue",
                "value": 391035000000,
                "unit": "USD",
                "fiscal_year": 2025,
                "accession_number": "0000320193-25-000079",
                "period_end": "2025-09-27",
            }
        ]
        connection = FakeReadConnection(facts)
        repository = SecPostgresRepository(connection)

        result = await repository.get_financial_facts(str(company_id))

        self.assertEqual(result, tuple(facts))
        statement, parameters = connection.executed[0]
        self.assertEqual(parameters, (company_id,))
        self.assertIn("fact.context->>'fiscal_period' = 'FY'", statement)
        self.assertIn("fact.context->>'fiscal_year'", statement)
        self.assertIn("fact.context->>'accession_number'", statement)
        self.assertIn("fact.version_number DESC", statement)
        self.assertIn("accession_number,\n                    period_end", statement)
        self.assertTrue(statement.lstrip().startswith("WITH"))

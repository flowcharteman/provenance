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

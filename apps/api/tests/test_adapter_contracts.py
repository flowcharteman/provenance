import unittest

from app.adapters.contracts import CompanySearchAdapter, SourceAdapter
from app.adapters.errors import AdapterError, AdapterErrorStatus
from app.adapters.normalization import ObservationNormalizer


class AdapterContractTests(unittest.TestCase):
    def test_capability_can_be_implemented_without_unrelated_methods(self) -> None:
        self.assertIn("metadata", SourceAdapter.__dict__)
        self.assertIn("aclose", SourceAdapter.__dict__)
        self.assertIn("search_companies", CompanySearchAdapter.__dict__)
        self.assertNotIn("list_filings", CompanySearchAdapter.__dict__)
        self.assertNotIn("fetch_macro_observations", CompanySearchAdapter.__dict__)
        self.assertIn("normalize", ObservationNormalizer.__dict__)

    def test_adapter_error_exposes_retry_metadata(self) -> None:
        error = AdapterError(
            AdapterErrorStatus.RATE_LIMITED,
            "Provider asked the caller to retry later.",
            retryable=True,
            retry_after_seconds=30,
            source_system_key="test-source",
        )

        self.assertEqual(error.status, AdapterErrorStatus.RATE_LIMITED)
        self.assertTrue(error.retryable)
        self.assertEqual(error.retry_after_seconds, 30)

    def test_retry_after_requires_retryable_error(self) -> None:
        with self.assertRaises(ValueError):
            AdapterError(
                AdapterErrorStatus.PERMANENT_FAILURE,
                "Permanent failure.",
                retryable=False,
                retry_after_seconds=1,
            )

    def test_provenance_requires_timezone_aware_retrieval_time(self) -> None:
        from datetime import datetime
        from uuid import uuid4

        from app.adapters.types import Provenance

        with self.assertRaises(ValueError):
            Provenance(
                source_system_key="contract-test",
                retrieved_at=datetime(2026, 1, 1),
                retrieval_batch_id=uuid4(),
            )


if __name__ == "__main__":
    unittest.main()

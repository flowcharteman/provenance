import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from app.adapters.contracts import (
    CompanySearchAdapter,
    FinancialFactsAdapter,
    FilingAdapter,
    IdentifierAdapter,
    MacroDataAdapter,
    MarketDataAdapter,
)
from app.adapters.errors import AdapterError, AdapterErrorStatus
from app.adapters.sec.adapter import SecEdgarAdapter
from app.adapters.sec.client import SecHttpClient, SecHttpResponse
from app.adapters.types import ObservationQuery
from app.config.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures" / "sec"


def _load(name):
    with (FIXTURES / name).open(encoding="utf-8") as stream:
        return json.load(stream)


class FakeSecClient:
    def __init__(self):
        self.urls = []

    async def get_json(self, url):
        self.urls.append(url)
        if "company_tickers" in url:
            payload = _load("company_tickers.json")
        elif "submissions" in url:
            payload = _load("submissions.json")
        else:
            payload = _load("companyfacts_excerpt.json")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return SecHttpResponse(
            url=url,
            status=200,
            headers={"Content-Type": "application/json"},
            body=body,
            payload=payload,
        )


class FakeHTTPResponse:
    status = 200

    def __init__(self, body, headers):
        self._body = body
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self._body


class SecAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings(
            database_url="postgresql://local/test",
            sec_user_agent_name="Test project",
            sec_contact_email="test@example.invalid",
        )
        self.client = FakeSecClient()
        self.adapter = SecEdgarAdapter(self.settings, client=self.client)

    async def test_adapter_implements_only_supported_capabilities(self):
        self.assertIsInstance(self.adapter, CompanySearchAdapter)
        self.assertIsInstance(self.adapter, IdentifierAdapter)
        self.assertIsInstance(self.adapter, FilingAdapter)
        self.assertIsInstance(self.adapter, FinancialFactsAdapter)
        self.assertNotIsInstance(self.adapter, MarketDataAdapter)
        self.assertNotIsInstance(self.adapter, MacroDataAdapter)

    async def test_search_and_identifier_lookup_use_official_sources(self):
        by_ticker = await self.adapter.search_companies("AAPL")
        by_cik = await self.adapter.lookup_identifier("CIK", "320193")

        self.assertEqual(by_ticker[0].provider_reference, "0000320193")
        self.assertEqual(by_cik[0].provider_reference, "0000320193")
        self.assertIn("www.sec.gov/files/company_tickers.json", self.client.urls[0])
        self.assertIn("data.sec.gov/submissions/CIK0000320193.json", self.client.urls[1])

    async def test_filings_and_companyfacts_are_exposed_as_observations(self):
        filings = await self.adapter.list_filings("0000320193")
        observations = await self.adapter.fetch_financial_observations(
            query=ObservationQuery(subject_reference="0000320193")
        )

        self.assertEqual(filings[0].filing_type, "10-K")
        self.assertEqual(filings[0].source_observation.kind.value, "FILING")
        self.assertEqual(observations[0].kind.value, "DOCUMENT")
        self.assertTrue(any(item.kind.value == "FINANCIAL" for item in observations))
        self.assertIn("data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json", self.client.urls[-1])

    def test_http_429_maps_to_retryable_rate_limit_error(self):
        http_error = HTTPError(
            "https://data.sec.gov/submissions/CIK0000320193.json",
            429,
            "Too Many Requests",
            {"Retry-After": "30"},
            BytesIO(b""),
        )
        client = SecHttpClient("Configured Test Name test@example.invalid")
        with patch("app.adapters.sec.client.urlopen", side_effect=http_error):
            with self.assertRaises(AdapterError) as captured:
                client._get_json(
                    "https://data.sec.gov/submissions/CIK0000320193.json"
                )
        self.assertEqual(captured.exception.status, AdapterErrorStatus.RATE_LIMITED)
        self.assertTrue(captured.exception.retryable)
        self.assertEqual(captured.exception.retry_after_seconds, 30)
        self.assertEqual(captured.exception.http_status, 429)

    def test_conditional_cache_reuses_payload_after_sec_not_modified(self):
        url = "https://data.sec.gov/submissions/CIK0000320193.json"
        body = b'{"cik":"320193","name":"Apple Inc."}'
        with tempfile.TemporaryDirectory() as cache_dir:
            client = SecHttpClient(
                "Configured Test Name test@example.invalid",
                cache_dir=cache_dir,
            )
            initial_response = FakeHTTPResponse(
                body,
                {"ETag": '"sec-version-1"', "Content-Type": "application/json"},
            )
            with patch(
                "app.adapters.sec.client.urlopen",
                return_value=initial_response,
            ):
                first = client._get_json(url)

            not_modified = HTTPError(url, 304, "Not Modified", {"ETag": '"sec-version-1"'}, BytesIO(b""))
            with patch(
                "app.adapters.sec.client.urlopen",
                side_effect=not_modified,
            ) as mocked_open:
                second = client._get_json(url)

            request = mocked_open.call_args.args[0]
            self.assertEqual(request.get_header("If-none-match"), '"sec-version-1"')
            self.assertEqual(second.status, 304)
            self.assertEqual(second.payload, first.payload)
            self.assertEqual(second.body, body)

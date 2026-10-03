# SEC EDGAR ingestion

## Scope

The Phase 2 SEC integration implements company/ticker search, CIK lookup, recent
filing ingestion, and selected US-GAAP facts from SEC Company Facts. It writes
to the approved Phase 1 PostgreSQL schema. It does not implement valuation
models, an API server, a frontend, external sources other than SEC, arbitrary
filing HTML scraping, or authenticated/paid datasets.

## Official SEC resources

Only official SEC hosts are requested:

- Ticker/name mapping: `https://www.sec.gov/files/company_tickers.json`
- Company submissions and recent filing metadata:
  `https://data.sec.gov/submissions/CIK##########.json`
- Standard taxonomy XBRL company facts:
  `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
- Filing archive index references:
  `https://www.sec.gov/Archives/edgar/data/{cik}/{accession-without-dashes}/{accession}-index.html`

SEC documentation and fair-access information:

- <https://www.sec.gov/edgar/sec-api-documentation>
- <https://www.sec.gov/about/developer-resources>

The HTTP client validates HTTPS and an official SEC hostname. It does not send
credentials, scrape third-party sites, or retry requests itself.

## User-Agent and configuration

Before SEC requests, configure `SEC_USER_AGENT_NAME` and `SEC_CONTACT_EMAIL` in
the local, ignored `.env` file. The request header is built only from those
values (`name email`); the project supplies no invented product identity or
contact address. Missing/invalid contact configuration prevents client
creation. No SEC API key or paid subscription is required.

The PostgreSQL URL can be configured as `DATABASE_URL`, or is assembled from
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and
`POSTGRES_DB`. The example environment contains empty secret/contact fields.
Official SEC GET responses with `ETag` or `Last-Modified` are cached in the
configured `SEC_HTTP_CACHE_DIR` (default:
`~/.cache/investment-analysis/sec-edgar`) and revalidated conditionally. Cache
files retain the SEC response body and are not committed to the repository.

`SEC_REQUESTS_PER_SECOND` defaults to 8 and cannot exceed 10. Retry attempts,
exponential backoff, `Retry-After`, and per-process request pacing are owned by
`SecIngestionExecutor`, outside the adapter. Adapters emit standardized
`AdapterError` values with status, HTTP status where applicable, retryability,
source key, and optional retry-after seconds. Each adapter operation performs
one request attempt.

## Company resolution

1. Name/ticker lookup reads the SEC ticker-to-CIK JSON mapping.
2. Exact ticker matches take precedence; otherwise names are matched
   case-insensitively as substrings.
3. Multiple ticker rows for one CIK are grouped; different CIKs remain distinct
   candidates. Multiple input selectors must all resolve to the same CIK.
4. A direct CIK request reads the matching SEC submissions resource.
5. No result or multiple CIK candidates is an explicit error; the system does
   not guess. Candidate observations are retained when resolution is ambiguous.
6. Persistence looks up the SEC CIK identifier before creating a company.
   CIKs are normalized to ten digits. Tickers are stored as SEC identifiers in
   a CIK-scoped namespace, not assumed globally unique.

## Filing ingestion

The submissions resource's `filings.recent` arrays are parsed for 10-K, 10-Q,
and 8-K entries. Filing accession, form, filing date, report date, primary
document, official archive index reference, source system, company, and
retrieval timestamp are persisted. Each filing-list item is also stored as an
immutable source observation tied to its filing.

Existing accessions are not overwritten. This implementation reads the SEC
`recent` submissions block; it does not yet follow historical
`filings.files` references beyond that block or download filing documents.

## XBRL normalization

Company Facts is fetched from the official SEC XBRL endpoint. The full parsed
response is retained as a document source observation; selected fact records
are separately retained as source observations for row-level lineage.

The initial canonical map is deliberately small and covers selected US-GAAP
consolidated metrics: revenue, operating income, net income, total assets, total
liabilities, stockholders' equity, and cash and cash equivalents. Mappings are
recorded in `source_metric_mappings`; taxonomy, tag, source label/description,
form, accession, fiscal year/period, frame, and original unit are kept in
observation/context data. Unsupported concepts remain in the retained Company
Facts document and are counted in the normalization run report; no heuristic
tag matching is used.

Period rules:

- Facts without `start` are instant facts and keep their `end` date.
- 10-K/8-K duration facts of 300–400 days are annual.
- 10-Q/8-K duration facts of 70–110 days are quarterly.
- Other duration/form combinations, including YTD periods, are retained but
  not normalized. No subtraction to derive quarters is performed.
- Fiscal year, fiscal period, frame, form, and accession remain in fact context.

SEC units are preserved exactly. Three-letter currency units are retained as
currency codes; no currency conversion, scaling, or unit reinterpretation is
performed. Unsupported units are reported and not normalized.

## Provenance and duplicate handling

The persisted flow is:

```text
SEC response/document
  -> source_observations (document snapshot and relevant original records)
  -> normalization_runs + normalization_run_observations
  -> financial_facts + fact_source_observations
```

Each new fact links to both its SEC fact-record observation and the full
Company Facts document observation. The latter can support many facts. The
original accession can additionally connect an observation to a persisted
filing. SEC responses are hashed from raw HTTP bytes when available; extracted
records use deterministic canonical-JSON SHA-256 hashes. Identical records are
deduplicated; changed records remain distinct and produce new fact versions
instead of changing prior facts.

## Testing

Offline tests use selected excerpts from official SEC response structures in
`apps/api/tests/fixtures/sec`. The financial values in the Company Facts
excerpt are SEC-reported FY2023 Apple facts and are read from the fixture, not
embedded as asserted constants. Unit tests do not make live network requests.

From `apps/api`:

```sh
python -m unittest discover -s tests -v
```

An explicit end-to-end live smoke command uses ticker AAPL, the configured
PostgreSQL database, and real SEC endpoints:

```sh
SEC_LIVE_TESTS=1 python -m app.scripts.sec_live_smoke
```

This command is not part of unittest discovery. It writes SEC observations and
facts to the configured database and checks the persisted CIK, filings, facts,
and fact-to-observation provenance.

## Known limitations

- Company search is based on the SEC ticker/CIK mapping and does not resolve
  every legal entity or non-US issuer.
- Only SEC `filings.recent` is processed; older submissions file lists are not
  followed yet.
- Company Facts contains standard taxonomies; custom taxonomy statements,
  segment-specific facts, and facts requiring detailed XBRL context selection
  are not mapped by this initial adapter.
- The curated concept map is not a complete statement-normalization taxonomy.
  Alternative tags can yield separate canonical series and require review
  before being compared.
- Unmapped counts are summarized; raw data remains in the source observation,
  but no review UI is included.
- Request pacing is per process. A multi-process deployment must coordinate
  SEC request limits across workers before scaling ingestion horizontally.
- The live smoke test was not run during implementation unless explicitly
  enabled by the operator; it requires local PostgreSQL and a real configured
  SEC User-Agent contact.

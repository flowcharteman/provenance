# Project status and evidence dossier

**Prepared:** 2026-10-06  
**Status:** Phase 1 approved. Phase 2 is **not approved**.  
**Purpose:** Consolidate the architecture, implemented foundation, SEC code audit,
database evidence, SEC response-capture metadata, and outstanding verification
work collected so far.

This report distinguishes repository facts, database/live-request evidence, and
code-level claims. It does not reproduce `.env`, credentials, the SEC User-Agent,
raw SEC payloads, or raw response-header values. No SEC XBRL semantic analysis
is included: that is a later, explicitly gated task.

## Executive summary

- Phase 1 delivered a monorepo foundation, PostgreSQL schema, provenance/version
  model, capability-based source contracts, local PostgreSQL/Redis Compose
  services, and offline tests. The project owner confirmed Phase 1 was locally
  approved and verified.
- Phase 2 code for SEC EDGAR exists in the repository but is untrusted and has
  not been approved. It provides a real pipeline shape, but the audit found
  important correctness, auditability, and verification gaps.
- Python was recreated at the requested project `.venv` using Python 3.12.10.
  The prior Python 3.9 environment was retained at
  `/Users/eman9iine/Documents/venv-py39-backup`; its package freeze is at
  `/Users/eman9iine/Documents/venv-py39-freeze.txt`. The full offline suite
  passed on Python 3.12.10: 23 tests.
- The approved Phase 1 migration was applied successfully to a separate
  `phase2_audit` database running on PostgreSQL 16.15. It contains 21 public
  tables, created from the migration, and no test rows were inserted. A
  provenance join query executed successfully and returned zero rows.
- Seven official SEC HTTP requests have been captured as byte-preserved
  response-body files in the ignored `.scratch/sec-captures/` directory.
  All returned direct HTTP 200 responses, and all saved-file hashes match the
  capture manifest.
- SEC policy pages could not be fetched by the tool because they returned 403.
  The user supplied policy text retrieved directly from SEC pages. Its
  documented ceiling is 10 requests/second; the capture requests were spaced at
  no more than one per second. No SEC XBRL analysis, further capture request,
  or PostgreSQL ingestion has been performed.

## 1. Project objective and approved architecture

The intended product is a financial-analysis platform for public companies.
The eventual product vision includes financial analysis, comparable-company
analysis, precedent transactions, DCF, LBO, SOTP, M&A, accretion/dilution, and
macroeconomic analysis. These are roadmap objectives, not all implemented
features.

### Technology direction

| Area | Approved/intended technology |
|---|---|
| Future web client | Next.js, React, TypeScript |
| Future API | Python, FastAPI |
| Database | PostgreSQL |
| Local infrastructure | Docker Compose; Phase 1 Compose scope is PostgreSQL and Redis only |
| Future background jobs | Redis plus Celery or equivalent, not implemented here |
| Python database driver | psycopg 3 |

The API package is currently a Python package and CLI, not a running FastAPI
service. The web application is not implemented. Financial calculations must
remain separate from database and API logic; no valuation calculations exist
in the SEC ingestion scope.

### Architectural boundaries

```text
Future Next.js UI
       |
       v
Future FastAPI API
       |
       +---------------------------+
       |                           |
       v                           v
Financial models               Data ingestion
(not implemented)                  |
                                   +-- provider adapters
                                   +-- source-specific parsers
                                   +-- canonical normalizers
                                   +-- PostgreSQL repositories
```

Provider-specific payloads remain provider-specific in adapters and parsers.
Canonical data models and normalization do not belong in provider/database
code. Secrets come from environment configuration. No credentials should be
hard-coded. Fake provider responses or financial data are prohibited.

### Capability-based adapter model

```text
SourceAdapter
├── CompanySearchAdapter
├── IdentifierAdapter
├── FilingAdapter
├── FinancialFactsAdapter
├── MarketDataAdapter
├── MacroDataAdapter
└── DocumentAdapter
```

A provider implements only the capabilities it actually offers. Retry,
backoff, and rate-limit orchestration belongs to the ingestion/execution layer.
Adapters report standardized error status, retryability, HTTP status where
available, and optional `retry_after_seconds`.

## 2. Phase 1 repository and schema foundation

### Provenance and versioning model

The approved provenance path is:

```text
External source
  -> source_observations
  -> normalization_runs
  -> financial_facts
  -> future models
```

`normalization_run_observations` records the input observations for a
normalization run. `fact_source_observations` creates a many-to-many relationship
between canonical facts and supporting observations; a fact can have multiple
supporting observations and an observation can support multiple facts. The
schema also includes `precedent_transaction_source_observations` for
many-to-many transaction provenance.

The source observation retains provider payload JSON or a payload-storage
reference, source record identifier and hash, source system, optional company
and filing, retrieval batch, retrieval timestamp, publication/effective/
observation timestamps, and source document reference. Raw JSONB is not the
same thing as exact original HTTP bytes.

### Core table inventory

The migration creates 21 public tables:

```text
companies
company_identifiers
securities
source_systems
filings
source_observations
normalization_runs
normalization_run_observations
metric_definitions
source_metric_mappings
financial_facts
fact_source_observations
market_data
market_data_source_observations
valuation_runs
model_assumptions
valuation_outputs
precedent_transactions
precedent_transaction_source_observations
user_assumptions
audit_log
```

Key relationships:

- `companies` → `company_identifiers`; `companies` → `securities`.
- `source_systems` → `filings` → `source_observations`.
- `source_observations` → `normalization_run_observations` →
  `normalization_runs`.
- `metric_definitions` → `financial_facts`.
- `financial_facts` → `fact_source_observations` →
  `source_observations`.
- `companies` → `valuation_runs` → `model_assumptions` and
  `valuation_outputs`.
- `precedent_transactions` ↔ `source_observations` via
  `precedent_transaction_source_observations`.
- `market_data` refers to a security, a canonical metric definition, a
  normalization run, and source observations.

### Database constraints and immutability

The migration includes primary/foreign keys, unique constraints and indexes,
appropriate non-null constraints, checks for non-empty values and valid
ranges/statuses, and `created_at`/`updated_at` timestamps. Selected records and
lineage tables are append-only. Financial facts have a `series_key`,
`version_number`, and `supersedes_fact_id`, with a uniqueness constraint over
company, canonical metric, series, and version. Trigger guards enforce
successive fact versions and prevent modifications to persisted facts.

Metric definitions are versioned by `(metric_key, definition_version)`.
Source-metric mappings are unique per `(source_system_id, source_metric_code,
source_context_key)`.

## 3. SEC implementation currently present

The following files provide the current SEC-only implementation:

| File | Role |
|---|---|
| `apps/api/app/adapters/sec/client.py` | HTTPS JSON transport restricted to official SEC hosts; response/error handling and conditional local cache |
| `apps/api/app/adapters/sec/adapter.py` | SEC company search, CIK lookup, recent filings, and Company Facts adapter methods |
| `apps/api/app/adapters/sec/parsing.py` | Provider-specific parsing, provenance records, accession/period extraction, deterministic record hashes |
| `apps/api/app/adapters/sec/catalog.py` | Curated US-GAAP tag-to-canonical-metric catalog |
| `apps/api/app/adapters/sec/normalizer.py` | Limited canonical fact mapping and period/unit eligibility rules |
| `apps/api/app/services/sec_ingestion.py` | Company resolution, request pacing/retries, and the company-to-facts pipeline |
| `apps/api/app/db/sec_repository.py` | PostgreSQL writes for identity, filings, observations, mappings, normalization runs, facts, provenance, and audit log |
| `apps/api/app/cli.py` | CLI entry point for name/ticker/CIK ingestion |
| `apps/api/app/scripts/sec_live_smoke.py` | Explicitly opted-in SEC-to-PostgreSQL smoke command; not run in this audit |
| `apps/api/app/config/settings.py` | Environment-only database and SEC request configuration |

The adapter advertises company search, identifier lookup, filings, and
financial-facts capabilities. It does not implement document download, market
data, or macro data. The current implementation supports a small set of US-GAAP
metrics, rather than a complete financial-statement mapping.

### Current code path

```text
CLI
 -> SEC ingestion service
 -> execution executor (pacing/retries)
 -> SEC capability adapter
 -> official SEC HTTP client
 -> source-specific parser
 -> canonical fact normalizer
 -> PostgreSQL repository
 -> normalization run + fact/observation provenance
```

The adapter/client does one HTTP attempt per operation; retry and pacing are
implemented in the execution layer. The service combines multiple selectors by
intersecting CIK results and errors on ambiguous/no match. The repository
persists identity, filing metadata, source observations, metrics/mappings,
normalization runs, financial facts, provenance links, and audit entries.

### Configured behavior and known limits from code/documentation

- Search uses the SEC ticker/name mapping: exact ticker first; otherwise
  case-insensitive name substring matching.
- CIK values are normalized to ten digits.
- Implemented filing forms are exactly `10-K`, `10-Q`, and `8-K`, from the
  recent submissions arrays only. Older `filings.files` entries and filing
  document content are not ingested by this code.
- The catalog includes revenue, operating income, net income, total assets,
  total liabilities, total stockholders' equity, and cash and cash equivalents.
- Instant facts are recognized when `start` is absent. Duration classification
  is limited to annual (300–400 days for 10-K/8-K) and quarterly (70–110 days
  for 10-Q/8-K). Other durations, including year-to-date periods, are not
  normalized. No derived quarter subtraction is performed.
- Currency/unit conversion is not performed.
- A full parsed Company Facts document observation and selected fact-row
  observations are created. Individual fact-row observations are emitted for
  tags in the current catalog; unmapped tags remain within the full document
  payload and are counted.
- The client cache stores bodies and ETag/Last-Modified validators locally when
  available. The normal ingestion code can return cached bodies on 304.
- Rate pacing is process-local, so different processes do not share a global
  limiter.

These are descriptions of code/configuration, not proof of correct behavior on
real SEC payloads or with PostgreSQL. The audit findings below qualify them.

## 4. Environment and offline test evidence

### Python environments

The earlier workspace environment was Python 3.9.6. At the user's direction:

- Its `pip freeze` was saved outside the repository at
  `/Users/eman9iine/Documents/venv-py39-freeze.txt`.
- The old virtual environment was moved intact to
  `/Users/eman9iine/Documents/venv-py39-backup`; it was not deleted.
- The project `.venv` was created using the exact Python
  `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`.
- The configured workspace interpreter now points to
  `/Users/eman9iine/Documents/CodeProjects/.venv/bin/python`.

The Python 3.12.10 environment installed only the API manifest dependency
`psycopg[binary]>=3.2,<4` (and its dependency `typing_extensions`). The
resolved versions were `psycopg==3.3.6`, `psycopg-binary==3.3.6`, and
`typing_extensions==4.16.0`. The saved 3.9 freeze had psycopg and
psycopg-binary at 3.2.13 and the same typing_extensions version. Pytest is not
declared in the API manifest and was absent; the project README names unittest
as the offline runner.

### Test command and result

Executed from `apps/api` using the new interpreter:

```sh
/Users/eman9iine/Documents/CodeProjects/.venv/bin/python \
  -m unittest discover -s tests -v
```

Result: **23 tests passed** in 0.122 seconds. Coverage is the current offline
test suite only; this does not validate SEC live behavior or real PostgreSQL
repository transactions.

Tests exercise adapter capability shape, basic company parsing and ambiguity,
CIK normalization, filing parsing, a selected Company Facts fixture, simple
normalization, unsupported period behavior, error/retry metadata, cache
revalidation, one fake repository deduplication path, and settings validation.

## 5. PostgreSQL migration evidence

### Isolated audit database

PostgreSQL Compose service was healthy at `127.0.0.1:5432`. The reported server
version was PostgreSQL 16.15 on Alpine Linux, aarch64. A separate database
named `phase2_audit` was created and the approved migration
`db/migrations/001_init_core_schema.sql` was applied to it. The migration
completed with `COMMIT`, exit code 0, and no warnings or errors.

The migration created 21 public tables, 15 public functions, and 45
non-internal triggers. No new extension was created; `plpgsql` 1.0 is present.
The `phase2_audit` schema contained no data rows when the provenance query was
run.

The main database `investment_analysis` was checked read-only: it reported 21
public tables. Database creation and migration commands targeted only
`phase2_audit`; no write statement was run against `investment_analysis`.

### Observation uniqueness and content hash

The migration's observation uniqueness is:

```sql
CREATE UNIQUE INDEX uq_source_observations_record_per_retrieval
    ON source_observations (source_system_id, source_record_id, retrieved_at)
    WHERE source_record_id IS NOT NULL;
```

The hash has a SHA-256 shape check, not a uniqueness constraint:

```sql
CONSTRAINT source_observations_hash_sha256
    CHECK (source_record_hash ~ '^[0-9a-f]{64}$'),
```

There is no unique constraint over
`(source_system_id, source_record_id, source_record_hash)`.

### Fact version fields

```sql
series_key TEXT NOT NULL,
version_number INTEGER NOT NULL,
supersedes_fact_id UUID,
```

The unique key is:

```sql
UNIQUE (company_id, metric_definition_id, series_key, version_number)
```

### Provenance join smoke query

A query joining facts, companies, normalization runs, fact/source link rows,
run-input rows, source observations, source systems, and optional filings was
run against the empty `phase2_audit` schema with the placeholder UUID
`00000000-0000-0000-0000-000000000000`. It executed without error and returned
zero rows. No rows were inserted.

This verifies that the join is syntactically compatible with the migrated
schema. It does not verify a real populated provenance chain or repository
transactions.

## 6. SEC policy and capture procedure

The direct fetch attempts for official documentation URLs returned HTTP 403:

- `https://www.sec.gov/os/accessing-edgar-data`
- `https://www.sec.gov/edgar/sec-api-documentation`
- `https://www.sec.gov/about/developer-resources`

The project owner supplied text they retrieved from SEC itself. The supplied
sources were:

- `https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm`
- `https://www.sec.gov/edgar/sec-api-documentation`

The supplied SEC text says the current maximum is 10 requests per second,
requests must declare a User-Agent header, and describes the submissions and
Company Facts endpoints. The user's operational limit for the capture exercise
was stricter: at most one request per second, no retries, and immediate stop on
non-200 responses, redirects, 403, 429, or 5xx. That one-per-second limit was
followed.

No SEC request was attempted until the owner approved the exact plan. The
first Python TLS attempt failed locally with certificate verification error
before an HTTP response; it saved no response and was not retried in that
attempt. A later, separately authorized attempt used system curl with redirects
and retries disabled and succeeded.

### Captured resources

The captured directory is
`/Users/eman9iine/Documents/CodeProjects/.scratch/sec-captures/`. `.scratch/`
is ignored by the repository's `.gitignore`. Capture files are ignored
artifacts; they are not source fixtures and have not been committed.

All seven responses were direct HTTP 200, with no redirects. The SEC contact
and User-Agent name were searched for in the scratch directory; both were
reported not found. The manifest contains response metadata and no request
headers or User-Agent.

| Filename | Resource | UTC capture time | Status | Bytes | SHA-256 |
|---|---|---:|---:|---:|---|
| `company_tickers.json` | ticker-to-CIK mapping | 2026-10-03 16:55:42.407162 | 200 | 799,085 | `31a807ba3f3c0b3340008aba9c3b487734d5b2d8dd5751c2a1b3667696cfa315` |
| `apple_submissions.json` | Apple submissions, CIK `0000320193` | 2026-10-03 17:02:26.846566 | 200 | 163,997 | `2159349dae17cc9148a2f2a9d2eab12c84f59c2135b62e78d56ac9b00ca86b1e` |
| `jpm_submissions.json` | JPM submissions, CIK `0000019617` | 2026-10-03 17:02:28.090933 | 200 | 4,646,256 | `65f6ac19237ad09a607d7077a90bedce77f55af444ad55290dd231981e117b8c` |
| `jpm_submissions_001.json` | JPM additional submissions 001 | 2026-10-03 18:05:06.810115 | 200 | 388,706 | `967849419526ae81d5d87693b9f706a9abec02bb3aae77a15daf160836eb0510` |
| `jpm_submissions_002.json` | JPM additional submissions 002 | 2026-10-03 18:05:07.915368 | 200 | 383,680 | `bb02e155bc67a19fee028f00bbf848e54f25c7884874856cfe68c58ac85025ba` |
| `apple_companyfacts.json` | Apple Company Facts | 2026-10-03 18:05:09.020557 | 200 | 3,789,099 | `73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43` |
| `jpm_companyfacts.json` | JPM Company Facts | 2026-10-03 18:05:10.125713 | 200 | 7,973,442 | `1ba256b88d172b809505576b43254a8039039ecf9004eb1b528ddeaadf488913` |

For the four requests in the final approved batch (JPM historical files and
Apple/JPM Company Facts), the manifest recorded no `Content-Encoding` and no
`Content-Length`. The saved byte rule was consistent: curl wrote response-body
entity bytes, without HTTP transfer framing and without content decoding
(`--compressed` was not used). Each saved file's SHA-256 was recomputed and
matched the manifest. The byte hashes therefore identify the saved file bytes
under that rule; they are not a claim to include HTTP transfer framing or TLS
records.

The captured ticker mapping had top-level JSON object type and 10,440 entries;
its observed record fields were `cik_str`, `ticker`, and `title`. It contained
one row for each of AAPL and JPM:

```json
{"cik_str":320193,"ticker":"AAPL","title":"Apple Inc."}
{"cik_str":19617,"ticker":"JPM","title":"JPMORGAN CHASE & CO"}
```

The padded submissions identifiers were derived from those exact captured
records. There were no duplicate ticker matches for either.

### Additional submissions files discovered

Apple's submissions response listed one older file. It has not been fetched:

| File name | Filing range | URL |
|---|---|---|
| `CIK0000320193-submissions-001.json` | 1994-01-26 – 2015-09-07 | `https://data.sec.gov/submissions/CIK0000320193-submissions-001.json` |

JPM's first submissions response listed 70 historical files. Files 001 and
002 were fetched under an explicitly approved four-request batch. The other 68
were not fetched.

| File suffix | Filing range |
|---:|---|
| 001 | 2025-09-02 – 2025-10-01 |
| 002 | 2025-07-30 – 2025-08-31 |
| 003 | 2025-06-24 – 2025-07-28 |
| 004 | 2025-05-13 – 2025-06-22 |
| 005 | 2025-04-04 – 2025-05-11 |
| 006 | 2025-03-04 – 2025-04-02 |
| 007 | 2025-01-29 – 2025-03-02 |
| 008 | 2024-12-17 – 2025-01-27 |
| 009 | 2024-11-13 – 2024-12-15 |
| 010 | 2024-10-08 – 2024-11-11 |
| 011 | 2024-09-03 – 2024-10-06 |
| 012 | 2024-07-30 – 2024-09-01 |
| 013 | 2024-06-25 – 2024-07-28 |
| 014 | 2024-05-20 – 2024-06-23 |
| 015 | 2024-04-11 – 2024-05-18 |
| 016 | 2024-03-04 – 2024-04-09 |
| 017 | 2024-01-25 – 2024-03-02 |
| 018 | 2023-12-13 – 2024-01-23 |
| 019 | 2023-11-02 – 2023-12-11 |
| 020 | 2023-09-29 – 2023-10-31 |
| 021 | 2023-08-24 – 2023-09-27 |
| 022 | 2023-07-18 – 2023-08-22 |
| 023 | 2023-06-02 – 2023-07-16 |
| 024 | 2023-04-24 – 2023-05-31 |
| 025 | 2023-03-10 – 2023-04-22 |
| 026 | 2023-02-02 – 2023-03-08 |
| 027 | 2022-12-13 – 2023-01-31 |
| 028 | 2022-10-25 – 2022-12-11 |
| 029 | 2022-09-19 – 2022-10-23 |
| 030 | 2022-08-09 – 2022-09-17 |
| 031 | 2022-07-01 – 2022-08-07 |
| 032 | 2022-05-17 – 2022-06-29 |
| 033 | 2022-04-04 – 2022-05-15 |
| 034 | 2022-02-15 – 2022-04-02 |
| 035 | 2021-12-23 – 2022-02-13 |
| 036 | 2021-10-28 – 2021-12-21 |
| 037 | 2021-09-01 – 2021-10-26 |
| 038 | 2021-06-22 – 2021-08-30 |
| 039 | 2021-04-20 – 2021-06-20 |
| 040 | 2021-02-19 – 2021-04-18 |
| 041 | 2020-12-15 – 2021-02-17 |
| 042 | 2020-09-15 – 2020-12-13 |
| 043 | 2020-06-08 – 2020-09-13 |
| 044 | 2020-03-18 – 2020-06-06 |
| 045 | 2020-01-09 – 2020-03-16 |
| 046 | 2019-10-21 – 2020-01-07 |
| 047 | 2019-07-23 – 2019-10-19 |
| 048 | 2019-03-29 – 2019-07-21 |
| 049 | 2018-12-04 – 2019-03-27 |
| 050 | 2018-07-31 – 2018-12-02 |
| 051 | 2018-03-26 – 2018-07-29 |
| 052 | 2017-11-02 – 2018-03-24 |
| 053 | 2017-06-09 – 2017-10-31 |
| 054 | 2017-01-23 – 2017-06-07 |
| 055 | 2016-08-09 – 2017-01-21 |
| 056 | 2016-01-29 – 2016-08-07 |
| 057 | 2015-08-06 – 2016-01-27 |
| 058 | 2015-02-23 – 2015-08-04 |
| 059 | 2014-08-26 – 2015-02-21 |
| 060 | 2014-01-31 – 2014-08-24 |
| 061 | 2013-06-11 – 2014-01-29 |
| 062 | 2012-10-25 – 2013-06-09 |
| 063 | 2011-12-21 – 2012-10-23 |
| 064 | 2011-01-12 – 2011-12-19 |
| 065 | 2009-10-02 – 2011-01-10 |
| 066 | 2008-06-27 – 2009-09-30 |
| 067 | 2007-09-20 – 2008-06-25 |
| 068 | 2006-08-03 – 2007-09-18 |
| 069 | 2002-02-11 – 2006-08-01 |
| 070 | 1994-01-20 – 2002-02-09 |

### Request accounting

There were seven completed SEC HTTP requests in total:

1. Ticker mapping.
2. Apple submissions.
3. JPM submissions.
4. JPM additional submissions file 001.
5. JPM additional submissions file 002.
6. Apple Company Facts.
7. JPM Company Facts.

The failed local TLS connection attempt did not receive an HTTP response and
did not save a capture. No SEC XBRL content analysis or PostgreSQL ingestion
followed these captures.

## 7. Audit findings retained for remediation planning

The SEC implementation was explicitly designated untrusted. An earlier audit
covered schema fit (D1–D9) and implementation/design fit (E1–E19), and concluded
that Phase 2 was **not ready**. Its retained summary identifies these principal
concerns:

- Raw-response fidelity: storing parsed JSON/JSONB does not by itself preserve
  byte-identical SEC response bodies.
- Filing coverage: implementation handles only recent filing metadata and
  does not yet traverse all historical submissions files or retrieve filing
  documents.
- Filing/fact linkage: fact accessions need reliable matching to persisted
  filings; amendments and restatements need explicit treatment.
- Fact-version authority: version creation must not mistake ingestion order
  for source authority or restatement priority.
- Observation deduplication: concurrent ingestion needs a database-enforced
  identity policy, not only application-level check-then-insert.
- Transaction recovery: pipeline stages can commit partially; failure,
  restart, and idempotency behavior need explicit design and testing.
- Validation depth: offline tests alone do not establish live SEC behavior,
  PostgreSQL repository correctness, concurrency safety, historical traversal,
  or restatement behavior.

The available project handoff records the audit's D1–D9 and E1–E19 labels, but
does not retain the original full finding text/status mapping for every ID.
This dossier therefore does not invent a per-ID mapping. The observations above
are the principal issues preserved in the handoff; they should not be treated
as a replacement for the original audit table.

The later database evidence did establish that the migration's observation
unique index uses source system, source record ID, and retrieval timestamp,
not content hash; the empty-schema provenance join is valid; and no real
populated provenance chain was tested. The later capture evidence established
that seven real SEC response bodies and matching hashes are available outside
tracked files. Neither evidence run changed SEC implementation code or
resolved the other audit concerns.

### Additional schema evidence: observation uniqueness and version columns

The clean migrated database confirmed:

```sql
CREATE UNIQUE INDEX uq_source_observations_record_per_retrieval
    ON source_observations (source_system_id, source_record_id, retrieved_at)
    WHERE source_record_id IS NOT NULL;
```

There is no unique constraint on
`(source_system_id, source_record_id, source_record_hash)`. Financial fact
versioning uses `series_key`, `version_number`, and `supersedes_fact_id`, with
`UNIQUE (company_id, metric_definition_id, series_key, version_number)`.

## 8. Explicitly not established yet

The following have not been done or proven:

- No SEC content/XBRL semantic analysis. In particular, no evidence has yet
  been reported for instant-versus-duration item examples, comparative
  restatements, fiscal-year/fiscal-period label meaning, 3/6/9/12-month
  durations, Q4 derivation, units, custom taxonomies, tag variance, conflicting
  duplicates, or DEI fact semantics.
- No fetch of any of the other 68 JPM historical files or Apple's historical
  submissions file.
- No additional SEC requests after the seven captures.
- No SEC response persisted to PostgreSQL; database remains a schema-only
  evidence target.
- No live SEC-to-PostgreSQL smoke test.
- No reproduction of the company-name merge risk using real SEC identities in
  a throwaway database.
- No test determining whether a full Company Facts response's original-byte
  SHA-256 can be reproduced from a parsed/stored JSONB value.
- No design file `docs/design/phase2-sec-design.md`, all 14 Part E design
  sections, numbered open decisions, or final acceptance checklist.
- No final READY decision for Phase 2. The project owner explicitly stated
  Phase 2 is not approved.
- No remediation, source edits, migrations beyond the approved Phase 1 schema,
  valuation logic, frontend, or non-SEC integrations.

## 9. Recommended order of remaining evidence work

This order is descriptive, not authorization to proceed:

1. Obtain explicit approval for the next exact SEC URL list and request count.
2. If approved, capture additional responses with the same one-request-per-
   second, no-retry, stop-on-non-200 policy and manifest verification.
3. Analyze XBRL semantics only from captured real responses and cite exact
   payload paths/values and accession/date context.
4. Reproduce name-only company merge behavior in a throwaway database without
   touching the main database.
5. Test byte-hash reproducibility against JSONB using a captured Company Facts
   response and an explicitly stated canonicalization procedure.
6. Complete the 14-part SEC design document with open decisions and testable
   acceptance criteria.
7. Only after owner approval, plan and perform narrowly scoped remediation.

## 10. Readiness statement

**Phase 1: approved by the project owner.** The migration was independently
applied to a separate PostgreSQL 16.15 database during the evidence step, and
the Python 3.12.10 offline test run passed.

**Phase 2: NOT READY / NOT APPROVED.** The live captures now supply useful
response-level evidence, and the schema was exercised in an empty clean
database. However, the required XBRL semantics analysis and several specific
reproductions remain outstanding, implementation audit risks remain, and the
formal Part E design/open-decision gate has not been completed or approved.

No provider work beyond the SEC capture batch is authorized by this dossier.

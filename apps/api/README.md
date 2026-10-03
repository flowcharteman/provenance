# Backend foundations

This package contains provider-neutral contracts and an SEC EDGAR ingestion
path for company identity, recent filing metadata, and selected XBRL Company
Facts. SEC HTTP handling, provider parsing, canonical normalization, and
PostgreSQL persistence are separate modules.

The future backend framework is FastAPI. FastAPI, persistence, and provider
HTTP endpoints and frontend functionality remain out of scope. PostgreSQL
persistence uses psycopg against the migration-defined schema.

Configure PostgreSQL and the SEC User-Agent/contact fields in the root `.env`
before running the ingestion command. No paid API credentials are required.
The adapter supports only SEC capabilities and emits immutable observations
and normalized facts with provenance.

Run the offline test suite from this directory with:

```sh
python -m unittest discover -s tests -v
```

Ingest a company by SEC ticker, name, or CIK:

```sh
python -m app.cli --ticker AAPL
python -m app.cli --name "Apple Inc."
python -m app.cli --cik 320193
```

See [`docs/data-sources/sec-edgar.md`](../../docs/data-sources/sec-edgar.md)
for endpoints, provenance, limitations, configuration, and the opt-in live
smoke test. The PostgreSQL DDL under `../../db/migrations` remains the schema
source of truth.

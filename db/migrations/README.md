# PostgreSQL migrations

Migrations are ordered SQL files named `NNN_description.sql`. They are
forward-only and applied once, in order, to a database. The Phase 1 migration
is `001_init_core_schema.sql`.

For local development, start PostgreSQL using the root Docker Compose file, then
apply a migration with `psql` using the local database settings. The migration
does not seed company, financial, market, or provider data.

From the repository root, the default local setup commands are:

```sh
cp .env.example .env
# Set a local-only POSTGRES_PASSWORD value in .env.
docker compose up -d --wait
docker compose exec -T postgres psql -U investment_app -d investment_analysis \
  < db/migrations/001_init_core_schema.sql
docker compose exec postgres psql -U investment_app -d investment_analysis \
  -c '\dt'
```

If the database name or user is changed in `.env`, use those values in the
`psql` commands as well. No provider API credentials are needed.

The SQL file is the Phase 1 schema source of truth. Later migrations should
preserve historical observations, facts, normalization records, and completed
valuation runs.

The normalized financial provenance path is:

```text
source_systems -> source_observations
source_observations -> normalization_run_observations -> normalization_runs
normalization_runs -> financial_facts
financial_facts <-> source_observations via fact_source_observations
```

The many-to-many link permits several observations to support one fact and one
observation to contribute to multiple facts. Database constraints require
matching company/run lineage, retained raw payload or storage reference,
retrieval time, and a SHA-256 observation hash. Normalization runs must finish
before facts can be committed.

Precedent transactions use the
`precedent_transaction_source_observations` many-to-many association to retain
multiple supporting observations without assigning a transaction a single
authoritative source.

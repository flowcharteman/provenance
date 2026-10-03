# Phase 1 architecture and development guardrails

## Scope

Phase 1 establishes the monorepo boundaries, the canonical PostgreSQL schema,
and generic source-adapter contracts. It does not implement an API, frontend,
provider integration, financial calculation, market-data feed, macroeconomic
integration, or document processor.

## Repository boundaries

- `apps/web` is reserved for the future Next.js and TypeScript frontend.
- `apps/api` contains Python backend contracts and configuration only; future
  HTTP endpoints will use FastAPI.
- `db/migrations` is the authoritative PostgreSQL schema history.
- `docs/architecture` contains cross-cutting architecture decisions and
  development guardrails.
- `docker-compose.yml` runs only local PostgreSQL and Redis.

## Dependency direction

- Source adapters own provider-specific request/response parsing.
- Normalization maps source observations to canonical metric definitions.
- Persistence stores observations, normalization runs, normalized facts, and
  their lineage; it does not implement financial calculations.
- Future financial calculations must be independently testable and must not
  depend on API handlers, provider adapters, or database sessions.
- The frontend communicates with the backend only through a future API; it
  must not call source providers directly.

## Data integrity and provenance

- Do not invent or fabricate financial data, provider responses, or missing
  values.
- Keep source observations immutable and retain retrieval timestamps, source
  identity, document/record references, and a content hash or retained payload.
- Every normalized fact is linked to a normalization run and one or more
  source observations. One observation may support multiple facts.
- Ingestion computes and persists a SHA-256 hash when an adapter returns a raw
  payload without a source-provided hash.
- Retain prior fact versions. A later normalization creates a new fact version;
  it does not rewrite the prior fact.
- Manual assumptions are distinct from reported observations.
- Changes to mutable company, identifier, filing, source, and mapping records
  must be accompanied by actor-aware audit events in the same application
  transaction when persistence services are introduced.
- Keep raw provider payload shapes within observations/adapters; canonical
  models must not encode a provider's response structure.

## Secrets and local development

- Never commit `.env`, credentials, API keys, or tokens.
- Read secrets from environment variables or a future secret manager.
- `.env.example` contains variable names and non-secret local configuration
  only. Set a local PostgreSQL password in the ignored `.env` file.
- Phase 1 requires no external API credentials.
- Compose binds PostgreSQL and Redis to localhost and contains no web/API
  containers.

## Schema and migration policy

- Apply schema changes as ordered, forward-only SQL migrations.
- Add foreign keys, constraints, and indexes in the migration that introduces
  the relevant data.
- Do not delete or rewrite historical observations, facts, or completed model
  runs as a means of updating data.
- A valuation execution is a new `valuation_run`. Its assumptions and outputs
  become immutable when the run is completed or failed.

## Source adapter policy

- Implement only the capability interfaces a provider actually supports.
- Keep provider-specific parsing in the concrete adapter, not in canonical
  types or persistence models.
- Return standardized adapter errors, including retryability and optional
  `retry_after_seconds`.
- Central ingestion/execution code owns rate-limit scheduling, retry/backoff,
  and orchestration; adapters do not sleep or implement a retry loop.
- An adapter may omit a raw-content hash; ingestion is responsible for
  computing the retained observation hash before database persistence.

## Testing and change workflow

- Every financial calculation added later requires independent unit tests.
- Source integrations require adapter contract and integration tests using
  permitted, real source behavior; fake payloads must never be presented as
  real data.
- Make small, reviewable changes; run relevant tests and migration checks
  before proceeding to the next roadmap phase.

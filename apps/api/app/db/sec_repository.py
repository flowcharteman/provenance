"""PostgreSQL operations for SEC ingestion, kept separate from parsing."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping, Sequence, Tuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.adapters.sec.catalog import SEC_METRICS, SecMetricSpec
from app.adapters.types import (
    CompanyCandidate,
    FilingReference,
    NormalizedFactCandidate,
    PersistedSourceObservation,
    SourceMetadata,
    SourceObservation,
)


class CompanyResolutionError(ValueError):
    def __init__(self, message: str, candidates: Sequence[CompanyCandidate] = ()) -> None:
        super().__init__(message)
        self.candidates = tuple(candidates)


class SecPostgresRepository:
    def __init__(self, connection: AsyncConnection[Any]) -> None:
        self._connection = connection
        self._source_system_id: UUID | None = None

    @classmethod
    async def connect(cls, database_url: str) -> "SecPostgresRepository":
        connection = await AsyncConnection.connect(
            database_url,
            row_factory=dict_row,
        )
        return cls(connection)

    async def close(self) -> None:
        await self._connection.close()

    async def _source_id(self, metadata: SourceMetadata) -> UUID:
        if self._source_system_id is not None:
            return self._source_system_id
        async with self._connection.transaction():
            row = await (
                await self._connection.execute(
                    """
                    INSERT INTO source_systems
                        (name, source_type, base_url, documentation_url, license_terms_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id, source_type
                    """,
                    (
                        metadata.name,
                        "SEC_EDGAR",
                        metadata.base_url,
                        metadata.documentation_url,
                        metadata.license_terms_url,
                    ),
                )
            ).fetchone()
            if row is None:
                row = await (
                    await self._connection.execute(
                        "SELECT id, source_type FROM source_systems WHERE name = %s",
                        (metadata.name,),
                    )
                ).fetchone()
            if row is None or row["source_type"] != "SEC_EDGAR":
                raise RuntimeError("SEC source system registry entry conflicts with configuration")
            self._source_system_id = row["id"]
        return self._source_system_id

    async def persist_company(
        self,
        candidate: CompanyCandidate,
        metadata: SourceMetadata,
    ) -> Tuple[UUID, str, int, int]:
        cik = _candidate_cik(candidate)
        source_id = await self._source_id(metadata)
        created_observations = 0
        created_identifiers = 0
        async with self._connection.transaction():
            await self._connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"sec-cik:{cik}",),
            )
            existing = await (
                await self._connection.execute(
                    """
                    SELECT company_id FROM company_identifiers
                    WHERE namespace = 'SEC'
                      AND identifier_type = 'CIK'
                      AND normalized_value = %s
                    """,
                    (cik,),
                )
            ).fetchone()
            company_id = existing["company_id"] if existing else None
            if company_id is None:
                name_rows = await (
                    await self._connection.execute(
                        """
                        SELECT id FROM companies
                        WHERE jurisdiction = 'US'
                          AND (
                            lower(display_name) = lower(%s)
                            OR lower(legal_name) = lower(%s)
                          )
                        LIMIT 2
                        """,
                        (candidate.display_name, candidate.legal_name or candidate.display_name),
                    )
                ).fetchall()
                unique_ids = {row["id"] for row in name_rows}
                if len(unique_ids) > 1:
                    raise CompanyResolutionError(
                        "More than one existing company matches the SEC company name; "
                        "refusing to merge without an authoritative CIK match.",
                        (candidate,),
                    )
                if unique_ids:
                    company_id = next(iter(unique_ids))
                else:
                    company_row = await (
                        await self._connection.execute(
                            """
                            INSERT INTO companies
                                (legal_name, display_name, jurisdiction, country_code)
                            VALUES (%s, %s, 'US', 'US')
                            RETURNING id
                            """,
                            (candidate.legal_name or candidate.display_name, candidate.display_name),
                        )
                    ).fetchone()
                    company_id = company_row["id"]
                    await self._audit(
                        "company",
                        company_id,
                        "CREATED_FROM_SEC_IDENTITY",
                        {"cik": cik, "display_name": candidate.display_name},
                    )

            identifiers = []
            for identifier_type, value in candidate.identifiers:
                if identifier_type == "CIK":
                    identifiers.append(("SEC", "CIK", cik, cik, True))
                elif identifier_type == "TICKER":
                    ticker = value.strip().upper()
                    if ticker:
                        identifiers.append(
                            (f"SEC:CIK:{cik}", "TICKER", ticker, ticker, False)
                        )
            if not any(row[1] == "CIK" for row in identifiers):
                identifiers.append(("SEC", "CIK", cik, cik, True))
            for namespace, kind, value, normalized, primary in identifiers:
                row = await (
                    await self._connection.execute(
                        """
                        INSERT INTO company_identifiers (
                            company_id, source_system_id, identifier_type,
                            identifier_value, normalized_value, namespace, is_primary
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (namespace, identifier_type, normalized_value)
                        DO NOTHING
                        RETURNING id
                        """,
                        (
                            company_id,
                            source_id,
                            kind,
                            value,
                            normalized,
                            namespace,
                            primary,
                        ),
                    )
                ).fetchone()
                if row:
                    created_identifiers += 1
                    await self._audit(
                        "company_identifier",
                        row["id"],
                        "CREATED_FROM_SEC",
                        {
                            "company_id": str(company_id),
                            "identifier_type": kind,
                            "namespace": namespace,
                        },
                    )
                else:
                    existing_identifier = await (
                        await self._connection.execute(
                            """
                            SELECT company_id FROM company_identifiers
                            WHERE namespace = %s AND identifier_type = %s
                              AND normalized_value = %s
                            """,
                            (namespace, kind, normalized),
                        )
                    ).fetchone()
                    if existing_identifier["company_id"] != company_id:
                        raise CompanyResolutionError(
                            "SEC identifier is already linked to a different company."
                        )

            for observation in candidate.source_observations:
                _, inserted = await self._persist_observation(
                    observation,
                    source_id=source_id,
                    company_id=company_id,
                    filing_id=None,
                )
                created_observations += int(inserted)
        return company_id, cik, created_identifiers, created_observations

    async def persist_unresolved_candidates(
        self,
        candidates: Sequence[CompanyCandidate],
        metadata: SourceMetadata,
    ) -> int:
        source_id = await self._source_id(metadata)
        inserted_count = 0
        async with self._connection.transaction():
            for candidate in candidates:
                for observation in candidate.source_observations:
                    _, inserted = await self._persist_observation(
                        observation,
                        source_id=source_id,
                        company_id=None,
                        filing_id=None,
                    )
                    inserted_count += int(inserted)
        return inserted_count

    async def persist_filings(
        self,
        company_id: UUID,
        references: Sequence[FilingReference],
        metadata: SourceMetadata,
    ) -> Tuple[int, int]:
        source_id = await self._source_id(metadata)
        inserted_filings = 0
        inserted_observations = 0
        async with self._connection.transaction():
            for reference in references:
                accession = reference.provider_reference
                payload = reference.source_observation.provider_payload if reference.source_observation else {}
                filing_row = payload.get("filing", {})
                filing_date = _parse_date(filing_row.get("filingDate"))
                period_start = _parse_date(filing_row.get("periodStart"))
                period_end = reference.period_end
                document_reference = (
                    reference.provenance.filing_reference
                    or reference.provenance.source_document_reference
                )
                row = await (
                    await self._connection.execute(
                        """
                        INSERT INTO filings (
                            company_id, source_system_id, filing_type, filing_code,
                            accession_number, document_title, document_reference,
                            filing_date, period_start, period_end, published_at, retrieved_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source_system_id, accession_number)
                            WHERE accession_number IS NOT NULL
                        DO NOTHING
                        RETURNING id
                        """,
                        (
                            company_id,
                            source_id,
                            reference.filing_type,
                            accession,
                            accession,
                            filing_row.get("primaryDocument"),
                            document_reference,
                            filing_date,
                            period_start,
                            period_end,
                            reference.provenance.published_at,
                            reference.provenance.retrieved_at,
                        ),
                    )
                ).fetchone()
                if row:
                    filing_id = row["id"]
                    inserted_filings += 1
                    await self._audit(
                        "filing",
                        filing_id,
                        "INGESTED_FROM_SEC",
                        {"accession_number": accession, "form": reference.filing_type},
                    )
                else:
                    existing = await (
                        await self._connection.execute(
                            """
                            SELECT id, company_id, filing_type
                            FROM filings
                            WHERE source_system_id = %s AND accession_number = %s
                            """,
                            (source_id, accession),
                        )
                    ).fetchone()
                    if existing is None or existing["company_id"] != company_id:
                        raise CompanyResolutionError(
                            f"SEC accession {accession} is already linked to another company."
                        )
                    filing_id = existing["id"]
                if reference.source_observation is not None:
                    _, inserted = await self._persist_observation(
                        reference.source_observation,
                        source_id=source_id,
                        company_id=company_id,
                        filing_id=filing_id,
                    )
                    inserted_observations += int(inserted)
        return inserted_filings, inserted_observations

    async def persist_financial_observations(
        self,
        company_id: UUID,
        observations: Sequence[SourceObservation],
        metadata: SourceMetadata,
    ) -> Tuple[Sequence[PersistedSourceObservation], int]:
        source_id = await self._source_id(metadata)
        persisted = []
        duplicate_count = 0
        async with self._connection.transaction():
            for observation in observations:
                accession = _payload_accession(observation.provider_payload)
                filing_id = None
                if accession:
                    filing_row = await (
                        await self._connection.execute(
                            """
                            SELECT id FROM filings
                            WHERE company_id = %s AND source_system_id = %s
                              AND accession_number = %s
                            """,
                            (company_id, source_id, accession),
                        )
                    ).fetchone()
                    if filing_row:
                        filing_id = filing_row["id"]
                observation_id, inserted = await self._persist_observation(
                    observation,
                    source_id=source_id,
                    company_id=company_id,
                    filing_id=filing_id,
                )
                if inserted:
                    persisted.append(PersistedSourceObservation(observation_id, observation))
                else:
                    duplicate_count += 1
        return tuple(persisted), duplicate_count

    async def persist_normalization(
        self,
        company_id: UUID,
        observations: Sequence[PersistedSourceObservation],
        candidates: Sequence[NormalizedFactCandidate],
        unsupported_counts: Mapping[str, int],
        normalizer_version: str,
        metadata: SourceMetadata,
    ) -> Tuple[UUID, int]:
        source_id = await self._source_id(metadata)
        run_id = uuid4()
        configuration = {
            "source_system": metadata.key,
            "normalizer_version": normalizer_version,
            "source_observation_count": len(observations),
            "unsupported_counts": dict(unsupported_counts),
        }
        written_facts = 0
        async with self._connection.transaction():
            await self._connection.execute(
                """
                INSERT INTO normalization_runs
                    (id, normalizer_name, normalization_version, run_status, configuration)
                VALUES (%s, 'sec-companyfacts', %s, 'RUNNING', %s)
                """,
                (run_id, normalizer_version, Jsonb(configuration)),
            )
            for persisted in observations:
                await self._connection.execute(
                    """
                    INSERT INTO normalization_run_observations
                        (normalization_run_id, source_observation_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (run_id, persisted.id),
                )

            for candidate in candidates:
                if candidate.company_id != company_id:
                    raise ValueError("Normalized fact candidate belongs to a different company")
                metric_spec = _metric_spec(candidate.metric_key)
                metric_id = await self._ensure_metric(metric_spec)
                tag = str(candidate.context.get("tag") or "")
                taxonomy = str(candidate.context.get("taxonomy") or "")
                await self._ensure_source_metric_mapping(
                    source_id, f"{taxonomy}:{tag}", taxonomy, metric_id
                )
                series_key = _series_key(candidate, taxonomy, tag)
                await self._connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"fact-series:{company_id}:{series_key}",),
                )
                latest = await (
                    await self._connection.execute(
                        """
                        SELECT id, version_number
                        FROM financial_facts
                        WHERE company_id = %s AND metric_definition_id = %s
                          AND series_key = %s
                        ORDER BY version_number DESC
                        LIMIT 1
                        FOR UPDATE
                        """,
                        (company_id, metric_id, series_key),
                    )
                ).fetchone()
                version = latest["version_number"] + 1 if latest else 1
                supersedes = latest["id"] if latest else None
                fact_row = await (
                    await self._connection.execute(
                        """
                        INSERT INTO financial_facts (
                            company_id, metric_definition_id, normalization_run_id,
                            series_key, version_number, supersedes_fact_id, value,
                            unit_code, currency, period_start, period_end, period_type,
                            effective_at, data_type, confidence, context, notes
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s
                        )
                        RETURNING id
                        """,
                        (
                            company_id,
                            metric_id,
                            run_id,
                            series_key,
                            version,
                            supersedes,
                            candidate.value,
                            candidate.unit_code,
                            candidate.currency,
                            candidate.period_start,
                            candidate.period_end,
                            candidate.period_type,
                            candidate.effective_at,
                            candidate.data_type.value,
                            candidate.confidence,
                            Jsonb(dict(candidate.context)),
                            "Normalized from SEC companyfacts without unit or currency conversion.",
                        ),
                    )
                ).fetchone()
                fact_id = fact_row["id"]
                source_ids = set(candidate.source_observation_ids)
                for persisted in observations:
                    if persisted.id not in source_ids:
                        continue
                    await self._connection.execute(
                        """
                        INSERT INTO fact_source_observations (
                            financial_fact_id, source_observation_id,
                            normalization_run_id, company_id, support_role
                        )
                        VALUES (%s, %s, %s, %s, 'PRIMARY')
                        """,
                        (fact_id, persisted.id, run_id, company_id),
                    )
                if not source_ids:
                    raise ValueError("Normalized financial fact has no source observation")
                if not source_ids.issubset({item.id for item in observations}):
                    raise ValueError("Normalized financial fact references an unpersisted observation")
                written_facts += 1
                await self._audit(
                    "financial_fact",
                    fact_id,
                    "NORMALIZED_FROM_SEC",
                    {
                        "metric_key": candidate.metric_key,
                        "normalization_run_id": str(run_id),
                        "source_observation_ids": [str(value) for value in source_ids],
                        "version_number": version,
                    },
                )

            await self._connection.execute(
                """
                UPDATE normalization_runs
                   SET run_status = 'COMPLETED', completed_at = now()
                 WHERE id = %s
                """,
                (run_id,),
            )
        return run_id, written_facts

    async def verify_pipeline(self, company_id: UUID) -> Mapping[str, int]:
        rows = await (
            await self._connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM company_identifiers
                      WHERE company_id = %s AND namespace = 'SEC'
                        AND identifier_type = 'CIK') AS sec_cik_count,
                    (SELECT count(*) FROM filings WHERE company_id = %s) AS filing_count,
                    (SELECT count(*) FROM source_observations
                      WHERE company_id = %s AND source_system_id = %s) AS observation_count,
                    (SELECT count(*) FROM financial_facts WHERE company_id = %s) AS fact_count,
                    (SELECT count(DISTINCT f.id)
                       FROM financial_facts f
                       JOIN fact_source_observations fso ON fso.financial_fact_id = f.id
                       JOIN source_observations so ON so.id = fso.source_observation_id
                       JOIN normalization_runs nr ON nr.id = fso.normalization_run_id
                      WHERE f.company_id = %s AND so.source_system_id = %s
                        AND nr.run_status = 'COMPLETED') AS traceable_fact_count
                """,
                (
                    company_id,
                    company_id,
                    company_id,
                    self._source_system_id,
                    company_id,
                    company_id,
                    self._source_system_id,
                ),
            )
        ).fetchone()
        return dict(rows)

    async def company_cik(self, company_id: UUID) -> str | None:
        row = await (
            await self._connection.execute(
                """
                SELECT normalized_value
                FROM company_identifiers
                WHERE company_id = %s AND namespace = 'SEC'
                  AND identifier_type = 'CIK'
                """,
                (company_id,),
            )
        ).fetchone()
        return row["normalized_value"] if row else None

    async def _persist_observation(
        self,
        observation: SourceObservation,
        *,
        source_id: UUID,
        company_id: UUID | None,
        filing_id: UUID | None,
    ) -> Tuple[UUID, bool]:
        provenance = observation.provenance
        record_hash = provenance.source_record_hash or _hash_payload(
            observation.provider_payload
        )
        if provenance.source_record_id is not None:
            existing = await (
                await self._connection.execute(
                    """
                    SELECT id FROM source_observations
                    WHERE source_system_id = %s AND source_record_id = %s
                      AND source_record_hash = %s
                      AND company_id IS NOT DISTINCT FROM %s
                      AND filing_id IS NOT DISTINCT FROM %s
                    ORDER BY retrieved_at
                    LIMIT 1
                    """,
                    (
                        source_id,
                        provenance.source_record_id,
                        record_hash,
                        company_id,
                        filing_id,
                    ),
                )
            ).fetchone()
            if existing:
                return existing["id"], False

        row = await (
            await self._connection.execute(
                """
                INSERT INTO source_observations (
                    source_system_id, company_id, filing_id, retrieval_batch_id,
                    observation_kind, source_record_id, source_record_hash,
                    source_document_reference, provider_payload, published_at,
                    effective_at, observed_at, retrieved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    source_id,
                    company_id,
                    filing_id,
                    provenance.retrieval_batch_id,
                    observation.kind.value,
                    provenance.source_record_id,
                    record_hash,
                    provenance.source_document_reference,
                    Jsonb(dict(observation.provider_payload)),
                    provenance.published_at,
                    provenance.effective_at,
                    provenance.effective_at,
                    provenance.retrieved_at,
                ),
            )
        ).fetchone()
        observation_id = row["id"]
        await self._audit(
            "source_observation",
            observation_id,
            "RETRIEVED_FROM_SEC",
            {
                "source_record_id": provenance.source_record_id,
                "source_record_hash": record_hash,
                "observation_kind": observation.kind.value,
                "retrieved_at": provenance.retrieved_at.isoformat(),
            },
        )
        return observation_id, True

    async def _ensure_metric(self, metric: SecMetricSpec) -> UUID:
        row = await (
            await self._connection.execute(
                """
                INSERT INTO metric_definitions (
                    metric_key, definition_version, display_name, metric_group,
                    unit_dimension, currency_requirement, period_requirement,
                    statement_context, accounting_basis, consolidation_scope,
                    definition_context, description
                )
                VALUES (%s, 1, %s, %s, %s, %s, %s, %s, 'US_GAAP',
                        'CONSOLIDATED', %s, %s)
                ON CONFLICT (metric_key, definition_version) DO NOTHING
                RETURNING id
                """,
                (
                    metric.key,
                    metric.display_name,
                    metric.metric_group,
                    metric.unit_dimension,
                    metric.currency_requirement,
                    metric.period_requirement,
                    metric.statement_context,
                    Jsonb({"source_taxonomy": "us-gaap"}),
                    metric.description,
                ),
            )
        ).fetchone()
        if row:
            return row["id"]
        row = await (
            await self._connection.execute(
                """
                SELECT id, display_name, metric_group, unit_dimension,
                       statement_context, description
                FROM metric_definitions
                WHERE metric_key = %s AND definition_version = 1
                """,
                (metric.key,),
            )
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Metric definition {metric.key} could not be registered")
        expected = (
            metric.display_name,
            metric.metric_group,
            metric.unit_dimension,
            metric.statement_context,
            metric.description,
        )
        actual = (
            row["display_name"],
            row["metric_group"],
            row["unit_dimension"],
            row["statement_context"],
            row["description"],
        )
        if actual != expected:
            raise RuntimeError(
                f"Existing canonical metric definition {metric.key} differs from SEC catalog"
            )
        return row["id"]

    async def _ensure_source_metric_mapping(
        self,
        source_id: UUID,
        source_metric_code: str,
        source_context_key: str,
        metric_id: UUID,
    ) -> None:
        row = await (
            await self._connection.execute(
                """
                INSERT INTO source_metric_mappings (
                    source_system_id, metric_definition_id, source_metric_code,
                    source_context_key, mapping_context
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_system_id, source_metric_code, source_context_key)
                DO NOTHING
                RETURNING id
                """,
                (
                    source_id,
                    metric_id,
                    source_metric_code,
                    source_context_key,
                    Jsonb({"provider": "SEC_EDGAR"}),
                ),
            )
        ).fetchone()
        if row is None:
            existing = await (
                await self._connection.execute(
                    """
                    SELECT metric_definition_id
                    FROM source_metric_mappings
                    WHERE source_system_id = %s AND source_metric_code = %s
                      AND source_context_key = %s
                    """,
                    (source_id, source_metric_code, source_context_key),
                )
            ).fetchone()
            if existing is None or existing["metric_definition_id"] != metric_id:
                raise RuntimeError(
                    f"SEC mapping for {source_metric_code} conflicts with canonical metric"
                )

    async def _audit(
        self, entity_type: str, entity_id: UUID, action: str, payload: Mapping[str, Any]
    ) -> None:
        await self._connection.execute(
            """
            INSERT INTO audit_log (entity_type, entity_id, action_type, actor_type, event_payload)
            VALUES (%s, %s, %s, 'SEC_ADAPTER', %s)
            """,
            (entity_type, entity_id, action, Jsonb(dict(payload))),
        )


def _candidate_cik(candidate: CompanyCandidate) -> str:
    for identifier_type, value in candidate.identifiers:
        if identifier_type == "CIK":
            if len(value) != 10 or not value.isdigit():
                raise ValueError("SEC candidate CIK must be normalized to 10 digits")
            return value
    raise ValueError("SEC company candidate has no CIK identifier")


def _metric_spec(metric_key: str) -> SecMetricSpec:
    for metric in SEC_METRICS:
        if metric.key == metric_key:
            return metric
    raise ValueError(f"Unknown canonical SEC metric key: {metric_key}")


def _series_key(
    candidate: NormalizedFactCandidate, taxonomy: str, tag: str
) -> str:
    key = {
        "metric": candidate.metric_key,
        "taxonomy": taxonomy,
        "tag": tag,
        "unit": candidate.unit_code,
        "period_type": candidate.period_type,
        "period_start": candidate.period_start.isoformat() if candidate.period_start else None,
        "period_end": candidate.period_end.isoformat() if candidate.period_end else None,
    }
    return json.dumps(key, sort_keys=True, separators=(",", ":"))


def _payload_accession(payload: Mapping[str, Any]) -> str | None:
    fact = payload.get("fact")
    if not isinstance(fact, dict):
        return None
    accession = fact.get("accn")
    return str(accession) if accession else None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

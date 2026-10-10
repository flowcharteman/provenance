"""Safe, versioned normalization of SEC companyfacts into canonical facts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime, time, timezone
from typing import Any, Mapping
from uuid import UUID

from app.adapters.sec.catalog import (
    sec_metric_for_tag,
    sec_tag_is_issuer_scoped,
)
from app.adapters.sec.parsing import (
    is_currency_unit,
    parse_decimal,
    parse_period,
)
from app.adapters.types import (
    FactDataType,
    NormalizedFactCandidate,
    ObservationKind,
    PersistedSourceObservation,
)


NORMALIZER_VERSION = "sec-companyfacts-v3"


class SecFactNormalizer:
    """Maps a deliberately small US-GAAP subset without changing raw payloads."""

    @property
    def version(self) -> str:
        return NORMALIZER_VERSION

    async def normalize(
        self,
        observations: Sequence[PersistedSourceObservation],
        *,
        company_id: UUID,
    ) -> Sequence[NormalizedFactCandidate]:
        candidates = []
        document_ids = tuple(
            item.id
            for item in observations
            if item.observation.kind is ObservationKind.DOCUMENT
        )
        for persisted in observations:
            observation = persisted.observation
            if observation.kind is not ObservationKind.FINANCIAL:
                continue
            candidate = self.normalize_fact_observation(
                observation.provider_payload,
                company_id=company_id,
                source_observation_id=persisted.id,
                published_at=observation.provenance.published_at,
            )
            if candidate is not None:
                candidates.append(
                    NormalizedFactCandidate(
                        metric_key=candidate.metric_key,
                        value=candidate.value,
                        unit_code=candidate.unit_code,
                        data_type=candidate.data_type,
                        source_observation_ids=(persisted.id,) + document_ids,
                        normalization_version=candidate.normalization_version,
                        company_id=candidate.company_id,
                        period_type=candidate.period_type,
                        currency=candidate.currency,
                        period_start=candidate.period_start,
                        period_end=candidate.period_end,
                        effective_at=candidate.effective_at,
                        published_at=candidate.published_at,
                        confidence=candidate.confidence,
                        context=candidate.context,
                    )
                )
        return tuple(candidates)

    def normalize_fact_observation(
        self,
        payload: Mapping[str, Any],
        *,
        company_id: UUID,
        source_observation_id: UUID,
        published_at: datetime | None = None,
    ) -> NormalizedFactCandidate | None:
        taxonomy = str(payload.get("taxonomy") or "")
        tag = str(payload.get("tag") or "")
        metric = sec_metric_for_tag(
            taxonomy,
            tag,
            str(payload.get("cik") or "") or None,
        )
        fact = payload.get("fact")
        if metric is None or not isinstance(fact, dict):
            return None
        return self._normalize_fact(
            taxonomy=taxonomy,
            tag=tag,
            tag_info=payload,
            fact=fact,
            unit_code=str(payload.get("unit") or ""),
            metric=metric,
            company_id=company_id,
            source_observation_id=source_observation_id,
            published_at=published_at,
        )

    @staticmethod
    def _normalize_fact(
        *,
        taxonomy: str,
        tag: str,
        tag_info: Mapping[str, Any],
        fact: Any,
        unit_code: str,
        metric: Any,
        company_id: UUID,
        source_observation_id: UUID,
        published_at: datetime | None,
    ) -> NormalizedFactCandidate | None:
        if not isinstance(fact, dict):
            return None
        form = str(fact.get("form") or "")
        if form not in {"10-K", "10-Q", "8-K"}:
            return None
        if metric.unit_dimension == "CURRENCY" and not is_currency_unit(unit_code):
            return None
        if metric.unit_dimension == "SHARES" and unit_code != "shares":
            return None
        try:
            value = parse_decimal(fact.get("val"))
        except ValueError:
            return None
        period_type, period_start, period_end, reason = parse_period(fact)
        if reason is not None:
            return None

        fact_filed_at = _parse_datetime(fact.get("filed")) or published_at
        canonical_currency = unit_code if is_currency_unit(unit_code) else None
        issuer_cik = str(tag_info.get("cik") or "")
        context = {
            "taxonomy": taxonomy,
            "tag": tag,
            "issuer_cik": (
                issuer_cik
                if sec_tag_is_issuer_scoped(taxonomy, tag, issuer_cik)
                else None
            ),
            "label": str(tag_info.get("label") or ""),
            "description": str(tag_info.get("description") or ""),
            "form": form,
            "accession_number": str(fact.get("accn") or ""),
            "fiscal_year": fact.get("fy"),
            "fiscal_period": fact.get("fp"),
            "frame": fact.get("frame"),
            "original_unit": unit_code,
        }
        return NormalizedFactCandidate(
            metric_key=metric.key,
            value=value,
            unit_code=unit_code,
            data_type=FactDataType.REPORTED,
            source_observation_ids=(source_observation_id,),
            normalization_version=NORMALIZER_VERSION,
            company_id=company_id,
            period_type=period_type,
            currency=canonical_currency,
            period_start=period_start,
            period_end=period_end,
            effective_at=_date_as_utc(fact.get("end")),
            published_at=fact_filed_at,
            confidence=None,
            context=context,
        )


def unsupported_fact_reasons(
    payload: Mapping[str, Any],
) -> Mapping[str, int]:
    """Count source facts omitted by this intentionally limited normalizer."""
    reasons: Counter[str] = Counter()
    facts_root = payload.get("facts", {})
    if not isinstance(facts_root, dict):
        return {"invalid_companyfacts_shape": 1}
    cik = str(payload.get("cik") or "") or None
    for taxonomy, tags in facts_root.items():
        if not isinstance(tags, dict):
            continue
        for tag, tag_info in tags.items():
            if sec_metric_for_tag(str(taxonomy), str(tag), cik) is None:
                reasons["unmapped_tag"] += _fact_row_count(tag_info)
                continue
            units = tag_info.get("units", {}) if isinstance(tag_info, dict) else {}
            if not isinstance(units, dict):
                continue
            for unit_code, rows in units.items():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        reasons["invalid_fact_row"] += 1
                    elif str(row.get("form") or "") not in {"10-K", "10-Q", "8-K"}:
                        reasons["unsupported_form"] += 1
                    elif not (
                        is_currency_unit(str(unit_code))
                        or str(unit_code) == "shares"
                    ):
                        reasons["unsupported_unit"] += 1
                    else:
                        try:
                            parse_decimal(row.get("val"))
                        except ValueError:
                            reasons["invalid_numeric_value"] += 1
                            continue
                        _, _, _, reason = parse_period(row)
                        if reason:
                            reasons[reason] += 1
    return dict(reasons)


def _fact_row_count(tag_info: Any) -> int:
    if not isinstance(tag_info, dict):
        return 1
    units = tag_info.get("units", {})
    if not isinstance(units, dict):
        return 1
    return sum(len(rows) for rows in units.values() if isinstance(rows, list))


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.combine(
            date.fromisoformat(value),
            time.min,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _date_as_utc(value: Any) -> datetime | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed

"""Pure parsing and safe period classification for official SEC response shapes."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from uuid import UUID, uuid4

from app.adapters.types import (
    CompanyCandidate,
    FilingReference,
    ObservationKind,
    Provenance,
    SourceObservation,
)
from app.adapters.sec.catalog import SEC_TAG_TO_METRIC


SUPPORTED_FORMS = frozenset({"10-K", "10-Q", "8-K"})
_CIK_WIDTH = 10
_CURRENCY_UNIT = re.compile(r"^[A-Z]{3}$")


def normalize_cik(value: object) -> str:
    digits = str(value).strip()
    if not digits.isdigit() or len(digits) > _CIK_WIDTH:
        raise ValueError(f"Invalid SEC CIK: {value!r}")
    return digits.zfill(_CIK_WIDTH)


def canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _provenance(
    *,
    source_record_id: str,
    source_record: Mapping[str, Any],
    retrieved_at: datetime,
    retrieval_batch_id: UUID,
    url: str,
    published_at: datetime | None = None,
    effective_at: datetime | None = None,
    filing_reference: str | None = None,
) -> Provenance:
    return Provenance(
        source_system_key="sec-edgar",
        retrieved_at=retrieved_at,
        retrieval_batch_id=retrieval_batch_id,
        source_record_id=source_record_id,
        source_record_hash=canonical_hash(source_record),
        source_document_reference=url,
        published_at=published_at,
        effective_at=effective_at,
        filing_reference=filing_reference,
    )


def parse_company_tickers(
    payload: Mapping[str, Any],
    *,
    query: str,
    retrieved_at: datetime,
    retrieval_batch_id: UUID | None = None,
    url: str,
) -> Sequence[CompanyCandidate]:
    rows = list(payload.values())
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("SEC company ticker response has an invalid shape")

    stripped_query = query.strip()
    exact_ticker = [
        row for row in rows
        if str(row.get("ticker", "")).casefold() == stripped_query.casefold()
    ]
    matches = exact_ticker or [
        row for row in rows
        if stripped_query.casefold() in str(row.get("title", "")).casefold()
    ]
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for row in matches:
        try:
            cik = normalize_cik(row["cik_str"])
        except (KeyError, ValueError):
            continue
        grouped.setdefault(cik, []).append(row)

    result = []
    for cik, company_rows in grouped.items():
        observations = []
        identifiers = {("CIK", cik)}
        for row in company_rows:
            ticker = str(row.get("ticker", "")).strip().upper()
            if ticker:
                identifiers.add(("TICKER", ticker))
            row_payload = dict(row)
            provenance = _provenance(
                source_record_id=f"company-ticker:{cik}:{ticker}",
                source_record=row_payload,
                retrieved_at=retrieved_at,
                retrieval_batch_id=retrieval_batch_id or uuid4(),
                url=url,
            )
            observations.append(
                SourceObservation(
                    kind=ObservationKind.COMPANY_CANDIDATE,
                    provenance=provenance,
                    provider_payload=row_payload,
                    subject_reference=cik,
                )
            )
        first = company_rows[0]
        name = str(first.get("title", "")).strip()
        if not name:
            continue
        result.append(
            CompanyCandidate(
                provider_reference=cik,
                display_name=name,
                legal_name=name,
                jurisdiction="US",
                provenance=observations[0].provenance,
                identifiers=tuple(sorted(identifiers)),
                source_observations=tuple(observations),
            )
        )
    return tuple(result)


def parse_submission_candidate(
    payload: Mapping[str, Any],
    *,
    cik: str,
    retrieved_at: datetime,
    url: str,
    response_hash: str | None = None,
) -> CompanyCandidate:
    normalized_cik = normalize_cik(cik)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("SEC company submission response omitted the company name")
    tickers = payload.get("tickers", [])
    if not isinstance(tickers, list):
        raise ValueError("SEC company submission tickers field is not an array")
    identifiers = {("CIK", normalized_cik)}
    for ticker_item in tickers:
        ticker = str(ticker_item).strip().upper()
        if ticker:
            identifiers.add(("TICKER", ticker))
    provenance = Provenance(
        source_system_key="sec-edgar",
        retrieved_at=retrieved_at,
        retrieval_batch_id=uuid4(),
        source_record_id=f"submission:{normalized_cik}",
        source_record_hash=response_hash or canonical_hash(payload),
        source_document_reference=url,
    )
    observation = SourceObservation(
        kind=ObservationKind.IDENTIFIER_MATCH,
        provenance=provenance,
        provider_payload=dict(payload),
        subject_reference=normalized_cik,
    )
    return CompanyCandidate(
        provider_reference=normalized_cik,
        display_name=name,
        legal_name=name,
        jurisdiction="US",
        provenance=provenance,
        identifiers=tuple(sorted(identifiers)),
        source_observations=(observation,),
    )


def parse_filings(
    payload: Mapping[str, Any],
    *,
    cik: str,
    retrieved_at: datetime,
    url: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Sequence[FilingReference]:
    recent = payload.get("filings", {}).get("recent")
    if not isinstance(recent, dict):
        raise ValueError("SEC submissions response omitted filings.recent")
    fields = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "form",
        "primaryDocument",
    )
    arrays = {key: recent.get(key) for key in fields}
    if not all(isinstance(value, list) for value in arrays.values()):
        raise ValueError("SEC filings.recent response has missing or invalid arrays")
    if len({len(value) for value in arrays.values()}) != 1:
        raise ValueError("SEC filings.recent arrays have inconsistent lengths")

    normalized_cik = normalize_cik(cik)
    batch_id = uuid4()
    references = []
    for index in range(len(arrays["form"])):
        row = {key: arrays[key][index] for key in fields}
        form = str(row["form"] or "")
        filed = _date(row["filingDate"])
        accession = str(row["accessionNumber"] or "").strip()
        if form not in SUPPORTED_FORMS or not filed or not accession:
            continue
        filing_time = datetime.combine(filed, time.min, tzinfo=timezone.utc)
        if since and filing_time < since:
            continue
        if until and filing_time > until:
            continue
        report_end = _date(row["reportDate"])
        accession_path = accession.replace("-", "")
        archive_url = (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{int(normalized_cik)}/{accession_path}/{accession}-index.html"
        )
        provenance = _provenance(
            source_record_id=f"filing:{normalized_cik}:{accession}",
            source_record=row,
            retrieved_at=retrieved_at,
            retrieval_batch_id=batch_id,
            url=url,
            published_at=filing_time,
            effective_at=(
                datetime.combine(report_end, time.min, tzinfo=timezone.utc)
                if report_end
                else None
            ),
            filing_reference=archive_url,
        )
        observation = SourceObservation(
            kind=ObservationKind.FILING,
            provenance=provenance,
            provider_payload={
                "cik": normalized_cik,
                "filing": row,
                "filing_url": archive_url,
            },
            subject_reference=normalized_cik,
        )
        references.append(
            FilingReference(
                provider_reference=accession,
                filing_type=form,
                provenance=provenance,
                period_end=report_end,
                source_observation=observation,
            )
        )
    return tuple(references)


def parse_companyfacts_observations(
    payload: Mapping[str, Any],
    *,
    cik: str,
    retrieved_at: datetime,
    url: str,
    response_hash: str | None = None,
) -> Sequence[SourceObservation]:
    if not isinstance(payload.get("facts"), dict):
        raise ValueError("SEC companyfacts response omitted the facts object")
    normalized_cik = normalize_cik(cik)
    batch_id = uuid4()
    document_provenance = Provenance(
        source_system_key="sec-edgar",
        retrieved_at=retrieved_at,
        retrieval_batch_id=batch_id,
        source_record_id=f"companyfacts:{normalized_cik}",
        source_record_hash=response_hash or canonical_hash(payload),
        source_document_reference=url,
    )
    observations = [
        SourceObservation(
            kind=ObservationKind.DOCUMENT,
            provenance=document_provenance,
            provider_payload=dict(payload),
            subject_reference=normalized_cik,
        )
    ]
    facts_root = payload["facts"]
    for taxonomy, tag_collection in facts_root.items():
        if not isinstance(tag_collection, dict):
            continue
        for tag, tag_info in tag_collection.items():
            if (taxonomy, tag) not in SEC_TAG_TO_METRIC or not isinstance(tag_info, dict):
                continue
            units = tag_info.get("units")
            if not isinstance(units, dict):
                continue
            for unit_code, fact_rows in units.items():
                if not isinstance(fact_rows, list):
                    continue
                for index, fact_row in enumerate(fact_rows):
                    if not isinstance(fact_row, dict):
                        continue
                    source_record = {
                        "cik": normalized_cik,
                        "taxonomy": taxonomy,
                        "tag": tag,
                        "label": tag_info.get("label"),
                        "description": tag_info.get("description"),
                        "unit": unit_code,
                        "fact": fact_row,
                    }
                    accession = str(fact_row.get("accn") or "no-accession")
                    record_id = ":".join(
                        (
                            "xbrl",
                            normalized_cik,
                            str(taxonomy),
                            str(tag),
                            str(unit_code),
                            accession,
                            str(fact_row.get("start") or "instant"),
                            str(fact_row.get("end") or "no-end"),
                            str(fact_row.get("frame") or ""),
                            str(index),
                        )
                    )
                    filed = _date(fact_row.get("filed"))
                    end_date = _date(fact_row.get("end"))
                    filing_url = (
                        "https://www.sec.gov/Archives/edgar/data/"
                        f"{int(normalized_cik)}/{accession.replace('-', '')}/"
                        f"{accession}-index.html"
                        if accession != "no-accession"
                        else url
                    )
                    provenance = _provenance(
                        source_record_id=record_id,
                        source_record=source_record,
                        retrieved_at=retrieved_at,
                        retrieval_batch_id=batch_id,
                        url=url,
                        published_at=(
                            datetime.combine(filed, time.min, tzinfo=timezone.utc)
                            if filed
                            else None
                        ),
                        effective_at=(
                            datetime.combine(end_date, time.min, tzinfo=timezone.utc)
                            if end_date
                            else None
                        ),
                        filing_reference=filing_url,
                    )
                    observations.append(
                        SourceObservation(
                            kind=ObservationKind.FINANCIAL,
                            provenance=provenance,
                            provider_payload=source_record,
                            subject_reference=normalized_cik,
                        )
                    )
    return tuple(observations)


def parse_decimal(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("XBRL fact value is missing or non-numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Invalid XBRL decimal value: {value!r}") from error
    if not result.is_finite():
        raise ValueError("XBRL fact value must be finite")
    return result


def parse_period(
    fact: Mapping[str, Any],
) -> Tuple[str, date | None, date | None, str | None]:
    end_date = _date(fact.get("end"))
    if not end_date:
        return "UNSUPPORTED", None, None, "missing_period_end"
    start_date = _date(fact.get("start"))
    if start_date is None:
        return "INSTANT", None, end_date, None
    if start_date > end_date:
        return "UNSUPPORTED", start_date, end_date, "invalid_duration_range"

    duration_days = (end_date - start_date).days + 1
    form = str(fact.get("form") or "")
    if 300 <= duration_days <= 400 and form in {"10-K", "8-K"}:
        return "ANNUAL", start_date, end_date, None
    if 70 <= duration_days <= 110 and form in {"10-Q", "8-K"}:
        return "QUARTERLY", start_date, end_date, None
    return "UNSUPPORTED", start_date, end_date, "unsupported_duration_or_form"


def is_currency_unit(unit_code: str) -> bool:
    return bool(_CURRENCY_UNIT.fullmatch(unit_code))

"""Small, curated SEC US-GAAP-to-canonical metric catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SecMetricSpec:
    key: str
    display_name: str
    metric_group: str
    unit_dimension: str
    statement_context: str
    description: str
    tags: Tuple[str, ...]
    period_requirement: str = "REQUIRED"
    currency_requirement: str = "OPTIONAL"


SEC_METRICS = (
    SecMetricSpec(
        key="revenue",
        display_name="Revenue",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="Reported consolidated revenue; excludes adjusted and segment-only measures.",
        tags=(
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ),
    ),
    SecMetricSpec(
        key="operating_income",
        display_name="Operating income",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="US-GAAP operating income or loss.",
        tags=("OperatingIncomeLoss",),
    ),
    SecMetricSpec(
        key="net_income",
        display_name="Net income",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="US-GAAP net income or loss attributable to the consolidated entity.",
        tags=("NetIncomeLoss",),
    ),
    SecMetricSpec(
        key="total_assets",
        display_name="Total assets",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="US-GAAP total assets at a reporting date.",
        tags=("Assets",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="total_liabilities",
        display_name="Total liabilities",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="US-GAAP total liabilities at a reporting date.",
        tags=("Liabilities",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="total_stockholders_equity",
        display_name="Total stockholders' equity",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="US-GAAP stockholders' equity at a reporting date.",
        tags=("StockholdersEquity",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="cash_and_cash_equivalents",
        display_name="Cash and cash equivalents",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Cash and cash equivalents; restricted cash is not included by inference.",
        tags=("CashAndCashEquivalentsAtCarryingValue",),
        period_requirement="NOT_APPLICABLE",
    ),
)

SEC_TAG_TO_METRIC = {
    (taxonomy, tag): metric
    for metric in SEC_METRICS
    for tag in metric.tags
    for taxonomy in ("us-gaap",)
}

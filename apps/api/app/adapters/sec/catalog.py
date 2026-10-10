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
    issuer_tags: Tuple[Tuple[str, str], ...] = ()
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
    SecMetricSpec(
        key="cash_and_short_term_investments",
        display_name="Cash, cash equivalents and short-term investments",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description=(
            "Issuer-reported aggregate cash, cash equivalents and short-term "
            "investments; do not add its cash component separately."
        ),
        tags=(),
        issuer_tags=(("0001652044", "CashCashEquivalentsAndShortTermInvestments"),),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="other_long_term_investments",
        display_name="Other long-term investments",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Issuer-reported other long-term investments at a reporting date.",
        tags=(),
        issuer_tags=(("0001652044", "OtherLongTermInvestments"),),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="pretax_income",
        display_name="Income before income taxes",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="US-GAAP income from continuing operations before income taxes.",
        tags=(
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ),
        issuer_tags=((
            "0001018724",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ),),
    ),
    SecMetricSpec(
        key="income_tax_expense",
        display_name="Income tax expense",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="US-GAAP income tax expense or benefit.",
        tags=("IncomeTaxExpenseBenefit",),
    ),
    SecMetricSpec(
        key="depreciation_depletion_and_amortization",
        display_name="Depreciation, depletion and amortization",
        metric_group="CASH_FLOW",
        unit_dimension="CURRENCY",
        statement_context="CASH_FLOW",
        description="US-GAAP depreciation, depletion and amortization.",
        tags=("DepreciationDepletionAndAmortization",),
        issuer_tags=(("0001652044", "Depreciation"),),
    ),
    SecMetricSpec(
        key="capital_expenditures",
        display_name="Payments to acquire property, plant and equipment",
        metric_group="CASH_FLOW",
        unit_dimension="CURRENCY",
        statement_context="CASH_FLOW",
        description="Reported payments to acquire property, plant and equipment.",
        tags=("PaymentsToAcquirePropertyPlantAndEquipment",),
        issuer_tags=(("0001018724", "PaymentsToAcquireProductiveAssets"),),
    ),
    SecMetricSpec(
        key="weighted_average_diluted_shares",
        display_name="Weighted-average diluted shares outstanding",
        metric_group="INCOME_STATEMENT",
        unit_dimension="SHARES",
        statement_context="INCOME_STATEMENT",
        description="Reported weighted-average number of diluted shares outstanding.",
        tags=("WeightedAverageNumberOfDilutedSharesOutstanding",),
    ),
    SecMetricSpec(
        key="marketable_securities_current",
        display_name="Marketable securities, current",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Current marketable securities at a reporting date.",
        tags=("MarketableSecuritiesCurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="marketable_securities_noncurrent",
        display_name="Marketable securities, noncurrent",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Noncurrent marketable securities at a reporting date.",
        tags=("MarketableSecuritiesNoncurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    # Modeling choice, not an SEC fact: operating current assets are
    # AssetsCurrent less cash and current marketable securities; operating
    # current liabilities are LiabilitiesCurrent less current debt and
    # commercial paper. These component facts remain separate here.
    SecMetricSpec(
        key="assets_current",
        display_name="Current assets",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="US-GAAP current assets; retained as a reported component for a chosen NWC definition.",
        tags=("AssetsCurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="liabilities_current",
        display_name="Current liabilities",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="US-GAAP current liabilities; retained as a reported component for a chosen NWC definition.",
        tags=("LiabilitiesCurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="long_term_debt_current",
        display_name="Long-term debt, current maturities",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Reported current maturities of long-term debt.",
        tags=("LongTermDebtCurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="commercial_paper",
        display_name="Commercial paper",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Reported commercial paper outstanding at a reporting date.",
        tags=("CommercialPaper",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="long_term_debt_noncurrent",
        display_name="Long-term debt, noncurrent",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Reported long-term debt excluding current maturities.",
        tags=("LongTermDebtNoncurrent",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="long_term_debt",
        display_name="Long-term debt",
        metric_group="BALANCE_SHEET",
        unit_dimension="CURRENCY",
        statement_context="BALANCE_SHEET",
        description="Reported total long-term debt; do not add to its current/noncurrent components.",
        tags=("LongTermDebt",),
        period_requirement="NOT_APPLICABLE",
    ),
    SecMetricSpec(
        key="interest_expense",
        display_name="Interest expense",
        metric_group="INCOME_STATEMENT",
        unit_dimension="CURRENCY",
        statement_context="INCOME_STATEMENT",
        description="Reported standalone interest expense when present.",
        tags=("InterestExpense",),
    ),
)

SEC_TAG_TO_METRIC = {
    (taxonomy, tag): metric
    for metric in SEC_METRICS
    for tag in metric.tags
    for taxonomy in ("us-gaap",)
}

SEC_CIK_TAG_TO_METRIC = {
    (cik, taxonomy, tag): metric
    for metric in SEC_METRICS
    for cik, tag in metric.issuer_tags
    for taxonomy in ("us-gaap",)
}


def sec_metric_for_tag(
    taxonomy: str,
    tag: str,
    cik: str | None = None,
) -> SecMetricSpec | None:
    """Resolve a generic or explicitly issuer-scoped SEC tag mapping."""
    if cik is not None:
        issuer_metric = SEC_CIK_TAG_TO_METRIC.get((cik, taxonomy, tag))
        if issuer_metric is not None:
            return issuer_metric
    return SEC_TAG_TO_METRIC.get((taxonomy, tag))


def sec_tag_is_issuer_scoped(taxonomy: str, tag: str, cik: str | None) -> bool:
    """Return whether this tag's canonical meaning is explicitly CIK-scoped."""
    return cik is not None and (cik, taxonomy, tag) in SEC_CIK_TAG_TO_METRIC


def sec_tags_for_ingestion() -> Tuple[str, ...]:
    """Return all curated tags, including issuer-scoped concepts."""
    return tuple(
        sorted(
            {tag for _, tag in SEC_TAG_TO_METRIC}
            | {tag for _, _, tag in SEC_CIK_TAG_TO_METRIC}
        )
    )

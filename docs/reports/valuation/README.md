# Apple Valuation Summary — Seven-Company Football Field

This report summarizes the illustrative Apple DCF, seven-company trading-comps,
and LBO outputs. It is a reproducible summary of the approved inputs and
calculations, not a finalized valuation or investment recommendation. No new
SEC request or database write was made for this workbook and README update.

## Football field

Apple's supplied market price is **$332.89 per share** (Oct. 5, 2026). The
valuation methods below use Apple FY2025 reported financials and the already
established Day 3/Day 4 model results. For point estimates, the low and high are
equal; they are not ranges.

| Method | Low ($/share) | High ($/share) | Difference from $332.89 at low | Difference from $332.89 at high |
|---|---:|---:|---:|---:|
| DCF sensitivity | 88.53 | 124.33 | -73.41% | -62.65% |
| Comps: EV/EBITDA (Apple, Microsoft*, Alphabet) | 193.81 | 323.77 | -41.78% | -2.74% |
| Comps: EV/Revenue (Apple, Microsoft*, Alphabet) | 285.43 | 324.63 | -14.26% | -2.48% |
| Comps: Microsoft P/E | 219.32 | 219.32 | -34.12% | -34.12% |
| LBO ability-to-pay | 128.19 | 128.19 | -61.49% | -61.49% |

The DCF sensitivity endpoints are the minimum and maximum in the 3-by-3
WACC/terminal-growth grid. The workbook's formula-driven chart and table show
these beside the comps ranges, LBO ability-to-pay point, and Apple's supplied
market price. *Microsoft is re-included using the stated zero assumption for
FY2026 commercial paper described below; it is not a strict-completeness pass.

| WACC \ Terminal growth | 2.00% | 2.50% | 3.00% |
|---:|---:|---:|---:|
| 9.51% | $111.63 | $117.53 | $124.33 |
| 10.51% | $98.72 | $103.11 | $108.09 |
| 11.51% | $88.53 | $91.90 | $95.67 |

### Additional share-value calculations

Apple FY2025 net debt is **-$33.763bn**: debt of $98.657bn less cash and
investments of $132.420bn. A negative net-debt figure represents net cash. The
FY2025 diluted weighted-average share count is **15.004697bn**.

- **LBO ability-to-pay:** ($1,889.696bn maximum entry EV − (-$33.763bn net
  debt)) ÷ 15.004697bn shares = **$128.19/share**.
- **EV/EBITDA comps range:** Apple, Microsoft, and Alphabet are included.
  Their multiples are applied to Apple FY2025 EBITDA of $144.748bn, bridged
  using Apple's net cash, and divided by 15.004697bn Apple diluted shares,
  producing **$193.81–$323.77/share**. Microsoft is re-included under the
  explicit commercial-paper assumption described below. It contributes the
  low endpoint.
- **EV/Revenue comps range:** Apple, Microsoft, and Alphabet are included.
  Their multiples are applied to Apple FY2025 revenue of $416.161bn, with the
  same Apple net-cash bridge and diluted-share denominator, producing
  **$285.43–$324.63/share**. Microsoft contributes the high endpoint.
- **Microsoft P/E comps:** 29.38x × Apple FY2025 net income of $112.010bn =
  $3,290.854bn implied equity; ÷ 15.004697bn shares = **$219.32/share**.

The Comps sheet continues to show all seven companies and their calculated
multiples. The Football Field uses Apple and Alphabet, whose identified EV
inputs are complete, plus Microsoft under the clearly stated zero commercial-
paper assumption below. It continues to exclude Amazon and Tesla because no
adjacent commercial-paper value was found; Meta because current debt and
commercial paper lack adjacent reference values; and NVIDIA because its
missing FY2026 investments are not a low-materiality omission. The separately
shown Microsoft P/E point is an equity multiple, not an EV multiple.

## Methodology

### DCF

The DCF projects five years of unlevered free cash flow (UFCF), discounts the
forecast at WACC, and adds a Gordon-growth terminal value. UFCF is calculated as
NOPAT + D&A − capex − change in net working capital. Enterprise value is the
present value of explicit forecast UFCF plus the present value of terminal
value. The equity bridge adds net cash (equivalently subtracts net debt), and
the result is divided by diluted weighted-average shares.

The Day 3 sensitivity range varies WACC from 9.51% to 11.51% and terminal growth
from 2.00% to 3.00%; its endpoint values appear in the football field above.

### Trading comparables

The EV/EBITDA and EV/Revenue Football Field ranges use Apple and Alphabet's
complete identified EV inputs, and Microsoft with FY2026 commercial paper
assumed at zero based on its FY2025 reported value. This is a stated
modeling assumption, not an FY2026 fact. Their multiples are applied to
Apple's FY2025 EBITDA and revenue, respectively. Each implied enterprise
value is bridged to equity value using Apple's FY2025 net debt, then divided
by Apple's FY2025 diluted weighted-average shares. For the separately
retained P/E point, Microsoft's rounded P/E multiple is applied to Apple's
reported FY2025 net income to estimate equity value directly, then divided
by the same share count. Other unresolved balances remain flagged and are
not asserted to be zero.

Apple EBITDA uses EBIT plus the combined SEC D&A tag
`DepreciationDepletionAndAmortization`. Microsoft's compared EBITDA uses EBIT
plus `Depreciation` and `AmortizationOfIntangibleAssets`, explicitly excluding
`FinanceLeaseRightOfUseAssetAmortization`. The other issuer-specific EBITDA
definitions and their limitations are listed in the consolidated data-quality
appendix below.

### LBO ability-to-pay

The Day 4 illustrative LBO forecasts operating cash flow using the DCF
operating assumptions, deducts interest and cash taxes, and applies cash
available after scheduled amortization to repay the senior TLB first. At Year 5,
exit EV is exit EBITDA times the assumed exit multiple; remaining debt is
subtracted to obtain sponsor exit equity. Ability-to-pay solves for the maximum
entry EV (and multiple) that results in the target 20% five-year IRR under the
same financing, operating, exit, and fee assumptions.

**This is an illustrative LBO mechanics exercise on Apple's real financials,
not a realistic deal thesis. A company this large would not actually be a
leveraged buyout target.**

## Assumptions and traced facts

Assumptions and SEC-reported facts are distinct inputs. Forecasts, multiples,
and discount rates are not SEC facts.

### External market inputs and judgment calls

- Apple share price: **$332.89**, supplied external market input dated Oct. 5,
  2026. This is not an SEC fact.
- Apple market capitalization: **$4,858bn**, supplied external market input
  dated Oct. 5, 2026; used for Day 3 WACC capital structure and to derive the
  Apple trading multiples.
- Microsoft market capitalization: **$3,930bn**, supplied external market
  input dated Oct. 7, 2026; used to derive the Microsoft trading multiples.
  Microsoft's supplied $529.76 share price was not needed in the calculations
  summarized here.
- Other supplied external market inputs (none are SEC facts): Alphabet
  **$348.29/share** and **$4,260bn** market cap; Amazon **$254.06/share** and
  **$2,740bn**; Meta **$720.89/share** and **$1,840bn**; NVIDIA
  **$230.48/share** and **$5,730bn**; and Tesla **$375.00/share** and
  **$1,490bn**. These close prices and market caps are dated Oct. 8, 2026;
  NVIDIA's supplied figures are split-adjusted.
- Day 3 risk-free rate: **5.27%**, supplied as the 10-year US Treasury yield
  on Oct. 6, 2026; external market input.
- Day 3 Apple beta: **1.07**, supplied as five-year monthly levered equity
  beta; external market input.
- Equity risk premium: **5.00%**, supplied practitioner assumption and
  judgment call, not a sourced market quote.
- Day 3 cost of debt: 5.27% risk-free rate plus a proposed 0.75 percentage
  point spread = **6.02%** pretax; spread is a judgment call for review.
- Day 3 forward tax rate: **15.1646%**, calculated as the mean of FY2023 and
  FY2025 effective tax rates. FY2024's 24.0912% actual rate was excluded per
  instruction because it included a one-time EU State Aid charge and was not
  considered representative.
- Day 3 forecast revenue growth: **4.5%, 4.0%, 3.5%, 3.0%, 2.5%** for forecast
  years 1–5; proposed assumptions informed by historical Apple growth.
- Day 3 EBIT margin: **31.5%**; proposed assumption informed by FY2023–FY2025
  margins.
- Day 3 D&A / revenue: **2.9%**; proposed assumption informed by FY2023–FY2025.
- Day 3 capex / revenue: **2.8%**; proposed assumption informed by FY2023–FY2025.
- Day 3 NWC / revenue: **-12.51%**, holding FY2025 operating NWC / revenue
  constant; proposed assumption.
- Day 3 terminal growth: **2.5% nominal**, proposed as a long-run inflation
  anchor plus modest real growth; judgment call, not a sourced forecast.
- Day 3 discount timing: annual year-end cash flows discounted at t=1 through
  t=5; simplifying model convention.
- Day 4 entry EV / EBITDA: **20.0x**; proposed assumption informed by the
  previously derived trading-comp range.
- Day 4 exit EV / EBITDA: **19.0x**; proposed one-turn de-rating from entry,
  not an assertion that exit equals entry.
- Day 4 TLB leverage and pricing: **3.5x EBITDA**, risk-free + **2.50%**
  spread = 7.77%; proposed seven-year maturity and 1% annual original-principal
  scheduled amortization.
- Day 4 senior notes: **1.5x EBITDA**, risk-free + **3.25%** spread = 8.52%;
  proposed ten-year maturity and no scheduled amortization during the hold.
- Day 4 total opening debt: **5.0x EBITDA**; proposed assumption.
- Day 4 cash sweep: 100% of cash after interest, cash taxes, and scheduled TLB
  amortization pays down TLB first, then notes; no interim sponsor
  distributions.
- Day 4 transaction fees: **1.0% of entry EV**, proposed assumption.
- Day 4 interest is calculated on beginning-of-year debt balances; no minimum
  cash reserve, refinancing, or maturity payment is modeled.
- Day 4 ability-to-pay target: **20% five-year IRR**, specified by the user.
- Day 5's displayed Microsoft P/E point uses the previously derived rounded
  **29.38x** multiple. The seven-company EV/EBITDA and EV/Revenue multiples
  remain visible on the Comps sheet; the Football Field uses Apple and
  Alphabet's complete EV inputs plus Microsoft's expressly stated
  zero-commercial-paper assumption.

### Traced Apple SEC facts used

Apple FY2025 actuals: revenue **$416.161bn**; EBIT **$133.050bn**; net income
**$112.010bn**; combined D&A **$11.698bn**; capex **$12.715bn**; current debt
**$12.350bn**; commercial paper **$7.979bn**; noncurrent long-term debt
**$78.328bn**; cash **$35.934bn**; current marketable securities **$18.763bn**;
noncurrent marketable securities **$77.723bn**; diluted weighted-average
shares **15.004697bn**. Financial values and share count are SEC-reported
facts from Apple's FY2025 filing, accession `0000320193-25-000079`, as
previously captured and analyzed. The derived debt is $98.657bn; derived cash
and investments are $132.420bn; derived net debt is -$33.763bn.

## Data quality across issuers

This consolidated appendix describes cross-company comparability, data
coverage, provenance, and review limitations. It does not revise the underlying
SEC facts or finalize any modeling assumption.

- **Different EBITDA constructions:** Apple uses EBIT plus the combined
  `DepreciationDepletionAndAmortization` tag. Microsoft's definition is EBIT
  plus `Depreciation` and `AmortizationOfIntangibleAssets`; Amazon, Meta, and
  NVIDIA use the same two-component construction while excluding
  `FinanceLeaseRightOfUseAssetAmortization`. Alphabet and Tesla use EBIT plus
  `Depreciation` only because no intangible-amortization tag was identified
  for their selected fiscal years. These disclosed constructions are not
  perfectly comparable. The captured Apple combined D&A tag could not be
  confirmed to include or exclude finance-lease amortization.
- **Revenue tag ambiguity:** The workbook records the selected revenue tag
  alongside each accession. For Tesla FY2025, the capture contains the same
  reported value under both `Revenues` and
  `RevenueFromContractWithCustomerExcludingAssessedTax`; `Revenues` is listed
  as the selected input and the duplicate-looking match is disclosed rather
  than counted twice. Meta's selected revenue tag is
  `RevenueFromContractWithCustomerExcludingAssessedTax`.
- **NVIDIA share-count split:** NVIDIA FY2026 uses the split-adjusted diluted
  share count of **24.514bn** from the prior analysis; no pre-split count is
  used in this workbook. The NVIDIA peer multiple is calculated from its
  supplied split-adjusted market data. NVIDIA's own share count is not used
  as Apple's implied-price denominator.
- **Tesla tax outlier:** Tesla FY2023 reported a one-time deferred-tax-asset
  valuation-allowance release. It is excluded from normalized tax-rate
  calculations; FY2025's own tax and pretax facts are used instead. This
  resembles, but is not the same item as, Apple's excluded FY2024 EU State Aid
  tax effect.
- **Materiality-based treatment of missing EV facts:** Microsoft FY2026
  `CommercialPaper` is missing, but the same tag was reported as **$0.000bn**
  at FY2025 period end **June 30, 2025** (accession
  `0000950170-25-100235`). For the Football Field only, Microsoft is
  re-included using its last-known value of $0.000bn as an explicit
  FY2026 modeling assumption, not as a fact. The range labels and Football
  Field note identify this assumption.
- **Other incomplete EVs remain excluded:** Amazon and Tesla commercial
  paper have no adjacent same-tag reference value. Meta's current debt and
  commercial-paper facts have no adjacent same-tag reference value; Meta
  remains excluded explicitly because current debt is unresolved. NVIDIA's
  FY2026 `MarketableSecuritiesCurrent` fact is absent, but the same tag was
  **$34.621bn** at FY2025 period end **January 26, 2025** (accession
  `0001045810-25-000023`), a non-low prior value—not a zero/near-zero
  basis for carrying it forward. NVIDIA also had FY2025 commercial paper of
  $0.000bn, but that does not resolve the missing investments. NVIDIA and
  Meta therefore remain excluded. Missing values are not silently assumed
  zero. Their multiples remain visible on the Comps sheet, not used in the
  Football Field.
- **Issuer-by-issuer EV screen and provenance:**

  | Company | EV input status | Football Field EV-multiple range | Data provenance |
  |---|---|---|---|
  | Apple | Complete identified inputs | Included | Database-ingested |
  | Microsoft | FY2026 commercial paper missing; assumed $0.000bn from FY2025 for this field only | Re-included by stated assumption | Capture-only |
  | Alphabet | Complete identified inputs; commercial paper reported as zero | Included | Database-ingested |
  | Amazon | Commercial-paper fact missing; no adjacent same-tag value | Excluded | Database-ingested |
  | Meta | Current debt and commercial-paper facts missing; no adjacent same-tag values | Excluded | Capture-only |
  | NVIDIA | FY2026 investments missing; FY2025 same-tag value $34.621bn is not low | Excluded | Capture-only |
  | Tesla | Commercial-paper fact missing; no adjacent same-tag value | Excluded | Capture-only |

  Inclusion is based on EV completeness or the explicitly stated Microsoft
  materiality assumption, not ingestion status. Amazon is database-ingested
  but excluded; Microsoft is capture-only but re-included under the assumption.
- **Materiality decision is distinct from ingestion status:** Amazon is
  database-ingested but excluded due to an unresolved EV input. Microsoft is
  capture-only but re-included only under the stated prior-zero assumption.
  Meta, NVIDIA, and Tesla remain excluded based on missing-fact materiality
  evidence, not because they are capture-only. Provenance tier alone does not
  determine inclusion.
- **Provenance tiers:** Apple, Alphabet, and Amazon have database-provenance
  facts that were ingested and normalized. Microsoft, Meta, NVIDIA, and Tesla
  are analysis-only from the existing SEC capture files and have not been
  ingested. The workbook labels these tiers in the Comps sheet and records
  tags/accessions or external-source dates beside the inputs.
- **Timing mismatch:** FY2025/FY2026 annual financial facts and balance sheets
  are compared with externally supplied market inputs dated Oct. 5–8, 2026.
  This timing mismatch affects net-debt and per-share comparability.
- **Apple interest expense:** Standalone `InterestExpense` was available for
  Apple FY2023 only; no standalone FY2024 or FY2025 fact was found. It is not
  silently imputed from pretax income or used as a forward cost-of-debt fact.
- **LBO scope and scale:** The LBO is an illustrative mechanics exercise on
  Apple's real financials, not a realistic deal thesis; a company of Apple's
  size would not be a practical leveraged-buyout target. The proposed sponsor
  equity check at the 20.0x entry case is approximately **$2.200 trillion**,
  an unrealistic single-sponsor requirement.
- **Review status:** Day 4's entry case produces about **6.03% IRR** under the
  proposed assumptions; the **13.06x** maximum entry multiple and **$128.19**
  ability-to-pay price are derived at the specified 20% target. The DCF/LBO
  assumptions, external inputs, multiples, financing terms, and outputs
  remain subject to review and are not final conclusions.

## Workbook

The updated [`apple-day3-day4-model.xlsx`](./apple-day3-day4-model.xlsx)
contains formula-linked Inputs, DCF, LBO, seven-company Comps, and Football
Field sheets. The Comps and Football Field sheets include formula-driven peer
implied-price ranges and an Excel range chart. The original DCF and LBO sheets
were preserved unchanged. Excel is configured to recalculate formulas when
the workbook is opened.

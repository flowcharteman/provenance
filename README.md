# Investment Analysis Platform

A full-stack financial analysis platform designed to replicate key workflows used in investment banking, equity research and corporate finance.

The platform allows a user to enter a publicly available company and retrieve the latest available financial and market information, analyse the company using multiple valuation methodologies, and build M&A transaction models.

The system prioritises **data accuracy, source traceability, reproducibility and transparent assumptions**.

---

## Project Objective

The user should be able to enter almost any supported public company by:

- Company name
- Ticker
- ISIN
- Legal entity name
- Jurisdiction-specific identifier

The platform should identify the correct company, retrieve the latest available information from relevant sources, normalise the data and make it available across the financial models.

The platform should support:

- Company financial analysis
- Trading comparable companies analysis
- Precedent transaction analysis
- DCF valuation
- LBO analysis
- Sum-of-the-parts valuation
- Strategic valuation analysis
- M&A transaction modelling
- Accretion/dilution analysis
- Financing analysis
- Post-merger ownership analysis
- Macroeconomic analysis

---

# Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Recharts

## Backend

- Python
- FastAPI
- Pydantic
- pandas
- NumPy
- SQLAlchemy

## Database

- PostgreSQL

## Infrastructure

- Docker
- Docker Compose
- Redis
- Celery or equivalent background task system

## Testing

- pytest
- Vitest/Jest

---

# Architecture

The application should be modular.

```text
User
  |
  v
Next.js Frontend
  |
  v
FastAPI Backend
  |
  +--------------------+
  |                    |
  v                    v
Financial Models     Data Services
  |                    |
  |                    +----------------------+
  |                    |          |           |
  v                    v          v           v
DCF                  SEC       Companies    SEDAR+
LBO                  EDGAR     House
Trading Comps
PTA
SOTP
M&A
Accretion/Dilution
  |
  v
PostgreSQL
```

Financial calculations must remain separate from the frontend and database access layers.

---

# Data Sources

The platform should use the highest-authority available source for each datapoint.

## Primary Sources

### United States

- SEC EDGAR
- SEC Company Submissions
- SEC XBRL / Company Facts
- SEC filings

### United Kingdom

- Companies House
- Company accounts
- Company filings
- Confirmation statements
- Relevant official registers

### Canada

- SEDAR+

### Europe

- Eurostat
- Relevant national company registries
- Official securities regulators
- Official company filings

### Macroeconomic Data

- Federal Reserve FRED
- World Bank Open Data
- IMF
- ECB Statistical Data
- Eurostat

### Company Sources

- Company investor relations websites
- Annual reports
- Earnings releases
- Investor presentations
- Regulatory announcements

## Secondary Sources

Secondary sources may be used for market data, cross-checking and filling gaps where appropriate.

Potential sources include:

- Google Finance
- Macrotrends
- Other reputable market-data providers

Secondary sources should not automatically override authoritative filings or official datasets.

The application must respect the terms, licensing requirements, rate limits and access restrictions of every external data provider.

---

# Data Quality Principles

The platform must never fabricate financial data.

Every financial datapoint should contain:

- Value
- Unit
- Currency
- Period start
- Period end
- Publication date
- Retrieval timestamp
- Source
- Source URL
- Source document
- Data type
- Confidence
- Notes

Data types:

```text
REPORTED
DERIVED
ASSUMPTION
ESTIMATE
```

If information cannot be found, display:

```text
Data unavailable
```

The system should explain which sources were searched.

Users should be able to manually enter assumptions where appropriate.

Manual assumptions must always be clearly labelled.

---

# Company Identification

The system should resolve companies from:

- Company name
- Ticker
- ISIN
- Legal entity name
- Exchange
- CIK
- Companies House number
- SEDAR+ identifier
- LEI where available
- Other relevant jurisdiction-specific identifiers

If multiple companies match the user's search, the system should present the possible matches and allow the user to select the correct company.

---

# Financial Statement Normalisation

The platform should create a standard financial schema across different companies and jurisdictions.

Normalise:

- Revenue
- COGS
- Gross profit
- Operating expenses
- EBITDA
- EBIT
- D&A
- Operating income
- Interest expense
- Pre-tax income
- Tax
- Net income
- Cash
- Cash equivalents
- Total debt
- Current debt
- Long-term debt
- Lease liabilities
- Minority interest
- Preferred equity
- Total equity
- Capital expenditure
- Working capital
- Operating cash flow
- Free cash flow
- Shares outstanding

Support:

- Annual data
- Quarterly data
- TTM data
- Latest fiscal year
- Latest reported quarter

The system must correctly handle different fiscal year ends.

---

# Valuation Models

The platform should contain independent financial modelling modules.

## 1. Discounted Cash Flow

Calculate:

- Revenue
- EBITDA
- EBIT
- Taxes
- NOPAT
- D&A
- Capex
- Change in working capital
- Free cash flow
- Discount factors
- Terminal value
- Present value of FCF
- Present value of terminal value
- Enterprise value
- Net debt
- Equity value
- Shares outstanding
- Implied share price

Provide:

- Bear case
- Base case
- Bull case

Provide sensitivity tables for:

- WACC vs terminal growth
- Revenue growth vs EBITDA margin

---

# 2. Comparable Companies Analysis

Allow the system to identify potential comparable companies.

Users must be able to manually add and remove companies.

Calculate:

- EV/Revenue
- EV/EBITDA
- EV/EBIT
- P/E
- Price/Book
- EV/FCF where appropriate

Calculate:

- Mean
- Median
- 25th percentile
- 75th percentile

Apply selected multiples to the target company.

Output:

- Implied enterprise value
- Implied equity value
- Implied share price

Automated comparable-company selection should always be treated as a suggestion rather than an unquestionable conclusion.

---

# 3. Precedent Transaction Analysis

Create a transaction database.

For each transaction capture:

- Target
- Acquirer
- Announcement date
- Completion date
- Transaction value
- Enterprise value
- Equity value
- Revenue
- EBITDA
- EBIT
- EV/Revenue
- EV/EBITDA
- Premium
- Sector
- Geography
- Transaction type

Allow users to select transactions for analysis.

Calculate valuation ranges.

---

# 4. Leveraged Buyout Analysis

Build a simplified LBO model.

Inputs:

- Entry enterprise value
- Entry EBITDA
- Entry multiple
- Debt financing
- Equity financing
- Interest rate
- Mandatory amortisation
- Optional debt repayment
- Exit EBITDA
- Exit multiple
- Holding period
- Tax rate
- Fees
- Management rollover

Calculate:

- Sources & Uses
- Debt schedule
- Interest expense
- Cash available for debt repayment
- Debt paydown
- Exit enterprise value
- Exit equity value
- Sponsor equity
- MOIC
- IRR

Provide sensitivity tables for:

- Entry multiple
- Exit multiple
- Leverage
- EBITDA growth

---

# 5. Sum-of-the-Parts Analysis

Allow users to divide a company into business segments.

For each segment:

- Revenue
- EBITDA
- EBIT
- Growth
- Margin
- Selected valuation multiple

Calculate:

- Segment enterprise value
- Corporate costs
- Net debt
- Other adjustments
- Equity value
- Implied per-share value

---

# 6. M&A Deal Model

Build an acquisition model for completed or historical transactions.

Inputs:

- Acquirer
- Target
- Announcement date
- Purchase price
- Equity purchase price
- Enterprise value
- Cash consideration
- Stock consideration
- Debt financing
- New equity
- Existing cash
- Refinancing
- Transaction fees
- Synergies
- Tax rate
- Acquirer shares
- Target shares

Calculate:

- Sources & Uses
- Purchase price
- Financing mix
- New debt
- New equity
- Pro forma ownership
- Synergies
- Pro forma EBITDA
- Pro forma EPS
- Accretion/dilution
- Debt/EBITDA
- Interest coverage

Where sufficient information is available, calculate:

- Year 1
- Year 2
- Year 3

accretion/dilution.

---

# 7. Accretion / Dilution

Calculate:

- Standalone acquirer EPS
- Pro forma EPS
- EPS change
- Accretion/dilution percentage

Support:

- 100% cash transactions
- 100% stock transactions
- Mixed consideration transactions

Create an earnings bridge:

```text
Acquirer standalone earnings
+
Target earnings
+
After-tax synergies
-
Incremental interest expense
-
New share dilution
=
Pro forma earnings
```

---

# 8. Macroeconomic Data

Integrate relevant data from:

- FRED
- World Bank
- IMF
- ECB
- Eurostat

Potential metrics:

- GDP
- GDP growth
- Inflation
- Interest rates
- Government bond yields
- Unemployment
- Central bank rates
- FX rates
- Commodity data where available

Macroeconomic information can support:

- WACC assumptions
- Cost of debt
- Terminal growth assumptions
- FX conversion
- Scenario analysis

The application should show the underlying macroeconomic assumption rather than silently changing a model input.

---

# 9. Market Data

Retrieve where legally and technically available:

- Current share price
- Historical share price
- Market capitalisation
- Shares outstanding
- 52-week high
- 52-week low
- Trading volume
- Enterprise value

Calculate:

- Equity value
- Enterprise value
- Net debt
- Market-based multiples

Market data must have a timestamp.

---

# 10. Investor Relations and Document Processing

The platform should eventually process:

- Annual reports
- 10-K
- 10-Q
- 20-F
- 6-K
- 8-K
- UK annual reports
- Canadian filings
- Investor presentations
- Earnings releases

Extract relevant information such as:

- Revenue
- EBITDA
- Guidance
- Segment information
- Debt
- Cash
- Capex
- Management commentary
- Synergies
- Transaction information

Every extracted datapoint must retain its document source and location.

---

# Latest Data Engine

The system should always attempt to use the latest available information.

For each datapoint store:

```text
effective_date
published_date
retrieved_at
```

The system should:

1. Identify the latest available reporting period.
2. Identify the publication date.
3. Compare it with stored information.
4. Update when newer information is available.
5. Preserve historical versions.
6. Detect restatements.
7. Avoid overwriting historical data.

Do not simply overwrite old financial data.

---

# User Interface

The application should have a professional financial-analysis interface.

Main navigation:

```text
Overview
Financials
Market Data
Trading Comps
Deal Comps
DCF
LBO
SOTP
M&A
Accretion / Dilution
Macro
Sources
```

The homepage should contain:

```text
Search company, ticker or identifier
```

After selecting a company, show:

Company Name
Ticker
Exchange
Sector
Industry
Market capitalisation
Enterprise value
Share price
Revenue
EBITDA
EBIT
Net income
Free cash flow
Net debt
Valuation Summary
Display:
Current share price
DCF implied value
Trading comps range
Precedent transaction range
LBO value
SOTP value

Show the percentage difference between market price and each model-implied value.

Use neutral descriptions such as:

Below model-implied value

or:

Above model-implied value

The platform should not present a valuation model as a guaranteed prediction.

Show the assumptions driving each result.

Data Provenance

Every material financial number must be traceable.

Users should be able to see:

Value
Source
Document
Reporting period
Publication date
Retrieval date
Currency
Unit
Data type

Example:

Revenue: $Xbn

Source: SEC
Document: 10-K
Period: FY2025
Published: YYYY-MM-DD
Retrieved: YYYY-MM-DD
Type: REPORTED

Data Validation

Implement automated validation.

Examples:

Assets = Liabilities + Equity

where applicable.

Enterprise value should reconcile appropriately with:

Equity Value

- Debt
- Preferred Equity
- Minority Interest

* Cash

Flag:

Currency mismatches

Period mismatches

Duplicate filings

Restated financial statements

Missing values

Unit mismatches

Negative denominators

Zero denominators

Suspicious results

Conflicting sources

Security

Never hard-code:

API keys

Passwords

Database credentials

Authentication tokens

Use environment variables.

Provide:

.env.example

Never commit .env.

Include an appropriate .gitignore.

Testing

Every financial calculation must have automated tests.

Test:

DCF

WACC

Terminal value

Enterprise value

Equity value

EV/EBITDA

EV/Revenue

P/E

LBO IRR

LBO MOIC

Debt paydown

Accretion/dilution

Cash consideration

Stock consideration

Mixed consideration

SOTP

Also create integration tests for data-source adapters.

Development Roadmap

The application must be developed incrementally.

Phase 1 — Foundation

Development environment

Repository structure

Database schema

Source adapter interfaces

Company identification

SEC EDGAR integration

Financial data normalisation

Phase 2 — Core Valuation

DCF engine

DCF tests

Trading comparable engine

Trading comparable tests

Valuation dashboard

Phase 3 — Transaction Analysis

Transaction database

Precedent transactions

LBO model

SOTP model

Phase 4 — M&A

M&A deal model

Sources & Uses

Financing mix

Synergy analysis

Accretion/dilution

Post-merger ownership

Phase 5 — Global Data

Companies House

SEDAR+

European registries

Eurostat

FRED

World Bank

IMF

ECB

Phase 6 — Documents and Research

Investor relations ingestion

Filing/document processing

Document citations

AI-assisted research

Automated data updates

Phase 7 — Production

Full test suite

Security review

Performance optimisation

Docker deployment

Production deployment

Critical Development Rules

Do not build the entire application at once.

Before implementing a major component:

Inspect the existing repository.

Explain the proposed architecture.

Identify dependencies.

Identify external APIs required.

Implement the smallest working version.

Write tests.

Run the tests.

Fix errors.

Document the component.

Only then move to the next component.

Do not create fake API responses and present them as real financial data.

Do not invent financial values.

Do not silently make assumptions.

Do not mix database logic, financial calculations and UI logic.

Keep financial models independently testable.

Prioritise:

Data accuracy

Source traceability

Financial calculation correctness

Reproducibility

Security

Testing

Performance

UI design

The first working version should focus on:

Company Search
↓
Company Identification
↓
SEC EDGAR
↓
Financial Data
↓
PostgreSQL
↓
DCF Engine
↓
Valuation Dashboard
